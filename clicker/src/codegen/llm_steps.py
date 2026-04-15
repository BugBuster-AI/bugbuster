"""Вызовы LLM для генерации и починки JS-фрагментов Playwright (мультимодально, CODEGEN_AGENT_*)."""
from __future__ import annotations

import json
import logging
import os
import re
from html.parser import HTMLParser
from typing import Any, Dict, List, Optional, Sequence, Tuple

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from core.config import (
    CODEGEN_AGENT_API_KEY,
    CODEGEN_AGENT_BASE_URL,
    CODEGEN_AGENT_MODEL_NAME,
    OPENROUTER_PROVIDER_EXTRA_BODY,
)
from codegen.playwright_strict_mode_hints import format_strict_mode_hints_from_playwright_error
from codegen.llm_prompts import (
    PROMPT_VERSION,
    REPAIR_BAN_INTRO,
    REPAIR_BAN_OUTRO,
    REPAIR_ESC_PRIOR_MULTIPLE_FAILURES,
    REPAIR_PRIOR_CHAINS_HEADER,
    STRICT_JSON_RETRY_USER_MESSAGE,
    SYSTEM_PROMPT,
    SYSTEM_PROMPT_EXPECTED_RESULT,
    accessibility_snapshot_block,
    draft_user_message,
    draft_user_message_expected_result,
    log_codegen_context_flags,
    playwright_css_xpath_hint,
    repair_user_message,
    repair_user_message_expected_result,
    repair_user_message_expected_result_single_assertion,
)

logger = logging.getLogger("clicker")

# ---------------------------------------------------------------------------
# Клиент OpenAI-совместимого API + логирование сырого ответа
# ---------------------------------------------------------------------------
def _base_url_v1() -> str:
    base = (CODEGEN_AGENT_BASE_URL or "").rstrip("/")
    if not base.endswith("/v1"):
        base = f"{base}/v1"
    return base


CODEGEN_JSON_RESPONSE = os.getenv("CODEGEN_JSON_RESPONSE_FORMAT", "1").strip().lower() not in (
    "0",
    "false",
    "no",
    "",
)

# Raw LLM bodies always logged at INFO (truncated) for codegen draft/repair — same visibility in docker logs without extra env.
_CODEGEN_LLM_LOG_MAX_CHARS = 14_000


def _log_llm_raw_response(*, phase: str, step_uid: str, content: object) -> None:
    text = (str(content) if content is not None else "").strip()
    if not text:
        logger.info("codegen LLM raw (%s) step_uid=%s: <empty>", phase, step_uid)
        return
    if len(text) > _CODEGEN_LLM_LOG_MAX_CHARS:
        text = text[:_CODEGEN_LLM_LOG_MAX_CHARS] + "\n...[truncated for log]"
    logger.info("codegen LLM raw (%s) step_uid=%s:\n%s", phase, step_uid, text)

# ТЗ: колонка «Рефакторинг (детерминизм)» — draft vs repair
SAMPLING_DRAFT: Dict[str, Any] = {
    "temperature": 0.22,
    "top_p": 0.7,
    "frequency_penalty": 0.05,
}
SAMPLING_REPAIR: Dict[str, Any] = {
    # Base temperature for the first repair; see _repair_temperature (ramps up with attempt index).
    "temperature": 0.42,
    "top_p": 0.88,
    "frequency_penalty": 0.22,
}

# Repair LLM: temperature rises linearly from first repair (base) to last MCP attempt (cap).
REPAIR_TEMPERATURE_CAP = 0.92


def _repair_temperature(*, base: float, repair_attempt: int, max_validation_attempts: int) -> float:
    """MCP attempt index `repair_attempt` is 2 for the first LLM repair, `max` for the last."""
    if max_validation_attempts < 2:
        return min(REPAIR_TEMPERATURE_CAP, float(base))
    lo, hi = 2, int(max_validation_attempts)
    span = max(1, hi - lo)
    idx = max(0, int(repair_attempt) - lo)
    frac = min(1.0, float(idx) / float(span))
    return min(REPAIR_TEMPERATURE_CAP, float(base) + frac * (REPAIR_TEMPERATURE_CAP - float(base)))


def extract_mcp_waiting_chain(playwright_error: str) -> Optional[str]:
    """Строка 'waiting for …' из stderr MCP/Playwright (для промпта и списка prior_failed в таске), не ответ LLM."""
    ansi = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")
    t = ansi.sub("", playwright_error or "")
    for line in t.splitlines():
        if "waiting for" not in line.lower():
            continue
        m = re.search(r"waiting\s+for\s+(.+)", line, flags=re.IGNORECASE)
        if not m:
            continue
        chain = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", m.group(1)).strip()
        if len(chain) >= 12:
            return chain
    return None


def _end_index_after_locator_call(text: str, locator_paren_idx: int) -> int:
    """Индекс сразу после закрывающей `)` вызова `locator(...)`, начинающегося на locator_paren_idx."""
    i = locator_paren_idx + len("locator(")
    n = len(text)
    while i < n and text[i] in " \t\n\r":
        i += 1
    if i >= n:
        return n
    quote = text[i]
    if quote not in "'\"":
        return min(locator_paren_idx + len("locator("), n)
    i += 1
    while i < n:
        c = text[i]
        if c == "\\" and i + 1 < n:
            i += 2
            continue
        if c == quote:
            i += 1
            break
        i += 1
    while i < n and text[i] in " \t\n\r":
        i += 1
    if i < n and text[i] == ")":
        return i + 1
    return n


def _extract_first_string_inside_locator_call(text: str, locator_paren_idx: int) -> Optional[str]:
    """После `locator(` — пропуск пробелов и чтение первого строкового литерала '...' или \"...\" с экранированием."""
    i = locator_paren_idx + len("locator(")
    n = len(text)
    while i < n and text[i] in " \t\n\r":
        i += 1
    if i >= n:
        return None
    quote = text[i]
    if quote not in "'\"":
        return None
    i += 1
    out: List[str] = []
    while i < n:
        c = text[i]
        if c == "\\" and i + 1 < n:
            out.append(text[i : i + 2])
            i += 2
            continue
        if c == quote:
            return "".join(out)
        out.append(c)
        i += 1
    return None


