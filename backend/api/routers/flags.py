from typing import List

from fastapi import APIRouter, Depends
from pydantic import UUID4
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_session
from schemas import FlagCatalogRead, UserFlagsRead, UserRead, UserFlagsUpdate
from dependencies.auth import get_current_active_user
from api.flag_catalog_actions import get_flag_catalog, user_flags, update_user_flag

router = APIRouter(prefix="/api/flags", tags=["flags"])


@router.get("/catalog", response_model=List[FlagCatalogRead])
async def get_flags_catalog(current_user: UserRead = Depends(get_current_active_user),
                            session: AsyncSession = Depends(get_session)):
    """справочник всех  флагов"""
    return await get_flag_catalog(session)


@router.get("/get_user_flags", response_model=UserFlagsRead)
async def get_user_flags(current_user: UserRead = Depends(get_current_active_user),
                         session: AsyncSession = Depends(get_session)):
    """
    Получить все метки пользователя
    """
    return await user_flags(current_user, session)


@router.put("/{flag_name}", response_model=UserFlagsRead)
async def update_exists_user_flag(flag_name: str,
                                  user_flag_update: UserFlagsUpdate,
                                  current_user: UserRead = Depends(get_current_active_user),
                                  session: AsyncSession = Depends(get_session)):
    """
    Обновить конкретную метку текущего пользователя

    Параметры:
    - shown: установить состояние показа (True/False/None - не изменять)
    - view_count: установить конкретное значение счетчика (>=0)
    - increment_view: увеличить счетчик просмотров на 1 (игнорируется если указан view_count)
    """
    return await update_user_flag(flag_name, user_flag_update, current_user, session)
