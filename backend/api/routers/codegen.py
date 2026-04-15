from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import UUID4
from sqlalchemy.ext.asyncio import AsyncSession

from api.codegen_actions import (clear_playwright_codegen_job, delete_playwright_codegen_artifact,
                                 get_playwright_codegen_artifact, get_playwright_codegen_artifact_by_id,
                                 get_playwright_codegen_status, post_start_playwright_codegen)
from db.session import get_session
from dependencies.auth import check_permissions, get_current_active_user
from schemas import PlaywrightCodegenStartBody, UserRead

router = APIRouter(prefix="/api/cases", tags=["codegen"])


@router.post("/{case_id}/codegen/playwright")
async def post_playwright_codegen(
    case_id: UUID4,
    body: PlaywrightCodegenStartBody,
    current_user: UserRead = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_session),
):
    await check_permissions("update_existing_case", current_user.role, current_user.workspace_status)
    return await post_start_playwright_codegen(case_id, body, session, current_user)


@router.get("/{case_id}/codegen/playwright")
async def get_playwright_codegen_route(
    case_id: UUID4,
    run_id: Optional[UUID4] = Query(None),
    host: str | None = Header(None),
    current_user: UserRead = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_session),
):
    await check_permissions("get_case_by_case_id", current_user.role, current_user.workspace_status)
    return await get_playwright_codegen_status(case_id, session, current_user, run_id, host=host)


@router.get("/{case_id}/codegen/playwright/artifacts/{artifact_id}")
async def get_playwright_codegen_artifact_by_id_route(
    case_id: UUID4,
    artifact_id: UUID,
    current_user: UserRead = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_session),
):
    await check_permissions("get_case_by_case_id", current_user.role, current_user.workspace_status)
    return await get_playwright_codegen_artifact_by_id(case_id, artifact_id, session, current_user)


@router.get("/{case_id}/codegen/playwright/artifact")
async def get_playwright_codegen_artifact_route(
    case_id: UUID4,
    current_user: UserRead = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_session),
):
    await check_permissions("get_case_by_case_id", current_user.role, current_user.workspace_status)
    return await get_playwright_codegen_artifact(case_id, session, current_user)


@router.delete("/{case_id}/codegen/playwright/artifact")
async def delete_playwright_codegen_artifact_route(
    case_id: UUID4,
    current_user: UserRead = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_session),
):
    await check_permissions("update_existing_case", current_user.role, current_user.workspace_status)
    return await delete_playwright_codegen_artifact(case_id, session, current_user)


@router.delete("/{case_id}/codegen/playwright/job")
async def delete_playwright_codegen_job_route(
    case_id: UUID4,
    current_user: UserRead = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_session),
):
    await check_permissions("update_existing_case", current_user.role, current_user.workspace_status)
    return await clear_playwright_codegen_job(case_id, session, current_user)