def extract_failed_locator_inner_from_playwright_error(playwright_error: str) -> Optional[str]:
    """
    Внутренний селектор из первого `locator('...')` / `locator(\"...\")` в строках вида
    `Locator: locator(...)` или `waiting for locator(...)` (MCP / Playwright expect errors).
    """
    ansi = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")
    t = ansi.sub("", playwright_error or "")
    lower = t.lower()

    def _try_from_locator_call_at(q: int) -> Optional[str]:
        inner = _extract_first_string_inside_locator_call(t, q)
        if inner and len(inner.strip()) >= 6:
            return inner.strip()
        return None

    # 1) Явная строка Playwright: "Locator: locator('...')"
    for m in re.finditer(r"(?is)Locator:\s*locator\(", t):
        q = m.end() - len("locator(")
        got = _try_from_locator_call_at(q)
        if got:
            return got

    # 2) Call log: "waiting for locator('...')"
    p = lower.find("waiting for locator")
    if p >= 0:
        q = t.find("locator(", p)
        if q >= 0:
            got = _try_from_locator_call_at(q)
            if got:
                return got

    return None


def extract_locator_line_snippet_after_locator_colon(playwright_error: str) -> Optional[str]:
    """Текст после `Locator:` — одна строка цепочки `locator(...).locator(...)` как в логе Playwright."""
    ansi = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")
    t = ansi.sub("", playwright_error or "")
    m = re.search(r"(?is)Locator:\s*([^\n]+)", t)
    if not m:
        return None
    line = m.group(1).strip()
    return line if line else None


def extract_locator_chain_literals_from_playwright_error(playwright_error: str) -> Optional[Tuple[str, ...]]:
    """
    Все строковые аргументы `locator('...')` / `locator(\"...\")` с строки Locator: по порядку.
    Это сужает совпадение до одной assertion-строки (в отличие от первого сегмента вроде [data-test=...]).
    """
    snippet = extract_locator_line_snippet_after_locator_colon(playwright_error)
    if not snippet:
        return None
    literals: List[str] = []
    pos = 0
    while pos < len(snippet):
        q = snippet.find("locator(", pos)
        if q < 0:
            break
        inner = _extract_first_string_inside_locator_call(snippet, q)
        if inner is None:
            break
        literals.append(inner)
        nxt = _end_index_after_locator_call(snippet, q)
        if nxt <= q:
            break
        pos = nxt
    return tuple(literals) if literals else None


def _fragment_line_matches_locator_literals_in_order(ln: str, literals: Tuple[str, ...]) -> bool:
    """Все литералы из ошибки встречаются в строке кода в том же порядке (с допуском xpath= на сегментах)."""
    pos = 0
    for lit in literals:
        lit = lit.strip()
        if len(lit) < 1:
            return False
        candidates: List[str] = [lit]
        if not lit.startswith("xpath="):
            candidates.append("xpath=" + lit)
        found_at = -1
        for cand in candidates:
            idx = ln.find(cand, pos)
            if idx >= 0:
                found_at = idx
                pos = idx + len(cand)
                break
        if found_at < 0:
            return False
    return True


def find_expected_result_line_indices_matching_locator_chain(
    previous_js: str, literals: Tuple[str, ...]
) -> List[int]:
    """Строки фрагмента, где цепочка локаторов из ошибки совпадает по всем сегментам."""
    if not literals or not (previous_js or "").strip():
        return []
    out: List[int] = []
    for i, ln in enumerate((previous_js or "").splitlines()):
        if "locator(" not in ln:
            continue
        if _fragment_line_matches_locator_literals_in_order(ln, literals):
            out.append(i)
    return out


def find_expected_result_line_indices_matching_locator_inner(previous_js: str, locator_inner: str) -> List[int]:
    """Индексы строк фрагмента expected_result, где встречается упавший селектор внутри locator(...)."""
    if not (previous_js or "").strip() or not (locator_inner or "").strip():
        return []
    inner = locator_inner.strip()
    if len(inner) < 6:
        return []
    out: List[int] = []
    for i, ln in enumerate((previous_js or "").splitlines()):
        if "locator(" not in ln:
            continue
        if inner not in ln:
            continue
        out.append(i)
    return out


_STEP_UID_MARK_JS = re.compile(r"^\s*//\s*step_uid:(\S+)", re.MULTILINE)


def infer_step_uid_for_playwright_timeout(*, full_script: str, playwright_error: str) -> Optional[str]:
    """
    По тексту ошибки Playwright (waiting for locator…) и полному JS сценария находит step_uid блока,
    в котором встречается соответствующий локатор. Полный прогон падает на первом таймауте — часто это
    предыдущий шаг, хотя цикл codegen сейчас ведёт repair для другого uid.
    Возвращает None, если не удалось сопоставить или таймаут в коде до первого // step_uid:.
    """
    needle = extract_mcp_waiting_chain(playwright_error)
    if not needle:
        return None
    text = full_script or ""
    matches = list(_STEP_UID_MARK_JS.finditer(text))
    if not matches:
        return None

    candidates: List[str] = []
    n = needle.strip()
    if n:
        candidates.append(n)
    for m in re.finditer(r"locator\(\s*['\"]([^'\"]+)['\"]\s*\)", n):
        inner = m.group(1)
        if inner and len(inner) >= 6:
            candidates.append(inner)

    seen = set()
    uniq: List[str] = []
    for c in candidates:
        if c not in seen:
            seen.add(c)
            uniq.append(c)
    uniq.sort(key=len, reverse=True)

    pre = text[: matches[0].start()]
    for c in uniq:
        if c in pre:
            return None

    for i, m in enumerate(matches):
        uid = m.group(1)
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        block = text[start:end]
        for c in uniq:
            if c in block:
                return uid
    return None


