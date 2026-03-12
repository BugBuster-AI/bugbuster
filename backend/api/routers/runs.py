from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID

from fastapi import (APIRouter, BackgroundTasks, Body, Depends, Header,
                     HTTPException, Query)
from pydantic import UUID4
from sqlalchemy.ext.asyncio import AsyncSession

from api.actions import check_usage_limits
from api.run_actions import (complete_run_cases, copy_group_runs,
                             create_group_run_case,
                             delete_cases_in_group_run_case,
                             delete_group_run_case,
                             free_streams_for_grouprun_by_project_id,
                             get_group_run_case_tree, get_runs_tree,
                             run_case_get_by_id, run_case_stop_by_id,
                             run_single_case, start_group_run,
                             step_passed_run_case, stop_group_run,
                             streams_statistics, update_group_run_case)
from db.session import get_session
from dependencies.auth import check_permissions, get_current_active_user
from schemas import (CaseFinalStatusEnum, CaseStatusEnum, GroupRunCaseCreate,
                     GroupRunCaseOrderBy, GroupRunCaseRead, GroupRunCaseUpdate,
                     UserRead)

router = APIRouter(prefix="/api/runs", tags=["runs"])


@router.get("/list_statuses")
async def list_statuses():
    return [status.value for status in CaseStatusEnum]


@router.get("/list_final_statuses")
async def list_final_statuses():
    return [status.value for status in CaseFinalStatusEnum]


@router.get("/list_order_columns")
async def list_order_columns():
    return [column.value for column in GroupRunCaseOrderBy]


@router.get("")
async def get_runs_tree_route(current_user: UserRead = Depends(get_current_active_user),
                              session: AsyncSession = Depends(get_session),
                              host: str = Header(None),
                              group_run_id: Optional[UUID] = Query(None),
                              case_id: Optional[UUID] = Query(None),
                              group_run_case_id: Optional[UUID] = Query(None),
                              created_at: Optional[datetime] = Query(None),
                              start_date: Optional[datetime] = Query(None),
                              end_date: Optional[datetime] = Query(None),
                              status: Optional[str] = Query(None),
                              limit: int = Query(5, le=25),
                              offset: int = 0):
    """
    Возвращает дерево  runs.
    """
    await check_permissions("get_runs_tree_route", current_user.role, current_user.workspace_status)
    return await get_runs_tree(current_user, session, host, group_run_id, case_id,
                               group_run_case_id, created_at, start_date,
                               end_date, status, limit, offset)


@router.get("/get_free_streams_for_grouprun_by_project_id")
async def get_free_streams_for_grouprun_by_project_id(project_id: UUID4,
                                                      current_user: UserRead = Depends(get_current_active_user),
                                                      session: AsyncSession = Depends(get_session)):
    await check_permissions("get_free_streams_for_grouprun_by_project_id", current_user.role, current_user.workspace_status)
    return await free_streams_for_grouprun_by_project_id(project_id, current_user, session)


@router.get("/get_streams_statistics")
async def get_streams_statistics(current_user: UserRead = Depends(get_current_active_user),
                                 session: AsyncSession = Depends(get_session)):
    return await streams_statistics(current_user, session)


@router.get("/{run_id}")
async def get_run_by_id(run_id: UUID4,
                        current_user: UserRead = Depends(get_current_active_user),
                        session: AsyncSession = Depends(get_session),
                        host: str = Header(None)):
    """
    Возвращает run по run_id
    """
    await check_permissions("get_run_by_id", current_user.role, current_user.workspace_status)
    return await run_case_get_by_id(run_id, session, current_user, host)


@router.post("")
async def start_run_by_case_id(case_id: UUID4,
                               background_video_generate: Optional[bool] = True,
                               extra: Optional[str] = None,
                               current_user: UserRead = Depends(get_current_active_user),
                               session: AsyncSession = Depends(get_session)):
    """
    запускает run по case_id
    """
    await check_permissions("start_run_by_case_id", current_user.role, current_user.workspace_status)
    await check_usage_limits(current_user.active_workspace_id, "start_group_run", session)
    return await run_single_case(case_id, session, current_user, background_video_generate, extra)


@router.delete("")
async def stop_run_by_id(run_id: UUID4,
                         current_user: UserRead = Depends(get_current_active_user),
                         session: AsyncSession = Depends(get_session)):
    """
    Останавливает run по run_id
    """
    await check_permissions("stop_run_by_id", current_user.role, current_user.workspace_status)
    return await run_case_stop_by_id(run_id, session, current_user)


@router.post("/group_runs", response_model=GroupRunCaseRead)
async def create_group_run_by_cases(group_run_case_data: GroupRunCaseCreate,
                                    current_user: UserRead = Depends(get_current_active_user),
                                    session: AsyncSession = Depends(get_session)):
    await check_permissions("create_group_run_by_cases", current_user.role, current_user.workspace_status)
    return await create_group_run_case(group_run_case_data, session, current_user)


@router.post("/copy_group_runs_by_ids")
async def copy_group_runs_by_ids(group_run_ids: List[UUID4],
                                 current_user: UserRead = Depends(get_current_active_user),
                                 session: AsyncSession = Depends(get_session)):
    await check_permissions("copy_group_runs_by_ids", current_user.role, current_user.workspace_status)
    return await copy_group_runs(group_run_ids, current_user, session)


