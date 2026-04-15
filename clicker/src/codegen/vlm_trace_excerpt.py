"""
Фрагменты нативного Playwright trace (JSONL из trace.zip VLM-прогона) для промпта codegen.

Привязка к step_uid: в начале каждого шага VLM в trace пишется console.log('[BB_STEP_UID]' + uid)
(см. agent.trace_step_marker). Берём compact-строки API между маркерами (или пропорционально).
Полный compact trace читается один раз; refine_trace_excerpt_for_step добавляет строки из всего trace,
релевантные токенам NL/VLM (чтобы длинный сценарий не «терял» нужные click/fill в обрезанном сегменте).
"""
from __future__ import annotations

import io
import json
import logging
import re
import zipfile
from typing import Any, Dict, List, Optional, Set, Tuple

from agent.trace_step_marker import TRACE_STEP_UID_PREFIX
from codegen.codegen_limits import (
    CODEGEN_TRACE_RETRIEVAL,
    GLOBAL_TRACE_HEAD_LINES,
    GLOBAL_TRACE_TAIL_LINES,
    MAX_GLOBAL_TRACE_CHARS,
    MAX_VLM_LOG_CHARS,
    TRACE_RETRIEVAL_MARKER_BOOST,
    TRACE_RETRIEVAL_TOP_N,
    TRACE_RETRIEVAL_WINDOW,
    TRACE_SEGMENT_MAX_CHARS,
)
from core.utils import get_file_from_minio

logger = logging.getLogger("clicker")

TRACE_OBJECT_NAME = "{run_id}_trace.zip"
_BUCKET = "run-cases"

_UID_IN_TRACE_RE = re.compile(
    re.escape(TRACE_STEP_UID_PREFIX) + r"([^\s\"'\\,}\]]+)",
)


def _trace_zip_object_name(run_id: str) -> str:
    return f"{run_id}/{TRACE_OBJECT_NAME.format(run_id=run_id)}"


def extract_uid_from_trace_entry(entry: Dict[str, Any]) -> Optional[str]:
    """Достаёт step_uid из события trace, если в нём есть маркер Bugbuster (console и др.)."""
    blob = json.dumps(entry, ensure_ascii=False)
    if TRACE_STEP_UID_PREFIX not in blob:
        return None
    m = _UID_IN_TRACE_RE.search(blob)
    if not m:
        return None
    uid = (m.group(1) or "").strip()
    return uid if uid else None


# При сериализации params сначала идут поля, полезные для локаторов (selector, position, …).
_PARAM_PRIORITY_KEYS: Tuple[str, ...] = (
    "selector",
    "element",
    "locator",
    "position",
    "point",
    "location",
    "text",
    "value",
    "data",
    "modifiers",
    "button",
    "clickCount",
    "delay",
    "timeout",
    "force",
    "trial",
    "options",
)


def _serialize_params_for_codegen(params: Any, max_len: int = 700) -> str:
    if params is None:
        return ""
    if isinstance(params, dict):
        ordered: Dict[str, Any] = {}
        rest: Dict[str, Any] = {}
        for k in _PARAM_PRIORITY_KEYS:
            if k in params:
                ordered[k] = params[k]
        for k, v in params.items():
            if k not in ordered:
                rest[k] = v
        merged = {**ordered, **rest}
        try:
            p = json.dumps(merged, ensure_ascii=False)
        except (TypeError, ValueError):
            p = str(merged)
    else:
        try:
            p = json.dumps(params, ensure_ascii=False)
        except (TypeError, ValueError):
            p = str(params)
    if len(p) > max_len:
        p = p[:max_len] + "…"
    return p


def _compact_trace_entry(entry: Dict[str, Any]) -> Optional[str]:
    """Одна строка из trace.trace: только события с metadata (реальные вызовы Playwright API)."""
    meta = entry.get("metadata")
    if not isinstance(meta, dict):
        return None
    api = (meta.get("apiName") or meta.get("method") or "").strip()
    if not api:
        return None
    params = meta.get("params")
    p = _serialize_params_for_codegen(params, max_len=700)
    return f"{api} {p}" if p else api