def split_playwright_wait_chain_segments(chain: str) -> List[str]:
    """Разбить цепочку локаторов Playwright из лога ('a.b.c') по точкам вне кавычек."""
    if not chain or not str(chain).strip():
        return []
    s = str(chain).strip()
    parts: List[str] = []
    buf: List[str] = []
    in_sq = False
    in_dq = False
    i = 0
    while i < len(s):
        c = s[i]
        if in_sq:
            buf.append(c)
            if c == "'":
                in_sq = False
            i += 1
            continue
        if in_dq:
            buf.append(c)
            if c == '"':
                in_dq = False
            i += 1
            continue
        if c == "'":
            in_sq = True
            buf.append(c)
            i += 1
            continue
        if c == '"':
            in_dq = True
            buf.append(c)
            i += 1
            continue
        if c == ".":
            seg = "".join(buf).strip()
            if seg:
                parts.append(seg)
            buf = []
            i += 1
            continue
        buf.append(c)
        i += 1
    tail = "".join(buf).strip()
    if tail:
        parts.append(tail)
    return parts


def extract_wait_chain_anchor_first_segment(wait_chain: Optional[str]) -> Optional[str]:
    """Первый сегмент цепочки (якорь), например getByTestId('login-credentials') или page.getByText('x')."""
    if not wait_chain or not str(wait_chain).strip():
        return None
    segs = split_playwright_wait_chain_segments(wait_chain)
    if not segs:
        return None
    # В логах иногда бывает page.getByRole(...): первая «точка» режет на `page` и остальное — склеиваем.
    if len(segs) >= 2 and segs[0] == "page":
        return f"{segs[0]}.{segs[1]}"
    return segs[0]


_GET_BY_TEST_ID_RE = re.compile(
    r"getByTestId\s*\(\s*(['\"])([^'\"\\]*(?:\\.[^'\"\\]*)*)\1\s*\)",
    re.DOTALL,
)


# ---------------------------------------------------------------------------
# data-* attribute priority for deterministic locator rewrite
# ---------------------------------------------------------------------------
# Порядок фиксирован: data-testid (Playwright native) > data-test > data-cy > data-qa > data-id.
# Атрибуты не в списке получают индекс len(DATA_ATTR_PRIORITY) и сортируются
# лексикографически по имени — детерминированный tie-break для любых экзотических data-*.
DATA_ATTR_PRIORITY: Tuple[str, ...] = (
    "data-testid",
    "data-test",
    "data-cy",
    "data-qa",
    "data-id",
)

_DATA_ATTR_PRIORITY_INDEX = {name: idx for idx, name in enumerate(DATA_ATTR_PRIORITY)}


def _data_attr_sort_key(attr_name: str) -> Tuple[int, str]:
    idx = _DATA_ATTR_PRIORITY_INDEX.get(attr_name, len(DATA_ATTR_PRIORITY))
    return (idx, attr_name)


class _DataAttrScanner(HTMLParser):
    """Scan serialised HTML for data-* attributes whose value matches `target_value`."""

    def __init__(self, target_value: str) -> None:
        super().__init__()
        self.target_value = target_value
        self.depth = 0
        self.tag_order = 0
        # (attr_name, depth, tag_order)
        self.candidates: List[Tuple[str, int, int]] = []

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]) -> None:
        self.depth += 1
        self.tag_order += 1
        order = self.tag_order
        for attr_name, attr_val in attrs:
            if attr_name and attr_name.startswith("data-") and attr_val == self.target_value:
                self.candidates.append((attr_name, self.depth, order))

    def handle_endtag(self, tag: str) -> None:
        self.depth = max(0, self.depth - 1)


def find_best_data_attr(test_id: str, page_html: str) -> Optional[str]:
    """
    Найти лучший data-* атрибут с заданным значением в HTML по правилам приоритета.
    Возвращает имя атрибута (например 'data-test') или None если не найден / data-testid присутствует.
    """
    if not test_id or not page_html:
        return None
    tid = test_id.strip()
    if not tid:
        return None

    scanner = _DataAttrScanner(tid)
    try:
        scanner.feed(page_html)
    except Exception:
        return None

    if not scanner.candidates:
        return None

    # data-testid найден — getByTestId работает, rewrite не нужен.
    if any(c[0] == "data-testid" for c in scanner.candidates):
        return None

    # Сортировка: приоритет имени (меньше = лучше), глубина (больше = лучше, ↑closer to target),
    # порядок появления (меньше = лучше, tie-break).
    best = min(
        scanner.candidates,
        key=lambda c: (_data_attr_sort_key(c[0]), -c[1], c[2]),
    )
    return best[0]


def should_rewrite_get_by_test_id_to_data_attr(test_id: str, page_html: str) -> bool:
    """True если в DOM есть подходящий data-*, но нет data-testid — getByTestId не найдёт узел."""
    return find_best_data_attr(test_id, page_html) is not None


# Обратная совместимость: старое имя → новая реализация.
should_rewrite_get_by_test_id_to_data_test = should_rewrite_get_by_test_id_to_data_attr


def rewrite_js_fragment_get_by_test_id_to_data_attr(js_fragment: str, page_html: str) -> str:
    """
    Заменить вызовы getByTestId('id') на locator('[data-xxx="id"]') когда HTML содержит
    подходящий data-*, а data-testid отсутствует. Атрибут выбирается детерминированно
    по DATA_ATTR_PRIORITY и глубине.
    """
    if not js_fragment or not page_html:
        return js_fragment

    def repl(m: re.Match) -> str:
        inner = m.group(2)
        try:
            lit = bytes(inner, "utf-8").decode("unicode_escape")
        except Exception:
            lit = inner
        best = find_best_data_attr(lit, page_html)
        if best is None:
            return m.group(0)
        safe = lit.replace("\\", "\\\\").replace('"', '\\"')
        return f'locator(\'[{best}="{safe}"]\')'

    return _GET_BY_TEST_ID_RE.sub(repl, js_fragment)


