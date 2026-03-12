from typing import List, Optional, Union
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query
from pydantic import UUID4
from sqlalchemy.ext.asyncio import AsyncSession

from api.actions import check_usage_limits
from api.content_actions import (case_by_case_id, case_by_external_id,
                                 case_from_record, copy_case, create_case,
                                 create_project, create_shared_steps,
                                 create_suite, delete_case, delete_project,
                                 delete_shared_steps, delete_suite,
                                 free_streams_for_active_workspace,
                                 get_list_projects,
                                 get_list_projects_by_workspace_id,
                                 get_list_suites, get_user_tree,
                                 list_shared_steps_by_name,
                                 list_shared_steps_by_project_id,
                                 project_by_id, shared_steps_by_id,
                                 update_case, update_case_position,
                                 update_project, update_shared_steps,
                                 update_start_kit, update_suite,
                                 update_suite_position)
from db.session import get_session
from dependencies.auth import check_permissions, get_current_active_user
from schemas import (CaseCreate, CaseCreateFromRecord, CaseRead, CaseTypeEnum,
                     CaseUpdate, ProjectCreate, ProjectRead, ProjectReadFull,
                     ProjectSummary, ProjectUpdate, SharedStepsCreate,
                     SharedStepsRead, SharedStepsUpdate, SuiteCreate,
                     SuiteRead, SuiteReadFull, SuiteSummary, SuiteUpdate,
                     UserRead)

router = APIRouter(prefix="/api/content", tags=["content"])
router_shared_steps = APIRouter(prefix="/api/shared_steps", tags=["shared_steps"])

# Read


@router.get("/list_case_types")
async def list_case_types():
    return [case_type.value for case_type in CaseTypeEnum]


@router.get("/get_case_by_external_id", response_model=List[CaseRead])
async def get_case_by_external_id(external_id: str,
                                  current_user: UserRead = Depends(get_current_active_user),
                                  session: AsyncSession = Depends(get_session)):
    await check_permissions("get_case_by_external_id", current_user.role, current_user.workspace_status)
    return await case_by_external_id(external_id, current_user, session)


@router.get("/get_case_by_case_id", response_model=CaseRead)
async def get_case_by_case_id(case_id: UUID4,
                              current_user: UserRead = Depends(get_current_active_user),
                              session: AsyncSession = Depends(get_session)):
    await check_permissions("get_case_by_case_id", current_user.role, current_user.workspace_status)
    return await case_by_case_id(case_id, current_user, session)


@router.get("/get_project_by_id", response_model=ProjectSummary)
async def get_project_by_id(project_id: UUID4,
                            current_user: UserRead = Depends(get_current_active_user),
                            session: AsyncSession = Depends(get_session)
                            ):
    await check_permissions("get_project_by_id", current_user.role, current_user.workspace_status)
    return await project_by_id(project_id, current_user, session)


@router.get("/get_free_streams_for_active_workspace")
async def get_free_streams_for_active_workspace(current_user: UserRead = Depends(get_current_active_user),
                                                session: AsyncSession = Depends(get_session),
                                                exclude_project_id: Optional[UUID4] = Query(None)):
    await check_permissions("get_free_streams_for_active_workspace", current_user.role, current_user.workspace_status)
    return await free_streams_for_active_workspace(current_user, session, exclude_project_id)


@router.get("/list_projects", response_model=List[ProjectSummary])
async def list_projects(current_user: UserRead = Depends(get_current_active_user),
                        session: AsyncSession = Depends(get_session),
                        search: Optional[str] = Query(None)):
    await check_permissions("list_projects", current_user.role, current_user.workspace_status)
    return await get_list_projects(current_user, session, search)


@router.get("/list_projects_by_workspace_id", response_model=List[ProjectSummary])
async def list_projects_by_workspace_id(workspace_id: UUID4,
                                        current_user: UserRead = Depends(get_current_active_user),
                                        session: AsyncSession = Depends(get_session),
                                        search: Optional[str] = Query(None)):
    # await check_permissions("list_projects_by_workspace_id", current_user.role, current_user.workspace_status)
    return await get_list_projects_by_workspace_id(workspace_id, current_user, session, search)


