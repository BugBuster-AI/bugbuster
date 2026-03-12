from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from fastapi_pagination import Page
from pydantic import UUID4
from sqlalchemy.ext.asyncio import AsyncSession

from api.actions import (activate_or_renew_workspace_tariff, block_user,
                         change_workspace_tariff, deactivate_workspace,
                         get_user, get_users, list_tariffs,
                         tariff_all_limits_by_tariff_id, tariff_by_id,
                         tariff_limit_by_id, unlock_user)
from db.session import get_session
from dependencies.auth import check_permissions, get_current_active_user
from schemas import Roles, TariffLimitRead, TariffRead, UserId, UserRead

router = APIRouter(prefix="/api/admin_content", tags=["system_content"])


@router.get("/ping")
async def ping():
    return JSONResponse(content="pong")


@router.get("/list_roles")
async def list_roles(current_user=Depends(get_current_active_user)):
    return JSONResponse(content=[role.value for role in Roles])


@router.get("/list_users", response_model=Page[UserRead])
async def list_users(offset: int = 0, limit: int = Query(10, le=1000),
                     session: AsyncSession = Depends(get_session),
                     current_user=Depends(get_current_active_user)):
    await check_permissions("list_users", current_user.role)
    return await get_users(offset, limit, session)


@router.post("/check_user", response_model=UserRead)
async def check_user(user_id: UserId,
                     session: AsyncSession = Depends(get_session),
                     current_user=Depends(get_current_active_user)):
    await check_permissions("check_user", current_user.role)
    return await get_user(user_id.user_id, session)


@router.post("/block_user")
async def block_user_endpoint(user_id: UserId,
                              session: AsyncSession = Depends(get_session),
                              current_user=Depends(get_current_active_user)):
    await check_permissions("block_user_endpoint", current_user.role)
    return await block_user(user_id.user_id, current_user, session)


@router.post("/unlock_user")
async def unlock_user_endpoint(user_id: UserId,
                               session: AsyncSession = Depends(get_session),
                               current_user=Depends(get_current_active_user)):
    await check_permissions("unlock_user_endpoint", current_user.role)
    return await unlock_user(user_id.user_id, session)


@router.post("/activate_or_renew_workspace")
async def activate_or_renew_workspace(workspace_id: UUID4,
                                      additional_months: Optional[int] = 1,
                                      streams_count: Optional[int] = None,
                                      stream_only: Optional[bool] = None,
                                      session: AsyncSession = Depends(get_session),
                                      current_user=Depends(get_current_active_user)):
    "Продлить тариф"
    await check_permissions("activate_or_renew_workspace", current_user.role)
    return await activate_or_renew_workspace_tariff(workspace_id, session, additional_months, streams_count, stream_only)


@router.post("/change_renew_workspace_tariff")
async def change_renew_workspace_tariff(workspace_id: UUID4,
                                        additional_months: int,
                                        new_tariff_id: UUID4,
                                        streams_count: Optional[int] = None,
                                        session: AsyncSession = Depends(get_session),
                                        current_user=Depends(get_current_active_user)):
    "сменить тариф"
    await check_permissions("change_renew_workspace_tariff", current_user.role)
    return await change_workspace_tariff(workspace_id, additional_months, new_tariff_id, session, streams_count)


@router.post("/deactivate_workspace_now")
async def deactivate_workspace_now(workspace_id: UUID4,
                                   session: AsyncSession = Depends(get_session),
                                   current_user=Depends(get_current_active_user)):
    await check_permissions("deactivate_workspace_now", current_user.role)
    return await deactivate_workspace(workspace_id, session)


@router.get("/get_tariff_by_id", response_model=TariffRead)
async def get_tariff_by_id(tariff_id: UUID4,
                           session: AsyncSession = Depends(get_session),
                           current_user=Depends(get_current_active_user)):
    await check_permissions("get_tariff_by_id", current_user.role)
    return await tariff_by_id(tariff_id, session)


@router.get("/get_list_tariffs", response_model=List[TariffRead])
async def get_list_tariffs(session: AsyncSession = Depends(get_session),
                           current_user=Depends(get_current_active_user)):
    await check_permissions("get_list_tariffs", current_user.role)
    return await list_tariffs(session)


@router.get("/get_tariff_limit_by_id", response_model=TariffLimitRead)
async def get_tariff_limit_by_id(limit_id: UUID4,
                                 session: AsyncSession = Depends(get_session),
                                 current_user=Depends(get_current_active_user)):
    await check_permissions("get_tariff_limit_by_id", current_user.role)
    return await tariff_limit_by_id(limit_id, session)


@router.get("/get_tariff_all_limits_by_tariff_id", response_model=List[TariffLimitRead])
async def get_tariff_all_limits_by_tariff_id(tariff_id: UUID4,
                                             session: AsyncSession = Depends(get_session),
                                             current_user=Depends(get_current_active_user)):
    await check_permissions("get_tariff_all_limits_by_tariff_id", current_user.role)
    return await tariff_all_limits_by_tariff_id(tariff_id, session)
