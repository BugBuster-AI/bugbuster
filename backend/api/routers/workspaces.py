

from datetime import datetime
from typing import Dict, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, Header, Query
from pydantic import UUID4, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from api.actions import check_usage_limits, usage_summary
from api.workspace_actions import (accept_invite, change_user_avatar_workspace,
                                   change_user_workspace,
                                   change_user_workspace_name,
                                   edit_user_workspace,
                                   get_workspace_memberships,
                                   invite_user_workspace, list_user_workspace,
                                   remove_user_workspace, user_workspace_by_id,
                                   workspace_log)
from db.session import get_session
from dependencies.auth import check_permissions, get_current_active_user
from schemas import EditUserWorkspace, InviteUserRequest, UserRead

router = APIRouter(prefix="/api/workspace", tags=["workspace"])


@router.get("/get_workspace_memberships_list")
async def get_workspace_memberships_list(current_user: UserRead = Depends(get_current_active_user),
                                         session: AsyncSession = Depends(get_session),
                                         host: str = Header(None),
                                         role_filter: Optional[str] = None,
                                         status_filter: Optional[str] = None,
                                         role_title_filter: Optional[str] = None,
                                         last_action_filter_start_dt: Optional[datetime] = None,
                                         last_action_filter_end_dt: Optional[datetime] = None,
                                         limit: int = Query(5, le=15),
                                         offset: int = 0):
    await check_permissions("get_workspace_memberships_list", current_user.role, current_user.workspace_status)
    return await get_workspace_memberships(current_user, session, host, role_filter, status_filter,
                                           role_title_filter, last_action_filter_start_dt,
                                           last_action_filter_end_dt, limit, offset)


@router.get("/get_workspace_log")
async def get_workspace_log(current_user: UserRead = Depends(get_current_active_user),
                            session: AsyncSession = Depends(get_session),
                            host: str = Header(None),
                            user_email: Optional[str] = None,
                            start_dt: Optional[datetime] = None,
                            end_dt: Optional[datetime] = None,
                            limit: int = Query(10, le=100),
                            offset: int = 0):
    # await check_permissions("get_workspace_log", current_user.role, current_user.workspace_status)
    return await workspace_log(current_user, session, host, user_email, start_dt, end_dt, limit, offset)


@router.post("/invite_user")
async def invite_user(invite: InviteUserRequest,
                      background_tasks: BackgroundTasks,
                      current_user: UserRead = Depends(get_current_active_user),
                      session: AsyncSession = Depends(get_session),
                      host: str = Header(None)):

    await check_permissions("invite_user", current_user.role, current_user.workspace_status)
    await check_usage_limits(current_user.active_workspace_id, "invite_user_workspace", session)
    return await invite_user_workspace(invite, background_tasks, current_user, session, host)


@router.put("/edit_user_workspace_membership")
async def edit_user_workspace_membership(membership: EditUserWorkspace,
                                         current_user: UserRead = Depends(get_current_active_user),
                                         session: AsyncSession = Depends(get_session)):

    await check_permissions("edit_user_workspace_membership", current_user.role, current_user.workspace_status)
    return await edit_user_workspace(membership, current_user, session)


@router.delete("/remove_user_workspace_membership")
async def remove_user_workspace_membership(email: EmailStr,
                                           current_user: UserRead = Depends(get_current_active_user),
                                           session: AsyncSession = Depends(get_session)):

    await check_permissions("remove_user_workspace_membership", current_user.role, current_user.workspace_status)
    return await remove_user_workspace(email, current_user, session)


@router.get("/get_list_user_workspaces")
async def get_list_user_workspaces(current_user: UserRead = Depends(get_current_active_user),
                                   session: AsyncSession = Depends(get_session)):

    return await list_user_workspace(current_user, session)


@router.get("/get_user_workspace_by_id")
async def get_user_workspace_by_id(workspace_id: UUID4,
                                   current_user: UserRead = Depends(get_current_active_user),
                                   session: AsyncSession = Depends(get_session)):

    return await user_workspace_by_id(workspace_id, current_user, session)


@router.get("/get_usage_summary")
async def get_usage_summary(current_user: UserRead = Depends(get_current_active_user),
                            session: AsyncSession = Depends(get_session)):

    return await usage_summary(current_user.active_workspace_id, session)


@router.post("/change_user_active_workspace")
async def change_user_active_workspace(workspace_id: UUID4,
                                       current_user: UserRead = Depends(get_current_active_user),
                                       session: AsyncSession = Depends(get_session)):

    return await change_user_workspace(workspace_id, current_user, session)


@router.post("/change_user_active_workspace_name")
async def change_user_active_workspace_name(new_name: str,
                                            current_user: UserRead = Depends(get_current_active_user),
                                            session: AsyncSession = Depends(get_session)):

    return await change_user_workspace_name(new_name, current_user, session)


@router.post("/change_user_avatar_active_workspace")
async def change_user_avatar_active_workspace(avatar: dict,
                                              current_user: UserRead = Depends(get_current_active_user),
                                              session: AsyncSession = Depends(get_session)):

    return await change_user_avatar_workspace(avatar, current_user, session)


@router.post("/accept_invite_token")
async def accept_invite_token(token: str,
                              session: AsyncSession = Depends(get_session)):
    return await accept_invite(token, session)
