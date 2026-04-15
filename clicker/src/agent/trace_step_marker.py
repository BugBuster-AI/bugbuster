"""
Маркер step_uid в Playwright trace: console.log в начале каждого шага VLM,
чтобы codegen резал trace.trace по реальным границам NL-шага (см. codegen.vlm_trace_excerpt).
"""
from __future__ import annotations

import json
import logging
from typing import Optional

logger = logging.getLogger("clicker")

# Должен совпадать с парсером в codegen/vlm_trace_excerpt.py
TRACE_STEP_UID_PREFIX = "[BB_STEP_UID]"


async def inject_trace_step_marker(page, step_uid: Optional[str]) -> None:
    """Вызвать в начале итерации шага (после выбора page), до скриншота и действий."""
    if not page or not step_uid or not str(step_uid).strip():
        return
    uid = str(step_uid).strip()
    try:
        pfx = json.dumps(TRACE_STEP_UID_PREFIX)
        await page.evaluate(
            f"(uid) => {{ console.log({pfx} + uid); }}",
            uid,
        )
    except Exception:
        logger.debug("trace step marker inject failed (non-fatal)", exc_info=True)
