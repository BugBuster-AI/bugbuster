"""
Сохранение DOM до шага VLM (page.content + focused JSON) в MinIO для codegen.
Путь: {run_id}/vlm_dom/{step_uid}.before.full.html и .before.focus.json
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Any, Dict, Optional

from codegen.vlm_dom_focus import build_focused_dom_bundle

logger = logging.getLogger("clicker")

VLM_SAVE_STEP_HTML = os.getenv("VLM_SAVE_STEP_HTML", "1").strip().lower() not in (
    "0",
    "false",
    "no",
    "",
)
VLM_DOM_MAX_FULL_BYTES = int(os.getenv("VLM_DOM_MAX_FULL_BYTES", "1500000"))
VLM_DOM_FOCUS_SNIPPET_CHARS = int(os.getenv("VLM_DOM_FOCUS_SNIPPET_CHARS", "8000"))
VLM_DOM_FOCUS_MAX_CANDIDATES = int(os.getenv("VLM_DOM_FOCUS_MAX_CANDIDATES", "40"))


def _safe_step_uid(step_uid: str) -> str:
    return str(step_uid).replace("/", "_").replace("\\", "_")


async def capture_vlm_step_dom_before(
    page: Any,
    run_id: str,
    step_uid: str,
    viewport_w: int,
    viewport_h: int,
) -> Optional[Dict[str, Any]]:
    """
    Снимает DOM до действия шага, заливает full HTML + focused JSON в MinIO.
    Возвращает dict с ключами dom_before_full, dom_before_focus (MinioObjectPath-совместимые dict)
    или None при отключении/ошибке.
    """
    if not VLM_SAVE_STEP_HTML:
        return None
    if not page or not run_id or not step_uid or not str(step_uid).strip():
        return None

    from core.utils import upload_text_to_minio

    su = _safe_step_uid(step_uid)
    try:
        html = await page.content()
        purl = ""
        try:
            purl = page.url or ""
        except Exception:
            pass
    except Exception:
        logger.debug("vlm_step_dom: page.content failed", exc_info=True)
        return None

    raw_bytes = html.encode("utf-8")
    if len(raw_bytes) > VLM_DOM_MAX_FULL_BYTES:
        # Обрезка по байтам — аккуратно по границе UTF-8
        cut = raw_bytes[:VLM_DOM_MAX_FULL_BYTES]
        while cut and (cut[-1] & 0x80) and not (cut[-1] & 0x40):
            cut = cut[:-1]
        html = cut.decode("utf-8", errors="ignore") + "\n<!-- vlm_dom truncated -->\n"

    bundle = build_focused_dom_bundle(
        html,
        url=purl,
        max_candidates=VLM_DOM_FOCUS_MAX_CANDIDATES,
        max_snippet_chars=VLM_DOM_FOCUS_SNIPPET_CHARS,
    )
    bundle["viewport"] = {"width": int(viewport_w), "height": int(viewport_h)}
    bundle["step_uid"] = str(step_uid)

    focus_body = json.dumps(bundle, ensure_ascii=False, separators=(",", ":"))

    try:
        ref_full = await asyncio.to_thread(
            upload_text_to_minio,
            html,
            run_id,
            f"vlm_dom/{su}.before.full.html",
            "text/html; charset=utf-8",
        )
        ref_focus = await asyncio.to_thread(
            upload_text_to_minio,
            focus_body,
            run_id,
            f"vlm_dom/{su}.before.focus.json",
            "application/json; charset=utf-8",
        )
    except Exception:
        logger.warning("vlm_step_dom: minio upload failed", exc_info=True)
        return None

    logger.info(
        "vlm_step_dom: saved before-step DOM run_id=%s step_uid=%s full_bytes=%s focus_json_chars=%s",
        run_id,
        step_uid,
        len(html.encode("utf-8")),
        len(focus_body),
    )
    return {
        "dom_before_full": ref_full,
        "dom_before_focus": ref_focus,
    }