# Обратная совместимость.
rewrite_js_fragment_get_by_test_id_to_data_test = rewrite_js_fragment_get_by_test_id_to_data_attr


def _chat_client(
    *,
    temperature: float,
    max_tokens: int,
    top_p: Optional[float] = None,
    frequency_penalty: Optional[float] = None,
    callbacks: Optional[Sequence[Any]] = None,
) -> ChatOpenAI:
    kwargs: Dict[str, Any] = {}
    if "openrouter.ai" in _base_url_v1() and OPENROUTER_PROVIDER_EXTRA_BODY:
        kwargs["extra_body"] = OPENROUTER_PROVIDER_EXTRA_BODY
    model_kw: Dict[str, Any] = {}
    if CODEGEN_JSON_RESPONSE:
        model_kw["response_format"] = {"type": "json_object"}
    chat_kw: Dict[str, Any] = {
        "base_url": _base_url_v1(),
        "model": CODEGEN_AGENT_MODEL_NAME,
        "api_key": CODEGEN_AGENT_API_KEY,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "model_kwargs": model_kw,
        **kwargs,
    }
    if top_p is not None:
        chat_kw["top_p"] = top_p
    if frequency_penalty is not None:
        chat_kw["frequency_penalty"] = frequency_penalty
    if callbacks:
        chat_kw["callbacks"] = list(callbacks)
    return ChatOpenAI(**chat_kw)


def _parse_codegen_llm_response(text: str) -> Dict[str, Any]:
    """Строго один JSON-объект; без вырезания из текста и без восстановления обрезанных строк."""
    body = (text or "").strip()
    if not body:
        raise ValueError("LLM returned empty response")
    try:
        data = json.loads(body)
    except json.JSONDecodeError as e:
        raise ValueError(
            f"LLM response is not valid JSON ({e!s}); first 500 chars: {body[:500]!r}"
        ) from e
    if not isinstance(data, dict):
        raise ValueError("LLM JSON root must be a JSON object")
    return data


_MAX_JSON_RETRIES = 3


def _vlm_action_label(vlm_action: Any) -> str:
    if vlm_action is None:
        return "unknown"
    s = str(vlm_action).strip()
    return s if s else "unknown"


def _coerce_repair_round(repair_round: Any) -> Optional[int]:
    if repair_round is None:
        return None
    if isinstance(repair_round, bool):
        return None
    if isinstance(repair_round, int):
        return repair_round
    if isinstance(repair_round, float):
        return int(repair_round)
    if isinstance(repair_round, str) and repair_round.strip().isdigit():
        return int(repair_round.strip())
    try:
        return int(repair_round)
    except (TypeError, ValueError):
        return None


def _langfuse_codegen_run_name(
    *,
    phase: str,
    vlm_action: Any = None,
    repair_round: Any = None,
    trace_kind: str = "step",
    repair_single_line: bool = False,
) -> str:
    if trace_kind == "expected_result":
        if phase == "draft":
            return "expected_result"
        if phase == "repair":
            rr = _coerce_repair_round(repair_round)
            suf = " · targeted line" if repair_single_line else ""
            if rr is not None:
                return f"expected_result (repair {rr}){suf}"
            return f"expected_result (repair){suf}"
        return "expected_result"
    act = _vlm_action_label(vlm_action)
    if phase == "draft":
        return f"step ({act})"
    if phase == "repair":
        rr = _coerce_repair_round(repair_round)
        if rr is not None:
            return f"step ({act} · repair {rr})"
        return f"step ({act} · repair)"
    return f"step ({act})"


def _image_parts(
    before_b64: Optional[str],
    after_b64: Optional[str],
) -> List[dict]:
    parts: List[dict] = []
    if before_b64:
        parts.append(
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{before_b64}"},
            }
        )
    if after_b64:
        parts.append(
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{after_b64}"},
            }
        )
    return parts


