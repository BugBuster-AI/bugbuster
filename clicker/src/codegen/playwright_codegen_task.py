"""Celery: генерация Playwright JS (LLM + проверка фрагментов через Microsoft Playwright MCP), финализация в backend API."""
from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import logging
import os
import re
import tempfile
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union, cast
from uuid import UUID

import httpx
from langchain_core.messages import BaseMessage
from langfuse import get_client
from langfuse.langchain import CallbackHandler
from langfuse.types import TraceContext
from sqlalchemy import select

from codegen.browser_validate import (
    legacy_runner_ready,
    mcp_runner_ready,
    node_runner_ready,
    run_js_prefix_with_failshot_ex,
    USE_PLAYWRIGHT_MCP,
)
from codegen.effective_browser import mcp_browser_from_environment
from codegen.case_steps import (
    api_step_to_js,
    attach_run_steps,
    effective_step_uid,
    flatten_case_with_run_indices,
    nl_for_codegen,
    nl_hash_vectors,
)
from codegen.case_viewport import viewport_for_case
from codegen.codegen_limits import (
    CODEGEN_USE_VLM_STEP_HTML,
    CODEGEN_VLM_RUN_LOG,
    CODEGEN_VLM_TRACE_GLOBAL_SUMMARY,
    MAX_VLM_BEFORE_FULL_HTML_CHARS,
    MAX_VLM_FOCUSED_DOM_PROMPT_CHARS,
)
from codegen.js_fragment_await import (
    _collect_declared_bindings,
    dedupe_const_declarations,
    normalize_playwright_await_fragment,
)
from codegen.llm_prompts import format_vlm_run_step_context, prior_scenario_steps_block
from codegen.llm_steps import (
    PROMPT_VERSION,
    _langfuse_codegen_run_name,
    extract_mcp_waiting_chain,
    extract_wait_chain_anchor_first_segment,
    infer_step_uid_for_playwright_timeout,
    generate_action_fragment,
    meta_profile,
    repair_action_fragment,
    repair_expected_result_fragment_maybe_targeted,
    rewrite_js_fragment_get_by_test_id_to_data_attr,
)
from codegen.vlm_trace_excerpt import (
    download_run_log_excerpt,
    download_run_trace_zip_bytes,
    extract_trace_hint_from_excerpt,
    global_trace_compact_summary,
    refine_trace_excerpt_for_step,
    segment_trace_for_flat,
)
from codegen.vlm_step_dom_artifacts import (
    download_focus_dom_by_run_path,
    download_focus_dom_json_text_from_run_step,
    download_full_html_by_run_path,
    download_full_html_from_run_step,
    focused_json_to_llm_text,
)
from core.config import (
    BACKEND_BASE_URL,
    CODEGEN_AGENT_API_KEY,
    CODEGEN_AGENT_BASE_URL,
    CODEGEN_AGENT_MODEL_NAME,
    SECRET_KEY_API,
)
from core.utils import get_image_base64, upload_bytes_to_minio
from infra.db import RunCase, async_session