@router.put("/group_runs")
async def update_group_run_case_untested(group_run_id: UUID4,
                                         update_data: GroupRunCaseUpdate,
                                         current_user: UserRead = Depends(get_current_active_user),
                                         session: AsyncSession = Depends(get_session)):
    await check_permissions("update_group_run_case_untested", current_user.role, current_user.workspace_status)
    return await update_group_run_case(group_run_id, update_data, session, current_user)


@router.delete("/group_runs")
async def delete_group_run_case_by_id(group_run_id: UUID4,
                                      current_user: UserRead = Depends(get_current_active_user),
                                      session: AsyncSession = Depends(get_session)):
    await check_permissions("delete_group_run_case_by_id", current_user.role, current_user.workspace_status)
    return await delete_group_run_case(group_run_id, session, current_user)


@router.get("/group_runs/")
async def group_run_case_tree(project_id: UUID4,
                              current_user: UserRead = Depends(get_current_active_user),
                              session: AsyncSession = Depends(get_session),
                              group_run_id: Optional[UUID] = Query(None),
                              status: List[str] = Query(default=None),
                              search: Optional[str] = Query(None),
                              filter_cases: Optional[str] = Query(None),
                              order_by: GroupRunCaseOrderBy = Query(GroupRunCaseOrderBy.created_at, description="Field to order by"),
                              order_direction: str = Query("desc", regex="^(asc|desc)$", description="Sort direction: asc or desc"),
                              limit: int = Query(5, le=10),
                              offset: int = 0):
    await check_permissions("group_run_case_tree", current_user.role, current_user.workspace_status)
    return await get_group_run_case_tree(project_id, current_user, session,
                                         group_run_id, status, search, filter_cases, order_by, order_direction, limit, offset)


@router.post("/group_runs/start_run_by_group_run_id")
async def start_run_by_group_run_id(group_run_id: UUID4,
                                    retest_cases_ids: Optional[List[UUID4]] = Body(None, description="optional cases_ids for retest"),
                                    run_automated: bool = False,
                                    run_manual: bool = False,
                                    current_user: UserRead = Depends(get_current_active_user),
                                    session: AsyncSession = Depends(get_session)):

    await check_permissions("start_run_by_group_run_id", current_user.role, current_user.workspace_status)
    if run_automated is True and run_manual is True:
        raise HTTPException(status_code=400, detail="only run_automated or run_manual")

    if (run_automated or run_manual):
        if not retest_cases_ids or len(retest_cases_ids) == 0:
            raise HTTPException(
                status_code=400,
                detail="retest_cases_ids must be provided and non-empty when run_automated or run_manual is True"
            )

        # retest_cases_ids = [retest_cases_ids[0]]  # Берем только первый ID

    if retest_cases_ids and (run_automated is False and run_manual is False):
        if len(retest_cases_ids) > 0:
            raise HTTPException(status_code=400, detail="retest_cases_ids only with run_automated or run_manual mode")

    return await start_group_run(group_run_id, session, current_user, retest_cases_ids, run_automated, run_manual)


@router.delete("/group_runs/stop_run_by_group_run_id")
async def stop_run_by_group_run_id(group_run_id: UUID4,
                                   current_user: UserRead = Depends(get_current_active_user),
                                   session: AsyncSession = Depends(get_session)):
    await check_permissions("stop_run_by_group_run_id", current_user.role, current_user.workspace_status)
    return await stop_group_run(group_run_id, session, current_user)


@router.put("/complete_run_cases_by_run_id")
async def complete_run_cases_by_run_id(run_ids: List[UUID4],
                                       status: CaseFinalStatusEnum = Body(...),
                                       comment: Optional[str] = Body(None),
                                       attachments: Optional[List] = Body(None),
                                       failed_step_index: Optional[int] = Body(None),
                                       current_user: UserRead = Depends(get_current_active_user),
                                       session: AsyncSession = Depends(get_session)):
    await check_permissions("complete_run_cases_by_run_id", current_user.role, current_user.workspace_status)
    return await complete_run_cases(run_ids, status, session, current_user, attachments,
                                    comment, failed_step_index)


@router.put("/step_passed_run_case_by_run_id")
async def step_passed_run_case_by_run_id(run_id: UUID4 = Body(UUID4),
                                         passed_step_index: int = Body(int),
                                         comment: Optional[str] = Body(None),
                                         attachments: Optional[List] = Body(None),
                                         session: AsyncSession = Depends(get_session),
                                         current_user: UserRead = Depends(get_current_active_user),):
    await check_permissions("step_passed_run_case_by_run_id", current_user.role, current_user.workspace_status)
    return await step_passed_run_case(run_id, passed_step_index, session,
                                      current_user, comment, attachments)


@router.delete("/delete_cases_in_group_run")
async def delete_cases_in_group_run(group_run_id: UUID4,
                                    cases_ids: List[UUID4],
                                    current_user: UserRead = Depends(get_current_active_user),
                                    session: AsyncSession = Depends(get_session)):
    await check_permissions("delete_cases_in_group_run", current_user.role, current_user.workspace_status)
    return await delete_cases_in_group_run_case(group_run_id, cases_ids, session, current_user)
