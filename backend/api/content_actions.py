
import time
import uuid
from collections import defaultdict
from copy import deepcopy
from typing import Any, Dict, List, Optional, Set, Union
from uuid import UUID

from fastapi import HTTPException
from fastapi.responses import JSONResponse
from pydantic import UUID4
from sqlalchemy import and_, delete, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api.actions import search_for_filter_cases, update_usage_count

from api.record_actions import happy_pass_update_autosop
from api.variables_actions import add_default_variables_kit
from config import CLICKER_IP, CLICKER_PORT, REDIS_PREFIX, logger, redis_client
from db.models import (Case, CaseSharedSteps, Environment, HappyPass, Project,
                       ProjectUser, RunCase, SharedSteps, Suite, User,
                       Variables, Workspace, WorkspaceMembership)
from db.session import async_session, transaction_scope
from dependencies.auth import add_start_kit_to_workspace

from schemas import (ApiStep, CaseCreate, CaseCreateFromRecord, CaseRead,
                     CaseUpdate, ProjectCreate, ProjectRead, ProjectReadFull,
                     ProjectSummary, ProjectUpdate, Roles, SharedStepsCreate,
                     SharedStepsRead, SharedStepsUpdate, SuiteCreate,
                     SuiteRead, SuiteReadFull, SuiteSummary, SuiteUpdate)
from utils import async_request


async def detect_expanded_shared_steps(case: CaseUpdate) -> bool:

    all_sections = []

    if case.before_browser_start is not None:
        all_sections.extend(case.before_browser_start)
    if case.before_steps is not None:
        all_sections.extend(case.before_steps)
    if case.steps is not None:
        all_sections.extend(case.steps)
    if case.after_steps is not None:
        all_sections.extend(case.after_steps)

    for step in all_sections:
        if (isinstance(step, dict) and step.get("extra", {}).get("shared_step") and step["extra"].get("shared_step_id")):
            return True

    return False


async def update_db_expanded_shared_steps(case: CaseUpdate, user: User, session: AsyncSession):
    """
    обновляем shared steps из развернутых в ране
    Группируем по (shared_step_id, shared_step_group_index)
    Если group_index отсутствует, восстанавливаем последовательный номер
    При апдейте в БД для каждого shared_step_id обновляем ТОЛЬКО последнюю группу (максимальный index)
    """

    all_steps = []
    if case.before_browser_start is not None:
        all_steps.extend(case.before_browser_start)
    if case.before_steps is not None:
        all_steps.extend(case.before_steps)
    if case.steps is not None:
        all_steps.extend(case.steps)
    if case.after_steps is not None:
        all_steps.extend(case.after_steps)

    # временная группировка: key = (shared_id, group_index) -> list of steps
    groups = {}
    # если у каких-то шагов нет group_index, будем нумеровать их в порядке появления отдельно для каждого shared_id
    legacy_counters = defaultdict(int)

    for step in all_steps:
        if (isinstance(step, dict) and step.get("extra", {}).get("shared_step") and step["extra"].get("shared_step_id")):
            shared_id = step["extra"]["shared_step_id"]

            group_index = step["extra"].get("shared_step_group_index")
            if group_index is None:
                # legacy: назначаем последовательный индекс по shared_id
                group_index = legacy_counters[shared_id]
                legacy_counters[shared_id] += 1

            key = (shared_id, group_index)

            # удаляем тех флаги shared_step, но оставляем пользовательские extra
            clean_step = deepcopy(step)
            if "extra" in clean_step:
                clean_extra = clean_step["extra"].copy()
                clean_extra.pop("shared_step", None)
                clean_extra.pop("shared_step_id", None)
                clean_extra.pop("variables", None)
                clean_extra.pop("shared_step_group_index", None)
                clean_extra.pop("shared_step_group_size", None)
                clean_step["extra"] = clean_extra if clean_extra else clean_step.pop("extra", None)

            groups.setdefault(key, []).append(clean_step)

    # для каждого shared_id берем для апдейта первое вхождение если есть дубли
    by_shared_id = defaultdict(list)
    for (shared_id, group_index), steps_list in groups.items():
        by_shared_id[shared_id].append((group_index, steps_list))

    for shared_id, group_list in by_shared_id.items():
        # выбираем группу с минимальным индексом
        last_group_index, last_steps = min(group_list, key=lambda x: x[0])
        shared_update = SharedStepsUpdate(
            shared_steps_id=UUID(shared_id),
            steps=deepcopy(last_steps)
        )
        await update_shared_steps(shared_update, user, session)


def convert_expanded_shared_steps_to_case_steps(case: CaseUpdate) -> CaseUpdate:

    def process_section(section: Optional[List]) -> Optional[List]:
        if section is None:
            return None

        new_section = []
        current_shared_id = None
        current_group_index = None
        shared_steps_group = []

        # Если есть элементы без group_index старые
        legacy_counter = defaultdict(int)

        for step in section:
            is_shared = isinstance(step, dict) and step.get("extra", {}).get("shared_step") and step["extra"].get("shared_step_id")
            if is_shared:
                step_shared_id = step["extra"]["shared_step_id"]
                step_group_index = step["extra"].get("shared_step_group_index")

                if step_group_index is None:
                    # legacy_counter: последовательный индекс для данного shared_id в этой секции
                    step_group_index = legacy_counter[step_shared_id]
                    legacy_counter[step_shared_id] += 1

                # если открыта другая группа (id или индекс отличается) — закрываем прошлую
                if (current_shared_id is None) or (current_shared_id != step_shared_id) or (current_group_index != step_group_index):
                    if current_shared_id is not None and shared_steps_group:
                        # закрываем предыдущую группу как ссылка
                        new_section.append({
                            "type": "shared_step",
                            "value": current_shared_id
                        })
                    # начинаем новую группу
                    current_shared_id = step_shared_id
                    current_group_index = step_group_index
                    shared_steps_group = [step]
                else:
                    # продолжаем текущую группу
                    shared_steps_group.append(step)
            else:
                # если была открытая группа — закрываем её
                if current_shared_id is not None and shared_steps_group:
                    new_section.append({
                        "type": "shared_step",
                        "value": current_shared_id
                    })
                    current_shared_id = None
                    current_group_index = None
                    shared_steps_group = []

                new_section.append(step)

        # добавляем последнюю открытую группу
        if current_shared_id is not None and shared_steps_group:
            new_section.append({
                "type": "shared_step",
                "value": current_shared_id
            })

        return new_section

    if case.before_browser_start is not None:
        case.before_browser_start = process_section(case.before_browser_start)
    if case.before_steps is not None:
        case.before_steps = process_section(case.before_steps)
    if case.steps is not None:
        case.steps = process_section(case.steps)
    if case.after_steps is not None:
        case.after_steps = process_section(case.after_steps)

    return case


def extract_steps(sop: List[Union[str, Dict[str, Any]]]) -> List[str]:
    """
    Вход: [
        {"type": "action", "value": "открыть главную страницу"},
        "кликнуть синюю кнопку"
    ]
    Выход: ["открыть главную страницу", "кликнуть синюю кнопку"]
    """
    steps = []
    for item in sop:
        if isinstance(item, str):
            steps.append(item)
        elif isinstance(item, dict) and item.get("type") == "action" and "value" in item:
            steps.append(item["value"])

    return steps


def curl_validate(sop: List[Union[str, Dict[str, Any]]],
                  before_browser_start: List[Union[str, Dict[str, Any]]]) -> None:

    api_steps = []
    # тут обычные степы и могут быть апи
    for item in sop + before_browser_start:
        if isinstance(item, dict) and item.get("type") == "api":
            api_steps.append(item)

    for i, step in enumerate(api_steps):
        try:
            validated_step = ApiStep(**step)

            content_type = validated_step.get_content_type()

            if validated_step.method in ['GET', 'HEAD', 'OPTIONS'] and validated_step.data:
                raise ValueError(f"Method {validated_step.method} cannot have body data")

            if content_type and 'application/json' in content_type and validated_step.data:
                if not isinstance(validated_step.data, (dict, list)):
                    raise ValueError("For JSON content type, data must be dict or list")

        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid API {step=}: {str(e)}"
            )


async def validate_expected_steps(before_browser_start: List[Union[str, Dict[str, Any]]],
                                  before_steps: List[Union[str, Dict[str, Any]]],
                                  after_steps: List[Union[str, Dict[str, Any]]]):
    """expected_result только в разделе steps"""

    for step in before_browser_start + after_steps:
        if isinstance(step, dict) and step.get("type") == "expected_result":
            raise HTTPException(
                status_code=400,
                detail=f"Invalid expected_result group - only for step: {step}"
            )


async def validate_shared_steps(sop: List[Union[str, Dict[str, Any]]],
                                before_browser_start: List[Union[str, Dict[str, Any]]],
                                user: User,
                                session: AsyncSession) -> set:

    for step in before_browser_start:
        if isinstance(step, dict) and step.get("type") == "shared_step":
            raise HTTPException(
                status_code=400,
                detail=f"Invalid shared step group = before_browser_start: {step}"
            )

    async with transaction_scope(session):
        # Извлекаем все UUID из shared_steps
        shared_steps_ids = set()

        for step in sop:
            if isinstance(step, dict) and step.get("type") == "shared_step":
                if "value" not in step:
                    raise HTTPException(status_code=400, detail="Not found value in step")
                try:
                    shared_steps_ids.add(UUID(step['value']))
                except ValueError:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid shared step ID format: {step['value']}"
                    )

        if not shared_steps_ids:
            return shared_steps_ids

        # Проверяем наличие всех shared_steps
        shared_steps_query = (
            select(SharedSteps.shared_steps_id)
            .join(ProjectUser, and_(
                SharedSteps.project_id == ProjectUser.project_id,
                ProjectUser.user_id == user.user_id,
                ProjectUser.workspace_id == user.active_workspace_id
            ))
            .where(SharedSteps.shared_steps_id.in_(list(shared_steps_ids)))
        )

        shared_steps_results = await session.execute(shared_steps_query)
        existing_ids = {row[0] for row in shared_steps_results.all()}

        # Если не все ID найдены
        missing_ids = shared_steps_ids - existing_ids
        if missing_ids:
            raise HTTPException(
                status_code=404,
                detail=f"Shared steps not found or not authorized: {[str(i) for i in missing_ids]}"
            )
        return shared_steps_ids


async def _update_case_shared_steps_links(session: AsyncSession,
                                          case_id: UUID,
                                          shared_steps: Set[UUID]):
    """
    Обновляет связи между case и shared_steps в таблице CaseSharedSteps.
    """
    async with transaction_scope(session):
        # Удаляем все существующие связи для этого case_id
        delete_stmt = delete(CaseSharedSteps).where(CaseSharedSteps.case_id == case_id)
        await session.execute(delete_stmt)

        # Если переданы новые shared_steps, создаем связи
        if shared_steps:
            links_to_add = []
            for shared_steps_id in shared_steps:
                try:
                    links_to_add.append(
                        CaseSharedSteps(
                            case_id=case_id,
                            shared_steps_id=shared_steps_id
                        )
                    )
                except (ValueError, TypeError, KeyError) as e:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid shared step data: {shared_steps_id}. Error: {e}"
                    )

            # Добавляем все новые связи
            if links_to_add:
                session.add_all(links_to_add)

        await session.flush()


