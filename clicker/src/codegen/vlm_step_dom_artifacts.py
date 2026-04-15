"""
Загрузка артефактов VLM DOM (before-step) из MinIO для codegen.
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, Optional

from core.utils import get_file_from_minio

logger = logging.getLogger("clicker")

_BUCKET = "run-cases"

_ALLOWED_BUCKETS = frozenset({"run-cases", "screenshots"})
_PATH_TRAVERSAL_RE = re.compile(r"(^|/)\.\.(/|$)")


def _safe_uid(step_uid: str) -> str:
    return str(step_uid).replace("/", "_").replace("\\", "_")


def _minio_ref_path(ref: Any) -> Optional[tuple]:
    if not isinstance(ref, dict):
        return None
    b = ref.get("bucket")
    f = ref.get("file")
    if not b or not f:
        return None
    bucket = str(b).strip()
    file_key = str(f).strip()
    if bucket not in _ALLOWED_BUCKETS:
        logger.warning("vlm dom: rejected bucket %r (not in allowlist)", bucket)
        return None
    if _PATH_TRAVERSAL_RE.search(file_key) or file_key.startswith("/"):
        logger.warning("vlm dom: rejected file key %r (path traversal)", file_key)
        return None
    return (bucket, file_key)


def download_focus_dom_json_text_from_run_step(run_step: Optional[dict]) -> str:
    """Текст JSON focused bundle из поля run_step.dom_before_focus (MinIO ref)."""
    if not run_step or not isinstance(run_step, dict):
        return ""
    ref = run_step.get("dom_before_focus")
    path = _minio_ref_path(ref)
    if not path:
        return ""
    try:
        raw = get_file_from_minio(path[0], path[1])
        return raw.decode("utf-8", errors="replace")
    except Exception as e:
        logger.debug("vlm dom focus: minio get %s/%s: %s", path[0], path[1], e)
        return ""


def download_full_html_by_run_path(run_id: str, step_uid: str) -> str:
    """Fallback: {run_id}/vlm_dom/{step_uid}.before.full.html без ref в run_step."""
    if not run_id or not step_uid:
        return ""
    key = f"{run_id}/vlm_dom/{_safe_uid(step_uid)}.before.full.html"
    try:
        raw = get_file_from_minio(_BUCKET, key)
        return raw.decode("utf-8", errors="replace")
    except Exception as e:
        logger.debug("vlm dom full fallback %s: %s", key, e)
        return ""


def download_focus_dom_by_run_path(run_id: str, step_uid: str) -> str:
    """Fallback: {run_id}/vlm_dom/{step_uid}.before.focus.json без ref в run_step."""
    if not run_id or not step_uid:
        return ""
    key = f"{run_id}/vlm_dom/{_safe_uid(step_uid)}.before.focus.json"
    try:
        raw = get_file_from_minio(_BUCKET, key)
        return raw.decode("utf-8", errors="replace")
    except Exception as e:
        logger.debug("vlm dom focus fallback %s: %s", key, e)
        return ""


def focused_json_to_llm_text(json_text: str, max_chars: int) -> str:
    """Превращает JSON focused в компактный текст для промпта."""
    if not json_text or not str(json_text).strip():
        return ""
    try:
        data = json.loads(json_text)
    except json.JSONDecodeError:
        return json_text.strip()[:max_chars]
    from codegen.vlm_dom_focus import focused_dom_bundle_to_prompt_text

    if not isinstance(data, dict):
        return str(data)[:max_chars]
    return focused_dom_bundle_to_prompt_text(data, max_chars)


def download_full_html_from_run_step(run_step: Optional[dict]) -> str:
    """Полный HTML из dom_before_full (опционально для repair/diagnostics)."""
    if not run_step or not isinstance(run_step, dict):
        return ""
    ref = run_step.get("dom_before_full")
    path = _minio_ref_path(ref)
    if not path:
        return ""
    try:
        raw = get_file_from_minio(path[0], path[1])
        return raw.decode("utf-8", errors="replace")
    except Exception as e:
        logger.debug("vlm dom full: minio get: %s", e)
        return ""