async def generate_action_fragment(
    *,
    step_uid: str,
    nl: str,
    base_url: str,
    viewport_w: int,
    viewport_h: int,
    before_b64: Optional[str],
    after_b64: Optional[str],
    temperature: Optional[float] = None,
    langchain_callbacks: Optional[Sequence[Any]] = None,
    vlm_trace_excerpt: Optional[str] = None,
    vlm_run_step_context: Optional[str] = None,
    prior_steps_text: Optional[str] = None,
    prior_js_prefix: Optional[str] = None,
    global_trace_summary: Optional[str] = None,
    vlm_run_log: Optional[str] = None,
    vlm_focused_dom_before: Optional[str] = None,
    vlm_before_full_html: Optional[str] = None,
    vlm_action: Optional[str] = None,
    codegen_trace_kind: str = "step",
) -> str:
    sp = dict(SAMPLING_DRAFT)
    if temperature is not None:
        sp["temperature"] = temperature
    llm = _chat_client(
        temperature=float(sp["temperature"]),
        max_tokens=8192,
        top_p=float(sp["top_p"]),
        frequency_penalty=float(sp["frequency_penalty"]),
        callbacks=langchain_callbacks,
    )
    logger.info(
        log_codegen_context_flags(
            phase="draft",
            step_uid=step_uid,
            has_vlm_trace=bool(vlm_trace_excerpt and str(vlm_trace_excerpt).strip()),
            has_vlm_action=bool(vlm_run_step_context and str(vlm_run_step_context).strip()),
            has_prior_steps=bool(prior_steps_text and str(prior_steps_text).strip()),
            has_prior_js=bool(prior_js_prefix and str(prior_js_prefix).strip()),
            has_global_trace=bool(global_trace_summary and str(global_trace_summary).strip()),
            has_vlm_log=bool(vlm_run_log and str(vlm_run_log).strip()),
            has_vlm_dom_focus=bool(vlm_focused_dom_before and str(vlm_focused_dom_before).strip()),
            has_vlm_before_full=bool(vlm_before_full_html and str(vlm_before_full_html).strip()),
        )
    )
    if codegen_trace_kind == "expected_result":
        user_text = draft_user_message_expected_result(
            step_uid=step_uid,
            nl=nl,
            base_url=base_url,
            viewport_w=viewport_w,
            viewport_h=viewport_h,
            vlm_trace_excerpt=vlm_trace_excerpt,
            vlm_run_step_context=vlm_run_step_context,
            prior_steps_text=prior_steps_text,
            prior_js_prefix=prior_js_prefix,
            global_trace_summary=global_trace_summary,
            vlm_run_log=vlm_run_log,
            vlm_focused_dom_before=vlm_focused_dom_before,
            vlm_before_full_html=vlm_before_full_html,
        )
        system_prompt = SYSTEM_PROMPT_EXPECTED_RESULT
    else:
        user_text = draft_user_message(
            step_uid=step_uid,
            nl=nl,
            base_url=base_url,
            viewport_w=viewport_w,
            viewport_h=viewport_h,
            vlm_trace_excerpt=vlm_trace_excerpt,
            vlm_run_step_context=vlm_run_step_context,
            prior_steps_text=prior_steps_text,
            prior_js_prefix=prior_js_prefix,
            global_trace_summary=global_trace_summary,
            vlm_run_log=vlm_run_log,
            vlm_focused_dom_before=vlm_focused_dom_before,
            vlm_before_full_html=vlm_before_full_html,
        )
        system_prompt = SYSTEM_PROMPT
    content: List[dict] = [{"type": "text", "text": user_text}]
    content.extend(_image_parts(before_b64, after_b64))
    messages: List[BaseMessage] = [SystemMessage(content=system_prompt), HumanMessage(content=content)]
    data: Optional[Dict[str, Any]] = None
    vlm_label = _vlm_action_label(vlm_action)
    _draft_cfg: Dict[str, Any] = {
        "metadata": {
            "codegen_llm_phase": "draft",
            "step_uid": step_uid,
            "vlm_action": vlm_label,
            "codegen_trace_kind": codegen_trace_kind,
        },
        "run_name": _langfuse_codegen_run_name(
            phase="draft",
            vlm_action=vlm_action,
            trace_kind=codegen_trace_kind,
        ),
    }
    for json_attempt in range(_MAX_JSON_RETRIES):
        resp = await llm.ainvoke(messages, config=_draft_cfg)
        _log_llm_raw_response(phase="draft", step_uid=step_uid, content=resp.content)
        try:
            data = _parse_codegen_llm_response(str(resp.content))
            break
        except ValueError as e:
            if json_attempt + 1 >= _MAX_JSON_RETRIES:
                raise
            logger.warning(
                "codegen draft: step_uid=%s invalid JSON, strict retry %s/%s: %s",
                step_uid,
                json_attempt + 1,
                _MAX_JSON_RETRIES,
                e,
            )
            messages = list(messages) + [HumanMessage(content=STRICT_JSON_RETRY_USER_MESSAGE)]
    assert data is not None
    frag = data.get("js_fragment")
    if not frag or not isinstance(frag, str):
        raise ValueError("LLM JSON missing js_fragment")
    return frag.strip()


