import asyncio
import hmac

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import UUID4
from sqlalchemy.ext.asyncio import AsyncSession

from api.codegen_actions import (internal_append_codegen_log, internal_finalize_codegen,
                                 internal_get_artifact_by_id, internal_report_codegen_failure)
from config import SECRET_KEY_API
from db.session import get_session
from schemas import InternalCodegenFailBody, InternalCodegenFinalizeBody, InternalCodegenLogBody

router = APIRouter(prefix="/api/internal/codegen", tags=["internal-codegen"])


async def verify_internal_token(x_internal_token: str | None = Header(default=None, alias="X-Internal-Token")):
    if not SECRET_KEY_API:
        raise HTTPException(
            status_code=500,
            detail="SECRET_KEY_API not configured on server. Set the SECRET_KEY_API environment variable.",
        )
    if not x_internal_token or not hmac.compare_digest(x_internal_token, SECRET_KEY_API):
        raise HTTPException(status_code=403, detail="Forbidden")


@router.post("/playwright/finalize")
async def internal_finalize(
    body: InternalCodegenFinalizeBody,
    session: AsyncSession = Depends(get_session),
    _auth: None = Depends(verify_internal_token),
):
    aid = await internal_finalize_codegen(
        session,
        case_id=body.case_id,
        source_run_id=body.source_run_id,
        source_code=body.source_code,
        step_spans=body.step_spans,
        steps_content_hash=body.steps_content_hash,
        generator_meta=body.generator_meta,
    )
    return {"artifact_id": str(aid), "status": "ok"}


@router.post("/playwright/fail")
async def internal_fail(
    body: InternalCodegenFailBody,
    _auth: None = Depends(verify_internal_token),
):
    await internal_report_codegen_failure(
        body.case_id,
        message=body.message,
        step_uid=body.step_uid,
        reason_code=body.reason_code,
    )
    return {"status": "ok"}


@router.post("/playwright/log")
async def internal_codegen_log(
    body: InternalCodegenLogBody,
    _auth: None = Depends(verify_internal_token),
):
    await asyncio.to_thread(
        internal_append_codegen_log,
        body.case_id,
        message=body.message,
        level=body.level,
        step_uid=body.step_uid,
        phase=body.phase,
        screenshot_base64=body.screenshot_base64,
        screenshot_mime_type=body.screenshot_mime_type,
        screenshot_minio=body.screenshot_minio,
    )
    return {"status": "ok"}


@router.get("/playwright/artifact/{artifact_id}")
async def internal_artifact_by_id(
    artifact_id: UUID4,
    session: AsyncSession = Depends(get_session),
    _auth: None = Depends(verify_internal_token),
):
    row = await internal_get_artifact_by_id(session, artifact_id)
    return {
        "id": str(row.id),
        "case_id": str(row.case_id),
        "source_run_id": str(row.source_run_id),
        "source_code": row.source_code,
        "step_spans": row.step_spans,
        "steps_content_hash": row.steps_content_hash,
    }