@router.get("/list_suites", response_model=List[SuiteSummary])
async def list_suites(current_user: UserRead = Depends(get_current_active_user),
                      session: AsyncSession = Depends(get_session)):
    await check_permissions("list_suites", current_user.role, current_user.workspace_status)
    # await check_usage_limits(current_user.active_workspace_id, "list_suites", session)
    return await get_list_suites(current_user, session)


@router.get("/user_tree", response_model=List[Union[ProjectReadFull, SuiteReadFull, CaseRead]])
async def get_user_tree_route(project_id: Optional[UUID] = Query(None, description="filter"),
                              suite_id: Optional[UUID] = Query(None, description="filter"),
                              filter_cases: Optional[str] = Query(None),
                              current_user: UserRead = Depends(get_current_active_user),
                              session: AsyncSession = Depends(get_session)):
    await check_permissions("get_user_tree_route", current_user.role, current_user.workspace_status)
    return await get_user_tree(current_user, session, project_id, suite_id, filter_cases)


# Create

@router.post("/project", response_model=ProjectRead)
async def create_new_project(project: ProjectCreate,
                             current_user: UserRead = Depends(get_current_active_user),
                             session: AsyncSession = Depends(get_session)):
    await check_permissions("create_new_project", current_user.role, current_user.workspace_status)
    return await create_project(current_user, project, session)


@router.post("/suite", response_model=SuiteRead)
async def create_new_suite(suite: SuiteCreate,
                           current_user: UserRead = Depends(get_current_active_user),
                           session: AsyncSession = Depends(get_session)):
    await check_permissions("create_new_suite", current_user.role, current_user.workspace_status)
    return await create_suite(current_user, suite, session)


@router.post("/case", response_model=CaseRead)
async def create_new_case(case: CaseCreate,
                          current_user: UserRead = Depends(get_current_active_user),
                          session: AsyncSession = Depends(get_session)):
    await check_permissions("create_new_case", current_user.role, current_user.workspace_status)
    return await create_case(current_user, case, session)


@router.post("/generate_case_from_record/", response_model=CaseRead)
async def generate_case_from_record(case: CaseCreateFromRecord,
                                    current_user: UserRead = Depends(get_current_active_user),
                                    session: AsyncSession = Depends(get_session),
                                    host: str = Header(None)):
    await check_permissions("generate_case_from_record", current_user.role, current_user.workspace_status)
    return await case_from_record(current_user, case, session, host)


@router.post("/copy_case_by_case_id")
async def copy_case_by_case_id(case_ids: List[UUID4],
                               current_user: UserRead = Depends(get_current_active_user),
                               session: AsyncSession = Depends(get_session)):
    await check_permissions("copy_case_by_case_id", current_user.role, current_user.workspace_status)
    return await copy_case(case_ids, current_user, session)


# Update

@router.put("/project", response_model=ProjectRead)
async def update_existing_project(project: ProjectUpdate,
                                  current_user: UserRead = Depends(get_current_active_user),
                                  session: AsyncSession = Depends(get_session)):
    await check_permissions("update_existing_project", current_user.role, current_user.workspace_status)
    return await update_project(current_user, project, session)


@router.put("/start_kit")
async def update_start_kit_to_workspace(current_user: UserRead = Depends(get_current_active_user),
                                        session: AsyncSession = Depends(get_session)):
    await check_permissions("update_start_kit_to_workspace", current_user.role)
    return await update_start_kit(current_user, session)


@router.put("/suite", response_model=SuiteRead)
async def update_existing_suite(suite: SuiteUpdate,
                                current_user: UserRead = Depends(get_current_active_user),
                                session: AsyncSession = Depends(get_session)):
    await check_permissions("update_existing_suite", current_user.role, current_user.workspace_status)
    return await update_suite(current_user, suite, session)


@router.put("/change_suite_position")
async def change_suite_position(suite_id: UUID4,
                                new_position: int,
                                current_user: UserRead = Depends(get_current_active_user),
                                session: AsyncSession = Depends(get_session)):
    await check_permissions("change_suite_position", current_user.role, current_user.workspace_status)
    return await update_suite_position(current_user, suite_id, new_position, session)


@router.put("/case", response_model=CaseRead)
async def update_existing_case(case: CaseUpdate,
                               current_user: UserRead = Depends(get_current_active_user),
                               session: AsyncSession = Depends(get_session)):
    await check_permissions("update_existing_case", current_user.role, current_user.workspace_status)
    return await update_case(current_user, case, session)