async def repair_action_fragment(
    *,
    step_uid: str,
    nl: str,
    base_url: str,
    viewport_w: int,
    viewport_h: int,
    before_b64: Optional[str],
    after_b64: Optional[str],
    failure_screenshot_b64: Optional[str],
    previous_js: str,
    playwright_error: str,
    repair_attempt: int = 2,
    max_validation_attempts: int = 10,
    temperature: Optional[float] = None,
    accessibility_snapshot: Optional[str] = None,
    prior_failed_wait_chains: Optional[List[str]] = None,
    langchain_callbacks: Optional[Sequence[Any]] = None,
    vlm_coords: Optional[Any] = None,
    trace_hint: Optional[str] = None,
    anchor_must_change: bool = False,
    anchor_first_hint: Optional[str] = None,
    mcp_page_html: Optional[str] = None,
    vlm_action: Optional[str] = None,
    codegen_trace_kind: str = "step",
) -> str:
    # repair_attempt — индекс попытки валидации (2 = первый repair после draft); repair_round — 1,2,… для UI и промпта
    repair_round = max(1, int(repair_attempt) - 1)
    sp = dict(SAMPLING_REPAIR)
    base_t = float(sp["temperature"])
    if temperature is not None:
        temp = float(temperature)
    else:
        temp = _repair_temperature(
            base=base_t,
            repair_attempt=repair_attempt,
            max_validation_attempts=max_validation_attempts,
        )
        logger.info(
            "codegen repair sampling: step_uid=%s repair_round=%s validation_attempt=%s/%s temperature=%.3f (base=%.3f cap=%.2f)",
            step_uid,
            repair_round,
            repair_attempt,
            max_validation_attempts,
            temp,
            base_t,
            REPAIR_TEMPERATURE_CAP,
        )

    snap = ""
    if accessibility_snapshot and accessibility_snapshot.strip():
        snap = accessibility_snapshot_block(accessibility_snapshot)
    err_clip = (playwright_error or "")[: 2800]
    strict_mode_hints = format_strict_mode_hints_from_playwright_error(playwright_error)
    prev_clip = (previous_js or "")[: 4500]
    wait_line = extract_mcp_waiting_chain(playwright_error)
    ban_block = ""
    if wait_line:
        ban_block = REPAIR_BAN_INTRO + f"Runner wait chain (verbatim): {wait_line}\n" + REPAIR_BAN_OUTRO
    if prior_failed_wait_chains:
        ban_block += REPAIR_PRIOR_CHAINS_HEADER
        for i, pc in enumerate(prior_failed_wait_chains[:14], start=1):
            if pc and pc.strip():
                ban_block += f"  ({i}) {pc.strip()}\n"
    esc_prior = ""
    if prior_failed_wait_chains and len([x for x in prior_failed_wait_chains if (x or "").strip()]) >= 2:
        esc_prior = REPAIR_ESC_PRIOR_MULTIPLE_FAILURES
    logger.info(
        log_codegen_context_flags(
            phase="repair",
            step_uid=step_uid,
            has_vlm_trace=False,
            has_vlm_action=False,
            has_prior_steps=False,
            has_prior_js=False,
            has_global_trace=False,
            has_vlm_log=False,
            has_vlm_coords=vlm_coords is not None,
            has_trace_hint=bool(trace_hint and str(trace_hint).strip()),
            has_vlm_dom_focus=False,
            has_mcp_page_html=bool(mcp_page_html and str(mcp_page_html).strip()),
        )
    )
    if codegen_trace_kind == "expected_result":
        user_text = repair_user_message_expected_result(
            step_uid=step_uid,
            nl=nl,
            base_url=base_url,
            viewport_w=viewport_w,
            viewport_h=viewport_h,
            repair_round=repair_round,
            err_clip=err_clip,
            css_xpath_hint=playwright_css_xpath_hint(err_clip),
            esc_prior=esc_prior,
            ban_block=ban_block,
            snap=snap,
            prev_clip=prev_clip,
            vlm_coords=vlm_coords,
            trace_hint=trace_hint,
            anchor_must_change=anchor_must_change,
            anchor_first_hint=anchor_first_hint,
            mcp_page_html=mcp_page_html,
            strict_mode_hints=strict_mode_hints,
        )
        system_prompt = SYSTEM_PROMPT_EXPECTED_RESULT
    else:
        user_text = repair_user_message(
            step_uid=step_uid,
            nl=nl,
            base_url=base_url,
            viewport_w=viewport_w,
            viewport_h=viewport_h,
            repair_round=repair_round,
            err_clip=err_clip,
            css_xpath_hint=playwright_css_xpath_hint(err_clip),
            esc_prior=esc_prior,
            ban_block=ban_block,
            snap=snap,
            prev_clip=prev_clip,
            vlm_coords=vlm_coords,
            trace_hint=trace_hint,
            anchor_must_change=anchor_must_change,
            anchor_first_hint=anchor_first_hint,
            mcp_page_html=mcp_page_html,
            strict_mode_hints=strict_mode_hints,
        )
        system_prompt = SYSTEM_PROMPT
    content: List[dict] = [{"type": "text", "text": user_text}]
    content.extend(_image_parts(before_b64, after_b64))
    if failure_screenshot_b64:
        content.append(
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{failure_screenshot_b64}"},
            }
        )
    messages: List[BaseMessage] = [SystemMessage(content=system_prompt), HumanMessage(content=content)]
    llm = _chat_client(
        temperature=temp,
        max_tokens=4096,
        top_p=float(sp["top_p"]),
        frequency_penalty=float(sp["frequency_penalty"]),
        callbacks=langchain_callbacks,
    )
    vlm_label = _vlm_action_label(vlm_action)
    _repair_cfg: Dict[str, Any] = {
        "metadata": {
            "codegen_llm_phase": "repair",
            "repair_attempt": repair_round,
            "step_uid": step_uid,
            "vlm_action": vlm_label,
            "codegen_trace_kind": codegen_trace_kind,
        },
        "run_name": _langfuse_codegen_run_name(
            phase="repair",
            vlm_action=vlm_action,
            repair_round=repair_round,
            trace_kind=codegen_trace_kind,
        ),
    }
    data: Optional[Dict[str, Any]] = None
    for json_attempt in range(_MAX_JSON_RETRIES):
        resp = await llm.ainvoke(messages, config=_repair_cfg)
        log_phase = "repair" if json_attempt == 0 else f"repair_json_retry_{json_attempt}"
        _log_llm_raw_response(phase=log_phase, step_uid=step_uid, content=resp.content)
        try:
            data = _parse_codegen_llm_response(str(resp.content))
            break
        except ValueError as e:
            if json_attempt + 1 >= _MAX_JSON_RETRIES:
                raise
            logger.warning(
                "codegen repair: step_uid=%s invalid JSON, strict retry %s/%s: %s",
                step_uid,
                json_attempt + 1,
                _MAX_JSON_RETRIES,
                e,
            )
            messages = list(messages) + [HumanMessage(content=STRICT_JSON_RETRY_USER_MESSAGE)]
    assert data is not None
    frag = data.get("js_fragment")
    if not frag or not isinstance(frag, str):
        raise ValueError("LLM repair missing js_fragment")
    return frag.strip()


def _normalize_single_assertion_js_fragment(js_fragment: str) -> str:
    """Одна строка `await expect(...);` из ответа LLM (targeted repair)."""
    text = (js_fragment or "").strip()
    if not text:
        raise ValueError("LLM single-assertion repair returned empty js_fragment")
    for raw in text.splitlines():
        ln = raw.strip()
        if not ln or ln.startswith("//"):
            continue
        low = ln.lower()
        if "expect(" in low and ln.lstrip().startswith("await "):
            return ln if ln.endswith(";") else ln + ";"
    for raw in text.splitlines():
        ln = raw.strip()
        if ln and not ln.startswith("//"):
            return ln if ln.endswith(";") else ln + ";"
    raise ValueError("LLM single-assertion repair: no usable line in js_fragment")


