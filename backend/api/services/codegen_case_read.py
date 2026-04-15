"""Обогащение CaseRead полями Playwright codegen (Redis job + can_run_playwright_js)."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from api.codegen_actions import get_codegen_job_snapshot
from api.services.codegen_eligibility import CodegenEligibilityService, can_run_playwright_js
from schemas import CaseRead


def parse_codegen_job_updated_at(raw: Any) -> Optional[datetime]:
    if raw is None:
        return None
    if isinstance(raw, datetime):
        return raw
    if isinstance(raw, str):
        try:
            s = raw.replace("Z", "+00:00")
            return datetime.fromisoformat(s)
        except ValueError:
            return None
    return None


async def enrich_case_read_codegen_async(
    session: AsyncSession,
    case_id: UUID,
    base: CaseRead,
    *,
    workspace_id: Optional[UUID] = None,
    user_id: Optional[UUID] = None,
) -> CaseRead:
    """Set can_run_playwright_js + Redis job fields + reference eligibility for codegen UI."""
    can_js = await can_run_playwright_js(session, case_id)
    job = get_codegen_job_snapshot(case_id)
    state: Optional[str] = None
    updated_at: Optional[datetime] = None
    reason_code: Optional[str] = None
    if job:
        st = job.get("state")
        state = str(st) if st is not None else None
        updated_at = parse_codegen_job_updated_at(job.get("updated_at"))
        err = job.get("error")
        if isinstance(err, dict):
            reason_code = err.get("reason_code")
    if state in ("queued", "running", "failure"):
        can_js = False

    ref_ok = False
    ref_reason: Optional[str] = None
    job_running = state in ("queued", "running")
    if workspace_id is not None and user_id is not None:
        ref_ok, ref_reason = await CodegenEligibilityService.codegen_reference_available(
            session,
            case_id,
            workspace_id,
            user_id,
            codegen_job_running=job_running,
        )

    return base.model_copy(
        update={
            "can_run_playwright_js": can_js,
            "codegen_job_state": state,
            "codegen_job_updated_at": updated_at,
            "codegen_job_error_reason_code": reason_code,
            "codegen_can_start_reference": ref_ok,
            "codegen_reference_block_reason": ref_reason,
        }
    )
