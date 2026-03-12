import json
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import (APIRouter, BackgroundTasks, Body, Depends, Header,
                     HTTPException, Query, Request)
from fastapi.responses import PlainTextResponse
from pydantic import UUID4
from sqlalchemy.ext.asyncio import AsyncSession

from api.billing_actions import (current_tariffs_limits_usage,
                                 list_tariffs_limits_plan)
from config import logger
from db.session import get_session
from dependencies.auth import check_permissions, get_current_active_user
from schemas import UserRead

router = APIRouter(prefix="/api/billing", tags=["billing"])


@router.get("/get_current_tariffs_limits_usage")
async def get_current_tariffs_limits_usage(current_user: UserRead = Depends(get_current_active_user),
                                           session: AsyncSession = Depends(get_session)):
    await check_permissions("get_current_tariffs_limits_usage", current_user.role)
    return await current_tariffs_limits_usage(current_user, session)


@router.get("/get_list_tariffs_limits_plan")
async def get_list_tariffs_limits_plan(cnt_months: int = Query(12, ge=1, le=12),
                                       current_user: UserRead = Depends(get_current_active_user),
                                       session: AsyncSession = Depends(get_session)):
    await check_permissions("get_list_tariffs_limits_plan", current_user.role)
    return await list_tariffs_limits_plan(current_user, session, cnt_months)