# Create
async def create_project(user: User,
                         project: ProjectCreate,
                         session: AsyncSession) -> ProjectRead:
    try:
        async with session.begin():
            available_streams = await free_streams_for_active_workspace(user, session)
            if project.parallel_exec > available_streams:
                raise HTTPException(status_code=400,
                                    detail=f"Not enough available streams. Requested: {project.parallel_exec}, Available: {available_streams}")
            new_project = Project(name=project.name,
                                  description=project.description,
                                  user_id=user.user_id,
                                  workspace_id=user.active_workspace_id,
                                  parallel_exec=project.parallel_exec)
            session.add(new_project)
            await session.flush()

            # новый проект нужно также пошарить всем админами workspace
            admin_users_query = select(WorkspaceMembership.user_id).where(
                WorkspaceMembership.workspace_id == user.active_workspace_id,
                WorkspaceMembership.role == Roles.ROLE_ADMIN.value,
                WorkspaceMembership.status == 'Active'
            )
            result = await session.execute(admin_users_query)
            admin_users = result.scalars().all()

            for admin_user_id in admin_users:
                new_project_user = ProjectUser(
                    project_id=new_project.project_id,
                    workspace_id=user.active_workspace_id,
                    user_id=admin_user_id,
                    role=Roles.ROLE_ADMIN.value
                )
                session.add(new_project_user)
            await session.flush()

            # для нового проекта нужно создать дефолтный справочник переменных
            await add_default_variables_kit(new_project.project_id, user, session)
            logger.info(f"New project created: {new_project.name} for user: {user.email}")
            return ProjectRead.model_validate(new_project)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(e, exc_info=True)
        mess = {"status": "error", "message": f"Error: {e}"}
        raise HTTPException(400, mess)


async def create_suite(user: User,
                       suite: SuiteCreate,
                       session: AsyncSession) -> SuiteRead:
    try:
        async with session.begin():
            query = (
                select(ProjectUser.project_id)
                .where(ProjectUser.project_id == suite.project_id,
                       ProjectUser.user_id == user.user_id,
                       ProjectUser.workspace_id == user.active_workspace_id)
            )

            result = await session.execute(query)
            result = result.unique().one_or_none()

            if not result:
                raise HTTPException(status_code=404,
                                    detail="Project not found or Not authorized to create suite in this project")

            # Проверяем родительскую Suite, если она указана
            parent_id = None
            if suite.parent_id:
                parent_suite_query = (
                    select(Suite.suite_id)
                    .where(Suite.suite_id == suite.parent_id)
                    .where(Suite.project_id == suite.project_id)
                )
                parent_suite_result = await session.execute(parent_suite_query)
                parent_id = parent_suite_result.scalar_one_or_none()

                if not parent_id:
                    raise HTTPException(status_code=404, detail="Parent suite not found or not in the same project")

            await recalculate_positions(session, parent_id, Suite, "parent_id", "position", suite.project_id)
            max_position_result = await session.execute(
                select(func.max(Suite.position))
                .where(Suite.parent_id == suite.parent_id,
                       Suite.project_id == suite.project_id)
            )
            max_position = max_position_result.scalar_one_or_none() or 0

            new_suite = Suite(
                project_id=suite.project_id,
                name=suite.name,
                description=suite.description,
                parent_id=parent_id,
                position=max_position + 1
            )
            session.add(new_suite)
            await session.flush()
            await session.refresh(new_suite)
            return SuiteRead.model_validate(new_suite)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(e, exc_info=True)
        mess = {"status": "error", "message": f"Error: {e}"}
        raise HTTPException(400, mess)


async def create_case(user: User,
                      case: CaseCreate,
                      session: AsyncSession) -> CaseRead:
    try:
        async with session.begin():
            suite_query = (
                select(ProjectUser.user_id, ProjectUser.project_id, Suite.suite_id)
                .join(Suite, and_(ProjectUser.project_id == Suite.project_id,
                                  ProjectUser.workspace_id == user.active_workspace_id,
                                  ProjectUser.user_id == user.user_id))
                .where(Suite.suite_id == case.suite_id)
            )

            suite_result = await session.execute(suite_query)
            suite_data = suite_result.unique().one_or_none()

            if not suite_data:
                raise HTTPException(status_code=404, detail="Suite not found or not authorized")

            project_user_id, project_project_id, suite_id = suite_data

            if case.external_id:
                existing_case_query = (
                    select(Case)
                    .where(
                        Case.external_id == case.external_id,
                        Case.project_id == project_project_id
                    )
                )
                existing_case_result = await session.execute(existing_case_query)
                existing_case = existing_case_result.scalars().one_or_none()
                if existing_case:
                    raise HTTPException(status_code=400, detail="External ID already exists within this project")

            if case.environment_id:
                query = (
                    select(Environment)
                    .join(ProjectUser, and_(Environment.project_id == ProjectUser.project_id,
                                            ProjectUser.project_id == project_project_id,
                                            ProjectUser.workspace_id == user.active_workspace_id,
                                            ProjectUser.user_id == user.user_id))
                    .where(Environment.environment_id == case.environment_id)
                )

                result = await session.execute(query)
                environment = result.scalars().one_or_none()

                if not environment:
                    raise HTTPException(status_code=404, detail="Environment/Project not found or not authorized")

            is_valid = True
            validation_reason = {}
            action_plan = []
            full_action_plan = []  # Будет содержать все шаги, включая API
            action_plan_id = str(uuid.uuid4())

            all_steps = []
            validation_step_indices = []  # Индексы шагов, которые отправляем на валидацию

            sop: list = case.before_steps + case.steps + case.after_steps

            shared_steps_ids = await validate_shared_steps(sop,
                                                           case.before_browser_start,
                                                           user, session)
            await validate_expected_steps(case.before_browser_start,
                                          case.before_steps,
                                          case.after_steps)

            if case.type == "automated":
                # валидация СОП
                # clicker_ip = await model_ip_store.get_model_ip_clicker()
                # if clicker_ip is None:
                #     raise HTTPException(status_code=400, detail="server is unavailable")

                curl_validate(sop, case.before_browser_start)

                for step in case.before_browser_start:
                    # all_steps.append({
                    #     step
                    #     "type": "api",
                    #     "value": step["value"],
                    #     "extra": step.get("extra")
                    # })
                    all_steps.append(step)

                for step in sop:
                    if isinstance(step, str):
                        all_steps.append({
                            "type": "action",
                            "value": step
                        })
                        validation_step_indices.append(len(all_steps) - 1)  # Запоминаем индекс валидируемого шага
                    elif isinstance(step, dict):
                        if "value" not in step:
                            raise HTTPException(status_code=400, detail="Not found value in step")

                        if step.get("type") in ("action"):
                            all_steps.append(step)
                            validation_step_indices.append(len(all_steps) - 1)
                        elif step.get("type") in ("api", "shared_step", "expected_result"):  # не отправляем в rewriter
                            all_steps.append(step)
                        else:
                            raise HTTPException(status_code=400, detail=f"Uncorrect type {step.get('type')}")

                # Формируем SOP только для валидируемых шагов
                validation_sop = [
                    step["value"]
                    for idx, step in enumerate(all_steps)
                    if idx in validation_step_indices
                ]

                post_data = {
                    'sop': extract_steps(validation_sop),
                    'action_plan_id': action_plan_id,
                    'user_id': str(user.user_id)
                }

                if len(post_data['sop']) > 0:
                    status, res = await async_request(f"http://{CLICKER_IP}:{CLICKER_PORT}/sop_validation",
                                                      method='post',
                                                      params=post_data, timeout=60)
                    if status != 200:
                        raise HTTPException(status_code=400, detail=f"sop_validation error: {res}")
                    else:
                        is_valid = res.get("is_valid", False)
                        validation_reason = res.get("validation_reason", {})
                        action_plan = res.get("action_plan", [])

                        # КОРРЕКТИРУЕМ ИНДЕКСЫ: преобразуем индексы из validation_sop в оригинальные индексы all_steps
                        corrected_validation_reason = {}
                        for val_index, reason in validation_reason.items():
                            if val_index.isdigit():
                                val_index_int = int(val_index)
                                if val_index_int < len(validation_step_indices):
                                    original_index = validation_step_indices[val_index_int]
                                    corrected_validation_reason[str(original_index)] = reason
                                else:
                                    corrected_validation_reason[val_index] = reason
                            else:
                                corrected_validation_reason[val_index] = reason

                        validation_reason = corrected_validation_reason

                        # не сохраняем кейс
                        if is_valid is False:
                            logger.error(validation_reason)
                            raise HTTPException(status_code=400, detail=f"{validation_reason}")

                # Формируем полный action_plan, включая API шаги
                action_plan_ptr = 0  # Указатель на текущий элемент в action_plan
                for idx, step in enumerate(all_steps):
                    if idx in validation_step_indices:
                        # Берём следующий шаг из action_plan
                        if action_plan_ptr < len(action_plan):
                            full_action_plan.append(action_plan[action_plan_ptr])
                            action_plan_ptr += 1
                    elif step.get("type") == "api":
                        # Добавляем API-шаг
                        extra = step.get("extra", {})
                        # extra.setdefault("method", step["method"])
                        # extra.setdefault("url", step["url"])
                        # extra.setdefault("value", step["value"])

                        api_action = {
                            "action_type": "API",
                            "method": step["method"],
                            "url": step["url"],
                            "headers": step.get("headers", {}),
                            "data": step.get("data"),
                            "files": step.get("files", {}),
                            "value": step["value"],
                            "extra": extra
                        }
                        full_action_plan.append(api_action)
                    else:
                        full_action_plan.append({"action_type": step["type"], "value": step["value"]})

                logger.info(f"sop_validation: {is_valid=} | {validation_reason=} | {action_plan=}")

            await recalculate_positions(session, suite_id, Case, "suite_id", "position")
            max_position_result = await session.execute(
                select(func.max(Case.position))
                .where(Case.suite_id == suite_id)
            )
            max_position = max_position_result.scalar_one_or_none() or 0

            new_case = Case(
                name=case.name,
                context=case.context,
                description=case.description,
                before_browser_start=case.before_browser_start,
                before_steps=case.before_steps,
                steps=case.steps,
                after_steps=case.after_steps,
                type=case.type,
                status=case.status,
                priority=case.priority,
                url=str(case.url) if case.url else None,
                variables=case.variables,
                is_valid=is_valid,
                validation_reason=validation_reason,
                action_plan=full_action_plan,
                action_plan_id=action_plan_id,
                external_id=case.external_id,
                suite_id=suite_id,
                position=max_position + 1,
                project_id=project_project_id,
                environment_id=case.environment_id
            )
            session.add(new_case)
            await session.flush()
            await session.refresh(new_case)

            if shared_steps_ids:
                await _update_case_shared_steps_links(
                    session, new_case.case_id, shared_steps_ids
                )

            return CaseRead.model_validate(new_case)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(e, exc_info=True)
        mess = {"status": "error", "message": f"Error: {e}"}
        raise HTTPException(400, mess)


