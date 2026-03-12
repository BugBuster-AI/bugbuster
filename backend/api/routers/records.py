
from typing import Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Header
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import UUID4
from api.record_actions import (delete_happy_pass, happy_pass_update_autosop,
                                happy_passes_get_full, happy_passes_get_list,
                                happypass_update_action_plan, check_user_workspace_recording_available)
from db.session import get_session
from dependencies.auth import check_permissions, get_current_active_user
from schemas import UserRead

router = APIRouter(prefix="/api/records", tags=["records"])


@router.get("/check_workspace_recording_available")
async def check_workspace_recording_available(workspace_id: UUID4,
                                              current_user: UserRead = Depends(get_current_active_user),
                                              session: AsyncSession = Depends(get_session)):

    return await check_user_workspace_recording_available(workspace_id, session, current_user)


@router.get("/list_happypass")
async def happy_passes_list(project_id: UUID4,
                            current_user: UserRead = Depends(get_current_active_user),
                            session: AsyncSession = Depends(get_session)):
    """
    только id, name, context для скорости
    """
    await check_permissions("happy_passes_list", current_user.role, current_user.workspace_status)
    return await happy_passes_get_list(project_id, session, current_user)


@router.get("/happypass")
async def happy_passes_full(project_id: UUID4,
                            current_user: UserRead = Depends(get_current_active_user),
                            session: AsyncSession = Depends(get_session),
                            host: str = Header(None),
                            happy_pass_id: Optional[UUID] = Query(None),
                            name: Optional[str] = Query(None),
                            context: Optional[str] = Query(None),
                            limit: int = Query(5, le=25),
                            offset: int = 0):
    """
    один по id или все
    """
    await check_permissions("happy_passes_full", current_user.role, current_user.workspace_status)
    return await happy_passes_get_full(project_id, session, current_user, host,
                                       happy_pass_id, name, context, limit, offset)


@router.put("/happypass_autosop_generate")
async def happypass_autosop_generate(happy_pass_id: UUID,
                                     current_user: UserRead = Depends(get_current_active_user),
                                     host: str = Header(None)):
    """сгенерировать автосоп """
    await check_permissions("happypass_autosop_generate", current_user.role, current_user.workspace_status)
    return await happy_pass_update_autosop(current_user.active_workspace_id,
                                           current_user.user_id, happy_pass_id, 600, host)

# ! not use
# @router.put("/happypass_action_plan_update")
# async def happypass_action_plan_update(happy_pass_id: UUID,
#                                        action_plan: Optional[List[Dict]] = None,
#                                        current_user: UserRead = Depends(get_current_active_user),
#                                        host: str = Header(None)):
#     """юзер меняет экшен план вручную"""
#     await check_permissions("happypass_action_plan_update", current_user.role, current_user.workspace_status)
#     return await happypass_update_action_plan(current_user, happy_pass_id, action_plan, host)


@router.delete("/happypass/{happy_pass_id}")
async def delete_existing_happy_pass(happy_pass_id: UUID,
                                     current_user: UserRead = Depends(get_current_active_user),
                                     session: AsyncSession = Depends(get_session)):
    await check_permissions("delete_existing_happy_pass", current_user.role, current_user.workspace_status)
    return await delete_happy_pass(session, current_user, happy_pass_id)