class CodegenLangfuseCallbackHandler(CallbackHandler):
    """Langfuse: codegen LLM через on_chat_model_start как step (VLM action); repair под draft; полный prompt."""

    def __init__(self, *, public_key: Optional[str] = None) -> None:
        super().__init__(public_key=public_key)
        self.last_llm_parent_trace_context: Optional[TraceContext] = None
        self.draft_generation_trace_context: Optional[TraceContext] = None
        self._phase_by_run_id: Dict[UUID, Optional[str]] = {}
        self._armed_repair_attempt: Optional[int] = None

    def reset_for_nl_step(self) -> None:
        """Перед draft нового NL-шага: сброс контекста draft для вложенности repair."""
        self.draft_generation_trace_context = None
        self._armed_repair_attempt = None

    def begin_repair_llm(self, repair_round: int) -> None:
        """Вызывать сразу перед repair_action_fragment; repair_round — 1,2,… (первый repair = 1)."""
        self._armed_repair_attempt = int(repair_round)

    def end_repair_llm(self) -> None:
        self._armed_repair_attempt = None

    def _flatten_lc_message_dicts(self, messages: List[List[BaseMessage]]) -> List[Any]:
        """Как Langfuse __on_llm_action для chat: полные message dict (текст, image_url, HTML)."""
        return [
            item
            for row in [self._create_message_dicts(m) for m in messages]
            for item in row
        ]

    def on_chat_model_start(
        self,
        serialized: Optional[Dict[str, Any]],
        messages: List[List[BaseMessage]],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Any:
        meta = dict(metadata or {})
        phase_any = meta.get("codegen_llm_phase")
        phase: Optional[str] = phase_any if isinstance(phase_any, str) else None
        if phase is None and self._armed_repair_attempt is not None:
            phase = "repair"
            meta = {**meta, "repair_attempt": self._armed_repair_attempt}
        self._phase_by_run_id[run_id] = phase

        kw = dict(kwargs)
        tk = meta.get("codegen_trace_kind")
        trace_kind = tk if isinstance(tk, str) and tk.strip() else "step"
        if phase == "draft":
            kw["name"] = _langfuse_codegen_run_name(
                phase="draft",
                vlm_action=meta.get("vlm_action"),
                trace_kind=trace_kind,
            )
        elif phase == "repair":
            kw["name"] = _langfuse_codegen_run_name(
                phase="repair",
                vlm_action=meta.get("vlm_action"),
                repair_round=meta.get("repair_attempt"),
                trace_kind=trace_kind,
            )

        prompt_flat = cast(List[Any], self._flatten_lc_message_dicts(messages))

        if phase == "repair" and self.draft_generation_trace_context:
            return self._codegen_llm_start_repair_under_draft(
                serialized,
                run_id,
                prompt_flat,
                parent_run_id,
                tags,
                metadata,
                **kw,
            )
        return super().on_chat_model_start(
            serialized,
            messages,
            run_id=run_id,
            parent_run_id=parent_run_id,
            tags=tags,
            metadata=metadata,
            **kw,
        )

    def _codegen_llm_start_repair_under_draft(
        self,
        serialized: Optional[Dict[str, Any]],
        run_id: UUID,
        prompt_flat: List[Any],
        parent_run_id: Optional[UUID],
        tags: Optional[List[str]],
        metadata: Optional[Dict[str, Any]],
        **kwargs: Any,
    ) -> None:
        """Как Langfuse __on_llm_action, но generation с parent = draft; input — те же dict, что у chat."""
        tools = kwargs.get("invocation_params", {}).get("tools", None)
        plist: List[Any] = list(prompt_flat)
        if tools and isinstance(tools, list):
            plist.extend([{"role": "tool", "content": tool} for tool in tools])

        model_name = self._parse_model_and_log_errors(
            serialized=serialized, metadata=metadata, kwargs=kwargs
        )
        registered_prompt = self.prompt_to_parent_run_map.get(parent_run_id, None)

        if registered_prompt:
            self._deregister_langfuse_prompt(parent_run_id)

        content: Dict[str, Any] = {
            "name": kwargs.get("name") or self.get_langchain_run_name(serialized, **kwargs),
            "input": plist,
            "metadata": self._LangchainCallbackHandler__join_tags_and_metadata(tags, metadata),
            "model": model_name,
            "model_parameters": self._parse_model_parameters(kwargs),
            "prompt": registered_prompt,
        }

        ctx = self.draft_generation_trace_context
        assert ctx is not None
        self.runs[run_id] = self.client.start_generation(
            trace_context=ctx,
            **content,
        )
        self.last_trace_id = self.runs[run_id].trace_id

    def on_llm_end(
        self,
        response: Any,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> Any:
        gen = self.runs.get(run_id)
        phase = self._phase_by_run_id.get(run_id)
        super().on_llm_end(response, run_id=run_id, parent_run_id=parent_run_id, **kwargs)
        self._phase_by_run_id.pop(run_id, None)
        if gen is not None:
            try:
                ctx: TraceContext = {
                    "trace_id": gen.trace_id,
                    "parent_span_id": gen.id,
                }
                self.last_llm_parent_trace_context = ctx
                if phase == "draft":
                    self.draft_generation_trace_context = {
                        "trace_id": gen.trace_id,
                        "parent_span_id": gen.id,
                    }
            except Exception:
                self.last_llm_parent_trace_context = None
        return None

    def on_llm_error(
        self,
        error: BaseException,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> Any:
        self._phase_by_run_id.pop(run_id, None)
        return super().on_llm_error(error, run_id=run_id, parent_run_id=parent_run_id, **kwargs)


logger = logging.getLogger("clicker")

SKIP_BROWSER_VALIDATE = os.getenv("CODEGEN_SKIP_BROWSER_VALIDATE", "0").strip() in ("1", "true", "yes")

CODEGEN_MAX_VALIDATION_ATTEMPTS_CAP = 20
# Не кладём в Redis гигантские JPEG failshot (page.screenshot / редкий fallback MCP; типично ~50–400 KB).
_MAX_FAILSHOT_LOG_BYTES = 600_000


async def _failshot_minio_ref(run_id: str, path: Path) -> Optional[Dict[str, str]]:
    """Загружает failshot JPEG в MinIO; в API лог уходит только {bucket, file}."""
    if not path.is_file():
        return None
    try:
        data = path.read_bytes()
        if not data or len(data) > _MAX_FAILSHOT_LOG_BYTES:
            return None
        rel = f"codegen/screenshots/{uuid.uuid4().hex}.jpg"
        return await asyncio.to_thread(
            upload_bytes_to_minio,
            data,
            run_id,
            rel,
            "image/jpeg",
        )
    except OSError:
        return None


def _clamp_max_validation_attempts(raw: Union[int, str, None]) -> int:
    default = 10
    if raw is None:
        return default
    try:
        n = int(raw)
    except (TypeError, ValueError):
        return default
    return max(1, min(CODEGEN_MAX_VALIDATION_ATTEMPTS_CAP, n))


# Placeholders {{var}} in NL for codegen (same token class as backend substitute_variables_in_case).
_PLACEHOLDER_VAR_RE = re.compile(r"\{\{\s*([A-Za-z0-9_$.-]+)\s*\}\}")
# Valid JS identifier for const bindings (must match ТЗ).
_JS_IDENT_RE = re.compile(r"^[A-Za-z_$][A-Za-z0-9_$]*$")


def _is_resolved_variable_value(val: Any) -> bool:
    """False for missing, empty, and backend placeholder string 'undefined'."""
    if val is None:
        return False
    s = str(val).strip()
    if not s:
        return False
    if s.lower() == "undefined":
        return False
    return True


def _collect_variables_map_from_run_steps(run_steps: Optional[List[Any]]) -> Dict[str, str]:
    """First occurrence wins (same run_id). Values from run_cases.steps[].extra.variables[]."""
    out: Dict[str, str] = {}
    for step in run_steps or []:
        if not isinstance(step, dict):
            continue
        extra = step.get("extra")
        if not isinstance(extra, dict):
            continue
        vars_list = extra.get("variables")
        if not isinstance(vars_list, list):
            continue
        for v in vars_list:
            if not isinstance(v, dict):
                continue
            raw_name = v.get("name")
            if raw_name is None or not str(raw_name).strip():
                continue
            name = str(raw_name).strip()
            if name in out:
                continue
            val = v.get("value")
            if val is None:
                s = ""
            else:
                s = str(val)
            if not _is_resolved_variable_value(s):
                continue
            out[name] = s
    return out


def _placeholders_in_nl(nl: str) -> Set[str]:
    return {m.group(1) for m in _PLACEHOLDER_VAR_RE.finditer(nl or "")}


def _collect_used_variable_names_from_flat(flat: List[Dict[str, Any]]) -> Set[str]:
    used: Set[str] = set()
    for item in flat:
        nl = nl_for_codegen(item)
        used |= _placeholders_in_nl(nl)
    return used


def _read_captured_value_for_read_step(run_step: Optional[dict], name: str) -> Optional[str]:
    """
    Значение, прочитанное на READ-шаге эталонного прогона (для подсказки LLM и для const-преамбулы на других шагах).
    Не использовать строку-плейсхолдер 'undefined' из подстановки справочника.
    """
    if not run_step or not isinstance(run_step, dict):
        return None
    extra = run_step.get("extra")
    if isinstance(extra, dict):
        vars_list = extra.get("variables")
        if isinstance(vars_list, list):
            for v in vars_list:
                if not isinstance(v, dict):
                    continue
                if str(v.get("name") or "").strip() != name:
                    continue
                val = v.get("value")
                if val is None:
                    continue
                s = str(val).strip()
                if _is_resolved_variable_value(s):
                    return s
    ad = run_step.get("action_details")
    if isinstance(ad, dict):
        t = ad.get("text")
        if t is not None and _is_resolved_variable_value(str(t)):
            return str(t).strip()
        rt = ad.get("read_text")
        if rt is not None and _is_resolved_variable_value(str(rt)):
            return str(rt).strip()
    return None


def _validate_placeholder_identifiers(used_names: Set[str]) -> Tuple[Optional[str], Optional[str]]:
    """On failure: (bilingual message, reason_code). On success: (None, None)."""
    for name in sorted(used_names):
        if not _JS_IDENT_RE.match(name):
            token = "`{{" + name + "}}`"
            en = (
                f"Variable name {token} is not a valid JavaScript identifier for generated code. "
                "Rename the variable and retry generation."
            )
            ru = (
                f"Имя переменной {token} нельзя использовать в сгенерированном JavaScript-коде. "
                "Переименуйте переменную и повторите генерацию."
            )
            return (f"{en}\n{ru}", "codegen_variables_invalid_name")
    return (None, None)


def _step_variable_preamble_lines(
    prefix_js: str,
    item: Dict[str, Any],
    variables_map: Dict[str, str],
    literal_const_preamble_names: Set[str],
) -> Tuple[List[str], Optional[str], Optional[str]]:
    """
    const-строки из справочника (литерал) только для плейсхолдеров в NL этого шага.

    Одно и то же имя {{name}} часто встречается в нескольких шагах (TYPE / fill): литеральную
    строку `const name = "..."` вставляем не чаще одного раза на весь сценарий — см. literal_const_preamble_names.
    Имена из prefix_js (накопленный JS) и literal_const_preamble_names не дублируем.

    READ с {{name}}: преамбулу не вставляем — объявление во фрагменте.

    On failure: ([], bilingual message, reason_code).
    On success: (lines, None, None).
    """
    nl = nl_for_codegen(item)
    names = sorted(_placeholders_in_nl(nl))
    if not names:
        return ([], None, None)
    declared = _collect_declared_bindings(prefix_js)
    run_step = item.get("run_step")
    rs_action = str(run_step.get("action") or "") if isinstance(run_step, dict) else ""
    lines: List[str] = []
    for name in names:
        if name in declared:
            continue
        if name in literal_const_preamble_names:
            continue
        if rs_action == "READ" and name in _placeholders_in_nl(nl):
            continue
        val = variables_map.get(name)
        if not _is_resolved_variable_value(val):
            token = "`{{" + name + "}}`"
            en = (
                f"Failed to resolve variable {token} from the reference run for code generation. "
                "Check the test case variables and rerun the VLM run, or ensure the placeholder is filled."
            )
            ru = (
                f"Не удалось подставить значение переменной {token} из эталонного прогона для генерации кода. "
                "Проверьте переменные тест-кейса и повторите VLM-прогон."
            )
            return ([], f"{en}\n{ru}", "codegen_variables_unresolved")
        lines.append(f"  const {name} = {json.dumps(str(val).strip(), ensure_ascii=False)};")
        literal_const_preamble_names.add(name)
    return (lines, None, None)


def _step_block_for_mcp_run_after_preamble(step_uid: str, fragment: str) -> str:
    """
    Хвост шага для прогона в MCP: ``// step_uid`` + фрагмент LLM с отступом.
    Строки литеральной преамбулы (``const name = ...`` из справочника) сюда не входят: они уже
    включены в ``prior_js_with_step`` как ``prefix_for_validate + step_preamble_str``. Иначе в
    ``prior_js_with_step + block`` преамбула оказывается дважды подряд → SyntaxError: redeclaration.
    """
    lines: List[str] = [f"  // step_uid:{step_uid}"]
    for raw_ln in (fragment or "").strip().split("\n"):
        lines.append(f"  {raw_ln}".rstrip())
    return "\n".join(lines) + "\n"


def _read_capture_hint_for_llm(run_step: Optional[dict], nl: str) -> Optional[str]:
    """Подсказка для READ: одно значение по первому плейсхолдеру в NL, если оно известно из run."""
    if not run_step or not isinstance(run_step, dict):
        return None
    if str(run_step.get("action") or "") != "READ":
        return None
    ph = _placeholders_in_nl(nl)
    if not ph:
        return None
    for name in sorted(ph):
        v = _read_captured_value_for_read_step(run_step, name)
        if v is not None:
            return v
    return None


def _collect_nl_hash_vectors(case_json: dict, run_steps: Optional[List] = None) -> str:
    vectors = nl_hash_vectors(case_json, run_steps)
    raw = json.dumps(vectors, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _vlm_dom_prompts_for_step(
    run_id: str,
    step_uid: str,
    run_step: Optional[dict],
) -> Tuple[str, str]:
    """
    (focused_dom_llm_text, full_html_trimmed) для draft/repair.
    Пустые строки если выключено или артефактов нет.
    """
    if not CODEGEN_USE_VLM_STEP_HTML:
        return ("", "")
    jt = download_focus_dom_json_text_from_run_step(run_step)
    if not (jt or "").strip():
        jt = download_focus_dom_by_run_path(run_id, step_uid)
    focus = focused_json_to_llm_text(jt, MAX_VLM_FOCUSED_DOM_PROMPT_CHARS)
    full = download_full_html_from_run_step(run_step)
    if not (full or "").strip():
        full = download_full_html_by_run_path(run_id, step_uid)
    if full and len(full) > MAX_VLM_BEFORE_FULL_HTML_CHARS:
        full = full[:MAX_VLM_BEFORE_FULL_HTML_CHARS]
    return (focus, full)


def _vlm_coords_from_run_step(run_step: Optional[dict]) -> Optional[Any]:
    if not run_step or not isinstance(run_step, dict):
        return None
    ad = run_step.get("action_details")
    if isinstance(ad, dict) and ad.get("coords") is not None:
        return ad.get("coords")
    return None


def _case_entry_goto_lines(case_url: str) -> List[str]:
    """Первые исполняемые строки сценария: открыть URL из тест-кейса (как в MCP-прогоне до шагов)."""
    u = (case_url or "").strip()
    if not u or u == "about:blank":
        return []
    lit = json.dumps(u, ensure_ascii=False)
    return [
        "  // Navigate to URL from test case",
        f"  await page.goto({lit});",
    ]


def _finalize_source(
    body_lines: List[str],
    span_records: List[Tuple[str, int, int]],
    *,
    case_url: str,
    variable_preamble_lines: Optional[List[str]] = None,
) -> Tuple[str, list]:
    header = [
        "// Generated by Bugbuster codegen (LLM + Playwright validation).",
        "module.exports = async function runScenario(page) {",
        "  const context = page.context();",
        "  const request = context.request;",
    ]
    vpre = [ln for ln in (variable_preamble_lines or []) if ln is not None and str(ln).strip() != ""]
    nav_lines = _case_entry_goto_lines(case_url)
    footer = ["};"]
    all_lines = header + vpre + nav_lines + body_lines + footer
    offset = len(header) + len(vpre) + len(nav_lines)
    spans_out = []
    for step_uid, start, end in span_records:
        spans_out.append({"step_uid": step_uid, "start_line": start + offset, "end_line": end + offset})
    return "\n".join(all_lines) + "\n", spans_out


async def _screenshot_b64(run_step: Optional[dict], key: str) -> Optional[str]:
    if not run_step or not isinstance(run_step, dict):
        return None
    ref = run_step.get(key)
    if not ref:
        return None
    try:
        return await get_image_base64(minio_path=ref)
    except Exception as e:
        logger.warning("codegen: minio %s: %s", key, e)
        return None


async def _post_fail(client: httpx.AsyncClient, case_id: str, message: str, step_uid: Optional[str], code: str):
    await client.post(
        f"{BACKEND_BASE_URL}/api/internal/codegen/playwright/fail",
        json={"case_id": case_id, "message": message, "step_uid": step_uid, "reason_code": code},
        headers={"X-Internal-Token": SECRET_KEY_API},
    )


async def _notify_fail(case_id: str, message: str, step_uid: Optional[str], code: str = "codegen_step_failed"):
    async with httpx.AsyncClient(timeout=60.0) as client:
        await _post_fail(client, case_id, message, step_uid, code)


async def _emit_codegen_log(
    client: httpx.AsyncClient,
    case_id: str,
    run_id: str,
    message: str,
    *,
    level: str = "info",
    step_uid: Optional[str] = None,
    phase: Optional[str] = None,
    screenshot_minio: Optional[Dict[str, str]] = None,
):
    try:
        payload: Dict[str, Any] = {
            "case_id": str(case_id),
            "message": message,
            "level": level,
            "step_uid": step_uid,
            "phase": phase,
        }
        if screenshot_minio and screenshot_minio.get("bucket") and screenshot_minio.get("file"):
            payload["screenshot_minio"] = screenshot_minio
        await client.post(
            f"{BACKEND_BASE_URL}/api/internal/codegen/playwright/log",
            json=payload,
            headers={"X-Internal-Token": SECRET_KEY_API},
            timeout=120.0,
        )
    except Exception as e:
        logger.warning("codegen log append failed: %s", e)


_JS_LOG_CHUNK = 8000


async def _emit_codegen_log_js(
    client: httpx.AsyncClient,
    case_id: str,
    run_id: str,
    step_uid: str,
    label: str,
    js_text: str,
):
    """Log the full generated JS fragment (with all locators) into the user-facing generation log."""
    text = (js_text or "").strip()
    if not text:
        return
    if len(text) <= _JS_LOG_CHUNK:
        await _emit_codegen_log(
            client, case_id, run_id, f"{label}\n{text}",
            step_uid=step_uid, phase="generated_js",
        )
        return
    parts = [text[i:i + _JS_LOG_CHUNK] for i in range(0, len(text), _JS_LOG_CHUNK)]
    for idx, part in enumerate(parts, 1):
        await _emit_codegen_log(
            client, case_id, run_id, f"{label} (part {idx}/{len(parts)})\n{part}",
            step_uid=step_uid, phase="generated_js",
        )


def _langfuse_playwright_mcp_span(
    lf: Any,
    *,
    step_uid: str,
    attempt: Optional[int],
    phase: str,
    prefix_len: int,
    block_len: int,
    err: str,
    a11y: Optional[str],
    proc_io: Dict[str, Any],
    llm_parent_trace_context: Optional[TraceContext] = None,
) -> None:
    """Дочерний span: subprocess Node (Playwright MCP / legacy) — stdout/stderr и результат.

    Если передан llm_parent_trace_context (последняя ChatOpenAI-генерация), span вешается под неё, иначе — под текущий OTEL-контекст (например codegen).
    """
    try:
        runner = "playwright_mcp" if (USE_PLAYWRIGHT_MCP and mcp_runner_ready()) else "legacy_node"
        span_kw: Dict[str, Any] = {
            "name": "playwright_mcp",
            "input": {
                "step_uid": step_uid,
                "attempt": attempt,
                "phase": phase,
                "accumulated_prefix_js_chars": prefix_len,
                "step_block_js_chars": block_len,
                "runner": runner,
            },
            "metadata": {"component": "playwright_mcp"},
        }
        if llm_parent_trace_context is not None:
            span_kw["trace_context"] = llm_parent_trace_context
        with lf.start_as_current_span(**span_kw) as span:
            # При remote parent Langfuse помечает span AS_ROOT; UI может подставить его name как имя трейса.
            if llm_parent_trace_context is not None:
                try:
                    lf.update_current_trace(name="codegen")
                except Exception:
                    pass
            out: Dict[str, Any] = {
                "ok": not (err and err.strip()),
                "error_message": (err or None) if err else None,
                "stdout": proc_io.get("stdout"),
                "stderr": proc_io.get("stderr"),
                "returncode": proc_io.get("returncode"),
            }
            if a11y and str(a11y).strip():
                out["a11y_snapshot_excerpt"] = str(a11y)[:8000]
            if err and str(err).strip():
                span.update(
                    level="ERROR",
                    status_message=str(err)[:2000],
                    output=out,
                )
            else:
                span.update(output=out)
    except Exception as e:
        logger.warning("langfuse playwright_mcp span: %s", e)


def _mark_codegen_span_failed(
    codegen_span: Any,
    *,
    step_uid: Optional[str],
    phase: str,
    error_message: str,
    proc_io: Optional[Dict[str, Any]] = None,
) -> None:
    """Пометить корневой span codegen как ERROR в Langfuse, если артефакт не ушёл в finalize (MCP, исчерпание попыток, HTTP finalize, исключение)."""
    msg = (error_message or "").strip()
    if len(msg) > 4000:
        msg = msg[:4000] + "…"
    out: Dict[str, Any] = {
        "status": "failed",
        "phase": phase,
        "error_message": msg,
        "artifact_delivered": False,
    }
    if step_uid is not None:
        out["step_uid"] = step_uid
    if proc_io is not None:
        out["returncode"] = proc_io.get("returncode")
    try:
        codegen_span.update(
            level="ERROR",
            status_message=msg[:2000] if msg else "codegen failed before finalize",
            output=out,
        )
    except Exception as e:
        logger.warning("langfuse codegen span error mark: %s", e)


def _classify_codegen_exception(exc: Exception) -> Tuple[str, str]:
    """Return (user_message, reason_code) for a codegen-level exception."""
    cls_name = type(exc).__name__
    raw = str(exc) or repr(exc)

    if "APIConnectionError" in cls_name or "ConnectError" in cls_name:
        return (
            f"Failed to connect to the LLM provider: {raw}",
            "codegen_llm_connection_error",
        )
    if "APITimeoutError" in cls_name or "ReadTimeout" in cls_name or "TimeoutException" in cls_name:
        return (
            f"LLM request timed out: {raw}",
            "codegen_llm_timeout",
        )
    if "RateLimitError" in cls_name:
        return (
            f"LLM rate limit exceeded: {raw}",
            "codegen_llm_rate_limit",
        )
    if "AuthenticationError" in cls_name:
        return (
            f"LLM authentication failed: {raw}",
            "codegen_llm_auth_error",
        )
    return (raw, "codegen_exception")


async def run_playwright_codegen_async(
    *,
    case_id: str,
    run_id: str,
    user_id: str,
    workspace_id: str,
    task_id: str,
    max_validation_attempts: Union[int, str, None] = None,
):
    max_attempts = _clamp_max_validation_attempts(max_validation_attempts)
    if not SECRET_KEY_API:
        logger.error("SECRET_KEY_API is empty; cannot call backend internal codegen API")
        return
    if not CODEGEN_AGENT_BASE_URL or not CODEGEN_AGENT_API_KEY:
        logger.error("CODEGEN_AGENT / INFERENCE base URL or API key not configured")
        await _notify_fail(
            case_id,
            "Inference API is not configured for codegen (CODEGEN_AGENT_* / INFERENCE_*).",
            None,
            "codegen_config",
        )
        return

    async with async_session() as session:
        async with session.begin():
            q = await session.execute(select(RunCase).where(RunCase.run_id == UUID(run_id)))
            run_row = q.scalars().one_or_none()
            if not run_row:
                logger.error("codegen: run %s not found", run_id)
                return
            ver = run_row.current_case_version or {}
            if str(ver.get("case_id")) != str(case_id):
                logger.error("codegen: case mismatch")
                return
            run_steps = run_row.steps if isinstance(run_row.steps, list) else []

    if not SKIP_BROWSER_VALIDATE and not node_runner_ready():
        msg = (
            "Codegen browser runner is not installed (codegen/node_runner: npm install; "
            "validation needs @playwright/mcp and @modelcontextprotocol/sdk — see https://github.com/microsoft/playwright-mcp). "
            "Set CODEGEN_SKIP_BROWSER_VALIDATE=1 to bypass (not recommended)."
        )
        logger.error(msg)
        await _notify_fail(case_id, msg, None, "codegen_node_runner_missing")
        return

    async with httpx.AsyncClient(timeout=30.0) as log_client:
        await _emit_codegen_log(
            log_client,
            case_id,
            run_id,
            "Starting Playwright JS generation; fragment validation via Microsoft Playwright MCP (@playwright/mcp).",
            phase="start",
        )

    start_url = str(ver.get("url") or "about:blank")
    vw, vh = viewport_for_case(ver)
    mcp_browser = mcp_browser_from_environment(ver.get("environment"))
    flat = flatten_case_with_run_indices(ver)
    attach_run_steps(flat, run_steps)
    if run_steps and len(flat) != len(run_steps):
        logger.warning(
            "codegen: len(flat case steps)=%s != len(run_cases.steps)=%s — "
            "VLM/codegen alignment may be wrong (merge shared steps in case JSON?).",
            len(flat),
            len(run_steps),
        )
    for item in flat:
        item["step_uid"] = effective_step_uid(item)
    content_hash = _collect_nl_hash_vectors(ver, run_steps)

    variables_map = _collect_variables_map_from_run_steps(run_steps)
    used_variable_names = _collect_used_variable_names_from_flat(flat)
    v_err, v_code = _validate_placeholder_identifiers(used_variable_names)
    if v_err:
        async with httpx.AsyncClient(timeout=30.0) as log_client:
            await _emit_codegen_log(
                log_client,
                case_id,
                run_id,
                v_err,
                level="error",
                phase="variables",
            )
        await _notify_fail(case_id, v_err, None, v_code or "codegen_variables_unresolved")
        return

    trace_by_uid: Dict[str, str] = {}
    trace_compact_index: List[Tuple[int, str]] = []
    trace_bounds_by_uid: Dict[str, Optional[Tuple[int, int]]] = {}
    global_trace_summary = ""
    vlm_log_excerpt = ""
    zip_bytes: Optional[bytes] = None
    if os.getenv("CODEGEN_VLM_TRACE_EXCERPT", "1").strip().lower() not in ("0", "false", "no"):
        zip_bytes = await asyncio.to_thread(download_run_trace_zip_bytes, run_id)
        if zip_bytes:
            trace_by_uid, trace_compact_index, trace_bounds_by_uid = segment_trace_for_flat(zip_bytes, flat)
            if trace_by_uid:
                logger.info("codegen: VLM Playwright trace excerpts for %s NL steps", len(trace_by_uid))
            if CODEGEN_VLM_TRACE_GLOBAL_SUMMARY:
                global_trace_summary = global_trace_compact_summary(zip_bytes)
                if global_trace_summary:
                    logger.info("codegen: global VLM trace summary %s chars", len(global_trace_summary))
    if CODEGEN_VLM_RUN_LOG:
        vlm_log_excerpt = await asyncio.to_thread(download_run_log_excerpt, run_id)
        if vlm_log_excerpt:
            logger.info("codegen: VLM run log excerpt %s chars", len(vlm_log_excerpt))

    body_lines: List[str] = []
    span_records: List[Tuple[str, int, int]] = []
    step_attempts_log: List[dict] = []
    prefix_for_validate = ""
    literal_const_preamble_names: Set[str] = set()
    _failshot_dir = Path(tempfile.gettempdir()) / f"codegen_{task_id}"
    _failshot_dir.mkdir(parents=True, exist_ok=True)
    failshot_path = _failshot_dir / "codegen_fail_step.jpg"

    lf = get_client()
    trace_id = lf.create_trace_id()
    langfuse_cb = CodegenLangfuseCallbackHandler()

    try:
        with lf.start_as_current_span(
            trace_context=TraceContext(trace_id=trace_id),
            name="codegen",
            input={
                "case_id": case_id,
                "run_id": run_id,
                "task_id": task_id,
                "user_id": user_id,
                "workspace_id": workspace_id,
                "max_validation_attempts": max_attempts,
            },
            metadata={"prompt_version": PROMPT_VERSION},
        ) as codegen_span:
            lf.update_current_trace(
                name="codegen",
                user_id=user_id,
                session_id=f"{case_id}:{run_id}",
                tags=["codegen"],
                metadata={
                    "case_id": case_id,
                    "run_id": run_id,
                    "task_id": task_id,
                    "workspace_id": workspace_id,
                },
            )
            try:
                async with httpx.AsyncClient(timeout=30.0) as log_client:
                    for idx, item in enumerate(flat):
                        kind = item["kind"]
                        uid = item["step_uid"]
    
                        if kind == "api":
                            await _emit_codegen_log(
                                log_client,
                                case_id,
                                run_id,
                                f"API step ({uid}): inject fetch and validate in the browser (Playwright MCP).",
                                step_uid=uid,
                                phase="api",
                            )
                            raw = item["raw"] if isinstance(item.get("raw"), dict) else {}
                            frag = api_step_to_js(raw, uid)
                            await _emit_codegen_log_js(
                                log_client, case_id, run_id, uid,
                                "Generated JS (API step):", frag,
                            )
                            idx0 = len(body_lines)
                            for ln in frag.rstrip("\n").split("\n"):
                                body_lines.append(ln)
                            idx1 = len(body_lines)
                            span_records.append((uid, idx0 + 1, idx1))
                            block = "\n".join(body_lines[idx0:idx1]) + "\n"
                            if not SKIP_BROWSER_VALIDATE:
                                err, snap_a11y, proc_io = await asyncio.to_thread(
                                    run_js_prefix_with_failshot_ex,
                                    prefix_body=prefix_for_validate + block,
                                    start_url=start_url,
                                    viewport_w=vw,
                                    viewport_h=vh,
                                    failshot_path=failshot_path,
                                    timeout_sec=180,
                                    browser=mcp_browser,
                                )
                                _langfuse_playwright_mcp_span(
                                    lf,
                                    step_uid=uid,
                                    attempt=None,
                                    phase="api_validate",
                                    prefix_len=len(prefix_for_validate),
                                    block_len=len(block),
                                    err=err,
                                    a11y=snap_a11y,
                                    proc_io=proc_io,
                                )
                                if err:
                                    await _emit_codegen_log(
                                        log_client,
                                        case_id,
                                        run_id,
                                        f"MCP: fragment execution failed: {err[:500]}",
                                        level="error",
                                        step_uid=uid,
                                        phase="validate",
                                        screenshot_minio=await _failshot_minio_ref(run_id, failshot_path),
                                    )
                                    _mark_codegen_span_failed(
                                        codegen_span,
                                        step_uid=uid,
                                        phase="api_validate",
                                        error_message=err,
                                        proc_io=proc_io,
                                    )
                                    await _notify_fail(case_id, err, uid)
                                    return
                                await _emit_codegen_log(
                                    log_client,
                                    case_id,
                                    run_id,
                                    "MCP: API fragment passed validation.",
                                    step_uid=uid,
                                    phase="validate_ok",
                                )
                            prefix_for_validate += block
                            continue

                        if kind not in ("action", "expected_result"):
                            continue

                        codegen_trace_kind = "expected_result" if kind == "expected_result" else "step"
                        mcp_validate_phase = "er_validate" if kind == "expected_result" else "nl_validate"

                        run_step = item.get("run_step")
                        before_b64 = await _screenshot_b64(run_step, "before")
                        after_b64 = await _screenshot_b64(run_step, "after")
                        nl = nl_for_codegen(item)
                        if kind == "expected_result" and not (nl or "").strip():
                            await _emit_codegen_log(
                                log_client,
                                case_id,
                                run_id,
                                f"Expected result step ({uid}): empty text — cannot generate assertions.",
                                level="error",
                                step_uid=uid,
                                phase="validate_fail",
                            )
                            _mark_codegen_span_failed(
                                codegen_span,
                                step_uid=uid,
                                phase="er_validate",
                                error_message="expected_result step has empty NL",
                                proc_io=None,
                            )
                            await _notify_fail(
                                case_id,
                                f"expected_result step_uid={uid} has empty description",
                                uid,
                            )
                            return

                        if kind == "expected_result":
                            await _emit_codegen_log(
                                log_client,
                                case_id,
                                run_id,
                                f"Expected result step ({uid}): requesting draft from the LLM…",
                                step_uid=uid,
                                phase="er_llm_draft",
                            )
                        else:
                            await _emit_codegen_log(
                                log_client,
                                case_id,
                                run_id,
                                f"NL step ({uid}): requesting draft from the LLM…",
                                step_uid=uid,
                                phase="llm_draft",
                            )
                        rs = run_step if isinstance(run_step, dict) else None
                        vlm_action = (
                            str(rs["action"])
                            if rs and rs.get("action") is not None
                            else None
                        )
                        prior_steps_text = prior_scenario_steps_block(flat[:idx])
                        base_trace = trace_by_uid.get(uid) or ""
                        vlm_trace_for_llm = refine_trace_excerpt_for_step(
                            nl,
                            rs,
                            base_trace,
                            trace_compact_index,
                            trace_bounds_by_uid.get(uid),
                        )
                        dom_focus_txt, dom_full_txt = _vlm_dom_prompts_for_step(run_id, uid, rs)
                        if dom_focus_txt:
                            logger.info(
                                "codegen: VLM focused DOM for step_uid=%s prompt_chars=%s full_html_chars=%s",
                                uid,
                                len(dom_focus_txt),
                                len(dom_full_txt),
                            )
                        langfuse_cb.reset_for_nl_step()
                        step_preamble_lines, step_var_err, step_var_code = _step_variable_preamble_lines(
                            prefix_for_validate,
                            item,
                            variables_map,
                            literal_const_preamble_names,
                        )
                        if step_var_err:
                            async with httpx.AsyncClient(timeout=30.0) as log_client:
                                await _emit_codegen_log(
                                    log_client,
                                    case_id,
                                    run_id,
                                    step_var_err,
                                    level="error",
                                    step_uid=uid,
                                    phase="variables",
                                )
                            await _notify_fail(
                                case_id, step_var_err, uid, step_var_code or "codegen_variables_unresolved"
                            )
                            return
                        step_preamble_str = (
                            "\n".join(step_preamble_lines) + "\n" if step_preamble_lines else ""
                        )
                        prior_js_with_step = prefix_for_validate + step_preamble_str
                        read_hint = _read_capture_hint_for_llm(rs, nl)
                        fragment = await generate_action_fragment(
                            step_uid=uid,
                            nl=nl,
                            base_url=start_url,
                            viewport_w=vw,
                            viewport_h=vh,
                            before_b64=before_b64,
                            after_b64=after_b64,
                            langchain_callbacks=[langfuse_cb],
                            vlm_trace_excerpt=vlm_trace_for_llm,
                            vlm_run_step_context=format_vlm_run_step_context(
                                rs, read_capture_hint=read_hint
                            ),
                            prior_steps_text=prior_steps_text,
                            prior_js_prefix=prior_js_with_step,
                            global_trace_summary=global_trace_summary or None,
                            vlm_run_log=vlm_log_excerpt or None,
                            vlm_focused_dom_before=dom_focus_txt or None,
                            vlm_before_full_html=dom_full_txt or None,
                            vlm_action=vlm_action,
                            codegen_trace_kind=codegen_trace_kind,
                        )
                        await _emit_codegen_log_js(
                            log_client, case_id, run_id, uid,
                            "Generated JS (draft):", fragment,
                        )
    
                        attempt_metas: List[dict] = []
                        last_err = ""
                        step_failed_wait_chains: List[str] = []
                        last_anchor_first: Optional[str] = None
                        anchor_same_streak = 0
    
                        for attempt in range(1, max_attempts + 1):
                            if attempt > 1:
                                if kind == "expected_result":
                                    await _emit_codegen_log(
                                        log_client,
                                        case_id,
                                        run_id,
                                        f"Expected result step ({uid}): repair round {attempt - 1}/{max_attempts - 1} after Playwright MCP error…",
                                        step_uid=uid,
                                        phase="er_llm_repair",
                                    )
                                else:
                                    await _emit_codegen_log(
                                        log_client,
                                        case_id,
                                        run_id,
                                        f"Repair round {attempt - 1}/{max_attempts - 1} after Playwright MCP error…",
                                        step_uid=uid,
                                        phase="llm_repair",
                                    )
                                fail_b64: Optional[str] = None
                                if failshot_path.is_file():
                                    try:
                                        fail_b64 = base64.b64encode(failshot_path.read_bytes()).decode("utf-8")
                                    except OSError:
                                        pass
                                a11y_text: Optional[str] = None
                                a11y_path = failshot_path.parent / (failshot_path.stem + ".a11y.txt")
                                if a11y_path.is_file():
                                    try:
                                        a11y_text = a11y_path.read_text(encoding="utf-8", errors="replace")
                                        if not (a11y_text or "").strip():
                                            a11y_text = None
                                    except OSError:
                                        a11y_text = None
                                page_html_text: Optional[str] = None
                                html_path = failshot_path.parent / (failshot_path.stem + ".page.html")
                                if html_path.is_file():
                                    try:
                                        page_html_text = html_path.read_text(encoding="utf-8", errors="replace")
                                        if not (page_html_text or "").strip():
                                            page_html_text = None
                                    except OSError:
                                        page_html_text = None
                                det_applied = False
                                if page_html_text:
                                    rew = rewrite_js_fragment_get_by_test_id_to_data_attr(
                                        fragment or "", page_html_text
                                    )
                                    if rew != (fragment or ""):
                                        fragment = rew
                                        det_applied = True
                                        await _emit_codegen_log(
                                            log_client,
                                            case_id,
                                            run_id,
                                            "Codegen: deterministic rewrite getByTestId→locator([data-*]) "
                                            "from page HTML (skipping LLM for this attempt).",
                                            step_uid=uid,
                                            phase="deterministic_rewrite",
                                        )
                                if not det_applied:
                                    th = extract_trace_hint_from_excerpt(vlm_trace_for_llm)
                                    anchor_must_change = anchor_same_streak >= 2
                                    langfuse_cb.begin_repair_llm(attempt - 1)
                                    try:
                                        if kind == "expected_result":
                                            fragment = await repair_expected_result_fragment_maybe_targeted(
                                                step_uid=uid,
                                                nl=nl,
                                                base_url=start_url,
                                                viewport_w=vw,
                                                viewport_h=vh,
                                                before_b64=before_b64,
                                                after_b64=after_b64,
                                                failure_screenshot_b64=fail_b64,
                                                previous_js=fragment,
                                                playwright_error=last_err,
                                                repair_attempt=attempt,
                                                max_validation_attempts=max_attempts,
                                                prior_failed_wait_chains=list(step_failed_wait_chains),
                                                accessibility_snapshot=a11y_text,
                                                langchain_callbacks=[langfuse_cb],
                                                vlm_coords=_vlm_coords_from_run_step(rs),
                                                trace_hint=th or None,
                                                anchor_must_change=anchor_must_change,
                                                anchor_first_hint=last_anchor_first,
                                                mcp_page_html=page_html_text,
                                                vlm_action=vlm_action,
                                            )
                                        else:
                                            fragment = await repair_action_fragment(
                                                step_uid=uid,
                                                nl=nl,
                                                base_url=start_url,
                                                viewport_w=vw,
                                                viewport_h=vh,
                                                before_b64=before_b64,
                                                after_b64=after_b64,
                                                failure_screenshot_b64=fail_b64,
                                                previous_js=fragment,
                                                playwright_error=last_err,
                                                repair_attempt=attempt,
                                                max_validation_attempts=max_attempts,
                                                prior_failed_wait_chains=list(step_failed_wait_chains),
                                                accessibility_snapshot=a11y_text,
                                                langchain_callbacks=[langfuse_cb],
                                                vlm_coords=_vlm_coords_from_run_step(rs),
                                                trace_hint=th or None,
                                                anchor_must_change=anchor_must_change,
                                                anchor_first_hint=last_anchor_first,
                                                mcp_page_html=page_html_text,
                                                vlm_action=vlm_action,
                                                codegen_trace_kind=codegen_trace_kind,
                                            )
                                    finally:
                                        langfuse_cb.end_repair_llm()
                                    await _emit_codegen_log_js(
                                        log_client, case_id, run_id, uid,
                                        f"Generated JS (repair round {attempt - 1}/{max_attempts - 1}):",
                                        fragment,
                                    )
                                else:
                                    await _emit_codegen_log_js(
                                        log_client, case_id, run_id, uid,
                                        f"Generated JS (repair round {attempt - 1}/{max_attempts - 1}, deterministic):",
                                        fragment,
                                    )
    
                            fragment = dedupe_const_declarations(
                                prior_js_with_step,
                                normalize_playwright_await_fragment((fragment or "").strip()),
                                extra_declared=set(literal_const_preamble_names),
                            )
                            idx0 = len(body_lines)
                            for ln in step_preamble_lines:
                                body_lines.append(ln.rstrip())
                            body_lines.append(f"  // step_uid:{uid}")
                            for raw_ln in fragment.strip().split("\n"):
                                body_lines.append(f"  {raw_ln}".rstrip())
                            idx1 = len(body_lines)
                            block = "\n".join(body_lines[idx0:idx1]) + "\n"
                            block_for_run = _step_block_for_mcp_run_after_preamble(uid, fragment)
                            attempt_metas.append(
                                meta_profile(
                                    phase="repair" if attempt > 1 else "draft",
                                    attempt=attempt,
                                    codegen_trace_kind=codegen_trace_kind,
                                )
                            )
    
                            if SKIP_BROWSER_VALIDATE:
                                span_records.append((uid, idx0 + 1, idx1))
                                prefix_for_validate += block
                                break
    
                            if kind == "expected_result":
                                await _emit_codegen_log(
                                    log_client,
                                    case_id,
                                    run_id,
                                    f"MCP: running accumulated scenario (expected result, attempt {attempt}/{max_attempts})…",
                                    step_uid=uid,
                                    phase="er_mcp_run",
                                )
                            else:
                                await _emit_codegen_log(
                                    log_client,
                                    case_id,
                                    run_id,
                                    f"MCP: running accumulated scenario (attempt {attempt}/{max_attempts})…",
                                    step_uid=uid,
                                    phase="mcp_run",
                                )
                            last_err, snap, proc_io = await asyncio.to_thread(
                                run_js_prefix_with_failshot_ex,
                                prefix_body=prior_js_with_step + block_for_run,
                                start_url=start_url,
                                viewport_w=vw,
                                viewport_h=vh,
                                failshot_path=failshot_path,
                                timeout_sec=180,
                                browser=mcp_browser,
                            )
                            _langfuse_playwright_mcp_span(
                                lf,
                                step_uid=uid,
                                attempt=attempt,
                                phase=mcp_validate_phase,
                                prefix_len=len(prior_js_with_step),
                                block_len=len(block_for_run),
                                err=last_err,
                                a11y=snap,
                                proc_io=proc_io,
                                llm_parent_trace_context=langfuse_cb.last_llm_parent_trace_context,
                            )
                            if not last_err:
                                # Post-validation deterministic rewrite (draft and repair):
                                # page HTML is now saved by MCP runner even on success.
                                _html_path = failshot_path.parent / (failshot_path.stem + ".page.html")
                                if _html_path.is_file():
                                    try:
                                        _ph = _html_path.read_text(encoding="utf-8", errors="replace")
                                    except OSError:
                                        _ph = ""
                                    if _ph.strip():
                                        _rew = rewrite_js_fragment_get_by_test_id_to_data_attr(
                                            fragment or "", _ph,
                                        )
                                        if _rew != (fragment or ""):
                                            fragment = _rew
                                            del body_lines[idx0:idx1]
                                            _chunk: List[str] = []
                                            for _pl in step_preamble_lines:
                                                _chunk.append(_pl.rstrip())
                                            _chunk.append(f"  // step_uid:{uid}")
                                            for _rl in fragment.strip().split("\n"):
                                                _chunk.append(f"  {_rl}".rstrip())
                                            for _j, _ln in enumerate(_chunk):
                                                body_lines.insert(idx0 + _j, _ln)
                                            idx1 = idx0 + len(_chunk)
                                            block = "\n".join(body_lines[idx0:idx1]) + "\n"
                                            await _emit_codegen_log(
                                                log_client,
                                                case_id,
                                                run_id,
                                                "Codegen: post-validation deterministic rewrite "
                                                "getByTestId\u2192locator([data-*]) from page HTML.",
                                                step_uid=uid,
                                                phase="deterministic_rewrite",
                                            )
                                await _emit_codegen_log(
                                    log_client,
                                    case_id,
                                    run_id,
                                    "MCP: fragment passed validation.",
                                    step_uid=uid,
                                    phase="validate_ok",
                                )
                                span_records.append((uid, idx0 + 1, idx1))
                                prefix_for_validate += block
                                break
    
                            _full_for_attr = prior_js_with_step + block_for_run
                            _timeout_uid = infer_step_uid_for_playwright_timeout(
                                full_script=_full_for_attr,
                                playwright_error=last_err,
                            )
                            _attr_note = ""
                            if _timeout_uid and _timeout_uid != uid:
                                _attr_note = (
                                    f" | timeout_locator_is_in_step_uid={_timeout_uid} "
                                    f"(codegen is repairing step_uid={uid} — the failing line is likely in another block)"
                                )
                            elif _timeout_uid and _timeout_uid == uid:
                                _attr_note = f" | timeout_locator_is_in_step_uid={_timeout_uid} (same as current step)"
                            await _emit_codegen_log(
                                log_client,
                                case_id,
                                run_id,
                                f"MCP: error: {last_err[:500]}{_attr_note}",
                                level="warning",
                                step_uid=uid,
                                phase="validate_fail",
                                screenshot_minio=await _failshot_minio_ref(run_id, failshot_path),
                            )
                            wchain = extract_mcp_waiting_chain(last_err)
                            if wchain and wchain not in step_failed_wait_chains:
                                step_failed_wait_chains.append(wchain)
                            a_first = extract_wait_chain_anchor_first_segment(wchain)
                            if a_first:
                                if a_first == last_anchor_first:
                                    anchor_same_streak += 1
                                else:
                                    last_anchor_first = a_first
                                    anchor_same_streak = 1
                            else:
                                last_anchor_first = None
                                anchor_same_streak = 0
                            del body_lines[idx0:idx1]
                            if attempt == max_attempts:
                                _tu = infer_step_uid_for_playwright_timeout(
                                    full_script=prior_js_with_step + block_for_run,
                                    playwright_error=last_err,
                                )
                                _hint = (
                                    "Playwright reports the first timed-out locator in the full run (prefix + current block)."
                                )
                                if _tu and _tu != uid:
                                    _hint += (
                                        f" Inferred: that locator appears under step_uid={_tu}, not the current "
                                        f"codegen step_uid={uid} — fix or stabilize the earlier step, not only this one."
                                    )
                                elif _tu and _tu == uid:
                                    _hint += f" Inferred: timeout is in the current step block (step_uid={_tu})."
                                fail_msg = f"{last_err} (codegen step_uid={uid}, repair attempts exhausted). {_hint}"
                                _mark_codegen_span_failed(
                                    codegen_span,
                                    step_uid=uid,
                                    phase=mcp_validate_phase,
                                    error_message=fail_msg,
                                    proc_io=proc_io,
                                )
                                await _notify_fail(
                                    case_id,
                                    fail_msg,
                                    uid,
                                )
                                return
    
                        step_attempts_log.append(
                            {"step_uid": uid, "attempts": attempt_metas, "step_kind": kind}
                        )
    
                src, spans = _finalize_source(
                    body_lines,
                    span_records,
                    case_url=start_url,
                    variable_preamble_lines=None,
                )
                meta = {
                    "profile": "llm_playwright_validate",
                    "model": CODEGEN_AGENT_MODEL_NAME,
                    "base_url": CODEGEN_AGENT_BASE_URL,
                    "prompt_version": PROMPT_VERSION,
                    "task_id": task_id,
                    "max_validation_attempts": max_attempts,
                    "mcp_browser": mcp_browser,
                    "browser_validate": not SKIP_BROWSER_VALIDATE,
                    "node_runner": node_runner_ready(),
                    "playwright_mcp": USE_PLAYWRIGHT_MCP and mcp_runner_ready(),
                    "legacy_node_fragment_fallback": not (USE_PLAYWRIGHT_MCP and mcp_runner_ready()) and legacy_runner_ready(),
                    "step_attempts": step_attempts_log,
                }
                payload = {
                    "case_id": case_id,
                    "source_run_id": run_id,
                    "source_code": src,
                    "step_spans": spans,
                    "steps_content_hash": content_hash,
                    "generator_meta": meta,
                }
                async with httpx.AsyncClient(timeout=30.0) as log_client:
                    await _emit_codegen_log(
                        log_client,
                        case_id,
                        run_id,
                        "All steps passed; sending artifact to backend (finalize).",
                        phase="finalize",
                    )
                finalize_url = f"{BACKEND_BASE_URL}/api/internal/codegen/playwright/finalize"
                async with httpx.AsyncClient(timeout=120.0) as client:
                    r = await client.post(
                        finalize_url,
                        json=payload,
                        headers={"X-Internal-Token": SECRET_KEY_API},
                    )
                    if r.status_code >= 400:
                        logger.error("codegen finalize failed %s %s", r.status_code, r.text)
                        fin_err = (r.text or "finalize failed")[:4000]
                        _mark_codegen_span_failed(
                            codegen_span,
                            step_uid=None,
                            phase="finalize_http",
                            error_message=f"HTTP {r.status_code}: {fin_err}",
                        )
                        await _post_fail(
                            client,
                            case_id,
                            r.text or "finalize failed",
                            None,
                            "codegen_finalize_http_error",
                        )
                    else:
                        codegen_span.update(
                            output={
                                "status": "finalized",
                                "artifact_delivered": True,
                                "case_id": case_id,
                                "run_id": run_id,
                                "finalize_http_status": r.status_code,
                            }
                        )
            except Exception as span_exc:
                _mark_codegen_span_failed(
                    codegen_span,
                    step_uid=None,
                    phase="codegen_exception",
                    error_message=str(span_exc) or type(span_exc).__name__,
                )
                raise
    except Exception as e:
        logger.exception("codegen error")
        err_msg, err_code = _classify_codegen_exception(e)
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                await _post_fail(client, case_id, err_msg, None, err_code)
        except Exception:
            logger.exception("codegen fail callback error")
    finally:
        import shutil
        try:
            shutil.rmtree(_failshot_dir, ignore_errors=True)
        except Exception:
            pass