async def case_from_record(user: User,
                           case: CaseCreateFromRecord,
                           session: AsyncSession,
                           host: str = None) -> CaseRead:
    try:
        async with session.begin():
            suite_query = (
                select(ProjectUser.user_id, ProjectUser.project_id, Suite.suite_id)
                .join(Suite, and_(ProjectUser.project_id == Suite.project_id,
                                  ProjectUser.workspace_id == user.active_workspace_id,
                                  ProjectUser.user_id == user.user_id))
                .where(Suite.suite_id == case.suite_id)
            )

            suite_result = await session.execute(suite_query)
            suite_data = suite_result.unique().one_or_none()

            if not suite_data:
                raise HTTPException(status_code=404, detail="Suite not found or not authorized")

            project_user_id, project_project_id, suite_id = suite_data

            if case.external_id:
                existing_case_query = (
                    select(Case)
                    .where(
                        Case.external_id == case.external_id,
                        Case.project_id == project_project_id
                    )
                )
                existing_case_result = await session.execute(existing_case_query)
                existing_case = existing_case_result.scalars().one_or_none()
                if existing_case:
                    raise HTTPException(status_code=400, detail="External ID already exists within this project")

            query = await session.execute(select(HappyPass)
                                          .where(HappyPass.workspace_id == user.active_workspace_id,
                                                 HappyPass.happy_pass_id == case.happy_pass_id))

            happy_pass: HappyPass = query.scalars().one_or_none()

            if not happy_pass:
                raise HTTPException(status_code=404, detail="HappyPass not found")

            # получили степы по картинкам, если их нет
            if case.type == 'automated':
                if not happy_pass.steps:
                    logger.info("happy_pass not full, wait regenerate steps")
                    await happy_pass_update_autosop(user.active_workspace_id, user.user_id,
                                                    case.happy_pass_id, 600, host)
                    await session.refresh(happy_pass)

            # валидация

            is_valid = True
            validation_reason = {}
            action_plan = []
            sop: list = case.before_steps + happy_pass.steps + case.after_steps

            full_action_plan = []
            action_plan_id = str(uuid.uuid4())

            all_steps = []
            validation_step_indices = []

            shared_steps_ids = await validate_shared_steps(sop,
                                                           case.before_browser_start,
                                                           user, session)
            await validate_expected_steps(case.before_browser_start,
                                          case.before_steps,
                                          case.after_steps)
            curl_validate(sop, case.before_browser_start)

            for step in case.before_browser_start:
                # all_steps.append({
                #     "type": "api",
                #     "value": step["value"],
                #     "extra": step.get("extra")
                # })
                all_steps.append(step)

            for step in sop:
                if isinstance(step, str):
                    all_steps.append({
                        "type": "action",
                        "value": step
                    })
                    validation_step_indices.append(len(all_steps) - 1)  # Запоминаем индекс валидируемого шага
                elif isinstance(step, dict):
                    if "value" not in step:
                        raise HTTPException(status_code=400, detail="Not found value in step")

                    if step.get("type") in ("action"):
                        all_steps.append(step)
                        validation_step_indices.append(len(all_steps) - 1)
                    elif step.get("type") in ("api", "shared_step", "expected_result"):  # не отправляем в rewriter
                        all_steps.append(step)
                    else:
                        raise HTTPException(status_code=400, detail=f"Uncorrect type {step.get('type')}")

            # Формируем SOP только для валидируемых шагов
            validation_sop = [
                step["value"]
                for idx, step in enumerate(all_steps)
                if idx in validation_step_indices
            ]

            post_data = {
                'sop': extract_steps(validation_sop),
                'action_plan_id': action_plan_id,
                'user_id': str(user.user_id)
            }

            if case.type == "automated":
                # валидация СОП
                # clicker_ip = await model_ip_store.get_model_ip_clicker()
                # if clicker_ip is None:
                #     raise HTTPException(status_code=400, detail="server is unavailable")
                if len(post_data['sop']) > 0:
                    status, res = await async_request(f"http://{CLICKER_IP}:{CLICKER_PORT}/sop_validation",
                                                      method='post',
                                                      params=post_data, timeout=60)
                    if status != 200:
                        raise HTTPException(status_code=400, detail=f"sop_validation error: {res}")
                    else:
                        is_valid = res.get("is_valid", False)
                        validation_reason = res.get("validation_reason", {})
                        action_plan = res.get("action_plan", [])

                        # КОРРЕКТИРУЕМ ИНДЕКСЫ: преобразуем индексы из validation_sop в оригинальные индексы all_steps
                        corrected_validation_reason = {}
                        for val_index, reason in validation_reason.items():
                            if val_index.isdigit():
                                val_index_int = int(val_index)
                                if val_index_int < len(validation_step_indices):
                                    original_index = validation_step_indices[val_index_int]
                                    corrected_validation_reason[str(original_index)] = reason
                                else:
                                    corrected_validation_reason[val_index] = reason
                            else:
                                corrected_validation_reason[val_index] = reason

                        validation_reason = corrected_validation_reason

                        # не сохраняем кейс
                        if is_valid is False:
                            raise HTTPException(status_code=400, detail=f"{validation_reason}")

                # Формируем полный action_plan, включая API шаги
                action_plan_ptr = 0  # Указатель на текущий элемент в action_plan
                for idx, step in enumerate(all_steps):
                    if idx in validation_step_indices:
                        # Берём следующий шаг из action_plan
                        if action_plan_ptr < len(action_plan):
                            full_action_plan.append(action_plan[action_plan_ptr])
                            action_plan_ptr += 1
                    elif step.get("type") == "api":
                        # Добавляем API-шаг
                        extra = step.get("extra", {})
                        # extra.setdefault("method", step["method"])
                        # extra.setdefault("url", step["url"])
                        # extra.setdefault("value", step["value"])

                        api_action = {
                            "action_type": "API",
                            "method": step["method"],
                            "url": step["url"],
                            "headers": step.get("headers", {}),
                            "data": step.get("data"),
                            "files": step.get("files", {}),
                            "value": step["value"],
                            "extra": extra
                        }
                        full_action_plan.append(api_action)
                    else:
                        full_action_plan.append({"action_type": step["type"], "value": step["value"]})

                logger.info(f"sop_validation: {is_valid=} | {validation_reason=} | {action_plan=}")

            await recalculate_positions(session, suite_id, Case, "suite_id", "position")
            max_position_result = await session.execute(
                select(func.max(Case.position))
                .where(Case.suite_id == suite_id)
            )
            max_position = max_position_result.scalar_one_or_none() or 0

            new_case = Case(
                name=happy_pass.name,
                context=happy_pass.context,
                description=case.description,
                before_browser_start=case.before_browser_start,
                before_steps=case.before_steps,
                steps=happy_pass.steps,
                after_steps=case.after_steps,
                type=case.type,
                status=case.status,
                priority=case.priority,
                url=str(case.url) if case.url else None,
                variables=case.variables,
                is_valid=is_valid,
                validation_reason=validation_reason,
                action_plan=full_action_plan,  # happy_pass.action_plan
                action_plan_id=action_plan_id,
                external_id=case.external_id,
                suite_id=case.suite_id,
                position=max_position + 1,
                project_id=project_project_id
            )

            session.add(new_case)
            await session.flush()
            await session.refresh(new_case)

            if shared_steps_ids:
                await _update_case_shared_steps_links(
                    session, new_case.case_id, shared_steps_ids
                )

            return CaseRead.model_validate(new_case)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(e, exc_info=True)
        mess = {"status": "error", "message": f"Error: {e}"}
        raise HTTPException(400, mess)


async def copy_case(case_ids: List[UUID4],
                    user: User,
                    session: AsyncSession) -> List[UUID4]:
    try:
        async with session.begin():
            new_cases_ids = []
            for case_id in case_ids:
                query = (
                    select(ProjectUser.user_id, Case)
                    .join(Suite, and_(ProjectUser.project_id == Suite.project_id,
                                      ProjectUser.workspace_id == user.active_workspace_id,
                                      ProjectUser.user_id == user.user_id))
                    .join(Case, Suite.suite_id == Case.suite_id)
                    .where(Case.case_id == case_id)
                )
                result = await session.execute(query)
                result = result.unique().one_or_none()

                if not result:
                    raise HTTPException(status_code=404, detail="Case not found or not authorized to read this case")

                project_user_id, existing_case = result

                await recalculate_positions(session, existing_case.suite_id, Case, "suite_id", "position")

                max_position_result = await session.execute(
                    select(func.max(Case.position))
                    .where(Case.suite_id == existing_case.suite_id)
                )
                max_position = max_position_result.scalar_one_or_none() or 0

                new_case = Case(
                    name=f"Copy of {existing_case.name}",
                    context=existing_case.context,
                    description=existing_case.description,
                    before_browser_start=existing_case.before_browser_start,
                    before_steps=existing_case.before_steps,
                    steps=existing_case.steps,
                    after_steps=existing_case.after_steps,
                    type=existing_case.type,
                    status=existing_case.status,
                    priority=existing_case.priority,
                    url=existing_case.url,
                    variables=existing_case.variables,
                    is_valid=existing_case.is_valid,
                    validation_reason=existing_case.validation_reason,
                    action_plan=existing_case.action_plan,
                    external_id=None,  # они уникальны из джиры
                    suite_id=existing_case.suite_id,
                    position=max_position + 1,
                    project_id=existing_case.project_id,
                    environment_id=existing_case.environment_id
                )

                session.add(new_case)
                await session.flush()

                await recalculate_positions(session, existing_case.suite_id, Case, "suite_id", "position")
                await session.refresh(new_case)
                # new_cases_ids.append(new_case.case_id)
                new_cases_ids.append(CaseRead.model_validate(new_case))

        # return CaseRead.model_validate(new_case)
            return new_cases_ids
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(e, exc_info=True)
        mess = {"status": "error", "message": f"Error: {e}"}
        raise HTTPException(400, mess)