@router.put("/change_case_position")
async def change_case_position(case_id: UUID4,
                               new_position: int,
                               current_user: UserRead = Depends(get_current_active_user),
                               session: AsyncSession = Depends(get_session)):
    await check_permissions("change_case_position", current_user.role, current_user.workspace_status)
    return await update_case_position(current_user, case_id, new_position, session)


# Delete
@router.delete("/project/{project_id}")
async def delete_existing_project(project_id: UUID4,
                                  current_user: UserRead = Depends(get_current_active_user),
                                  session: AsyncSession = Depends(get_session)):
    await check_permissions("delete_existing_project", current_user.role, current_user.workspace_status)
    return await delete_project(project_id, session, current_user)


@router.delete("/suite/{suite_id}")
async def delete_existing_suite(suite_id: UUID4,
                                current_user: UserRead = Depends(get_current_active_user),
                                session: AsyncSession = Depends(get_session)):
    await check_permissions("delete_existing_suite", current_user.role, current_user.workspace_status)
    return await delete_suite(suite_id, session, current_user)


@router.delete("/case")
async def delete_existing_case(case_ids: List[UUID4],
                               current_user: UserRead = Depends(get_current_active_user),
                               session: AsyncSession = Depends(get_session)):
    await check_permissions("delete_existing_case", current_user.role, current_user.workspace_status)
    return await delete_case(case_ids, session, current_user)


# shared steps

@router_shared_steps.post("", response_model=SharedStepsRead)
async def create_new_shared_steps(shared_steps: SharedStepsCreate,
                                  current_user: UserRead = Depends(get_current_active_user),
                                  session: AsyncSession = Depends(get_session)):
    await check_permissions("create_new_shared_steps", current_user.role, current_user.workspace_status)
    return await create_shared_steps(shared_steps, current_user, session)


@router_shared_steps.get("/get_list_shared_steps_by_project_id", response_model=List[SharedStepsRead])
async def get_list_shared_steps_by_project_id(project_id: UUID4,
                                              search: Optional[str] = Query(None, description="Search in name, desc or steps"),
                                              current_user: UserRead = Depends(get_current_active_user),
                                              session: AsyncSession = Depends(get_session)):
    await check_permissions("get_list_shared_steps_by_project_id", current_user.role, current_user.workspace_status)
    return await list_shared_steps_by_project_id(project_id, current_user, session, search)


@router_shared_steps.get("/get_list_shared_steps_by_name", response_model=List[SharedStepsRead])
async def get_list_shared_steps_by_name(shared_steps_name: str,
                                        project_id: UUID4,
                                        current_user: UserRead = Depends(get_current_active_user),
                                        session: AsyncSession = Depends(get_session)):
    await check_permissions("get_list_shared_steps_by_name", current_user.role, current_user.workspace_status)
    return await list_shared_steps_by_name(shared_steps_name, project_id, current_user, session)


@router_shared_steps.get("/{shared_steps_id}", response_model=SharedStepsRead)
async def get_shared_steps_by_id(shared_steps_id: UUID4,
                                 current_user: UserRead = Depends(get_current_active_user),
                                 session: AsyncSession = Depends(get_session)):
    await check_permissions("get_shared_steps_by_id", current_user.role, current_user.workspace_status)
    return await shared_steps_by_id(shared_steps_id, current_user, session)


@router_shared_steps.put("", response_model=SharedStepsRead)
async def update_existing_shared_steps(shared_steps: SharedStepsUpdate,
                                       current_user: UserRead = Depends(get_current_active_user),
                                       session: AsyncSession = Depends(get_session)):
    await check_permissions("update_existing_shared_steps", current_user.role, current_user.workspace_status)
    return await update_shared_steps(shared_steps, current_user, session)


@router_shared_steps.delete("/{shared_steps_id}")
async def delete_existing_shared_steps(shared_steps_id: UUID4,
                                       current_user: UserRead = Depends(get_current_active_user),
                                       session: AsyncSession = Depends(get_session)):
    await check_permissions("delete_existing_shared_steps", current_user.role, current_user.workspace_status)
    return await delete_shared_steps(shared_steps_id, current_user, session)