async def repair_expected_result_single_assertion_line(
    *,
    step_uid: str,
    nl: str,
    base_url: str,
    viewport_w: int,
    viewport_h: int,
    before_b64: Optional[str],
    after_b64: Optional[str],
    failure_screenshot_b64: Optional[str],
    original_assertion_line: str,
    rest_of_fragment_excerpt: str,
    failed_locator_inner: str,
    playwright_error: str,
    repair_attempt: int = 2,
    max_validation_attempts: int = 10,
    temperature: Optional[float] = None,
    accessibility_snapshot: Optional[str] = None,
    prior_failed_wait_chains: Optional[List[str]] = None,
    langchain_callbacks: Optional[Sequence[Any]] = None,
    vlm_coords: Optional[Any] = None,
    trace_hint: Optional[str] = None,
    anchor_must_change: bool = False,
    anchor_first_hint: Optional[str] = None,
    mcp_page_html: Optional[str] = None,
    vlm_action: Optional[str] = None,
    failed_locator_chain_text: Optional[str] = None,
) -> str:
    """Один вызов LLM: починить одну строку assertion в expected_result (targeted repair)."""
    repair_round = max(1, int(repair_attempt) - 1)
    sp = dict(SAMPLING_REPAIR)
    base_t = float(sp["temperature"])
    if temperature is not None:
        temp = float(temperature)
    else:
        temp = _repair_temperature(
            base=base_t,
            repair_attempt=repair_attempt,
            max_validation_attempts=max_validation_attempts,
        )

    snap = ""
    if accessibility_snapshot and accessibility_snapshot.strip():
        snap = accessibility_snapshot_block(accessibility_snapshot)
    err_clip = (playwright_error or "")[: 2800]
    strict_mode_hints = format_strict_mode_hints_from_playwright_error(playwright_error)
    wait_line = extract_mcp_waiting_chain(playwright_error)
    ban_block = ""
    if wait_line:
        ban_block = REPAIR_BAN_INTRO + f"Runner wait chain (verbatim): {wait_line}\n" + REPAIR_BAN_OUTRO
    if prior_failed_wait_chains:
        ban_block += REPAIR_PRIOR_CHAINS_HEADER
        for i, pc in enumerate(prior_failed_wait_chains[:14], start=1):
            if pc and pc.strip():
                ban_block += f"  ({i}) {pc.strip()}\n"
    esc_prior = ""
    if prior_failed_wait_chains and len([x for x in prior_failed_wait_chains if (x or "").strip()]) >= 2:
        esc_prior = REPAIR_ESC_PRIOR_MULTIPLE_FAILURES

    user_text = repair_user_message_expected_result_single_assertion(
        step_uid=step_uid,
        nl=nl,
        base_url=base_url,
        viewport_w=viewport_w,
        viewport_h=viewport_h,
        repair_round=repair_round,
        err_clip=err_clip,
        css_xpath_hint=playwright_css_xpath_hint(err_clip),
        esc_prior=esc_prior,
        ban_block=ban_block,
        snap=snap,
        failed_locator_inner=failed_locator_inner,
        failed_locator_chain_text=failed_locator_chain_text,
        original_assertion_line=(original_assertion_line or "").strip(),
        rest_of_fragment_excerpt=rest_of_fragment_excerpt,
        vlm_coords=vlm_coords,
        trace_hint=trace_hint,
        anchor_must_change=anchor_must_change,
        anchor_first_hint=anchor_first_hint,
        mcp_page_html=mcp_page_html,
        strict_mode_hints=strict_mode_hints,
    )
    system_prompt = SYSTEM_PROMPT_EXPECTED_RESULT
    content: List[dict] = [{"type": "text", "text": user_text}]
    content.extend(_image_parts(before_b64, after_b64))
    if failure_screenshot_b64:
        content.append(
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{failure_screenshot_b64}"},
            }
        )
    messages: List[BaseMessage] = [SystemMessage(content=system_prompt), HumanMessage(content=content)]
    llm = _chat_client(
        temperature=temp,
        max_tokens=4096,
        top_p=float(sp["top_p"]),
        frequency_penalty=float(sp["frequency_penalty"]),
        callbacks=langchain_callbacks,
    )
    vlm_label = _vlm_action_label(vlm_action)
    _repair_cfg: Dict[str, Any] = {
        "metadata": {
            "codegen_llm_phase": "repair",
            "repair_attempt": repair_round,
            "step_uid": step_uid,
            "vlm_action": vlm_label,
            "codegen_trace_kind": "expected_result",
            "repair_targeted_line": True,
        },
        "run_name": _langfuse_codegen_run_name(
            phase="repair",
            vlm_action=vlm_action,
            repair_round=repair_round,
            trace_kind="expected_result",
            repair_single_line=True,
        ),
    }
    data: Optional[Dict[str, Any]] = None
    for json_attempt in range(_MAX_JSON_RETRIES):
        resp = await llm.ainvoke(messages, config=_repair_cfg)
        log_phase = "repair_er_targeted" if json_attempt == 0 else f"repair_er_targeted_json_retry_{json_attempt}"
        _log_llm_raw_response(phase=log_phase, step_uid=step_uid, content=resp.content)
        try:
            data = _parse_codegen_llm_response(str(resp.content))
            break
        except ValueError as e:
            if json_attempt + 1 >= _MAX_JSON_RETRIES:
                raise
            logger.warning(
                "codegen repair_er_targeted: step_uid=%s invalid JSON, strict retry %s/%s: %s",
                step_uid,
                json_attempt + 1,
                _MAX_JSON_RETRIES,
                e,
            )
            messages = list(messages) + [HumanMessage(content=STRICT_JSON_RETRY_USER_MESSAGE)]
    assert data is not None
    frag = data.get("js_fragment")
    if not frag or not isinstance(frag, str):
        raise ValueError("LLM targeted repair missing js_fragment")
    return _normalize_single_assertion_js_fragment(frag.strip())


