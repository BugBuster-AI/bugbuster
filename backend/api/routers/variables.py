from typing import Dict, List, Union, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Query
from pydantic import UUID4
from sqlalchemy.ext.asyncio import AsyncSession

from api.variables_actions import (create_variable, create_variables_kit,
                                   delete_existing_variable,
                                   delete_existing_variable_kit,
                                   list_variables_by_variables_kit_id,
                                   list_variables_by_variables_kit_name,
                                   list_variables_kit, precalc_variable,
                                   update_existing_variable,
                                   update_existing_variables_kit,
                                   variable_by_id, variables_kit_by_id)
from db.session import get_session
from dependencies.auth import check_permissions, get_current_active_user
from schemas import (UserRead, VariablesCreate, VariablesDetailsCreate,
                     VariablesDetailsRead, VariablesDetailsUpdate,
                     VariablesRead, VariablesUpdate)

router_variables = APIRouter(prefix="/api/variables", tags=["variables"])
router_variables_details = APIRouter(prefix="/api/variables_details", tags=["variables_details"])


# Variables
@router_variables.get("/get_list_variables_kit", response_model=Union[List[VariablesRead], List])
async def get_list_variables_kit(project_id: UUID4,
                                 search: Optional[str] = Query(None, max_length=200),
                                 current_user: UserRead = Depends(get_current_active_user),
                                 session: AsyncSession = Depends(get_session)):
    await check_permissions("get_list_variables_kit", current_user.role, current_user.workspace_status)
    return await list_variables_kit(project_id, current_user, session, search)


@router_variables.get("/{variables_kit_id}", response_model=Union[VariablesRead, List])
async def get_variables_kit_by_id(variables_kit_id: UUID4,
                                  current_user: UserRead = Depends(get_current_active_user),
                                  session: AsyncSession = Depends(get_session)):
    await check_permissions("get_variables_kit_by_id", current_user.role, current_user.workspace_status)
    return await variables_kit_by_id(variables_kit_id, current_user, session)


@router_variables.post("", response_model=VariablesRead)
async def create_new_variables_kit(variables_kit: VariablesCreate,
                                   current_user: UserRead = Depends(get_current_active_user),
                                   session: AsyncSession = Depends(get_session)):
    await check_permissions("create_new_variables_kit", current_user.role, current_user.workspace_status)
    return await create_variables_kit(variables_kit, current_user, session)


@router_variables.put("/{variables_kit_id}", response_model=VariablesRead)
async def update_variables_kit(variables_kit_id: UUID4,
                               variables_kit_update: VariablesUpdate,
                               current_user: UserRead = Depends(get_current_active_user),
                               session: AsyncSession = Depends(get_session)):
    await check_permissions("update_variables_kit", current_user.role, current_user.workspace_status)
    return await update_existing_variables_kit(variables_kit_id, variables_kit_update, current_user, session)


@router_variables.delete("/{variables_kit_id}")
async def delete_variable_kit(variables_kit_id: UUID4,
                              current_user: UserRead = Depends(get_current_active_user),
                              session: AsyncSession = Depends(get_session)):
    await check_permissions("delete_variable_kit", current_user.role, current_user.workspace_status)
    return await delete_existing_variable_kit(variables_kit_id, current_user, session)


# VariablesDetails
@router_variables_details.get("/get_list_variables_by_variables_kit_id", response_model=Dict)
async def get_list_variables_by_variables_kit_id(variables_kit_id: UUID4,
                                                 search: Optional[str] = Query(None, max_length=200),
                                                 current_user: UserRead = Depends(get_current_active_user),
                                                 session: AsyncSession = Depends(get_session)):
    await check_permissions("get_list_variables_by_variables_kit_id", current_user.role, current_user.workspace_status)
    return await list_variables_by_variables_kit_id(variables_kit_id, current_user, session, search)


@router_variables_details.get("/get_list_variables_by_variables_kit_name", response_model=Dict)
async def get_list_variables_by_variables_kit_name(variables_kit_name: str,
                                                   project_id: UUID4,
                                                   current_user: UserRead = Depends(get_current_active_user),
                                                   session: AsyncSession = Depends(get_session)):
    await check_permissions("get_list_variables_by_variables_kit_name", current_user.role, current_user.workspace_status)
    return await list_variables_by_variables_kit_name(variables_kit_name, project_id, current_user, session)


@router_variables_details.get("/{variable_details_id}", response_model=Union[VariablesDetailsRead, List])
async def get_variable_by_id(variable_details_id: UUID4,
                             current_user: UserRead = Depends(get_current_active_user),
                             session: AsyncSession = Depends(get_session)):
    await check_permissions("get_variable_by_id", current_user.role, current_user.workspace_status)
    return await variable_by_id(variable_details_id, current_user, session)


@router_variables_details.post("", response_model=VariablesDetailsRead)
async def create_new_variable(variable: VariablesDetailsCreate,
                              current_user: UserRead = Depends(get_current_active_user),
                              session: AsyncSession = Depends(get_session)):
    await check_permissions("create_new_variable", current_user.role, current_user.workspace_status)
    return await create_variable(variable, current_user, session)


@router_variables_details.post("/precalc_new_variable", response_model=VariablesDetailsRead)
async def precalc_new_variable(variable: VariablesDetailsCreate,
                               date: str = Query(default=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
                                                 description="Date in format YYYY-MM-DD HH:mm:ss"),
                               current_user: UserRead = Depends(get_current_active_user)):
    """посчитать computed_value

       variables_kit_id / variable_details_id фиктивные

       можно установить исходную дату
       """
    return await precalc_variable(variable, date, current_user)


@router_variables_details.put("/{variable_details_id}", response_model=VariablesDetailsRead)
async def update_variable(variable_details_id: UUID4,
                          variable_update: VariablesDetailsUpdate,
                          current_user: UserRead = Depends(get_current_active_user),
                          session: AsyncSession = Depends(get_session)):
    await check_permissions("update_variables_kit", current_user.role, current_user.workspace_status)
    return await update_existing_variable(variable_details_id, variable_update, current_user, session)


@router_variables_details.delete("/{variable_details_id}")
async def delete_variable(variable_details_id: UUID4,
                          current_user: UserRead = Depends(get_current_active_user),
                          session: AsyncSession = Depends(get_session)):
    await check_permissions("delete_variable_kit", current_user.role, current_user.workspace_status)
    return await delete_existing_variable(variable_details_id, current_user, session)
