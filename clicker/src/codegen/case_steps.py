"""Сопоставление шагов кейса с run_cases.steps и вспомогательные фрагменты API."""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Tuple

AUTORUN_SECTIONS = ("before_browser_start", "before_steps", "steps", "after_steps")


def _norm_nl(step: Any) -> str:
    if isinstance(step, str):
        return step.strip()
    if isinstance(step, dict) and step.get("value") is not None:
        return str(step.get("value")).strip()
    return ""


def case_step_kind(raw: Any) -> str:
    if isinstance(raw, str):
        return "action"
    if not isinstance(raw, dict):
        return "action"
    t = raw.get("type")
    if t == "api":
        return "api"
    if t == "expected_result":
        return "expected_result"
    return "action"


def api_step_to_js(raw: dict, step_uid: str) -> str:
    method = str(raw.get("method", "GET")).upper()
    url = str(raw.get("url", ""))
    lines = [f"  // step_uid:{step_uid} api"]
    opts: Dict[str, Any] = {"method": method}
    extra = raw.get("extra") or {}
    if isinstance(extra, dict):
        headers = extra.get("headers")
        if isinstance(headers, dict) and headers:
            opts["headers"] = headers
    val = raw.get("value")
    if val is not None and val != "":
        if isinstance(val, (dict, list)):
            opts["data"] = val
        else:
            opts["data"] = str(val)
    lines.append(f"  await request.fetch({json.dumps(url)}, {json.dumps(opts, ensure_ascii=False)});")
    return "\n".join(lines) + "\n"


def flatten_case_with_run_indices(case_json: dict) -> List[Dict[str, Any]]:
    """
    Элементы в том же порядке, что process_prepare_case_steps_web.
    Для каждого элемента: run_index, kind, step_uid, nl, raw_case_step, run_step placeholder.
    """
    out: List[Dict[str, Any]] = []
    run_idx = 0
    for sec in AUTORUN_SECTIONS:
        arr = case_json.get(sec) or []
        if not isinstance(arr, list):
            continue
        for raw in arr:
            kind = case_step_kind(raw)
            uid = None
            if isinstance(raw, dict):
                uid = raw.get("step_uid")
            if not uid:
                uid = f"idx_{run_idx}"
            nl = _norm_nl(raw)
            out.append(
                {
                    "run_index": run_idx,
                    "section": sec,
                    "kind": kind,
                    "step_uid": str(uid),
                    "nl": nl,
                    "raw": raw,
                }
            )
            run_idx += 1
    return out


def effective_step_uid(item: Dict[str, Any]) -> str:
    """
    Предпочитает step_uid из записи рана (run_cases.steps), совпадает с MinIO vlm_dom/{step_uid}.*;
    иначе step_uid из плоского кейса (в т.ч. idx_N).
    """
    rs = item.get("run_step")
    if isinstance(rs, dict):
        u = rs.get("step_uid")
        if u is not None and str(u).strip():
            return str(u).strip()
    u = item.get("step_uid")
    return str(u) if u is not None else ""


def attach_run_steps(
    flat: List[Dict[str, Any]],
    run_steps: Optional[List],
) -> None:
    if not run_steps:
        return
    for item in flat:
        ri = item["run_index"]
        if 0 <= ri < len(run_steps):
            item["run_step"] = run_steps[ri]


def nl_for_codegen(item: Dict[str, Any]) -> str:
    """
    Текст шага для LLM (codegen): если в записи запуска есть непустой
    raw_step_description — оригинал шага без подстановки переменных из кейса;
    иначе nl из версии кейса (как в flatten_case_with_run_indices).
    """
    run_step = item.get("run_step")
    if isinstance(run_step, dict):
        raw = run_step.get("raw_step_description")
        if raw is not None and str(raw).strip():
            return str(raw).strip()
    return str(item.get("nl") or "").strip()


def nl_hash_vectors(
    case_json: dict,
    run_steps: Optional[List] = None,
) -> List[Tuple[str, int, str, str]]:
    """
    Векторы для steps_content_hash: (section, index_in_section, case_nl, run_raw_or_empty).
    Порядок и run_index совпадают с flatten_case_with_run_indices.
    """
    out: List[Tuple[str, int, str, str]] = []
    run_idx = 0
    for sec in AUTORUN_SECTIONS:
        arr = case_json.get(sec) or []
        if not isinstance(arr, list):
            continue
        for i, raw in enumerate(arr):
            case_nl = _norm_nl(raw)
            run_raw = ""
            if run_steps and 0 <= run_idx < len(run_steps):
                rs = run_steps[run_idx]
                if isinstance(rs, dict):
                    r = rs.get("raw_step_description")
                    if r is not None and str(r).strip():
                        run_raw = str(r).strip()
            out.append((sec, i, case_nl, run_raw))
            run_idx += 1
    return out