async def create_shared_steps(shared_steps: SharedStepsCreate,
                              user: User,
                              session: AsyncSession) -> SharedStepsRead:
    try:
        async with transaction_scope(session):

            query = (
                select(ProjectUser.user_id, ProjectUser.project_id)
                .where(ProjectUser.project_id == shared_steps.project_id,
                       ProjectUser.workspace_id == user.active_workspace_id,
                       ProjectUser.user_id == user.user_id)
            )

            result = await session.execute(query)
            result = result.unique().one_or_none()

            if not result:
                raise HTTPException(status_code=404, detail="Project not found or not authorized to create shared steps in this project")

            is_valid = True
            validation_reason = {}
            action_plan = []
            full_action_plan = []  # Будет содержать все шаги, включая API
            action_plan_id = str(uuid.uuid4())
            all_steps = []
            validation_step_indices = []  # Индексы шагов, которые отправляем на валидацию

            curl_validate(shared_steps.steps, [])
            for step in shared_steps.steps:
                if isinstance(step, str):
                    raise HTTPException(status_code=400, detail="Step must be dict")

                elif isinstance(step, dict):
                    if "value" not in step:
                        raise HTTPException(status_code=400, detail="Not found value in step")

                    if step.get("type") in ("action"):
                        all_steps.append(step)
                        validation_step_indices.append(len(all_steps) - 1)
                    elif step.get("type") in ("api", "shared_step"):  # не отправляем в rewriter
                        all_steps.append(step)
                    else:
                        raise HTTPException(status_code=400, detail=f"Uncorrect type {step.get('type')}")

            # Формируем SOP только для валидируемых шагов
            validation_sop = [
                step["value"]
                for idx, step in enumerate(all_steps)
                if idx in validation_step_indices
            ]

            post_data = {
                'sop': extract_steps(validation_sop),
                'action_plan_id': action_plan_id,
                'user_id': str(user.user_id)
            }

            if len(post_data['sop']) > 0:
                status, res = await async_request(f"http://{CLICKER_IP}:{CLICKER_PORT}/sop_validation",
                                                  method='post',
                                                  params=post_data, timeout=60)
                if status != 200:
                    raise HTTPException(status_code=400, detail=f"sop_validation error: {res}")
                else:
                    is_valid = res.get("is_valid", False)
                    validation_reason = res.get("validation_reason", {})
                    action_plan = res.get("action_plan", [])

                    # КОРРЕКТИРУЕМ ИНДЕКСЫ: преобразуем индексы из validation_sop в оригинальные индексы all_steps
                    corrected_validation_reason = {}
                    for val_index, reason in validation_reason.items():
                        if val_index.isdigit():
                            val_index_int = int(val_index)
                            if val_index_int < len(validation_step_indices):
                                original_index = validation_step_indices[val_index_int]
                                corrected_validation_reason[str(original_index)] = reason
                            else:
                                corrected_validation_reason[val_index] = reason
                        else:
                            corrected_validation_reason[val_index] = reason

                    validation_reason = corrected_validation_reason

                    # не сохраняем кейс
                    if is_valid is False:
                        logger.error(validation_reason)
                        raise HTTPException(status_code=400, detail=f"{validation_reason}")

            # Формируем полный action_plan, включая API шаги
            action_plan_ptr = 0  # Указатель на текущий элемент в action_plan
            for idx, step in enumerate(all_steps):
                if idx in validation_step_indices:
                    # Берём следующий шаг из action_plan
                    if action_plan_ptr < len(action_plan):
                        full_action_plan.append(action_plan[action_plan_ptr])
                        action_plan_ptr += 1
                elif step.get("type") == "api":
                    # Добавляем API-шаг
                    extra = step.get("extra", {})

                    api_action = {
                        "action_type": "API",
                        "method": step["method"],
                        "url": step["url"],
                        "headers": step.get("headers", {}),
                        "data": step.get("data"),
                        "files": step.get("files", {}),
                        "value": step["value"],
                        "extra": extra
                    }
                    full_action_plan.append(api_action)
                else:
                    full_action_plan.append({"action_type": step["type"], "value": step["value"]})

            logger.info(f"sop_validation: {is_valid=} | {validation_reason=} | {action_plan=}")

            new_shared_steps = SharedSteps(
                name=shared_steps.name,
                description=shared_steps.description,
                steps=shared_steps.steps,
                is_valid=is_valid,
                validation_reason=validation_reason,
                action_plan=full_action_plan,
                action_plan_id=action_plan_id,
                project_id=shared_steps.project_id
            )
            session.add(new_shared_steps)
            await session.flush()
            await session.refresh(new_shared_steps)
            return SharedStepsRead.model_validate(new_shared_steps)

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(e, exc_info=True)
        mess = {"status": "error", "message": f"Error: {e}"}
        raise HTTPException(400, mess)

# Update


async def update_project(user: User,
                         project: ProjectUpdate,
                         session: AsyncSession) -> ProjectRead:
    try:
        async with session.begin():
            result = await session.execute(
                select(Project)
                .join(ProjectUser, and_(ProjectUser.project_id == Project.project_id,
                                        ProjectUser.workspace_id == user.active_workspace_id,
                                        ProjectUser.user_id == user.user_id))
                .where(Project.project_id == project.project_id)
            )
            exist_project = result.scalar_one_or_none()

            if not exist_project:
                raise HTTPException(status_code=404, detail="Project not found or not authorized to update this suite")

            # проверка свободных потоков
            if project.parallel_exec is not None:
                available = await free_streams_for_active_workspace(user,
                                                                    session,
                                                                    exclude_project_id=exist_project.project_id)

                if project.parallel_exec > available:
                    raise HTTPException(status_code=400,
                                        detail=f"Not enough available streams. Requested additional: {project.parallel_exec}, Available: {available}")

                exist_project.parallel_exec = project.parallel_exec

            update_data = project.model_dump(exclude_unset=True)
            if project.name is not None:
                exist_project.name = project.name
            if "description" in update_data:
                exist_project.description = project.description

            await session.flush()
            await session.refresh(exist_project)

            return ProjectRead.model_validate(exist_project)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(e, exc_info=True)
        mess = {"status": "error", "message": f"Error: {e}"}
        raise HTTPException(400, mess)


async def update_start_kit(user: User,
                           session: AsyncSession):
    try:
        async with session.begin():

            result = await session.execute(
                select(Project)
                .join(ProjectUser, and_(ProjectUser.project_id == Project.project_id,
                                        ProjectUser.workspace_id == user.active_workspace_id,
                                        ProjectUser.user_id == user.user_id))
                .where(or_(
                    Project.name == "BB Demo Project",
                    Project.name == "SM Demo Project"
                ))
            )

            exist_project = result.scalar_one_or_none()
            # удаляем если есть
            if exist_project:
                await delete_project(exist_project.project_id, session, user)

            await add_start_kit_to_workspace(user.source,
                                             user.host,
                                             session,
                                             user,
                                             user.active_workspace_id,
                                             user.role)

            return JSONResponse(content={"status": "OK"})

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(e, exc_info=True)
        mess = {"status": "error", "message": f"Error: {e}"}
        raise HTTPException(400, mess)


async def update_suite(user: User, suite: SuiteUpdate, session: AsyncSession) -> SuiteRead:
    try:
        async with session.begin():
            # result = await session.execute(
            #     select(Suite, Project.user_id, Suite.project_id)
            #     .join(Project, Suite.project_id == Project.project_id)
            #     .join(ProjectUser, and_(ProjectUser.project_id == Project.project_id,
            #                             ProjectUser.workspace_id == user.active_workspace_id,
            #                             ProjectUser.user_id == user.user_id))
            #     .where(Suite.suite_id == suite.suite_id)
            # )
            result = await session.execute(
                select(Suite)
                .join(ProjectUser, and_(Suite.project_id == ProjectUser.project_id,
                                        ProjectUser.workspace_id == user.active_workspace_id,
                                        ProjectUser.user_id == user.user_id))
                .where(Suite.suite_id == suite.suite_id)
            )
            exist_suite = result.scalars().one_or_none()

            if not exist_suite:
                raise HTTPException(status_code=404, detail="Suite not found or not authorized to update this suite")

            # Сохраняем старый parent_id для пересчета позиций после перемещения
            old_parent_id = exist_suite.parent_id

            update_data = suite.model_dump(exclude_unset=True)

            if suite.name:
                exist_suite.name = suite.name
            if "description" in update_data:
                exist_suite.description = suite.description

            if suite.parent_id is not None:
                if suite.parent_id == suite.suite_id:
                    raise HTTPException(status_code=400, detail="A suite cannot be its own parent.")

                # проверяем чтобы родителя не переместили в его же дочку
                current_parent_id = suite.parent_id
                while current_parent_id is not None:
                    if current_parent_id == exist_suite.suite_id:
                        raise HTTPException(status_code=400, detail="Cannot move a suite into one of its descendants.")
                    result = await session.execute(
                        select(Suite.parent_id).where(Suite.suite_id == current_parent_id)
                    )
                    current_parent_id = result.scalar_one_or_none()

                parent_suite_query = select(Suite.suite_id, Suite.project_id).where(Suite.suite_id == suite.parent_id)
                parent_suite_result = await session.execute(parent_suite_query)
                parent_suite_data = parent_suite_result.unique().one_or_none()

                if not parent_suite_data:
                    raise HTTPException(status_code=404, detail="Parent suite not found")

                new_parent_id, new_parent_project_id = parent_suite_data

                # запрет перемещения в другой проект
                if new_parent_project_id != exist_suite.project_id:
                    raise HTTPException(status_code=400, detail="Cannot move suite to a different project")

                exist_suite.parent_id = new_parent_id

            else:
                # перемещаем в корень, если уже не в корне
                if exist_suite.parent_id is not None:
                    exist_suite.parent_id = None

            await session.flush()
            # await session.refresh(exist_suite)

            # пересчет позиции в старом родителе, а затем в новом
            await recalculate_positions(session, old_parent_id, Suite, "parent_id", "position", exist_suite.project_id)
            await recalculate_positions(session, exist_suite.parent_id, Suite, "parent_id", "position", exist_suite.project_id)

            # Обновляем позицию, если указано
            if suite.new_position is not None:
                affected_suites_query = (
                    select(Suite)
                    .where(Suite.parent_id == exist_suite.parent_id,
                           Suite.project_id == exist_suite.project_id)
                    .order_by(Suite.position)
                )
                affected_suites_result = await session.execute(affected_suites_query)
                affected_suites = affected_suites_result.scalars().all()

                for s in affected_suites:
                    if s.suite_id == exist_suite.suite_id:
                        continue
                    if suite.new_position < exist_suite.position:
                        if suite.new_position <= s.position < exist_suite.position:
                            s.position += 1
                    else:
                        if exist_suite.position < s.position <= suite.new_position:
                            s.position -= 1
                exist_suite.position = suite.new_position
                await session.flush()
                await recalculate_positions(session, exist_suite.parent_id, Suite, "parent_id", "position", exist_suite.project_id)

            return SuiteRead.model_validate(exist_suite)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(e, exc_info=True)
        mess = {"status": "error", "message": f"Error: {e}"}
        raise HTTPException(400, mess)


