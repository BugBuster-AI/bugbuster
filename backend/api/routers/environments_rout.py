from typing import List, Union

from fastapi import APIRouter, Depends, Query
from pydantic import UUID4
from sqlalchemy.ext.asyncio import AsyncSession

from api.environments_actions import (create_new_environment,
                                      delete_existing_environments,
                                      environments_by_id, list_environments,
                                      update_existing_environment)
from db.session import get_session
from schemas import (BrowserEnum, EnvironmentCreate, EnvironmentRead,
                     EnvironmentUpdate, OSEnum, UserRead)
from dependencies.auth import check_permissions, get_current_active_user

router = APIRouter(prefix="/api/environments", tags=["environments"])


@router.get("/get_list_browsers", response_model=List[str])
async def get_browsers(current_user: UserRead = Depends(get_current_active_user),):
    return [browser.value for browser in BrowserEnum]


@router.get("/get_list_os", response_model=List[str])
async def get_operation_systems(current_user: UserRead = Depends(get_current_active_user)):
    return [os.value for os in OSEnum]


@router.get("/get_list_environments", response_model=Union[List[EnvironmentRead], List])
async def get_list_environments(project_id: UUID4,
                                current_user: UserRead = Depends(get_current_active_user),
                                session: AsyncSession = Depends(get_session)):
    await check_permissions("get_list_environments", current_user.role, current_user.workspace_status)
    return await list_environments(project_id, current_user, session)


@router.get("/{environment_id}", response_model=Union[EnvironmentRead, List])
async def get_environments_by_id(environment_id: UUID4,
                                 current_user: UserRead = Depends(get_current_active_user),
                                 session: AsyncSession = Depends(get_session)):
    await check_permissions("get_environments_by_id", current_user.role, current_user.workspace_status)
    return await environments_by_id(environment_id, current_user, session)


@router.post("", response_model=EnvironmentRead)
async def create_environment(environment: EnvironmentCreate,
                             current_user: UserRead = Depends(get_current_active_user),
                             session: AsyncSession = Depends(get_session)):
    await check_permissions("create_environment", current_user.role, current_user.workspace_status)
    return await create_new_environment(environment, current_user, session)


@router.put("/{environment_id}", response_model=EnvironmentRead)
async def update_environment(environment_id: UUID4,
                             environment_update: EnvironmentUpdate,
                             current_user: UserRead = Depends(get_current_active_user),
                             session: AsyncSession = Depends(get_session)):
    await check_permissions("update_environment", current_user.role, current_user.workspace_status)
    return await update_existing_environment(environment_id, environment_update,
                                             current_user, session)


@router.delete("/{environment_id}")
async def delete_environments(environment_id: UUID4,
                              current_user: UserRead = Depends(get_current_active_user),
                              session: AsyncSession = Depends(get_session)):
    await check_permissions("delete_environments", current_user.role, current_user.workspace_status)
    return await delete_existing_environments(environment_id, current_user, session)