async def repair_expected_result_fragment_maybe_targeted(
    *,
    step_uid: str,
    nl: str,
    base_url: str,
    viewport_w: int,
    viewport_h: int,
    before_b64: Optional[str],
    after_b64: Optional[str],
    failure_screenshot_b64: Optional[str],
    previous_js: str,
    playwright_error: str,
    repair_attempt: int = 2,
    max_validation_attempts: int = 10,
    temperature: Optional[float] = None,
    accessibility_snapshot: Optional[str] = None,
    prior_failed_wait_chains: Optional[List[str]] = None,
    langchain_callbacks: Optional[Sequence[Any]] = None,
    vlm_coords: Optional[Any] = None,
    trace_hint: Optional[str] = None,
    anchor_must_change: bool = False,
    anchor_first_hint: Optional[str] = None,
    mcp_page_html: Optional[str] = None,
    vlm_action: Optional[str] = None,
) -> str:
    """
    Для expected_result: если MCP указал упавший locator и он найден в фрагменте — чинить только эти строки.
    Иначе — полный repair_action_fragment.
    """
    prev = (previous_js or "").strip()
    chain_literals = extract_locator_chain_literals_from_playwright_error(playwright_error)
    indices: List[int] = []
    if chain_literals:
        indices = find_expected_result_line_indices_matching_locator_chain(prev, chain_literals)
    inner = extract_failed_locator_inner_from_playwright_error(playwright_error)
    if not indices and inner:
        indices = find_expected_result_line_indices_matching_locator_inner(prev, inner)
    chain_text = extract_locator_line_snippet_after_locator_colon(playwright_error)
    if not indices:
        if chain_literals or inner or (playwright_error and "Locator:" in playwright_error):
            logger.info(
                "codegen expected_result repair: targeted skipped (locator chain/inner not found in fragment) step_uid=%s",
                step_uid,
            )
        return await repair_action_fragment(
            step_uid=step_uid,
            nl=nl,
            base_url=base_url,
            viewport_w=viewport_w,
            viewport_h=viewport_h,
            before_b64=before_b64,
            after_b64=after_b64,
            failure_screenshot_b64=failure_screenshot_b64,
            previous_js=previous_js,
            playwright_error=playwright_error,
            repair_attempt=repair_attempt,
            max_validation_attempts=max_validation_attempts,
            temperature=temperature,
            accessibility_snapshot=accessibility_snapshot,
            prior_failed_wait_chains=prior_failed_wait_chains,
            langchain_callbacks=langchain_callbacks,
            vlm_coords=vlm_coords,
            trace_hint=trace_hint,
            anchor_must_change=anchor_must_change,
            anchor_first_hint=anchor_first_hint,
            mcp_page_html=mcp_page_html,
            vlm_action=vlm_action,
            codegen_trace_kind="expected_result",
        )

    if len(indices) > 1:
        logger.info(
            "codegen expected_result repair: multiple lines matched chain/inner; "
            "repairing only the first (Playwright fails on first assertion in order) step_uid=%s indices=%s",
            step_uid,
            indices,
        )
        indices = [indices[0]]

    logger.info(
        "codegen expected_result repair: targeted lines=%s step_uid=%s",
        indices,
        step_uid,
    )
    lines = prev.splitlines()
    out_lines = list(lines)
    for idx in indices:
        orig = out_lines[idx]
        rest_lines = [out_lines[j] for j in range(len(out_lines)) if j != idx]
        rest_ex = "\n".join(rest_lines)
        try:
            fixed = await repair_expected_result_single_assertion_line(
                step_uid=step_uid,
                nl=nl,
                base_url=base_url,
                viewport_w=viewport_w,
                viewport_h=viewport_h,
                before_b64=before_b64,
                after_b64=after_b64,
                failure_screenshot_b64=failure_screenshot_b64,
                original_assertion_line=orig,
                rest_of_fragment_excerpt=rest_ex,
                failed_locator_inner=inner or (chain_literals[0] if chain_literals else ""),
                failed_locator_chain_text=chain_text,
                playwright_error=playwright_error,
                repair_attempt=repair_attempt,
                max_validation_attempts=max_validation_attempts,
                temperature=temperature,
                accessibility_snapshot=accessibility_snapshot,
                prior_failed_wait_chains=prior_failed_wait_chains,
                langchain_callbacks=langchain_callbacks,
                vlm_coords=vlm_coords,
                trace_hint=trace_hint,
                anchor_must_change=anchor_must_change,
                anchor_first_hint=anchor_first_hint,
                mcp_page_html=mcp_page_html,
                vlm_action=vlm_action,
            )
        except Exception as e:
            logger.warning(
                "codegen expected_result targeted repair failed step_uid=%s line_idx=%s: %s — falling back to full repair",
                step_uid,
                idx,
                e,
            )
            return await repair_action_fragment(
                step_uid=step_uid,
                nl=nl,
                base_url=base_url,
                viewport_w=viewport_w,
                viewport_h=viewport_h,
                before_b64=before_b64,
                after_b64=after_b64,
                failure_screenshot_b64=failure_screenshot_b64,
                previous_js=previous_js,
                playwright_error=playwright_error,
                repair_attempt=repair_attempt,
                max_validation_attempts=max_validation_attempts,
                temperature=temperature,
                accessibility_snapshot=accessibility_snapshot,
                prior_failed_wait_chains=prior_failed_wait_chains,
                langchain_callbacks=langchain_callbacks,
                vlm_coords=vlm_coords,
                trace_hint=trace_hint,
                anchor_must_change=anchor_must_change,
                anchor_first_hint=anchor_first_hint,
                mcp_page_html=mcp_page_html,
                vlm_action=vlm_action,
                codegen_trace_kind="expected_result",
            )
        out_lines[idx] = fixed
    return "\n".join(out_lines)


def meta_profile(*, phase: str, attempt: int, codegen_trace_kind: str = "step") -> dict:
    sampling = SAMPLING_DRAFT if phase == "draft" else SAMPLING_REPAIR
    return {
        "profile": phase,
        "model": CODEGEN_AGENT_MODEL_NAME,
        "base_url": CODEGEN_AGENT_BASE_URL,
        "prompt_version": PROMPT_VERSION,
        "attempt": attempt,
        "json_response_format": CODEGEN_JSON_RESPONSE,
        "sampling": {**sampling},
        "codegen_trace_kind": codegen_trace_kind,
    }