async def update_suite_position(user: User,
                                suite_id: UUID4,
                                new_position: int,
                                session: AsyncSession):
    try:
        async with session.begin():

            result = await session.execute(
                select(Suite)
                .join(ProjectUser, and_(Suite.project_id == ProjectUser.project_id,
                                        ProjectUser.workspace_id == user.active_workspace_id,
                                        ProjectUser.user_id == user.user_id))
                .where(Suite.suite_id == suite_id)
            )
            suite = result.scalars().one_or_none()

            if not suite:
                raise HTTPException(status_code=404, detail="Suite not found")

            parent_id = suite.parent_id
            # Пересчитываем сначала, чтобы правильные позиции были перед изменением
            await recalculate_positions(session, parent_id, Suite, "parent_id", "position", suite.project_id)

            if suite.position == new_position:
                return JSONResponse(content={"status": "current position = new position"})

            affected_suites_query = (
                select(Suite)
                .where(Suite.parent_id == suite.parent_id,
                       Suite.project_id == suite.project_id)
                .order_by(Suite.position)
            )
            affected_suites = await session.execute(affected_suites_query)
            affected_suites = affected_suites.scalars().all()

            for s in affected_suites:
                if s.suite_id == suite_id:
                    continue
                if new_position < suite.position:
                    if new_position <= s.position < suite.position:
                        s.position += 1
                else:
                    if suite.position < s.position <= new_position:
                        s.position -= 1

            suite.position = new_position
            await session.flush()
            await recalculate_positions(session, parent_id, Suite, "parent_id", "position", suite.project_id)  # Финальный пересчет
            return JSONResponse(content={"status": "OK"})
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(e, exc_info=True)
        mess = {"status": "error", "message": f"Error: {e}"}
        raise HTTPException(400, mess)


async def update_case(user: User,
                      case: CaseUpdate,
                      session: AsyncSession) -> CaseRead:
    try:
        async with session.begin():

            logger.info(f"Received case update: {case.model_dump_json(exclude_none=True)}")

            existing_case_query = (
                select(Case)
                .join(ProjectUser, and_(ProjectUser.project_id == Case.project_id,
                                        ProjectUser.workspace_id == user.active_workspace_id,
                                        ProjectUser.user_id == user.user_id))
                .where(Case.case_id == case.case_id)
            )

            existing_case_result = await session.execute(existing_case_query)
            existing_case = existing_case_result.scalars().one_or_none()

            if not existing_case:
                raise HTTPException(status_code=404, detail="Case not found or not authorized to update this case")

            # проверяем, если апдейт из дебаг режима
            has_expanded_shared_steps = await detect_expanded_shared_steps(case)

            if has_expanded_shared_steps:
                logger.info("update from debug mode")
                # Обрабатываем развернутые shared steps
                await update_db_expanded_shared_steps(case, user, session)

                # Преобразуем развернутые из рана shared_steps обратно в ссылки
                case = convert_expanded_shared_steps_to_case_steps(case)

            if case.external_id:
                check_external_existing_case_query = (
                    select(Case)
                    .where(
                        Case.external_id == case.external_id,
                        Case.project_id == existing_case.project_id,
                        Case.case_id != case.case_id
                    )
                )
                check_external_existing_case_result = await session.execute(check_external_existing_case_query)
                check_external_existing_case = check_external_existing_case_result.scalars().one_or_none()
                if check_external_existing_case:
                    raise HTTPException(status_code=400, detail="External ID already exists within this project")

            if case.environment_id:
                query = (
                    select(Environment)
                    .join(ProjectUser, and_(Environment.project_id == ProjectUser.project_id,
                                            ProjectUser.project_id == existing_case.project_id,
                                            ProjectUser.workspace_id == user.active_workspace_id,
                                            ProjectUser.user_id == user.user_id))
                    .where(Environment.environment_id == case.environment_id)
                )

                result = await session.execute(query)
                environment = result.scalars().one_or_none()

                if not environment:
                    raise HTTPException(status_code=404, detail="Environment/Project not found or not authorized")

            # Старый suite_id
            old_suite_id = existing_case.suite_id

            # Если указан новый suite_id
            if case.suite_id and case.suite_id != existing_case.suite_id:
                suite_query = select(Suite.suite_id, Suite.project_id).where(Suite.suite_id == case.suite_id)

                suite_result = await session.execute(suite_query)
                suite_result = suite_result.unique().one_or_none()

                if not suite_result:
                    raise HTTPException(status_code=404, detail="Suite not found")

                new_suite_id, new_suite_project_id = suite_result

                if not new_suite_id:
                    raise HTTPException(status_code=404, detail="Suite not found")

                if new_suite_project_id != existing_case.project_id:
                    raise HTTPException(status_code=400, detail="Cannot move case to a suite in a different project")

                existing_case.suite_id = new_suite_id

                await session.flush()
                # Пересчитываем позиции в старом и новом сьютах
                await recalculate_positions(session, old_suite_id, Case, "suite_id", "position")
                await recalculate_positions(session, new_suite_id, Case, "suite_id", "position")

            # Используем новые значения или существующие, если они не обновлялись
            combined_before_steps = case.before_steps if case.before_steps is not None else existing_case.before_steps
            combined_steps = case.steps if case.steps is not None else existing_case.steps
            combined_after_steps = case.after_steps if case.after_steps is not None else existing_case.after_steps

            combined_before_browser_start = case.before_browser_start if case.before_browser_start is not None else existing_case.before_browser_start

            sop = combined_before_steps + combined_steps + combined_after_steps

            shared_steps_ids = await validate_shared_steps(sop,
                                                           combined_before_browser_start,
                                                           user, session)
            await validate_expected_steps(combined_before_browser_start,
                                          combined_before_steps,
                                          combined_after_steps)
            # Валидируем SOP
            is_finally_automated = case.type == 'automated' if case.type is not None else existing_case.type == 'automated'

            # if (steps_changed or not existing_case.action_plan) and is_finally_automated:
            # при переключении на авто нужно всегда запускать валидатор, шаги могли поменять на мануале
            if is_finally_automated:
                # clicker_ip = await model_ip_store.get_model_ip_clicker()
                # if clicker_ip is None:
                #     raise HTTPException(status_code=400, detail="server is unavailable")
                clicker_ip = '127.0.0.1'

                curl_validate(sop, combined_before_browser_start)

                is_valid = True
                action_plan_id = str(uuid.uuid4())
                validation_reason = {}
                action_plan = []
                full_action_plan = []
                all_steps = []
                validation_step_indices = []  # Индексы шагов, которые отправляем на валидацию

                for step in combined_before_browser_start:
                    # all_steps.append({
                    #     step
                    #     "type": "api",
                    #     "value": step["value"],
                    #     "extra": step.get("extra")
                    # })
                    all_steps.append(step)

                for step in sop:
                    if isinstance(step, str):
                        all_steps.append({
                            "type": "action",
                            "value": step
                        })
                        validation_step_indices.append(len(all_steps) - 1)  # Запоминаем индекс валидируемого шага
                    elif isinstance(step, dict):
                        if "value" not in step:
                            raise HTTPException(status_code=400, detail="Not found value in step")

                        if step.get("type") in ("action"):
                            all_steps.append(step)
                            validation_step_indices.append(len(all_steps) - 1)
                        elif step.get("type") in ("api", "shared_step", "expected_result"):  # не отправляем в rewriter
                            all_steps.append(step)
                        else:
                            raise HTTPException(status_code=400, detail=f"Uncorrect type {step.get('type')}")

                # Формируем SOP только для валидируемых шагов
                validation_sop = [
                    step["value"]
                    for idx, step in enumerate(all_steps)
                    if idx in validation_step_indices
                ]

                post_data = {
                    'sop': extract_steps(validation_sop),
                    'action_plan_id': action_plan_id,
                    'user_id': str(user.user_id),
                    'case_id': str(case.case_id)
                }
                if len(post_data['sop']) > 0:
                    status, res = await async_request(f"http://{CLICKER_IP}:{CLICKER_PORT}/sop_validation",
                                                      method='post',
                                                      params=post_data, timeout=60)
                    if status != 200:
                        raise HTTPException(status_code=400, detail=f"sop_validation error: {res}")

                    else:
                        is_valid = res.get("is_valid", False)
                        validation_reason = res.get("validation_reason", {})
                        action_plan = res.get("action_plan", [])

                        # КОРРЕКТИРУЕМ ИНДЕКСЫ: преобразуем индексы из validation_sop в оригинальные индексы all_steps
                        corrected_validation_reason = {}
                        for val_index, reason in validation_reason.items():
                            if val_index.isdigit():
                                val_index_int = int(val_index)
                                if val_index_int < len(validation_step_indices):
                                    original_index = validation_step_indices[val_index_int]
                                    corrected_validation_reason[str(original_index)] = reason
                                else:
                                    corrected_validation_reason[val_index] = reason
                            else:
                                corrected_validation_reason[val_index] = reason

                        validation_reason = corrected_validation_reason

                        # не сохраняем кейс
                        if is_valid is False:
                            raise HTTPException(status_code=400, detail=f"{validation_reason}")

                # Формируем полный action_plan, включая API шаги
                action_plan_ptr = 0  # Указатель на текущий элемент в action_plan
                for idx, step in enumerate(all_steps):
                    if idx in validation_step_indices:
                        # Берём следующий шаг из action_plan
                        if action_plan_ptr < len(action_plan):
                            full_action_plan.append(action_plan[action_plan_ptr])
                            action_plan_ptr += 1
                    elif step.get("type") == "api":
                        # Добавляем API-шаг
                        extra = step.get("extra", {})
                        # extra.setdefault("method", step["method"])
                        # extra.setdefault("url", step["url"])
                        # extra.setdefault("value", step["value"])

                        api_action = {
                            "action_type": "API",
                            "method": step["method"],
                            "url": step["url"],
                            "headers": step.get("headers", {}),
                            "data": step.get("data"),
                            "files": step.get("files", {}),
                            "value": step["value"],
                            "extra": extra
                        }
                        full_action_plan.append(api_action)
                    else:
                        full_action_plan.append({"action_type": step["type"], "value": step["value"]})

                existing_case.is_valid = is_valid
                existing_case.validation_reason = validation_reason
                existing_case.action_plan = full_action_plan
                existing_case.action_plan_id = action_plan_id

                logger.info(f"sop_validation {existing_case.case_id} | {existing_case.is_valid=} | {existing_case.validation_reason=} {existing_case.action_plan=}")

            # Обновление позиции, если указано новое значение
            if case.new_position is not None and existing_case.position != case.new_position:
                await recalculate_positions(session, existing_case.suite_id, Case, "suite_id", "position")
                suite_cases_query = (
                    select(Case)
                    .where(Case.suite_id == existing_case.suite_id)
                    .order_by(Case.position)
                )
                suite_cases_result = await session.execute(suite_cases_query)
                suite_cases = suite_cases_result.scalars().all()
                for other_case in suite_cases:
                    if other_case.case_id == case.case_id:
                        continue
                    if case.new_position < existing_case.position:
                        if case.new_position <= other_case.position < existing_case.position:
                            other_case.position += 1
                    else:
                        if existing_case.position < other_case.position <= case.new_position:
                            other_case.position -= 1
                existing_case.position = case.new_position
                await session.flush()
                await recalculate_positions(session, existing_case.suite_id, Case, "suite_id", "position")

            # Обновляем остальные поля кейса
            update_data = case.model_dump(exclude_unset=True)

            if case.name is not None:
                existing_case.name = case.name
            if "context" in update_data:
                existing_case.context = case.context
            if "description" in update_data:
                existing_case.description = case.description
            if case.before_browser_start is not None:
                existing_case.before_browser_start = case.before_browser_start
            if case.before_steps is not None:
                existing_case.before_steps = case.before_steps
            if case.steps is not None:
                existing_case.steps = case.steps
            if case.after_steps is not None:
                existing_case.after_steps = case.after_steps
            if "url" in update_data:
                existing_case.url = str(case.url) if case.url else None
            if case.variables is not None:
                existing_case.variables = case.variables
            if case.type is not None:
                existing_case.type = case.type
            if "status" in update_data:
                existing_case.status = case.status
            if "priority" in update_data:
                existing_case.priority = case.priority
            if "external_id" in update_data:
                existing_case.external_id = case.external_id
            if "environment_id" in update_data:
                existing_case.environment_id = case.environment_id

            if shared_steps_ids:
                await _update_case_shared_steps_links(
                    session, case.case_id, shared_steps_ids
                )

            await session.flush()
            await session.refresh(existing_case)
            return CaseRead.model_validate(existing_case)

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(e, exc_info=True)
        mess = {"status": "error", "message": f"Error: {e}"}
        raise HTTPException(400, mess)