def _read_trace_jsonl(zip_bytes: bytes) -> List[Tuple[int, Dict[str, Any]]]:
    """(номер_строки_1based, entry) для каждой строки trace.trace."""
    out: List[Tuple[int, Dict[str, Any]]] = []
    try:
        with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zf:
            names = zf.namelist()
            trace_name = "trace.trace"
            if trace_name not in names:
                cand = [n for n in names if n.endswith("trace.trace") or n.endswith("/trace.trace")]
                trace_name = cand[0] if cand else ""
            if not trace_name:
                logger.warning("codegen vlm trace: no trace.trace in zip (%s)", names[:8])
                return out
            raw = zf.read(trace_name).decode("utf-8", errors="replace")
    except (zipfile.BadZipFile, KeyError, OSError) as e:
        logger.warning("codegen vlm trace: cannot read zip: %s", e)
        return out

    for line_no, line in enumerate(raw.splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(entry, dict):
            continue
        out.append((line_no, entry))
    return out


def _collect_markers(entries: List[Tuple[int, Dict[str, Any]]]) -> List[Tuple[int, str]]:
    markers: List[Tuple[int, str]] = []
    for line_no, entry in entries:
        uid = extract_uid_from_trace_entry(entry)
        if uid:
            markers.append((line_no, uid))
    return markers


def _compact_lines_indexed(entries: List[Tuple[int, Dict[str, Any]]]) -> List[Tuple[int, str]]:
    out: List[Tuple[int, str]] = []
    for line_no, entry in entries:
        c = _compact_trace_entry(entry)
        if c:
            out.append((line_no, c))
    return out


_TRACE_STOP = frozenset(
    {
        "the",
        "a",
        "an",
        "and",
        "or",
        "to",
        "of",
        "in",
        "on",
        "for",
        "is",
        "are",
        "as",
        "at",
        "be",
        "by",
        "it",
        "как",
        "что",
        "это",
        "в",
        "на",
        "и",
        "по",
        "из",
        "не",
        "с",
        "к",
        "а",
        "же",
        "у",
        "от",
        "до",
        "за",
        "при",
    }
)


def _truncate_excerpt(text: str, max_chars: int) -> str:
    t = (text or "").strip()
    if len(t) > max_chars:
        return t[:max_chars] + "\n...[trace excerpt truncated]"
    return t


def _trace_query_tokens(nl: str, run_step: Optional[dict]) -> Set[str]:
    parts: List[str] = []
    if nl:
        parts.append(nl)
    if isinstance(run_step, dict):
        if run_step.get("action") is not None:
            parts.append(str(run_step["action"]))
        ad = run_step.get("action_details")
        if isinstance(ad, dict):
            if ad.get("text") is not None and str(ad.get("text")).strip():
                parts.append(str(ad["text"]))
    blob = " ".join(parts)
    tokens: Set[str] = set()
    for m in re.finditer(r"[\w\-]+", blob, re.UNICODE):
        w = m.group(0).lower()
        if len(w) < 2:
            continue
        if w in _TRACE_STOP:
            continue
        tokens.add(w)
    return tokens


def _compact_range_for_trace_lines(
    compact_indexed: List[Tuple[int, str]],
    lo_ln: int,
    hi_ln: int,
) -> Tuple[int, int]:
    """Индексы в compact_indexed: строки trace с line_no в [lo_ln, hi_ln)."""
    n = len(compact_indexed)
    i0 = n
    for i, (ln, _) in enumerate(compact_indexed):
        if ln >= lo_ln:
            i0 = i
            break
    for i, (ln, _) in enumerate(compact_indexed):
        if ln >= hi_ln:
            return (i0, i)
    return (i0, n)


def _trace_line_bounds_for_uids(
    markers: List[Tuple[int, str]],
    action_uids: List[str],
) -> Dict[str, Tuple[int, int]]:
    first_line_by_uid: Dict[str, int] = {}
    for line_no, u in sorted(markers, key=lambda x: x[0]):
        if u not in first_line_by_uid:
            first_line_by_uid[u] = line_no
    out: Dict[str, Tuple[int, int]] = {}
    hi_inf = 10**12
    for i, uid in enumerate(action_uids):
        if not uid or uid not in first_line_by_uid:
            continue
        start = first_line_by_uid[uid]
        if i + 1 < len(action_uids):
            nu = action_uids[i + 1]
            if nu not in first_line_by_uid:
                continue
            end = first_line_by_uid[nu]
            lo_ln = start + 1
            hi_ln = end
        else:
            lo_ln = start + 1
            hi_ln = hi_inf
        out[uid] = (lo_ln, hi_ln)
    return out


def refine_trace_excerpt_for_step(
    nl: str,
    run_step: Optional[dict],
    base_excerpt: str,
    compact_indexed: List[Tuple[int, str]],
    compact_bounds: Optional[Tuple[int, int]] = None,
) -> str:
    """
    Полный compact trace уже в памяти: маркерный/пропорциональный сегмент (base_excerpt)
    дополняется строками с совпадением токенов NL/VLM; строки внутри границ шага получают boost.
    """
    if not CODEGEN_TRACE_RETRIEVAL or not compact_indexed:
        return _truncate_excerpt(base_excerpt, TRACE_SEGMENT_MAX_CHARS)

    tokens = _trace_query_tokens(nl, run_step)
    if not tokens:
        return _truncate_excerpt(base_excerpt, TRACE_SEGMENT_MAX_CHARS)

    n = len(compact_indexed)
    scores = [0] * n
    for i, (_, text) in enumerate(compact_indexed):
        low = text.lower()
        for t in tokens:
            if len(t) >= 2 and t in low:
                scores[i] += 1
        if compact_bounds:
            lo, hi = compact_bounds
            if lo <= i < hi:
                scores[i] += TRACE_RETRIEVAL_MARKER_BOOST

    chosen: Set[int] = set()
    base_lines = {ln.strip() for ln in str(base_excerpt).splitlines() if ln.strip()}
    for i, (_, text) in enumerate(compact_indexed):
        tx = text.strip()
        if tx in base_lines:
            chosen.add(i)
            for d in range(-TRACE_RETRIEVAL_WINDOW, TRACE_RETRIEVAL_WINDOW + 1):
                j = i + d
                if 0 <= j < n:
                    chosen.add(j)

    ranked = [i for i in range(n) if scores[i] > 0]
    ranked.sort(key=lambda i: scores[i], reverse=True)
    for i in ranked[:TRACE_RETRIEVAL_TOP_N]:
        chosen.add(i)
        for d in range(-TRACE_RETRIEVAL_WINDOW, TRACE_RETRIEVAL_WINDOW + 1):
            j = i + d
            if 0 <= j < n:
                chosen.add(j)

    if not chosen:
        return _truncate_excerpt(base_excerpt, TRACE_SEGMENT_MAX_CHARS)

    ordered = sorted(chosen)
    text = "\n".join(compact_indexed[i][1] for i in ordered)
    return _truncate_excerpt(text, TRACE_SEGMENT_MAX_CHARS)


def _segment_lines(lines: List[str], ordinal: int, n_segments: int) -> str:
    if not lines or n_segments <= 0:
        return ""
    if ordinal < 0:
        ordinal = 0
    if ordinal >= n_segments:
        ordinal = n_segments - 1
    n = len(lines)
    start = (ordinal * n) // n_segments
    end = ((ordinal + 1) * n) // n_segments
    if end <= start and start < n:
        end = start + 1
    chunk = lines[start:end]
    text = "\n".join(chunk)
    max_chars = TRACE_SEGMENT_MAX_CHARS
    if len(text) > max_chars:
        text = text[:max_chars] + "\n...[trace excerpt truncated]"
    return text


def _segment_by_step_uid_markers(
    markers: List[Tuple[int, str]],
    compact_indexed: List[Tuple[int, str]],
    action_uids: List[str],
) -> Optional[Dict[str, str]]:
    """
    Границы: первое по времени появление каждого uid в маркерах (первый шаг, первый retry — один uid,
    граница между шагами — по первому маркеру следующего step_uid).
    """
    if not action_uids:
        return {}

    first_line_by_uid: Dict[str, int] = {}
    for line_no, u in sorted(markers, key=lambda x: x[0]):
        if u not in first_line_by_uid:
            first_line_by_uid[u] = line_no

    out: Dict[str, str] = {}
    hi_inf = 10**12

    for i, uid in enumerate(action_uids):
        if not uid:
            continue
        if uid not in first_line_by_uid:
            return None
        start = first_line_by_uid[uid]
        if i + 1 < len(action_uids):
            nu = action_uids[i + 1]
            if nu not in first_line_by_uid:
                return None
            end = first_line_by_uid[nu]
            if end <= start:
                return None
            lo = start + 1
            hi = end
        else:
            lo = start + 1
            hi = hi_inf

        chunk = [t for ln, t in compact_indexed if lo <= ln < hi]
        text = "\n".join(chunk)
        max_chars = TRACE_SEGMENT_MAX_CHARS
        if len(text) > max_chars:
            text = text[:max_chars] + "\n...[trace excerpt truncated]"
        if text:
            out[uid] = text

    return out if out else None


def segment_trace_for_flat(
    zip_bytes: bytes,
    flat: List[Dict[str, Any]],
) -> Tuple[Dict[str, str], List[Tuple[int, str]], Dict[str, Optional[Tuple[int, int]]]]:
    """
    (1) step_uid -> текстовый фрагмент trace для kind==action (маркеры или пропорционально).
    (2) полный compact_indexed — для retrieval по всему trace.
    (3) границы шага в индексах compact (для boost в refine_trace_excerpt_for_step).
    """
    action_items = [x for x in flat if x.get("kind") == "action"]
    bounds_by_uid: Dict[str, Optional[Tuple[int, int]]] = {}
    if not action_items:
        return {}, [], {}

    action_uids = [str(x.get("step_uid") or "") for x in action_items]
    entries = _read_trace_jsonl(zip_bytes)
    if not entries:
        return {}, [], {}

    markers = _collect_markers(entries)
    compact_indexed = _compact_lines_indexed(entries)

    if markers:
        by_uid = _segment_by_step_uid_markers(markers, compact_indexed, action_uids)
        if by_uid is not None:
            logger.info("codegen vlm trace: segmented by step_uid markers (%s markers)", len(markers))
            line_bounds = _trace_line_bounds_for_uids(markers, action_uids)
            for uid in action_uids:
                if not uid:
                    continue
                if uid in line_bounds:
                    lo_ln, hi_ln = line_bounds[uid]
                    bounds_by_uid[uid] = _compact_range_for_trace_lines(compact_indexed, lo_ln, hi_ln)
                else:
                    bounds_by_uid[uid] = None
            return by_uid, compact_indexed, bounds_by_uid
        logger.info(
            "codegen vlm trace: markers present but incomplete for all steps → fallback to proportional",
        )

    lines = [t for _, t in compact_indexed]
    n_seg = len(action_items)
    n = len(compact_indexed)
    out: Dict[str, str] = {}
    for i, item in enumerate(action_items):
        uid = str(item.get("step_uid") or "")
        excerpt = _segment_lines(lines, i, n_seg)
        if excerpt:
            out[uid] = excerpt
        start = (i * n) // n_seg if n else 0
        end = ((i + 1) * n) // n_seg if n else 0
        if n and end <= start and start < n:
            end = start + 1
        bounds_by_uid[uid] = (start, end) if n else None
    return out, compact_indexed, bounds_by_uid


def global_trace_compact_summary(zip_bytes: bytes) -> str:
    """Начало и конец компактных строк API по всему trace.trace (тот же zip, что и сегменты по шагам)."""
    if not zip_bytes:
        return ""
    entries = _read_trace_jsonl(zip_bytes)
    if not entries:
        return ""
    compact_indexed = _compact_lines_indexed(entries)
    lines = [t for _, t in compact_indexed]
    if not lines:
        return ""
    h = max(0, int(GLOBAL_TRACE_HEAD_LINES))
    t = max(0, int(GLOBAL_TRACE_TAIL_LINES))
    head = lines[:h]
    parts: List[str] = []
    if head:
        parts.append("--- trace begin (compact API lines) ---\n" + "\n".join(head))
    if t and len(lines) > h:
        tail = lines[-t:]
        parts.append("--- trace end (compact API lines) ---\n" + "\n".join(tail))
    text = "\n\n".join(parts)
    if len(text) > MAX_GLOBAL_TRACE_CHARS:
        text = text[:MAX_GLOBAL_TRACE_CHARS] + "\n...[global trace truncated]"
    return text


def extract_trace_hint_from_excerpt(excerpt: Optional[str]) -> str:
    """
    Короткая подсказка для repair: первая строка click/fill с selector/position/locator в compact trace.
    """
    if not excerpt or not str(excerpt).strip():
        return ""
    lines = [ln.strip() for ln in str(excerpt).splitlines() if ln.strip()]
    for line in lines:
        low = line.lower()
        if any(k in low for k in ("click", "fill", "dblclick", "tap", "press", "type")):
            if any(k in low for k in ("selector", "position", "locator", "point", "element")):
                return line[:800]
    return lines[0][:400] if lines else ""


def download_run_log_excerpt(run_id: str, max_chars: Optional[int] = None) -> str:
    """Хвост лога VLM-агента из MinIO {run_id}/{run_id}.log (если объект есть)."""
    mc = max_chars if max_chars is not None else MAX_VLM_LOG_CHARS
    path = f"{run_id}/{run_id}.log"
    try:
        raw = get_file_from_minio(_BUCKET, path)
    except Exception as e:
        logger.debug("codegen vlm log: minio get %s: %s", path, e)
        return ""
    if not raw:
        return ""
    text = raw.decode("utf-8", errors="replace")
    if len(text) > mc:
        text = "...[log truncated]\n" + text[-mc:]
    return text


def download_run_trace_zip_bytes(run_id: str) -> Optional[bytes]:
    """Скачать {run_id}_trace.zip из MinIO (тот же объект, что заливает graph после VLM)."""
    path = _trace_zip_object_name(run_id)
    try:
        return get_file_from_minio(_BUCKET, path)
    except Exception as e:
        logger.warning("codegen vlm trace: minio get %s: %s", path, e)
        return None
