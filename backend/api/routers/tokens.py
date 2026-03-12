from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.actions import check_usage_limits
from api.tokens_actions import (activate_user_token, create_stored_user_token,
                                deactivate_user_token, delete_user_token,
                                get_user_tokens, update_user_token)
from db.models import User
from db.session import get_session
from dependencies.auth import check_permissions, get_current_active_user
from schemas import (UserTokenCreate, UserTokenCreated, UserTokenRead,
                     UserTokenUpdate)

router = APIRouter(prefix="/api/tokens", tags=["tokens"])


@router.post("", response_model=UserTokenCreated)
async def create_token(create_token: UserTokenCreate,
                       current_user: User = Depends(get_current_active_user),
                       session: AsyncSession = Depends(get_session)):
    await check_permissions("api_tokens", current_user.role, current_user.workspace_status)
    await check_usage_limits(current_user.active_workspace_id, "api_tokens", session)
    return await create_stored_user_token(current_user.user_id, create_token, session)


@router.put("/{token_id}", response_model=UserTokenRead)
async def update_token(token_id: UUID,
                       update_token: UserTokenUpdate,
                       current_user: User = Depends(get_current_active_user),
                       session: AsyncSession = Depends(get_session)):
    await check_permissions("api_tokens", current_user.role, current_user.workspace_status)
    await check_usage_limits(current_user.active_workspace_id, "api_tokens", session)
    return await update_user_token(str(token_id), current_user.user_id, update_token, session)


@router.get("", response_model=List[UserTokenRead])
async def get_tokens(current_user: User = Depends(get_current_active_user),
                     session: AsyncSession = Depends(get_session)):
    await check_permissions("api_tokens", current_user.role, current_user.workspace_status)
    await check_usage_limits(current_user.active_workspace_id, "api_tokens", session)
    return await get_user_tokens(current_user.user_id, session)


@router.delete("/{token_id}")
async def delete_token(token_id: UUID,
                       current_user: User = Depends(get_current_active_user),
                       session: AsyncSession = Depends(get_session)):
    await check_permissions("api_tokens", current_user.role, current_user.workspace_status)
    await check_usage_limits(current_user.active_workspace_id, "api_tokens", session)
    return await delete_user_token(token_id, current_user.user_id, session)


@router.post("/{token_id}/activate")
async def activate_token(token_id: UUID,
                         current_user: User = Depends(get_current_active_user),
                         session: AsyncSession = Depends(get_session)):
    await check_permissions("api_tokens", current_user.role, current_user.workspace_status)
    await check_usage_limits(current_user.active_workspace_id, "api_tokens", session)
    return await activate_user_token(token_id, current_user.user_id, session)


@router.post("/{token_id}/deactivate")
async def deactivate_token(token_id: UUID,
                           current_user: User = Depends(get_current_active_user),
                           session: AsyncSession = Depends(get_session)):
    await check_permissions("api_tokens", current_user.role, current_user.workspace_status)
    await check_usage_limits(current_user.active_workspace_id, "api_tokens", session)
    return await deactivate_user_token(token_id, current_user.user_id, session)