async def update_case_position(user: User,
                               case_id: UUID4,
                               new_position: int,
                               session: AsyncSession):
    try:
        async with session.begin():

            existing_case_query = (
                select(Case)
                .join(ProjectUser, and_(ProjectUser.project_id == Case.project_id,
                                        ProjectUser.workspace_id == user.active_workspace_id,
                                        ProjectUser.user_id == user.user_id))
                .where(Case.case_id == case_id)
            )

            existing_case_result = await session.execute(existing_case_query)
            case = existing_case_result.scalars().one_or_none()

            if not case:
                raise HTTPException(status_code=404, detail="Case not found")
            if case.position == new_position:
                return JSONResponse(content={"status": "current_position = new_position"})

            suite_id = case.suite_id
            # Пересчитываем сначала, чтобы правильные позиции были перед изменением
            await recalculate_positions(session, suite_id, Case, "suite_id", "position")

            suite_cases_query = (
                select(Case)
                .where(Case.suite_id == case.suite_id)
                .order_by(Case.position)
            )
            suite_cases_result = await session.execute(suite_cases_query)
            suite_cases = suite_cases_result.scalars().all()

            for other_case in suite_cases:
                if other_case.case_id == case_id:
                    continue
                if new_position < case.position:
                    if new_position <= other_case.position < case.position:
                        other_case.position += 1
                else:
                    if case.position < other_case.position <= new_position:
                        other_case.position -= 1

            case.position = new_position
            await session.flush()
            await recalculate_positions(session, suite_id, Case, "suite_id", "position")  # Финальный пересчет
            return JSONResponse(content={"status": "OK"})
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(e, exc_info=True)
        mess = {"status": "error", "message": f"Error: {e}"}
        raise HTTPException(400, mess)


async def recalculate_positions(session: AsyncSession,
                                parent_id,
                                model_class,
                                parent_key,
                                position_key,
                                project_id=None):

    query = (
        select(model_class)
        .where(getattr(model_class, parent_key) == parent_id)
    )

    if project_id is not None:
        query = query.where(getattr(model_class, 'project_id') == project_id)

    query = query.order_by(getattr(model_class, position_key))

    results = await session.execute(query)
    items = results.scalars().all()

    for index, item in enumerate(items):
        setattr(item, position_key, index + 1)

    await session.flush()


async def update_shared_steps(shared_steps: SharedStepsUpdate,
                              user: User,
                              session: AsyncSession) -> CaseRead:
    try:
        async with transaction_scope(session):

            existing_shared_steps_query = (
                select(SharedSteps)
                .join(ProjectUser, and_(ProjectUser.project_id == SharedSteps.project_id,
                                        ProjectUser.workspace_id == user.active_workspace_id,
                                        ProjectUser.user_id == user.user_id))
                .where(SharedSteps.shared_steps_id == shared_steps.shared_steps_id)
            )

            existing_shared_steps_result = await session.execute(existing_shared_steps_query)
            existing_shared_steps = existing_shared_steps_result.scalars().one_or_none()

            if not existing_shared_steps:
                raise HTTPException(status_code=404, detail="Shared steps not found or not authorized")

            # Используем новые значения или существующие, если они не обновлялись

            sop = shared_steps.steps if shared_steps.steps is not None else existing_shared_steps.steps
            curl_validate(sop, [])

            is_valid = True
            action_plan_id = str(uuid.uuid4())
            validation_reason = {}
            action_plan = []
            full_action_plan = []
            all_steps = []
            validation_step_indices = []  # Индексы шагов, которые отправляем на валидацию

            for step in sop:
                if isinstance(step, str):
                    raise HTTPException(status_code=400, detail="Step must be dict")
                elif isinstance(step, dict):
                    if "value" not in step:
                        raise HTTPException(status_code=400, detail="Not found value in step")

                    if step.get("type") in ("action"):
                        all_steps.append(step)
                        validation_step_indices.append(len(all_steps) - 1)
                    elif step.get("type") in ("api", "shared_step"):  # не отправляем в rewriter
                        all_steps.append(step)
                    else:
                        raise HTTPException(status_code=400, detail=f"Uncorrect type {step.get('type')}")

            # Формируем SOP только для валидируемых шагов
            validation_sop = [
                step["value"]
                for idx, step in enumerate(all_steps)
                if idx in validation_step_indices
            ]

            post_data = {
                'sop': extract_steps(validation_sop),
                'action_plan_id': action_plan_id,
                'user_id': str(user.user_id),
                'case_id': str(shared_steps.shared_steps_id)
            }
            if len(post_data['sop']) > 0:
                status, res = await async_request(f"http://{CLICKER_IP}:{CLICKER_PORT}/sop_validation",
                                                  method='post',
                                                  params=post_data, timeout=60)
                if status != 200:
                    raise HTTPException(status_code=400, detail=f"sop_validation error: {res}")

                else:
                    is_valid = res.get("is_valid", False)
                    validation_reason = res.get("validation_reason", {})
                    action_plan = res.get("action_plan", [])

                    # КОРРЕКТИРУЕМ ИНДЕКСЫ: преобразуем индексы из validation_sop в оригинальные индексы all_steps
                    corrected_validation_reason = {}
                    for val_index, reason in validation_reason.items():
                        if val_index.isdigit():
                            val_index_int = int(val_index)
                            if val_index_int < len(validation_step_indices):
                                original_index = validation_step_indices[val_index_int]
                                corrected_validation_reason[str(original_index)] = reason
                            else:
                                corrected_validation_reason[val_index] = reason
                        else:
                            corrected_validation_reason[val_index] = reason

                    validation_reason = corrected_validation_reason

                    # не сохраняем кейс
                    if is_valid is False:
                        raise HTTPException(status_code=400, detail=f"{validation_reason}")

            # Формируем полный action_plan, включая API шаги
            action_plan_ptr = 0  # Указатель на текущий элемент в action_plan
            for idx, step in enumerate(all_steps):
                if idx in validation_step_indices:
                    # Берём следующий шаг из action_plan
                    if action_plan_ptr < len(action_plan):
                        full_action_plan.append(action_plan[action_plan_ptr])
                        action_plan_ptr += 1
                elif step.get("type") == "api":
                    # Добавляем API-шаг
                    extra = step.get("extra", {})
                    api_action = {
                        "action_type": "API",
                        "method": step["method"],
                        "url": step["url"],
                        "headers": step.get("headers", {}),
                        "data": step.get("data"),
                        "files": step.get("files", {}),
                        "value": step["value"],
                        "extra": extra
                    }
                    full_action_plan.append(api_action)
                else:
                    full_action_plan.append({"action_type": step["type"], "value": step["value"]})

            existing_shared_steps.is_valid = is_valid
            existing_shared_steps.validation_reason = validation_reason
            existing_shared_steps.action_plan = full_action_plan
            existing_shared_steps.action_plan_id = action_plan_id

            logger.info(f"sop_validation: {is_valid=} | {validation_reason=} | {action_plan=}")

            # Обновляем остальные
            update_data = shared_steps.model_dump(exclude_unset=True)

            if shared_steps.name is not None:
                existing_shared_steps.name = shared_steps.name

            if "description" in update_data:
                existing_shared_steps.description = shared_steps.description

            if shared_steps.steps is not None:
                existing_shared_steps.steps = shared_steps.steps

            await session.flush()
            await session.refresh(existing_shared_steps)
            return SharedStepsRead.model_validate(existing_shared_steps)

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(e, exc_info=True)
        mess = {"status": "error", "message": f"Error: {e}"}
        raise HTTPException(400, mess)


# delete
async def delete_project(project_id: UUID4,
                         session: AsyncSession,
                         user: User) -> JSONResponse:
    try:
        async with transaction_scope(session):
            query = (
                select(Project)
                .join(ProjectUser, and_(ProjectUser.project_id == Project.project_id,
                                        ProjectUser.workspace_id == user.active_workspace_id,
                                        ProjectUser.user_id == user.user_id))
                .where(Project.project_id == project_id)
            )

            result = await session.execute(query)
            project = result.scalars().one_or_none()

            if not project:
                return JSONResponse(content={"status": "not found or not authorized to delete this project"})

            # нужно убрать проект у всех
            await session.execute(
                delete(ProjectUser).where(
                    ProjectUser.workspace_id == user.active_workspace_id,
                    ProjectUser.project_id == project_id
                )
            )
            await session.flush()

            # Удаляем все окружения проекта
            await session.execute(
                delete(Environment).where(Environment.project_id == project_id)
            )
            await session.flush()

            # Удаляем все records
            await session.execute(
                delete(HappyPass).where(HappyPass.project_id == project_id)
            )
            await session.flush()

            # нужно убрать все справочники переменных
            variables_query = await session.execute(
                select(Variables).where(Variables.project_id == project_id)
            )
            variables = variables_query.scalars().all()

            for variable in variables:
                await session.delete(variable)
            await session.flush()

            # теперь грохаем проект
            await session.delete(project)
            await session.flush()

            return JSONResponse(content={"status": "OK"})

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(e, exc_info=True)
        mess = {"status": "error", "message": f"Error: {e}"}
        raise HTTPException(400, mess)


async def delete_suite(suite_id: UUID4,
                       session: AsyncSession,
                       user: User) -> JSONResponse:
    try:
        async with session.begin():
            query = (
                select(ProjectUser.user_id, Suite, Suite.parent_id)
                .join(Suite, and_(ProjectUser.project_id == Suite.project_id,
                                  ProjectUser.workspace_id == user.active_workspace_id,
                                  ProjectUser.user_id == user.user_id))
                .where(Suite.suite_id == suite_id)
            )

            result = await session.execute(query)
            result = result.unique().one_or_none()

            if not result:
                return JSONResponse(content={"status": "not found or not authorized to delete this suite"})

            project_user_id, suite, parent_id = result

            await session.delete(suite)
            await session.flush()
            await recalculate_positions(session, parent_id, Suite, "parent_id", "position", suite.project_id)
            return JSONResponse(content={"status": "OK"})

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(e, exc_info=True)
        mess = {"status": "error", "message": f"Error: {e}"}
        raise HTTPException(400, mess)


async def delete_case(case_ids: List[UUID4],
                      session: AsyncSession,
                      user: User) -> JSONResponse:
    try:
        async with session.begin():
            for case_id in case_ids:
                query = (
                    select(ProjectUser.user_id, Case, Suite.suite_id)
                    .join(Suite, and_(ProjectUser.project_id == Suite.project_id,
                                      ProjectUser.workspace_id == user.active_workspace_id,
                                      ProjectUser.user_id == user.user_id))
                    .join(Case, Suite.suite_id == Case.suite_id)
                    .where(Case.case_id == case_id)
                )
                result = await session.execute(query)
                result = result.unique().one_or_none()
                if not result:
                    return JSONResponse(content={"status": "not found or not authorized to delete this case"})

                project_user_id, case, suite_id = result

                await session.delete(case)
                await session.flush()
                # Recalculate positions
                await recalculate_positions(session, suite_id, Case, "suite_id", "position")
            return JSONResponse(content={"status": "OK"})
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(e, exc_info=True)
        mess = {"status": "error", "message": f"Error: {e}"}
        raise HTTPException(400, mess)


# read

async def get_user_tree(user: User,
                        session: AsyncSession,
                        project_id: Optional[UUID4] = None,
                        suite_id: Optional[UUID4] = None,
                        filter_cases: str = None) -> List[Union[ProjectReadFull, SuiteReadFull, CaseRead]]:
    """Вывод иерархии пользователя с возможностью фильтрации по проекту или сьюту."""

    try:
        if suite_id:
            query = (
                select(Suite, ProjectUser.project_id)
                # .join(Project, Suite.project_id == Project.project_id)
                .join(ProjectUser, and_(ProjectUser.project_id == Suite.project_id,
                                        ProjectUser.workspace_id == user.active_workspace_id,
                                        ProjectUser.user_id == user.user_id))
                .options(
                    selectinload(Suite.cases),
                    selectinload(Suite.children)
                )
                .where(Suite.suite_id == suite_id)
            )

            results = await session.execute(query)
            suite_data = results.unique().one_or_none()

            if not suite_data:
                return []

            suite, project_project_id = suite_data

            if project_id and project_project_id != project_id:
                return []

            return [await transform_suite(suite, project_project_id, filter_cases)]

        if project_id:
            project_query = (
                select(Project)
                .options(
                    selectinload(Project.suites).selectinload(Suite.cases),
                    selectinload(Project.suites).selectinload(Suite.children)
                )
                .join(ProjectUser, and_(ProjectUser.project_id == Project.project_id,
                                        ProjectUser.workspace_id == user.active_workspace_id,
                                        ProjectUser.user_id == user.user_id))
                .where(Project.project_id == project_id)
            )

            project_results = await session.execute(project_query)
            project = project_results.scalars().one_or_none()

            if not project:
                return []

            return [await transform_project(project, filter_cases)]

        all_projects_query = (
            select(Project)
            .options(
                selectinload(Project.suites).selectinload(Suite.cases),
                selectinload(Project.suites).selectinload(Suite.children)
            )
            .join(ProjectUser, and_(ProjectUser.project_id == Project.project_id,
                                    ProjectUser.workspace_id == user.active_workspace_id,
                                    ProjectUser.user_id == user.user_id))
        )

        st = time.perf_counter()
        project_results = await session.execute(all_projects_query)
        projects = project_results.scalars().unique().all()
        et = time.perf_counter()
        logger.info(f"Query get_user_tree without filters: {(et - st):.4f} seconds")

        return [await transform_project(project, filter_cases) for project in projects]

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(e, exc_info=True)
        mess = {"status": "error", "message": f"Error: {e}"}
        raise HTTPException(400, mess)


async def transform_project(project: Project, filter_cases: Optional[str] = None) -> ProjectReadFull:
    suites = sorted(project.suites, key=lambda s: s.position)
    return ProjectReadFull(
        project_id=project.project_id,
        name=project.name,
        description=project.description,
        suites=[await transform_suite(suite, project.project_id, filter_cases) for suite in suites if not suite.parent_id]
    )


async def transform_suite(suite: Suite, project_id: UUID4, filter_cases: Optional[str] = None) -> SuiteReadFull:

    children = sorted(await suite.awaitable_attrs.children, key=lambda s: s.position)
    cases = sorted(await suite.awaitable_attrs.cases, key=lambda c: c.position)

    # Фильтруем только кейсы
    filtered_cases = [await transform_case(case, project_id, filter_cases) for case in cases]
    # Убираем None (отфильтрованные кейсы)
    filtered_cases = [case for case in filtered_cases if case is not None]

    return SuiteReadFull(
        suite_id=suite.suite_id,
        name=suite.name,
        description=suite.description,
        parent_id=suite.parent_id,
        position=suite.position,
        cases=filtered_cases,
        children=[await transform_suite(child, project_id, filter_cases) for child in children]
    )


async def transform_case(case: Case, project_id: UUID4, filter_cases: Optional[str] = None) -> CaseRead:

    if filter_cases:
        case_data = {
            "name": case.name,
            "url": case.url,
            "before_browser_start": case.before_browser_start,
            "before_steps": case.before_steps,
            "steps": case.steps,
            "after_steps": case.after_steps
        }
        if not search_for_filter_cases(filter_cases, case_data):
            return None

    return CaseRead(
        case_id=case.case_id,
        suite_id=case.suite_id,
        name=case.name,
        context=case.context,
        description=case.description,
        before_browser_start=case.before_browser_start,
        before_steps=case.before_steps,
        steps=case.steps,
        after_steps=case.after_steps,
        type=case.type,
        status=case.status,
        priority=case.priority,
        url=case.url,
        is_valid=case.is_valid,
        validation_reason=case.validation_reason,
        action_plan=case.action_plan,
        external_id=case.external_id,
        position=case.position,
        variables=case.variables,
        project_id=project_id,
        environment_id=case.environment_id
    )


async def get_list_projects(user: User,
                            session: AsyncSession,
                            search: Optional[str] = None):
    try:
        async with session.begin():
            stmt = (
                select(
                    Project.project_id,
                    Project.name,
                    Project.description,
                    Project.parallel_exec,
                    func.count(func.distinct(Suite.suite_id)).label('suite_count'),
                    func.count(func.distinct(Case.case_id)).label('case_count'),
                    func.count(func.distinct(RunCase.run_id)).label('run_count')
                )
                .select_from(Project)
                .join(ProjectUser, and_(ProjectUser.workspace_id == user.active_workspace_id,
                                        ProjectUser.user_id == user.user_id,
                                        ProjectUser.project_id == Project.project_id))
                .outerjoin(Suite, Suite.project_id == Project.project_id)
                .outerjoin(Case, Case.suite_id == Suite.suite_id)
                .outerjoin(RunCase, RunCase.case_id == Case.case_id)
                .where(Project.workspace_id == user.active_workspace_id)
                .group_by(Project.project_id, Project.name, Project.description, Project.parallel_exec)
            )
            st = time.perf_counter()
            result = await session.execute(stmt)
            list_projects = result.fetchall()
            et = time.perf_counter()
            logger.info(f"Query get_list_projects: {(et - st):.4f} seconds")
            # await update_usage_count(user.active_workspace_id, "list_projects", 1)
            projects = [ProjectSummary.model_validate(project) for project in list_projects]
            # фильтрация по названию и описанию
            if search:
                search_lower = search.lower()
                projects = [
                    p for p in projects
                    if (p.name and search_lower in p.name.lower()) or
                       (p.description and search_lower in p.description.lower())
                ]
            return projects

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(e, exc_info=True)
        mess = {"status": "error", "message": f"Error: {e}"}
        raise HTTPException(400, mess)


async def get_list_projects_by_workspace_id(workspace_id: UUID4,
                                            user: User,
                                            session: AsyncSession,
                                            search: Optional[str] = None):
    try:
        async with session.begin():

            result = await session.execute(
                select(WorkspaceMembership)
                .join(Workspace, Workspace.workspace_id == WorkspaceMembership.workspace_id)
                .where(
                    WorkspaceMembership.user_id == user.user_id,
                    WorkspaceMembership.status == 'Active',
                    WorkspaceMembership.workspace_id == workspace_id
                )
            )

            workspace = result.scalars().one_or_none()
            if not workspace:
                raise HTTPException(status_code=403, detail="User not found or not active")
            if workspace.role == Roles.ROLE_READ_ONLY.value:
                raise HTTPException(status_code=403, detail="This role cant recording")

            stmt = (
                select(
                    Project.project_id,
                    Project.name,
                    Project.description,
                    Project.parallel_exec,
                    func.count(func.distinct(Suite.suite_id)).label('suite_count'),
                    func.count(func.distinct(Case.case_id)).label('case_count'),
                    func.count(func.distinct(RunCase.run_id)).label('run_count')
                )
                .select_from(Project)
                .join(ProjectUser, and_(ProjectUser.workspace_id == workspace_id,
                                        ProjectUser.user_id == user.user_id,
                                        ProjectUser.project_id == Project.project_id))
                .outerjoin(Suite, Suite.project_id == Project.project_id)
                .outerjoin(Case, Case.suite_id == Suite.suite_id)
                .outerjoin(RunCase, RunCase.case_id == Case.case_id)
                .where(Project.workspace_id == workspace_id)
                .group_by(Project.project_id, Project.name, Project.description, Project.parallel_exec)
            )
            st = time.perf_counter()
            result = await session.execute(stmt)
            list_projects = result.fetchall()
            et = time.perf_counter()
            logger.info(f"Query get_list_projects: {(et - st):.4f} seconds")
            # await update_usage_count(user.active_workspace_id, "list_projects", 1)
            projects = [ProjectSummary.model_validate(project) for project in list_projects]
            # фильтрация по названию и описанию
            if search:
                search_lower = search.lower()
                projects = [
                    p for p in projects
                    if (p.name and search_lower in p.name.lower()) or
                       (p.description and search_lower in p.description.lower())
                ]
            return projects

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(e, exc_info=True)
        mess = {"status": "error", "message": f"Error: {e}"}
        raise HTTPException(400, mess)


async def free_streams_for_active_workspace(user: User,
                                            session: AsyncSession,
                                            exclude_project_id: Optional[UUID4] = None):
    try:
        async with transaction_scope(session):
            query = (
                select(func.sum(Project.parallel_exec))
                .where(Project.workspace_id == user.active_workspace_id)
            )

            if exclude_project_id:
                query = query.where(Project.project_id != exclude_project_id)

            result = await session.execute(query)
            used_parallel = result.scalar() or 0

            workspace_limit = int(redis_client.get(f"{REDIS_PREFIX}_workspace_limit:{user.active_workspace_id}") or 0)

            return max(0, workspace_limit - used_parallel)

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(e, exc_info=True)
        mess = {"status": "error", "message": f"Error: {e}"}
        raise HTTPException(400, mess)


async def project_by_id(project_id: UUID4,
                        user: User,
                        session: AsyncSession):
    try:
        async with session.begin():
            stmt = (
                select(
                    Project.project_id,
                    Project.name,
                    Project.description,
                    Project.parallel_exec,
                    func.count(func.distinct(Suite.suite_id)).label('suite_count'),
                    func.count(func.distinct(Case.case_id)).label('case_count'),
                    func.count(func.distinct(RunCase.run_id)).label('run_count')
                )
                .select_from(Project)
                .join(ProjectUser, and_(ProjectUser.workspace_id == user.active_workspace_id,
                                        ProjectUser.user_id == user.user_id,
                                        ProjectUser.project_id == Project.project_id))
                .outerjoin(Suite, Suite.project_id == Project.project_id)
                .outerjoin(Case, Case.suite_id == Suite.suite_id)
                .outerjoin(RunCase, RunCase.case_id == Case.case_id)
                .where(Project.project_id == project_id)
                .group_by(Project.project_id, Project.name, Project.description, Project.parallel_exec)
            )
            st = time.perf_counter()
            result = await session.execute(stmt)
            project_by_id = result.fetchone()
            et = time.perf_counter()
            logger.info(f"Query project_by_id: {(et - st):.4f} seconds")

            if not project_by_id:
                raise HTTPException(status_code=404, detail="project_id not found")
            return ProjectSummary.model_validate(project_by_id)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(e, exc_info=True)
        mess = {"status": "error", "message": f"Error: {e}"}
        raise HTTPException(400, mess)


async def get_list_suites(user: User,
                          session: AsyncSession):
    try:
        async with session.begin():
            stmt = (
                select(
                    Suite.suite_id,
                    ProjectUser.project_id,
                    Suite.name,
                    Suite.description,
                    Suite.parent_id,
                    func.count(func.distinct(Case.case_id)).label('case_count')
                )
                .join(ProjectUser, and_(ProjectUser.workspace_id == user.active_workspace_id,
                                        ProjectUser.user_id == user.user_id,
                                        ProjectUser.project_id == Suite.project_id))
                .outerjoin(Case, Case.suite_id == Suite.suite_id)

                .group_by(Suite.suite_id, ProjectUser.project_id, Suite.name, Suite.description, Suite.parent_id)
            )
            st = time.perf_counter()
            result = await session.execute(stmt)
            list_suites = result.fetchall()
            et = time.perf_counter()
            logger.info(f"Query get_list_suites: {(et - st):.4f} seconds")
            # await update_usage_count(user.active_workspace_id, "list_suites", 1)
            return [SuiteSummary.model_validate(suite) for suite in list_suites]
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(e, exc_info=True)
        mess = {"status": "error", "message": f"Error: {e}"}
        raise HTTPException(400, mess)


async def case_by_external_id(external_id: str,
                              user: User,
                              session: AsyncSession):
    try:
        async with session.begin():

            query = (
                select(Case)
                .select_from(Case)
                .join(ProjectUser, and_(ProjectUser.project_id == Case.project_id,
                                        ProjectUser.workspace_id == user.active_workspace_id,
                                        ProjectUser.user_id == user.user_id))
                .where(Case.external_id == external_id)
            )

            result = await session.execute(query)
            # case = result.scalars().one_or_none()
            cases = result.scalars().all()
            if not cases:
                raise HTTPException(status_code=404, detail="Case not found or Not authorized to read this case")

        return [CaseRead.model_validate(case) for case in cases]
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(e, exc_info=True)
        mess = {"status": "error", "message": f"Error: {e}"}
        raise HTTPException(400, mess)


async def case_by_case_id(case_id: str,
                          user: User,
                          session: AsyncSession):
    try:
        async with session.begin():

            query = (
                select(Case)
                .select_from(Case)
                .join(ProjectUser, and_(ProjectUser.project_id == Case.project_id,
                                        ProjectUser.workspace_id == user.active_workspace_id,
                                        ProjectUser.user_id == user.user_id))
                .where(Case.case_id == case_id)
            )

            result = await session.execute(query)
            case = result.scalars().one_or_none()
            if not case:
                raise HTTPException(status_code=404, detail="Case not found or Not authorized to read this case")

        return CaseRead.model_validate(case)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(e, exc_info=True)
        mess = {"status": "error", "message": f"Error: {e}"}
        raise HTTPException(400, mess)


def extract_step_value(steps: List[Union[str, Dict[str, Any]]]) -> List[str]:
    total: List[str] = []
    for item in steps or []:
        if isinstance(item, str):
            total.append(item)
        elif isinstance(item, dict):
            v = item.get("value")
            if isinstance(v, str):
                total.append(v)
    return total


def search_shared_step(shared_step: SharedSteps, filter: str) -> bool:

    if shared_step.name and filter in shared_step.name.lower():
        return True
    if shared_step.description and filter in shared_step.description.lower():
        return True

    # steps: JSON list
    for el in extract_step_value(shared_step.steps):
        if filter in el.lower():
            return True
    return False


async def list_shared_steps_by_project_id(project_id: UUID4,
                                          user: User,
                                          session: AsyncSession,
                                          search: Optional[str] = None) -> List:
    try:
        async with transaction_scope(session):
            shared_steps_query = (
                select(SharedSteps)
                .join(ProjectUser, and_(SharedSteps.project_id == ProjectUser.project_id,
                                        ProjectUser.project_id == project_id,
                                        ProjectUser.user_id == user.user_id,
                                        ProjectUser.workspace_id == user.active_workspace_id))
            )
            shared_steps_results = await session.execute(shared_steps_query)
            list_shared_steps = shared_steps_results.scalars().unique().all()

            if not list_shared_steps:
                return []

            filter = (search or "").strip()
            if not filter:
                return [SharedStepsRead.model_validate(shared_steps) for shared_steps in list_shared_steps]

            st = time.perf_counter()
            # ищем в name, description и steps
            filtered = [x for x in list_shared_steps if search_shared_step(x, filter.lower())]
            et = time.perf_counter()
            logger.info(f"Search in shared steps: {(et - st):.4f} seconds")
            return [SharedStepsRead.model_validate(x) for x in filtered]

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(e, exc_info=True)
        mess = {"status": "error", "message": f"Error: {e}"}
        raise HTTPException(400, mess)


async def list_shared_steps_by_name(shared_steps_name: str,
                                    project_id: UUID4,
                                    user: User,
                                    session: AsyncSession) -> List:
    try:
        async with transaction_scope(session):
            shared_steps_query = (
                select(SharedSteps)
                .join(ProjectUser, and_(SharedSteps.project_id == ProjectUser.project_id,
                                        ProjectUser.project_id == project_id,
                                        ProjectUser.user_id == user.user_id,
                                        ProjectUser.workspace_id == user.active_workspace_id))
                .where(SharedSteps.name == shared_steps_name)
            )
            shared_steps_results = await session.execute(shared_steps_query)
            list_shared_steps = shared_steps_results.scalars().unique().all()

            if not list_shared_steps:
                return []
            return [SharedStepsRead.model_validate(shared_steps) for shared_steps in list_shared_steps]
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(e, exc_info=True)
        mess = {"status": "error", "message": f"Error: {e}"}
        raise HTTPException(400, mess)


async def shared_steps_by_id(shared_steps_id: UUID4,
                             user: User,
                             session: AsyncSession) -> List:
    try:
        async with transaction_scope(session):
            shared_steps_query = (
                select(SharedSteps)
                .join(ProjectUser, and_(SharedSteps.project_id == ProjectUser.project_id,
                                        ProjectUser.user_id == user.user_id,
                                        ProjectUser.workspace_id == user.active_workspace_id))
                .where(SharedSteps.shared_steps_id == shared_steps_id)
            )
            shared_steps_results = await session.execute(shared_steps_query)
            shared_steps = shared_steps_results.scalars().one_or_none()

            if not shared_steps:
                raise HTTPException(status_code=404, detail="Shared steps not found or Not authorized")

            return SharedStepsRead.model_validate(shared_steps)

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(e, exc_info=True)
        mess = {"status": "error", "message": f"Error: {e}"}
        raise HTTPException(400, mess)


async def delete_shared_steps(shared_steps_id: UUID4,
                              user: User,
                              session: AsyncSession) -> JSONResponse:
    try:
        async with transaction_scope(session):

            query = (
                select(SharedSteps)
                .join(ProjectUser, and_(SharedSteps.project_id == ProjectUser.project_id,
                                        ProjectUser.user_id == user.user_id,
                                        ProjectUser.workspace_id == user.active_workspace_id))
                .options(selectinload(SharedSteps.case_links).selectinload(CaseSharedSteps.case))
                .where(SharedSteps.shared_steps_id == shared_steps_id)
            )

            result = await session.execute(query)
            shared_steps = result.scalars().one_or_none()

            if not shared_steps:
                return JSONResponse(content={"status": "Not found or not authorized to delete shared_steps"})

            case_links_info = [
                {"case_id": str(case_link.case_id), "case_name": case_link.case.name}
                for case_link in shared_steps.case_links
            ]

            # если shared_steps используются в кейсах, то удалить нельзя
            if case_links_info:
                return JSONResponse(content={"status": "FAILED", "case_links": case_links_info})

            await session.delete(shared_steps)
            return JSONResponse(content={"status": "OK"})

    except IntegrityError as er:
        logger.error(er)
        raise HTTPException(status_code=400, detail="Shared steps are used in cases")
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(e, exc_info=True)
        mess = {"status": "error", "message": f"Error: {e}"}
        raise HTTPException(400, mess)
