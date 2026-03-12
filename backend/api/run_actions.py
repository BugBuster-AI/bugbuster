import asyncio
import copy
import json
import re
import time
import uuid
from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Union
from urllib.parse import urlencode, urlparse, urlunparse
from uuid import UUID

import urllib3
from fastapi import HTTPException
from fastapi.responses import JSONResponse
from minio import Minio
from pamqp.commands import Basic
from pydantic import UUID4
from sqlalchemy import (and_, asc, delete, desc, func, insert, or_, over,
                        select, update)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.orm.attributes import flag_modified

from api.actions import (check_usage_limits, search_for_filter_cases,
                         update_usage_count)
from api.variables_actions import compute_variable_value_from_raw_config
from config import (MINIO_ACCESS_KEY, MINIO_HOST, MINIO_PORT, MINIO_SECRET_KEY,
                    MINIO_SECURE, MINIO_PUBLIC_URL, REDIS_PREFIX, logger, redis_client, MINIO_USE_INTERNAL_PROXY)
from db.models import (Case, Environment, GroupRunCase, GroupRunCaseCase,
                       Project, ProjectUser, RunCase, SharedSteps, Suite, User,
                       Variables, VariablesDetails)
from db.session import async_session, transaction_scope
from schemas import (CaseFinalStatusEnum, CaseRead, CaseStatusEnum,
                     CaseTypeEnum, EnvironmentRead, ExecutionModeEnum,
                     GroupRunCaseCaseInput, GroupRunCaseCreate,
                     GroupRunCaseOrderBy, GroupRunCaseRead, GroupRunCaseUpdate,
                     RunSingleCase, SuiteRead)
from utils import (generate_presigned_url, select_minio_host,
                   select_trace_viewer_host)


def validate_group_run_cases_payload(cases: List[GroupRunCaseCaseInput]):
    """
    валидация нового формата передачи кейсов

    {
    "name": "Test Run Name",
    "project_id": "uuid",
    "parallel_exec": 3,
    "cases": [
        {
        "case_id": "case-uuid-1",
        "execution_mode": "sequential",
        "execution_order": 1
        },
        {
        "case_id": "case-uuid-2",
        "execution_mode": "sequential",
        "execution_order": 2
        },
        {
        "case_id": "case-uuid-3",
        "execution_mode": "parallel",
        "execution_order": null
        },
        {
        "case_id": "case-uuid-4",
        "execution_mode": "parallel",
        "execution_order": null
        }
    ]
    }


    """

    if not cases:
        return

    # уникальные case_id
    ids = [str(c.case_id) for c in cases]
    duplicate = [cid for cid, cnt in Counter(ids).items() if cnt > 1]
    if duplicate:
        raise HTTPException(status_code=400, detail=f"Duplicate case_ids: {duplicate}")

    # режимы
    seq = [c for c in cases if c.execution_mode == ExecutionModeEnum.sequential]
    prl = [c for c in cases if c.execution_mode == ExecutionModeEnum.parallel]

    # у параллельных нет порядка запуска
    bad_prl = [str(c.case_id) for c in prl if c.execution_order is not None]
    if bad_prl:
        raise HTTPException(status_code=400, detail=f"Parallel cases must have execution_order=null: {bad_prl}")

    # у последовательных обязателен порядок запуска
    bad_seq = [str(c.case_id) for c in seq if c.execution_order is None]
    if bad_seq:
        raise HTTPException(status_code=400, detail=f"Sequential cases must have execution_order set: {bad_seq}")

    # проверка порядка запуска у последовательных
    if seq:
        orders = [c.execution_order for c in seq]  # all not None
        if len(set(orders)) != len(orders):
            raise HTTPException(status_code=400, detail="Sequential execution_order must be unique")
        n = len(orders)
        if set(orders) != set(range(1, n + 1)):
            raise HTTPException(status_code=400, detail=f"Sequential execution_order must be contiguous 1..{n}")


async def free_streams_for_grouprun_by_project_id(project_id: UUID4,
                                                  user: User,
                                                  session: AsyncSession):
    try:
        async with transaction_scope(session):

            query = (
                select(Project.parallel_exec)
                .where(Project.workspace_id == user.active_workspace_id,
                       Project.project_id == project_id)
            )

            result = await session.execute(query)
            project_parallel = result.scalar()

            if project_parallel is None:
                raise HTTPException(status_code=404, detail="Project not found")

            return project_parallel if project_parallel else 0

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(e, exc_info=True)
        mess = {"status": "error", "message": f"Error: {e}"}
        raise HTTPException(400, mess)


async def streams_statistics(user: User,
                             session: AsyncSession):
    try:
        async with transaction_scope(session):
            st = time.perf_counter()
            # доступные проекты
            query = (select(Project.project_id, Project.parallel_exec)
                     .join(ProjectUser, and_(ProjectUser.project_id == Project.project_id,
                                             ProjectUser.workspace_id == user.active_workspace_id,
                                             ProjectUser.user_id == user.user_id)))

            projects_result = await session.execute(query)
            projects = projects_result.fetchall()
            # print("projects", projects)

            # групповые раны
            projects_ids = [project.project_id for project in projects]

            group_runs_query = (
                select(GroupRunCase.group_run_id, GroupRunCase.project_id, GroupRunCase.parallel_exec)
                .where(GroupRunCase.project_id.in_(projects_ids))
            )
            group_runs_result = await session.execute(group_runs_query)
            group_runs = group_runs_result.fetchall()
            # print("group_runs", group_runs)

            # workspace lim
            workspace_limit_key = f"{REDIS_PREFIX}_workspace_limit:{user.active_workspace_id}"
            workspace_limit = int(redis_client.get(workspace_limit_key) or 0)
            # print("workspace_limit", workspace_limit)

            streams_query = (
                select(RunCase.group_run_id,
                       RunCase.current_case_version,
                       RunCase.run_id)
                .where(
                    RunCase.group_run_id.isnot(None),
                    RunCase.status.in_([CaseStatusEnum.PREPARATION.value, CaseStatusEnum.IN_PROGRESS.value, CaseStatusEnum.STOP_IN_PROGRESS.value]),
                    RunCase.workspace_id == user.active_workspace_id
                )
            )
            streams_result = await session.execute(streams_query)
            streams = streams_result.fetchall()

            active_streams = {}
            # Только automated
            for run_case in streams:
                group_run_id, current_case_version, _ = run_case
                if isinstance(current_case_version, dict) and current_case_version.get('case_type_in_run') == CaseTypeEnum.AUTOMATED.value:
                    if group_run_id not in active_streams:
                        active_streams[group_run_id] = 0
                    active_streams[group_run_id] += 1
            # print("active_streams", active_streams)

            # collect stats
            project_statistics = {
                proj_id: {'active_streams': 0, 'total_streams': parallel_exec}
                for proj_id, parallel_exec in projects
            }

            group_statistics = {
                group_run_id: {'active_streams': active_streams.get(group_run_id, 0), 'total_streams': parallel_exec}
                for group_run_id, proj_id, parallel_exec in group_runs
            }

            for group_run_id, stats in group_statistics.items():
                project_id = next((proj_id for run_id, proj_id, _ in group_runs if run_id == group_run_id), None)
                if project_id and project_id in project_statistics:
                    project_statistics[project_id]['active_streams'] += stats['active_streams']

            workspace_statistics = {
                'active_streams': sum(data['active_streams'] for data in project_statistics.values()),
                'total_streams': workspace_limit
            }

            et = time.perf_counter()
            logger.info(f"Query streams_statistics: {(et - st):.4f} seconds")

            return {
                'workspace_statistics': workspace_statistics,
                'project_statistics': project_statistics,
                'group_run_statistics': group_statistics
            }

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(e, exc_info=True)
        mess = {"status": "error", "message": f"Error: {e}"}
        raise HTTPException(400, mess)


def mark_step_as_shared(section: list, shared_id, group_index: int, group_size: int) -> Any:
    """
    Помечает шаги как shared_steps.
    """
    new_section = []

    for step in section:
        if isinstance(step, dict):
            step_copy = copy.deepcopy(step)
            extra = step_copy.setdefault("extra", {})
            # ставим метки
            extra["shared_step"] = True
            extra["shared_step_id"] = shared_id
            extra["shared_step_group_index"] = group_index
            extra["shared_step_group_size"] = group_size
            step_copy["extra"] = extra
            new_section.append(step_copy)

    return new_section


def replace_shared_steps(case_dict: Dict[str, Any],
                         shared_steps: Dict[str, Any]) -> Dict[str, Any]:
    """Заменяет id shared_step внутри всех секций на значения"""

    # счётчик встраиваний для каждого shared_id (для шагов с одинаковым shared_id)
    group_counters = defaultdict(int)

    for section, steps in case_dict.items():
        if not isinstance(steps, list):
            continue

        new_steps = []
        for step in steps:
            if not isinstance(step, dict):
                new_steps.append(step)
                continue

            if step.get("type") == "shared_step" or step.get("action_type") == "shared_step":
                shared_id = step.get("value")
                shared_data = shared_steps.get(shared_id)
                if not shared_data:
                    raise HTTPException(status_code=404, detail=f"Shared step {shared_id} not found")

                # текущий индекс встраивания и размер группы
                group_index = group_counters[shared_id]

                if section == "action_plan":
                    to_insert = copy.deepcopy(shared_data["action_plan"])
                else:
                    to_insert = copy.deepcopy(shared_data["steps"])

                group_size = len(to_insert)

                if section == "action_plan":
                    # помечаем каждый элемент action_plan (если dict) одной и той же группой
                    marked = []
                    for s in to_insert:
                        marked.append(s)
                        # if isinstance(s, dict):
                        #     s_copy = copy.deepcopy(s)
                        #     extra = s_copy.setdefault("extra", {})
                        #     extra["shared_step"] = True
                        #     extra["shared_step_id"] = shared_id
                        #     extra["shared_step_group_index"] = group_index
                        #     extra["shared_step_group_size"] = group_size
                        #     s_copy["extra"] = extra
                        #     marked.append(s_copy)
                        # else:
                        #     marked.append(s)
                    new_steps.extend(marked)
                else:
                    new_steps.extend(mark_step_as_shared(to_insert, shared_id, group_index, group_size))

                # увеличиваем счётчик для следующего встраивания этого shared_id
                group_counters[shared_id] += 1
            else:
                new_steps.append(step)

        case_dict[section] = new_steps

    return case_dict


def process_prepare_case_steps_web(before_browser_start,
                                   before_steps,
                                   steps,
                                   after_steps,
                                   case_data_copy):

    web_steps = []
    total_steps = len(before_browser_start) + len(before_steps) + len(steps) + len(after_steps)

    def extract_step_description(item):
        if isinstance(item, str):
            return item
        elif isinstance(item, dict) and "value" in item:
            return item["value"]
        return str(item)

    def is_shared_step(item):
        if isinstance(item, dict):
            extra = item.get("extra")
            if extra is not None and isinstance(extra, dict):
                return extra.get("shared_step", False)
        return False

    current_part_num = 1  # Текущий номер шага, включая валидации

    def add_steps(steps_list, step_group, step_type="step", raw_steps_list=None):
        nonlocal current_part_num
        for step_index, step_description_raw in enumerate(steps_list):
            step_description = extract_step_description(step_description_raw)
            step_number = len(web_steps)
            is_shared = is_shared_step(step_description_raw)

            # Номер основного шага
            step_part_num = current_part_num
            current_part_num += 1  # Увеличиваем для следующего шага

            # берем оригинал шага без замен переменных из case_data_copy
            raw_step = None

            if raw_steps_list:
                raw_step = extract_step_description(raw_steps_list[step_index])

            step_data = {
                "status_step": CaseStatusEnum.UNTESTED.value,
                "index_step": step_number,
                "part_num": step_part_num,
                "part_all": total_steps,
                "comment": None,
                "attachments": None,
                "original_step_description": step_description,
                "raw_step_description": raw_step,
                "step_group": step_group,
                "step_type": step_type,
                "shared_step": is_shared,
                "extra": None
            }

            if isinstance(step_description_raw, dict):

                if "extra" not in step_description_raw or not isinstance(step_description_raw["extra"], dict):
                    step_description_raw["extra"] = {}

                if step_description_raw.get("type") == "api":
                    step_data["step_type"] = "api"

                    step_description_raw["extra"]['method'] = step_description_raw['method']
                    step_description_raw["extra"]['url'] = step_description_raw['url']
                    step_description_raw["extra"]['value'] = step_description_raw['value']

                if step_description_raw.get("type") == "expected_result":
                    step_data["step_type"] = "expected_result"
                    step_data["validation_result"] = {}

                step_data["extra"] = step_description_raw["extra"]

            web_steps.append(step_data)

    add_steps(before_browser_start, "before_browser", "api", case_data_copy.before_browser_start)
    add_steps(before_steps, "before", "step", case_data_copy.before_steps)
    add_steps(steps, "step", "step", case_data_copy.steps)
    add_steps(after_steps, "after", "step", case_data_copy.after_steps)

    return web_steps


async def copy_extra_to_action_plan(case_data: CaseRead) -> CaseRead:
    try:
        # Собираем все шаги в порядке их следования
        all_steps = []

        if hasattr(case_data, 'before_browser_start'):
            all_steps.extend(
                {
                    **({"type": "api", "value": step} if not isinstance(step, dict) else step),
                    "step_group": "before_browser_start"
                }
                for step in case_data.before_browser_start
            )
        if hasattr(case_data, 'before_steps'):
            all_steps.extend(
                {
                    **({"type": "action", "value": step} if not isinstance(step, dict) else step),
                    "step_group": "before_steps"
                }
                for step in case_data.before_steps
            )

        if hasattr(case_data, 'steps'):
            all_steps.extend(
                {
                    **({"type": "action", "value": step} if not isinstance(step, dict) else step),
                    "step_group": "steps"
                }
                for step in case_data.steps
            )

        if hasattr(case_data, 'after_steps'):
            all_steps.extend(
                {
                    **({"type": "action", "value": step} if not isinstance(step, dict) else step),
                    "step_group": "after_steps"
                }
                for step in case_data.after_steps
            )

        if hasattr(case_data, 'action_plan') and case_data.action_plan:
            for step, action in zip(all_steps, case_data.action_plan):
                action['step_group'] = step['step_group']

                if isinstance(step, dict) and 'extra' in step and step['extra']:
                    # Если в action нет extra или он пустой, копируем из шага
                    if 'extra' not in action or not action['extra']:
                        action['extra'] = step['extra']
                    # Иначе мержим, сохраняя приоритет за существующими данными в action
                    else:
                        action['extra'] = {**step['extra'], **action['extra']}

        return case_data

    except Exception as e:
        logger.error(f"Error copy_extra_to_action_plan: {e}", exc_info=True)
        return case_data


async def get_case_variables(
    case_data: CaseRead,
    user: User,
    session: AsyncSession
) -> Dict:
    # Собираем словарь переменных (имя -> значение)
    variables_dict = {}

    # 1. Определяем наборы переменных для поиска
    variables_kit_names = ["Default"]
    if case_data.variables and case_data.variables != "Default":
        variables_kit_names.insert(0, case_data.variables)

    # 2. Ищем соответствующие записи Variables и VariablesDetails
    try:
        async with transaction_scope(session):
            variables_query = (
                select(Variables, VariablesDetails)
                .join(VariablesDetails, Variables.variables_kit_id == VariablesDetails.variables_kit_id)
                .join(ProjectUser, and_(
                    Variables.project_id == ProjectUser.project_id,
                    ProjectUser.user_id == user.user_id,
                    ProjectUser.workspace_id == user.active_workspace_id
                ))
                .where(and_(
                    Variables.project_id == case_data.project_id,
                    Variables.variables_kit_name.in_(variables_kit_names)
                ))
            )

            results = await session.execute(variables_query)
            variables_data = results.all()

            # Сначала обрабатываем кастомный набор (если есть), затем Default
            for kit_name in variables_kit_names:
                for var_kit, var_detail in variables_data:
                    if var_kit.variables_kit_name == kit_name:
                        if var_detail.variable_name not in variables_dict:
                            if isinstance(var_detail.variable_config, dict):
                                calc_value = compute_variable_value_from_raw_config(var_detail.variable_config)
                                if calc_value:
                                    var_detail.variable_config["value"] = calc_value
                            variables_dict[var_detail.variable_name] = var_detail.variable_config or "undefined"
            return variables_dict
    except Exception as e:
        logger.error(f"Error get_case_variables: {e}", exc_info=True)
        return variables_dict


async def substitute_variables_in_case(
    case_data: CaseRead,
    user: User,
    session: AsyncSession
) -> CaseRead:
    """
    Подставляет значения переменных в case.

    1. Определяем набор переменных (variables_kit_name) из case_data.variables или "Default"
    2. Ищем записи в Variables для project_id и variables_kit_name (кастомный и Default)
    и берем VariablesDetails для найденных variables_kit_id
    3. Заменяем все вхождения {{variable_name}} в case_data на соответствующие значения
    4. сейвим позиции для отрисовки фронтом bold

      "data": {
        "action": "add_to_cart {{add_to_cart_val}}",
        "product_id": "430 {{product_id_val}}",
        "qty": "1 {{login}}",
        "user": {
           "contacts": [
                       {"type": "email", "value": "email"},
                       {"type": "phone", "value": "{{add_to_cart_val}} {{login}}"}
                       ]}
      },

      => => =>

    "extra": {
            "set_variables": {
                "add_to_cart_val": "123"
            },
            "variables": [
                {
                    "name": "add_to_cart_val",
                    "value": "undefined",
                    "original": "{{add_to_cart_val}}",
                    "positions": [
                        [
                            12,
                            21
                        ]
                    ],
                    "key": "data.action"
                },
                {
                    "name": "product_id_val",
                    "value": "undefined",
                    "original": "{{product_id_val}}",
                    "positions": [
                        [
                            4,
                            13
                        ]
                    ],
                    "key": "data.product_id"
                },
                {
                    "name": "login",
                    "value": "test_user",
                    "original": "{{login}}",
                    "positions": [
                        [
                            2,
                            11
                        ]
                    ],
                    "key": "data.qty"
                },
                {
                    "name": "add_to_cart_val",
                    "value": "undefined",
                    "original": "{{add_to_cart_val}}",
                    "positions": [
                        [
                            0,
                            9
                        ]
                    ],
                    "key": "data.user.contacts[1].value"
                },
                {
                    "name": "login",
                    "value": "test_user",
                    "original": "{{login}}",
                    "positions": [
                        [
                            10,
                            19
                        ]
                    ],
                    "key": "data.user.contacts[1].value"
                },

    """

    # 1. Определяем наборы переменных для поиска
    variables_kit_names = ["Default"]
    if case_data.variables and case_data.variables != "Default":
        variables_kit_names.insert(0, case_data.variables)

    # 2. Ищем соответствующие записи Variables и VariablesDetails
    try:
        async with transaction_scope(session):
            variables_query = (
                select(Variables, VariablesDetails)
                .join(VariablesDetails, Variables.variables_kit_id == VariablesDetails.variables_kit_id)
                .join(ProjectUser, and_(
                    Variables.project_id == ProjectUser.project_id,
                    ProjectUser.user_id == user.user_id,
                    ProjectUser.workspace_id == user.active_workspace_id
                ))
                .where(and_(
                    Variables.project_id == case_data.project_id,
                    Variables.variables_kit_name.in_(variables_kit_names)
                ))
            )

            results = await session.execute(variables_query)
            variables_data = results.all()

            # Собираем словарь переменных (имя -> значение)
            variables_dict = {}
            # Сначала обрабатываем кастомный набор (если есть), затем Default
            for kit_name in variables_kit_names:

                for var_kit, var_detail in variables_data:
                    if var_kit.variables_kit_name == kit_name:
                        if var_detail.variable_name not in variables_dict:
                            variables_dict[var_detail.variable_name] = compute_variable_value_from_raw_config(var_detail.variable_config) or "undefined"

            # 3. Рекурсивная замена переменных во всех полях case_data
            def replace_variables(data: Any, current_path: str = "", save_positions: bool = False) -> Tuple[Any, List]:

                var_pattern = re.compile(r'\{\{\s*([A-Za-z0-9_.-]+)\s*\}\}')

                def process_text(text: str, path: str) -> Tuple[str, List]:
                    if not isinstance(text, str):
                        return text, []

                    variables_info = []
                    result_text = text
                    offset = 0

                    # Пробегаем по совпадениям в оригинальном тексте (чтобы правильно считать позиции)
                    for match in var_pattern.finditer(text):
                        var_name = match.group(1)
                        original_var = match.group(0)
                        replacement = variables_dict.get(var_name, "undefined")

                        # start_pos в итоговой (после-замены) строке — считаем с учётом смещения
                        start_pos = match.start() - offset
                        end_pos = start_pos + len(replacement)

                        result_text = result_text[:match.start() - offset] + replacement + result_text[match.end() - offset:]
                        offset += len(original_var) - len(replacement)

                        if save_positions:
                            variables_info.append({
                                "name": var_name,
                                "value": replacement,
                                "original": original_var,
                                "positions": [[start_pos, end_pos]],
                                "key": path  # путь с индексом списка (если есть) — очистим позже
                            })

                    return result_text, variables_info

                if isinstance(data, str):
                    return process_text(data, current_path)

                elif isinstance(data, dict):
                    result = {}
                    all_variables = []

                    for key, value in data.items():
                        if key == "extra":
                            result[key] = value
                            continue

                        if current_path:
                            new_path = f"{current_path}.{key}"
                        else:
                            new_path = key

                        processed_value, variables = replace_variables(value, new_path, save_positions)
                        result[key] = processed_value
                        all_variables.extend(variables)

                    return result, all_variables

                elif isinstance(data, list):
                    result = []
                    all_variables = []

                    for i, item in enumerate(data):
                        # path для элемента списка содержит индекс — это нужно для правильной привязки
                        if current_path:
                            new_path = f"{current_path}[{i}]"
                        else:
                            new_path = f"[{i}]"

                        processed_item, variables = replace_variables(item, new_path, save_positions)
                        result.append(processed_item)
                        all_variables.extend(variables)

                    return result, all_variables

                # для чисел, None, булевых и т.п.
                return data, []

            # Обрабатываем поля case (список полей)
            fields_to_process = ['before_browser_start', 'before_steps', 'steps', 'after_steps', 'action_plan']

            for field in fields_to_process:
                if hasattr(case_data, field):
                    field_value = getattr(case_data, field)
                    if field_value:
                        processed, all_variables = replace_variables(field_value, "", True)

                        if isinstance(processed, list):
                            # Создаём контейнеры для переменных по элементам
                            element_variables = [[] for _ in range(len(processed))]

                            # Разбираем все найденные переменные и распределяем по элементам
                            for var in all_variables:
                                var_path = var.get("key", "")

                                # Если путь начинается с [index], выделяем индекс и чистый путь
                                if var_path.startswith('[') and ']' in var_path:
                                    bracket_pos = var_path.find(']')
                                    try:
                                        index = int(var_path[1:bracket_pos])
                                    except (ValueError, IndexError):
                                        # некорректный индекс — пропускаем
                                        continue

                                    # cleaned — путь без ведущего "[index]."
                                    cleaned = var_path[bracket_pos + 1:]
                                    if cleaned.startswith('.'):
                                        cleaned = cleaned[1:]

                                    # Копируем объект переменной и заменяем key на очищенный
                                    var_copy = dict(var)
                                    var_copy['key'] = cleaned  # может быть "" для plain-string steps

                                    if 0 <= index < len(element_variables):
                                        element_variables[index].append(var_copy)

                                else:
                                    # если ключ простой (типа "url", "curl", "value")
                                    # — пытаемся найти элемент, где такой ключ существует на верхнем уровне
                                    for i, item in enumerate(processed):
                                        if isinstance(item, dict):
                                            # берем верхний ключ (до точки)
                                            top_key = var_path.split('.', 1)[0] if var_path else var_path
                                            if top_key in item:
                                                # добавляем переменную как есть (ключ уже корректный)
                                                element_variables[i].append(var)
                                                break

                            # Добавляем переменные в extra каждого элемента (только если элемент — dict)
                            for i, item in enumerate(processed):
                                if isinstance(item, dict) and element_variables[i]:
                                    extra = item.get("extra", {})
                                    if not isinstance(extra, dict):
                                        extra = {}

                                    if "variables" in extra and isinstance(extra["variables"], list):
                                        extra["variables"].extend(element_variables[i])
                                    else:
                                        extra["variables"] = element_variables[i]

                                    item["extra"] = extra

                        # Сохраняем обратно в case_data
                        setattr(case_data, field, processed)

            return case_data

    except Exception as e:
        logger.error(f"Error substituting variables: {e}", exc_info=True)
        return case_data


async def merge_case_with_shared_steps(case_data: CaseRead,
                                       session: AsyncSession,
                                       user: User) -> CaseRead:
    """
    Встраивает shared_steps в case, включая steps и action_plan.
    """

    # (SOP)
    case_dict = {
        "before_browser_start": case_data.before_browser_start or [],
        "before_steps": case_data.before_steps or [],
        "steps": case_data.steps or [],
        "after_steps": case_data.after_steps or [],
        "action_plan": case_data.action_plan or []
    }

    # Собираем все shared_steps_id ---
    shared_ids = set()
    for section in case_dict:
        if isinstance(case_dict[section], list):
            for step in case_dict[section]:
                if isinstance(step, dict):
                    if step.get("type") == "shared_step" or step.get("action_type") == "shared_step":
                        shared_ids.add(UUID(step["value"]))

    if not shared_ids:
        return case_data

    # Грузим из БД ---
    shared_steps_query = (
        select(SharedSteps)
        .join(ProjectUser, and_(
            SharedSteps.project_id == ProjectUser.project_id,
            ProjectUser.user_id == user.user_id,
            ProjectUser.workspace_id == user.active_workspace_id
        ))
        .where(SharedSteps.shared_steps_id.in_(list(shared_ids)))
    )

    result = await session.execute(shared_steps_query)
    shared_objects = result.scalars().all()

    shared_steps_data = {
        str(s.shared_steps_id): {
            "steps": s.steps or [],
            "action_plan": s.action_plan or []
        }
        for s in shared_objects
    }

    # Проверяем, что все ID existing_case.shared_steps найдены
    missing = [str(v) for v in shared_ids if str(v) not in shared_steps_data]
    if missing:
        raise HTTPException(status_code=404, detail=f"Missing shared steps: {missing}")

    case_dict = replace_shared_steps(case_dict, shared_steps_data)

    updated_case_data = case_data.model_copy(update={
        "before_browser_start": case_dict["before_browser_start"],
        "before_steps": case_dict["before_steps"],
        "steps": case_dict["steps"],
        "after_steps": case_dict["after_steps"],
        "action_plan": case_dict["action_plan"]
    })

    return updated_case_data


async def run_single_case(case_id: UUID4,
                          session: AsyncSession,
                          user: User,
                          background_video_generate: Optional[bool] = True,
                          extra: Optional[str] = None) -> JSONResponse:
    try:
        async with session.begin():

            run_id = str(uuid.uuid4())
            existing_case_query = (
                select(Case)
                .join(Suite, Case.suite_id == Suite.suite_id)
                .join(ProjectUser, and_(Suite.project_id == ProjectUser.project_id,
                                        ProjectUser.workspace_id == user.active_workspace_id,
                                        ProjectUser.user_id == user.user_id))
                .where(Case.case_id == case_id)
            )

            existing_case_result = await session.execute(existing_case_query)
            existing_case = existing_case_result.scalars().one_or_none()

            if not existing_case:
                raise HTTPException(status_code=404, detail="Case not found")

            if existing_case.type != CaseTypeEnum.AUTOMATED.value:
                raise HTTPException(status_code=403, detail="This mode only for case with type auto")

            if existing_case.type == "automated" and existing_case.is_valid is False:
                raise HTTPException(status_code=403, detail="This case is invalid. Edit steps correctly")

            environment = {}
            if existing_case.environment_id:
                environment_query = (
                    select(Environment)
                    .where(Environment.environment_id == existing_case.environment_id)
                )

                environment_results = await session.execute(environment_query)
                environment = environment_results.scalars().one_or_none()
                environment = EnvironmentRead.model_validate(environment).model_dump(mode='json')

                if not environment:
                    raise HTTPException(status_code=404, detail="Environment not found")

            # разобраться с добавлением ensure_ascii=False
            # queue_name = f'{RABBIT_PREFIX}_celery.portal-clicker.run_single_case_queue'
            case_data = CaseRead.model_validate(existing_case)
            case_data = await merge_case_with_shared_steps(case_data, session, user)

            case_data_copy = case_data.model_copy(deep=True)

            case_data = await substitute_variables_in_case(case_data, user, session)
            case_variables = await get_case_variables(case_data, user, session)

            case_data.user_storage = case_variables
            case_data.case_type_in_run = CaseTypeEnum.AUTOMATED.value
            case_data.environment = environment
            case_data.original_case = case_data_copy

            automated_steps = process_prepare_case_steps_web(
                case_data.before_browser_start,
                case_data.before_steps,
                case_data.steps,
                case_data.after_steps,
                case_data_copy
            )
            await copy_extra_to_action_plan(case_data)
            # вставка в БД
            run_case_record = {
                "run_id": run_id,
                "case_id": case_id,
                "user_id": user.user_id,
                "status": CaseStatusEnum.IN_QUEUE,
                "steps": automated_steps,
                "current_case_version": case_data.model_dump(mode='json'),
                "workspace_id": user.active_workspace_id,
                "extra": extra,
                "project_id": case_data.project_id,
                "background_video_generate": background_video_generate,
                "case_type_in_run": CaseTypeEnum.AUTOMATED.value
            }

            query = insert(RunCase).values(**run_case_record)
            await session.execute(query)
            await session.flush()

            await update_usage_count(user.active_workspace_id, "start_group_run", 1)
            return JSONResponse(content={"run_id": run_id})

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(e, exc_info=True)
        mess = {"status": "error", "message": f"Error: {e}"}
        raise HTTPException(400, mess)


async def run_case_stop_by_id(run_id: UUID4,
                              session: AsyncSession,
                              user: User):
    try:
        async with session.begin():
            query = await session.execute(select(RunCase)
                                          .join(ProjectUser, and_(ProjectUser.project_id == RunCase.project_id,
                                                                  ProjectUser.workspace_id == user.active_workspace_id,
                                                                  ProjectUser.user_id == user.user_id))
                                          .where(RunCase.run_id == run_id))
            run_case: RunCase = query.scalars().one_or_none()

            if not run_case:
                raise HTTPException(status_code=404, detail="Run not found or not authorized to use this case")
            run_id = str(run_id)

            if run_case.status not in (CaseStatusEnum.IN_PROGRESS,
                                       CaseStatusEnum.PREPARATION,
                                       CaseStatusEnum.RETEST,
                                       CaseStatusEnum.IN_QUEUE,
                                       CaseStatusEnum.UNTESTED):
                raise HTTPException(status_code=400, detail=f"the run is already in its final status: {run_case.status}")

            if run_case.status in (CaseStatusEnum.IN_QUEUE, CaseStatusEnum.UNTESTED):
                run_case.status = CaseStatusEnum.STOPPED.value
                run_case.end_dt = datetime.now(timezone.utc)
                run_case.complete_time = (run_case.end_dt - run_case.start_dt).total_seconds() if run_case.start_dt else 0
                if not run_case.start_dt:
                    run_case.start_dt = datetime.now(timezone.utc)
                await session.flush()
                return JSONResponse(content={"run_id": "Task stopped"})

            else:
                # на этот статус фронт вешает лоадер
                run_case.status = CaseStatusEnum.STOP_IN_PROGRESS.value
                await session.flush()
                redis_client.sadd("stop_task", run_id)
                logger.info(f"sending stop {run_id} from user_id: {user.user_id}")
                return JSONResponse(content={"run_id": "Task is being processed in the background"})

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(e, exc_info=True)
        mess = {"status": "error", "message": f"Error: {e}"}
        raise HTTPException(400, mess)


async def start_group_run(group_run_id: UUID4, session: AsyncSession,
                          user: User, retest_cases_ids: Optional[List[UUID4]] = None,
                          run_automated: bool = False, run_manual: bool = False) -> JSONResponse:
    try:
        async with session.begin():
            group_run_case_query = (
                select(GroupRunCase)
                .join(ProjectUser, and_(ProjectUser.project_id == GroupRunCase.project_id,
                                        ProjectUser.workspace_id == user.active_workspace_id,
                                        ProjectUser.user_id == user.user_id))
                .options(selectinload(GroupRunCase.cases))
                .where(GroupRunCase.group_run_id == group_run_id)
            )
            group_run_case_result = await session.execute(group_run_case_query)
            group_run_case = group_run_case_result.scalars().one_or_none()

            if not group_run_case:
                raise HTTPException(status_code=404, detail="GroupRunCase not found")

            # запускается целиком только первый раз, далее через retest
            if group_run_case.status != CaseStatusEnum.UNTESTED.value and run_automated is False and run_manual is False:
                raise HTTPException(status_code=404, detail="GroupRunCase not in UNTESTED")

            # первый запуск невозможен при 0 лимита
            if group_run_case.status == CaseStatusEnum.UNTESTED.value and run_automated is False and run_manual is False:
                if group_run_case.parallel_exec <= 0:
                    raise HTTPException(status_code=403, detail="No streams available")

            environment_query = (
                select(Environment)
                .where(Environment.environment_id == group_run_case.environment)
            )

            environment_results = await session.execute(environment_query)
            environment = environment_results.scalars().one_or_none()
            environment = EnvironmentRead.model_validate(environment).model_dump(mode='json')

            if not environment:
                raise HTTPException(status_code=404, detail="Environment not found")

            # последние версии RunCase для каждого case_id
            run_cases_subquery = (
                select(
                    RunCase.group_run_case_id,
                    RunCase.status,
                    RunCase.run_id,
                    func.row_number().over(
                        partition_by=RunCase.group_run_case_id,
                        order_by=desc(RunCase.created_at)
                    ).label('row_number')
                )
                .where(RunCase.group_run_id == group_run_id)
            ).alias('latest_run_cases')

            run_cases_query = select(run_cases_subquery).where(run_cases_subquery.c.row_number == 1)
            run_cases_result = await session.execute(run_cases_query)
            latest_run_cases = {run_case.group_run_case_id: run_case for run_case in run_cases_result}

            NON_FINAL = {
                # CaseStatusEnum.UNTESTED.value,  # ?!
                CaseStatusEnum.IN_QUEUE.value,
                CaseStatusEnum.PREPARATION.value,
                CaseStatusEnum.STOP_IN_PROGRESS.value,
                CaseStatusEnum.IN_PROGRESS.value,
                CaseStatusEnum.RETEST.value,
            }

            sequential_done = True
            for case in group_run_case.cases:
                if case.execution_mode != ExecutionModeEnum.sequential.value:
                    continue

                latest = latest_run_cases.get(case.id)
                st = latest.status if latest else CaseStatusEnum.UNTESTED.value
                if st in NON_FINAL:
                    sequential_done = False
                    break

            records_to_insert = []
            run_ids = []

            for case in group_run_case.cases:

                case_id = case.id
                # если нам подали в retest конкретные кейсы
                selected_for_run = True if (not retest_cases_ids) or (retest_cases_ids and case_id in retest_cases_ids) else False

                latest = latest_run_cases.get(case_id)

                # retests
                is_retest_call = (run_automated or run_manual)
                if selected_for_run and is_retest_call:
                    # ручной перезапуск только в параллельном
                    if run_manual and case.execution_mode != ExecutionModeEnum.parallel.value:
                        raise HTTPException(
                            status_code=400,
                            detail=f"Manual retest allowed only for parallel cases. Update execution_mode to 'parallel' first. id={case.id}"
                        )

                # sequential: перезапуск в последовательном только после завершения секции
                if case.execution_mode == ExecutionModeEnum.sequential.value and not sequential_done:
                    raise HTTPException(
                        status_code=400,
                        detail="Sequential cases can be retested only after the whole Sequential section is finished (or after test run is finished/stopped)."
                    )

                # пропускаем, если уже запущен
                if selected_for_run:
                    status = latest.status if latest else None
                    if status in (CaseStatusEnum.IN_PROGRESS,
                                  CaseStatusEnum.RETEST,
                                  CaseStatusEnum.PREPARATION,
                                  CaseStatusEnum.STOP_IN_PROGRESS,
                                  CaseStatusEnum.IN_QUEUE):
                        # уже есть актуальная запись
                        continue

                case_data = CaseRead.model_validate(case.current_case_version)
                case_data = await merge_case_with_shared_steps(case_data, session, user)

                case_data_copy = case_data.model_copy(deep=True)

                case_data = await substitute_variables_in_case(case_data, user, session)
                case_variables = await get_case_variables(case_data, user, session)
                case_data.user_storage = case_variables

                # Проверка изначального типа кейса и флагов запуска
                # автоматический можно перезапускать и как авто и как ручной
                if selected_for_run:
                    # if run_automated is True and case_data.type != CaseTypeEnum.AUTOMATED.value:
                    #     continue
                    #     raise HTTPException(status_code=400, detail=f"Case type is not {CaseTypeEnum.AUTOMATED.value}")
                    if run_manual is True:
                        case.case_type_in_run = CaseTypeEnum.MANUAL.value

                    if run_automated is True:
                        # нельзя ретестить авто при нулевом лимите
                        if group_run_case.parallel_exec <= 0:
                            raise HTTPException(status_code=403, detail="No streams available")
                        #  !! нельзя ручной кейс запускать как автомат. Но нужно сохранить UNTESTED запись
                        # такой кейс все равно не запустится, так как ручные запускаются только если case.case_type_in_run MANUAL
                        if case_data.type != CaseTypeEnum.AUTOMATED.value:
                            case.case_type_in_run = case_data.type  # manual
                        else:
                            case.case_type_in_run = CaseTypeEnum.AUTOMATED.value

                # else: # ! просто оставляем как у него по дефолту в public.group_run_case_cases, он мог быть запущен
                #     # кейс не выбран — используем оригинальный тип для пустых записей
                #     case.case_type_in_run = case_data.type

                case_data.case_type_in_run = case.case_type_in_run
                case_data.execution_mode = case.execution_mode
                case_data.execution_order = case.execution_order
                case_data.environment = environment

                case_data.original_case = case_data_copy

                steps = process_prepare_case_steps_web(
                    case_data.before_browser_start,
                    case_data.before_steps,
                    case_data.steps,
                    case_data.after_steps,
                    case_data_copy
                )
                await copy_extra_to_action_plan(case_data)

                record = {"run_id": str(uuid.uuid4()),
                          "case_id": case.case_id,
                          "group_run_case_id": case_id,
                          "user_id": user.user_id,
                          "status": CaseStatusEnum.UNTESTED.value,
                          "steps": steps,
                          "current_case_version": case_data.model_dump(mode='json'),
                          "group_run_id": group_run_id,
                          "workspace_id": user.active_workspace_id,
                          "extra": group_run_case.extra,
                          "project_id": group_run_case.project_id,
                          "start_dt": None,
                          "background_video_generate": group_run_case.background_video_generate,
                          "case_type_in_run": case.case_type_in_run,
                          "execution_mode": case.execution_mode,
                          "execution_order": case.execution_order
                          }

                # Если кейс ручной, но run_manual не активен — не запускаем его
                if case.case_type_in_run == CaseTypeEnum.MANUAL.value and not run_manual:

                    # Если запись отсутствует — создаём UNTESTED для консистентности
                    if latest is None:
                        records_to_insert.append(record)
                    continue

                # если кейс НЕ выбран для запуска:
                if not selected_for_run:
                    # Если для него уже есть запись — ничего не делаем,
                    # если нет записи — создаём UNTESTED
                    if latest is None:
                        records_to_insert.append(record)
                    # если запись уже есть (включая UNTESTED) — оставляем как есть
                    continue

                # целевой статус для записи
                if case.case_type_in_run == CaseTypeEnum.AUTOMATED.value:
                    await check_usage_limits(user.active_workspace_id, "start_group_run", session)
                    target_status = CaseStatusEnum.IN_QUEUE.value

                else:  # MANUAL
                    if status is None or status == CaseStatusEnum.UNTESTED.value:
                        target_status = CaseStatusEnum.IN_PROGRESS.value
                    else:
                        target_status = CaseStatusEnum.RETEST.value if retest_cases_ids else CaseStatusEnum.IN_PROGRESS.value

                # Если НЕТ предыдущей записи — создаём новую
                if latest is None:
                    run_id = str(uuid.uuid4())
                    run_ids.append(run_id)

                    record["run_id"] = run_id
                    record["status"] = target_status
                    record["start_dt"] = datetime.now(timezone.utc) if target_status in (CaseStatusEnum.IN_PROGRESS.value,
                                                                                         CaseStatusEnum.RETEST.value) else None

                    records_to_insert.append(record)

                    # Если авто — обновляем счётчик использования
                    if case.case_type_in_run == CaseTypeEnum.AUTOMATED.value:
                        await update_usage_count(user.active_workspace_id, "start_group_run", 1)

                else:
                    # есть предыдущая запись — если она в UNTESTED, то обновляем её в target_status
                    if latest.status == CaseStatusEnum.UNTESTED.value:
                        run_id = str(latest.run_id)
                        run_ids.append(run_id)

                        update_values = {
                            "status": target_status,
                            "steps": steps,
                            "current_case_version": case_data.model_dump(mode='json'),
                            "workspace_id": user.active_workspace_id,
                            "extra": group_run_case.extra,
                            "project_id": group_run_case.project_id,
                            "background_video_generate": group_run_case.background_video_generate,
                            "case_type_in_run": case.case_type_in_run,
                            "execution_mode": case.execution_mode,
                            "execution_order": case.execution_order
                        }
                        if target_status in (CaseStatusEnum.IN_PROGRESS.value, CaseStatusEnum.RETEST.value):
                            update_values["start_dt"] = datetime.now(timezone.utc)

                        # UPDATE (в пределах транзакции)
                        await session.execute(
                            update(RunCase)
                            .where(RunCase.run_id == run_id)
                            .values(**update_values)
                        )

                        if case.case_type_in_run == CaseTypeEnum.AUTOMATED.value:
                            await update_usage_count(user.active_workspace_id, "start_group_run", 1)
                    else:
                        # есть запись, но не UNTESTED, (то есть в конечном) тогда создаём новую
                        run_id = str(uuid.uuid4())
                        run_ids.append(run_id)

                        record["run_id"] = run_id
                        record["status"] = target_status
                        record["start_dt"] = datetime.now(timezone.utc) if target_status in (CaseStatusEnum.IN_PROGRESS.value,
                                                                                             CaseStatusEnum.RETEST.value) else None
                        records_to_insert.append(record)

                        if case.case_type_in_run == CaseTypeEnum.AUTOMATED.value:
                            await update_usage_count(user.active_workspace_id, "start_group_run", 1)

            if records_to_insert:
                await session.execute(insert(RunCase).values(records_to_insert))

            # обновляем статус group_run_case если были созданы/обновлены рабочие записи
            if run_ids:
                group_run_case.status = CaseStatusEnum.IN_PROGRESS.value
                group_run_case.updated_at = datetime.now(timezone.utc)

            await session.flush()
            return JSONResponse(content={"run_ids": run_ids})

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(e, exc_info=True)
        mess = {"status": "error", "message": str(e)}
        raise HTTPException(400, mess)


async def stop_group_run(group_run_id: UUID4, session: AsyncSession, user: User) -> JSONResponse:
    try:
        async with session.begin():
            group_run_case_query = (
                select(GroupRunCase)
                .join(ProjectUser, and_(ProjectUser.project_id == GroupRunCase.project_id,
                                        ProjectUser.workspace_id == user.active_workspace_id,
                                        ProjectUser.user_id == user.user_id))
                .options(selectinload(GroupRunCase.cases))
                .where(GroupRunCase.group_run_id == group_run_id)
            )
            group_run_case_result = await session.execute(group_run_case_query)
            group_run_case = group_run_case_result.scalars().one_or_none()

            if not group_run_case:
                raise HTTPException(status_code=404, detail="GroupRunCase not found or not authorized to stop this group")

            case_type_in_run_all_cases = {case_template.id: case_template.case_type_in_run for case_template in group_run_case.cases}

            # последние версии RunCase для каждого case_id
            run_cases_subquery = (
                select(
                    RunCase.group_run_case_id,
                    RunCase.status,
                    RunCase.run_id,
                    func.row_number().over(
                        partition_by=RunCase.group_run_case_id,
                        order_by=desc(RunCase.created_at)
                    ).label('row_number')
                )
                .where(RunCase.group_run_id == group_run_id)
            ).alias('latest_run_cases')

            # run_cases_query = select(run_cases_subquery).where(run_cases_subquery.c.row_number == 1)
            run_cases_query = select(RunCase).join(
                run_cases_subquery, RunCase.run_id == run_cases_subquery.c.run_id
            ).where(run_cases_subquery.c.row_number == 1)

            run_cases_result = await session.execute(run_cases_query)
            run_cases = run_cases_result.scalars().all()

            stopped_runs = []
            for run_case in run_cases:
                status = run_case.status
                if status in (CaseStatusEnum.IN_PROGRESS, CaseStatusEnum.PREPARATION, CaseStatusEnum.RETEST,
                              CaseStatusEnum.IN_QUEUE, CaseStatusEnum.UNTESTED):
                    run_id = str(run_case.run_id)
                    current_case_type = case_type_in_run_all_cases.get(run_case.group_run_case_id, None)
                    if current_case_type is None:
                        raise HTTPException(status_code=404, detail="Not found case_type_in_run")

                    if current_case_type == CaseTypeEnum.MANUAL.value or (current_case_type == CaseTypeEnum.AUTOMATED.value and status in (CaseStatusEnum.IN_QUEUE, CaseStatusEnum.UNTESTED)):
                        run_case.status = CaseStatusEnum.STOPPED.value
                        run_case.end_dt = datetime.now(timezone.utc)
                        run_case.complete_time = (run_case.end_dt - run_case.start_dt).total_seconds() if run_case.start_dt else 0
                        if not run_case.start_dt:
                            run_case.start_dt = datetime.now(timezone.utc)
                        stopped_runs.append(run_id)
                        await session.flush()
                    else:
                        # на этот статус фронт вешает лоадер
                        run_case.status = CaseStatusEnum.STOP_IN_PROGRESS.value
                        await session.flush()

                        redis_client.sadd("stop_task", run_id)
                        stopped_runs.append(run_id)

                    logger.info(f"Requesting stop for run {run_id} from user_id: {user.user_id}")
            return JSONResponse(content={"stopped_run_ids": stopped_runs})

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(e, exc_info=True)
        mess = {"status": "error", "message": str(e)}
        raise HTTPException(400, mess)


async def run_case_get_by_id(run_id: str, session: AsyncSession,
                             user: User, host: str = None):

    try:
        current_minio_host = select_minio_host(host)

        if MINIO_USE_INTERNAL_PROXY:
            proxy = urllib3.ProxyManager(
                proxy_url=f"http://{current_minio_host}:{MINIO_PORT}",
                timeout=urllib3.Timeout(connect=5, read=60),
                cert_reqs="CERT_NONE",
            )
        http_client = proxy if MINIO_USE_INTERNAL_PROXY else None

        minio_client = Minio(
            endpoint=urlparse(MINIO_PUBLIC_URL).netloc or f"{current_minio_host}:{MINIO_PORT}",
            access_key=MINIO_ACCESS_KEY,
            secret_key=MINIO_SECRET_KEY,
            secure=MINIO_SECURE,
            http_client=http_client
        )
        async with session.begin():
            query = await session.execute(select(RunCase)
                                          .join(ProjectUser, and_(ProjectUser.project_id == RunCase.project_id,
                                                                  ProjectUser.workspace_id == user.active_workspace_id,
                                                                  ProjectUser.user_id == user.user_id))
                                          .where(RunCase.run_id == run_id))
            run_case: RunCase = query.scalars().one_or_none()

            if not run_case:
                raise HTTPException(status_code=404,
                                    detail="Run not found or not authorized to use this case")

        logs = await asyncio.to_thread(generate_presigned_url,
                                       'run-cases',
                                       f"{run_case.run_id}/{run_case.run_id}.log",
                                       host,
                                       minio_client)

        trace = await asyncio.to_thread(generate_presigned_url,
                                        'run-cases',
                                        f"{run_case.run_id}/{run_case.run_id}_trace.zip",
                                        host,
                                        minio_client)

        current_trace_viewer_host = select_trace_viewer_host(host)
        show_trace = f"{current_trace_viewer_host}/?{urlencode({'trace': trace})}"

        # Generate URLs for the video and steps
        if run_case.video:
            run_case.video['url'] = await asyncio.to_thread(generate_presigned_url,
                                                            run_case.video['bucket'],
                                                            run_case.video['file'],
                                                            host,
                                                            minio_client)

        for step in run_case.steps:
            if step.get('before_annotated_url', None):
                step['before_annotated_url']['url'] = await asyncio.to_thread(generate_presigned_url,
                                                                              step['before_annotated_url']['bucket'],
                                                                              step['before_annotated_url']['file'],
                                                                              host,
                                                                              minio_client)
            if step.get('before', None):
                step['before']['url'] = await asyncio.to_thread(generate_presigned_url,
                                                                step['before']['bucket'],
                                                                step['before']['file'],
                                                                host,
                                                                minio_client)
            if step.get('after', None):
                step['after']['url'] = await asyncio.to_thread(generate_presigned_url,
                                                               step['after']['bucket'],
                                                               step['after']['file'],
                                                               host,
                                                               minio_client)
            attachments = step.get('attachments', [])
            if attachments is not None:
                for step_attach in attachments:
                    if isinstance(step_attach, dict) and step_attach.get('bucket', None):
                        step_attach['url'] = await asyncio.to_thread(generate_presigned_url,
                                                                     step_attach['bucket'],
                                                                     step_attach['file'],
                                                                     host,
                                                                     minio_client)

        for attach in run_case.attachments:
            if isinstance(attach, dict) and attach.get('bucket', None):
                attach['url'] = await asyncio.to_thread(generate_presigned_url,
                                                        attach['bucket'],
                                                        attach['file'],
                                                        host,
                                                        minio_client)

        current_case_version = run_case.current_case_version  # or case
        case_data = CaseRead.model_validate(current_case_version)

        mess = {
            "run_id": str(run_case.run_id),
            "user_id": str(run_case.user_id),
            "case": case_data.model_dump(),
            "status": run_case.status,
            "execution_mode": run_case.execution_mode,
            "execution_order": run_case.execution_order,
            "run_summary": run_case.run_summary,
            "created_at": run_case.created_at,
            "start_dt": run_case.start_dt,
            "end_dt": run_case.end_dt,
            "complete_time": run_case.complete_time,
            "video": run_case.video,
            "steps": run_case.steps,
            "logs": logs,
            "trace": trace,
            "show_trace": show_trace,
            "attachments": run_case.attachments,
            "extra": run_case.extra
        }
        # logger.info(mess)
        return mess
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(e, exc_info=True)
        mess = {"status": "error", "message": f"Error: {e}"}
        raise HTTPException(400, mess)


async def get_runs_tree(current_user: User, session: AsyncSession,
                        host=None, group_run_id=None,
                        case_id=None, group_run_case_id=None, created_at=None, start_date=None,
                        end_date=None, status=None, limit: int = 10, offset: int = 0):

    try:

        async with session.begin():

            count_query = select(func.count(RunCase.run_id)).join(ProjectUser,
                                                                  and_(ProjectUser.project_id == RunCase.project_id,
                                                                       ProjectUser.workspace_id == current_user.active_workspace_id,
                                                                       ProjectUser.user_id == current_user.user_id))

            if group_run_id:
                count_query = count_query.where(RunCase.group_run_id == group_run_id)
            if case_id:
                count_query = count_query.where(RunCase.case_id == case_id)
            if group_run_case_id:
                count_query = count_query.where(RunCase.group_run_case_id == group_run_case_id)
            if created_at:
                count_query = count_query.where(RunCase.created_at >= created_at)
            if start_date:
                count_query = count_query.where(RunCase.start_dt >= start_date)
            if end_date:
                count_query = count_query.where(RunCase.end_dt <= end_date)
            if status:
                count_query = count_query.where(RunCase.status == status)

            st = time.perf_counter()
            total_result = await session.execute(count_query)
            total = total_result.scalar_one()
            et = time.perf_counter()
            logger.info(f"Query get count runs: {(et - st):.4f} seconds")

            subquery = select(RunCase.run_id).join(ProjectUser,
                                                   and_(ProjectUser.project_id == RunCase.project_id,
                                                        ProjectUser.workspace_id == current_user.active_workspace_id,
                                                        ProjectUser.user_id == current_user.user_id))

            if group_run_id:
                subquery = subquery.where(RunCase.group_run_id == group_run_id)
            if case_id:
                subquery = subquery.where(RunCase.case_id == case_id)
            if group_run_case_id:
                subquery = subquery.where(RunCase.group_run_case_id == group_run_case_id)
            if created_at:
                subquery = subquery.where(RunCase.created_at >= created_at)
            if start_date:
                subquery = subquery.where(RunCase.start_dt >= start_date)
            if end_date:
                subquery = subquery.where(RunCase.end_dt <= end_date)
            if status:
                subquery = subquery.where(RunCase.status == status)

            subquery = subquery.order_by(desc(RunCase.created_at)).limit(limit).offset(offset)
            aliased_subquery = subquery.alias("fast_filter")

            query = (
                select(RunCase)
                .join(aliased_subquery, RunCase.run_id == aliased_subquery.c.run_id)
                .order_by(desc(RunCase.created_at))
            )

            st = time.perf_counter()
            results = await session.execute(query)
            run_cases = results.unique().scalars().all()
            et = time.perf_counter()
            logger.info(f"Query get all runs: {(et - st):.4f} seconds")

            final_entries = []

            current_minio_host = select_minio_host(host)

            if MINIO_USE_INTERNAL_PROXY:
                proxy = urllib3.ProxyManager(
                    proxy_url=f"http://{current_minio_host}:{MINIO_PORT}",
                    timeout=urllib3.Timeout(connect=5, read=60),
                    cert_reqs="CERT_NONE",
                )
            http_client = proxy if MINIO_USE_INTERNAL_PROXY else None

            minio_client = Minio(
                endpoint=urlparse(MINIO_PUBLIC_URL).netloc or f"{current_minio_host}:{MINIO_PORT}",
                access_key=MINIO_ACCESS_KEY,
                secret_key=MINIO_SECRET_KEY,
                secure=MINIO_SECURE,
                http_client=http_client

            )

            # Process run_cases data
            for run_case in run_cases:
                final_img = None
                if run_case.steps:
                    final_step = run_case.steps[-1]
                    if final_step.get('before_annotated_url', None):
                        final_img = await asyncio.to_thread(
                            generate_presigned_url,
                            final_step['before_annotated_url']['bucket'],
                            final_step['before_annotated_url']['file'],
                            host,
                            minio_client
                        )

                logs = await asyncio.to_thread(generate_presigned_url,
                                               'run-cases',
                                               f"{run_case.run_id}/{run_case.run_id}.log",
                                               host,
                                               minio_client)
                trace = await asyncio.to_thread(generate_presigned_url,
                                                'run-cases',
                                                f"{run_case.run_id}/{run_case.run_id}_trace.zip",
                                                host,
                                                minio_client)
                current_trace_viewer_host = select_trace_viewer_host(host)
                show_trace = f"{current_trace_viewer_host}/?{urlencode({'trace': trace})}"

                if run_case.video:
                    run_case.video['url'] = await asyncio.to_thread(generate_presigned_url,
                                                                    run_case.video['bucket'],
                                                                    run_case.video['file'],
                                                                    host,
                                                                    minio_client)

                for step in run_case.steps:
                    if step.get('before_annotated_url', None):
                        step['before_annotated_url']['url'] = await asyncio.to_thread(generate_presigned_url,
                                                                                      step['before_annotated_url']['bucket'],
                                                                                      step['before_annotated_url']['file'],
                                                                                      host,
                                                                                      minio_client)
                    if step.get('before', None):
                        step['before']['url'] = await asyncio.to_thread(generate_presigned_url,
                                                                        step['before']['bucket'],
                                                                        step['before']['file'],
                                                                        host,
                                                                        minio_client)
                    if step.get('after', None):
                        step['after']['url'] = await asyncio.to_thread(generate_presigned_url,
                                                                       step['after']['bucket'],
                                                                       step['after']['file'],
                                                                       host,
                                                                       minio_client)

                    attachments = step.get('attachments', [])
                    if attachments is not None:
                        for step_attach in attachments:
                            if isinstance(step_attach, dict) and step_attach.get('bucket', None):
                                step_attach['url'] = await asyncio.to_thread(generate_presigned_url,
                                                                             step_attach['bucket'],
                                                                             step_attach['file'],
                                                                             host,
                                                                             minio_client)

                for attach in run_case.attachments:
                    if isinstance(attach, dict) and attach.get('bucket', None):
                        attach['url'] = await asyncio.to_thread(generate_presigned_url,
                                                                attach['bucket'],
                                                                attach['file'],
                                                                host,
                                                                minio_client)

                current_case_version = run_case.current_case_version
                case = CaseRead.model_validate(current_case_version)

                final_entries.append({
                    "run_id": str(run_case.run_id),
                    "user_id": str(run_case.user_id),
                    "group_run_id": str(run_case.group_run_id),
                    "group_run_case_id": str(run_case.group_run_case_id),
                    "status": run_case.status,
                    "execution_mode": run_case.execution_mode,
                    "execution_order": run_case.execution_order,
                    "run_summary": run_case.run_summary,
                    "final_img": final_img,
                    "created_at": run_case.created_at,
                    "start_dt": run_case.start_dt,
                    "end_dt": run_case.end_dt,
                    "complete_time": run_case.complete_time,
                    "case": case,
                    "steps": run_case.steps,
                    "logs": logs,
                    "trace": trace,
                    "show_trace": show_trace,
                    "video": run_case.video,
                    "attachments": run_case.attachments,
                    "extra": run_case.extra
                })

            # Подготовка данных о пагинации
            total_pages = (total - 1) // limit + 1
            current_page = (offset // limit) + 1

            pagination_info = {
                "total": total,
                "total_current_page": len(run_cases),
                "page": current_page,
                "size": limit,
                "pages": total_pages,
                "limit": limit,
                "offset": offset,
                "items": final_entries
            }

            return pagination_info
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(e, exc_info=True)
        mess = {"status": "error", "message": f"Error: {e}"}
        raise HTTPException(400, mess)


async def create_group_run_case(group_run_case_data: GroupRunCaseCreate,
                                session: AsyncSession,
                                user: User,
                                ) -> GroupRunCaseRead:
    try:
        async with transaction_scope(session):

            validate_group_run_cases_payload(group_run_case_data.cases)

            # env
            query = (
                select(Environment)
                .join(ProjectUser, and_(Environment.project_id == ProjectUser.project_id,
                                        ProjectUser.project_id == group_run_case_data.project_id,
                                        ProjectUser.workspace_id == user.active_workspace_id,
                                        ProjectUser.user_id == user.user_id))
                .where(Environment.environment_id == group_run_case_data.environment_id)
            )

            result = await session.execute(query)
            environment = result.scalars().one_or_none()

            if not environment:
                raise HTTPException(status_code=404, detail="Environment/Project not found or not authorized")

            # project limit
            project_limit = await free_streams_for_grouprun_by_project_id(group_run_case_data.project_id,
                                                                          user,
                                                                          session)

            if group_run_case_data.parallel_exec is None:
                group_run_case_data.parallel_exec = 0

            if group_run_case_data.parallel_exec > project_limit:
                raise HTTPException(status_code=400,
                                    detail=f"Requested parallel_exec ({group_run_case_data.parallel_exec}) exceeds project limit ({project_limit})")

            # host
            if group_run_case_data.host:
                parsed_host = urlparse(group_run_case_data.host)
                if not parsed_host.scheme or not parsed_host.netloc:
                    raise HTTPException(status_code=400, detail="Host must contain only scheme and domain")

                # Формируем host без path
                group_run_case_data.host = f"{parsed_host.scheme}://{parsed_host.netloc}"

            new_group_run_case = GroupRunCase(
                project_id=group_run_case_data.project_id,
                user_id=user.user_id,
                name=group_run_case_data.name,
                description=group_run_case_data.description,
                status=CaseStatusEnum.UNTESTED.value,
                environment=group_run_case_data.environment_id,
                deadline=group_run_case_data.deadline,
                parallel_exec=group_run_case_data.parallel_exec,
                host=group_run_case_data.host,
                extra=group_run_case_data.extra,
                variables=group_run_case_data.variables,
                background_video_generate=group_run_case_data.background_video_generate,
                current_phase=None,
                parallel_started_at=None,
            )
            session.add(new_group_run_case)
            await session.flush()

            # все кейсы из запроса
            case_ids = [c.case_id for c in group_run_case_data.cases]

            cases_query = (
                select(Case, Suite)
                .join(Suite, Case.suite_id == Suite.suite_id)
                .where(Case.case_id.in_(case_ids),
                       Suite.project_id == group_run_case_data.project_id)
            )
            cases_result = await session.execute(cases_query)
            rows = cases_result.all()
            db_cases_data = {str(c.case_id): (c, s) for c, s in rows}

            missing = [str(case_id) for case_id in case_ids if str(case_id) not in db_cases_data]
            if missing:
                raise HTTPException(status_code=404, detail=f"Case(s) not found in project: {missing}")

            req_cases_data = {str(x.case_id): x for x in group_run_case_data.cases}

            for cid_str, (existing_case, suite) in db_cases_data.items():

                req = req_cases_data[cid_str]

                # затесался невалидный автотест
                if existing_case.type == "automated" and existing_case.is_valid is False:
                    raise HTTPException(status_code=403,
                                        detail=f"This case {existing_case.case_id} is invalid. Edit steps correctly")
                # ручные кейсы только в палаллельном выполнении
                if existing_case.type == "manual" and req.execution_mode == ExecutionModeEnum.sequential:
                    raise HTTPException(status_code=400,
                                        detail=f"Manual case {existing_case.case_id} cannot be in sequential")

                existing_case_copy = CaseRead.model_validate(existing_case)

                # Обновление URL в рамках группового рана, если host указан
                if group_run_case_data.host:
                    if existing_case_copy.url:
                        parsed_url = urlparse(existing_case_copy.url.unicode_string())
                        parsed_host = urlparse(group_run_case_data.host)
                        new_parsed = parsed_url._replace(
                            scheme=parsed_host.scheme,
                            netloc=parsed_host.netloc
                        )
                        new_url = urlunparse(new_parsed)

                        existing_case_copy.url = new_url
                    # если урлы нет, ставим чистый хост
                    else:
                        existing_case_copy.url = group_run_case_data.host

                # Обновление справочника переменных в рамках группового рана, если variableshost указан
                if group_run_case_data.variables is not None:
                    existing_case_copy.variables = group_run_case_data.variables

                # existing_case_copy = await substitute_variables_in_case(existing_case_copy, user, session)

                # Получение иерархии сьютов
                suite_hierarchy = []
                current_suite = suite
                while current_suite:
                    # Добавляем текущий сьют в начало, чтобы построить путь "сверху вниз"
                    suite_hierarchy.insert(0, SuiteRead.model_validate(current_suite).model_dump(mode='json'))
                    suite_result = await session.execute(
                        select(Suite)
                        .where(Suite.suite_id == current_suite.parent_id)
                    )
                    current_suite = suite_result.scalar_one_or_none()

                group_run_case_case = GroupRunCaseCase(
                    group_run_id=new_group_run_case.group_run_id,
                    case_id=existing_case.case_id,
                    case_type_in_run=existing_case.type,
                    current_case_version=existing_case_copy.model_dump(mode='json'),
                    suite_hierarchy=suite_hierarchy,
                    execution_mode=req.execution_mode.value,
                    execution_order=req.execution_order
                )
                session.add(group_run_case_case)

            await session.flush()
            await session.refresh(new_group_run_case)
            return GroupRunCaseRead.model_validate(new_group_run_case)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(e, exc_info=True)
        mess = {"status": "error", "message": f"Error: {e}"}
        raise HTTPException(400, mess)


async def copy_group_runs(group_run_ids: List[UUID4],
                          current_user: User,
                          session: AsyncSession) -> List[UUID4]:
    try:
        async with transaction_scope(session):
            result = await session.execute(select(GroupRunCase)
                                           .options(selectinload(GroupRunCase.cases))
                                           .join(ProjectUser, and_(ProjectUser.project_id == GroupRunCase.project_id,
                                                                   ProjectUser.workspace_id == current_user.active_workspace_id,
                                                                   ProjectUser.user_id == current_user.user_id))
                                           .where(GroupRunCase.group_run_id.in_(group_run_ids)))

            group_run_cases = result.scalars().all()

            if not group_run_cases:
                return []

            new_group_run_cases_ids = []
            for group_run_case in group_run_cases:
                new_group_run_case = GroupRunCaseCreate(project_id=group_run_case.project_id,
                                                        name=f"Copy of {group_run_case.name}",
                                                        description=group_run_case.description,
                                                        environment_id=group_run_case.environment,
                                                        deadline=group_run_case.deadline,
                                                        parallel_exec=group_run_case.parallel_exec,
                                                        host=group_run_case.host,
                                                        variables=group_run_case.variables,
                                                        cases=[case.case_id for case in group_run_case.cases],
                                                        extra=group_run_case.extra,
                                                        background_video_generate=group_run_case.background_video_generate)

                new_group_run_case = await create_group_run_case(new_group_run_case, session, current_user)
                new_group_run_cases_ids.append(new_group_run_case.group_run_id)

            return new_group_run_cases_ids

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(e, exc_info=True)
        mess = {"status": "error", "message": f"Error: {e}"}
        raise HTTPException(400, mess)


async def update_group_run_case(group_run_id: UUID4,
                                update_data: GroupRunCaseUpdate,
                                session: AsyncSession,
                                current_user: User) -> GroupRunCaseRead:
    try:
        async with session.begin():
            cases_to_remove_response = {}
            result = await session.execute(
                select(GroupRunCase)
                .join(ProjectUser, and_(ProjectUser.project_id == GroupRunCase.project_id,
                                        ProjectUser.workspace_id == current_user.active_workspace_id,
                                        ProjectUser.user_id == current_user.user_id))
                .options(selectinload(GroupRunCase.cases))
                .where(GroupRunCase.group_run_id == group_run_id)
            )
            group_run_case = result.scalars().one_or_none()

            if not group_run_case:
                raise HTTPException(status_code=404, detail="GroupRunCase not found or not authorized to update this GroupRunCase")

            if group_run_case.status == CaseStatusEnum.IN_PROGRESS.value:
                raise HTTPException(status_code=400, detail="Cannot update Test Run while in_progress")

            update_data_group_run_case = update_data.model_dump(exclude_unset=True)

            if update_data.parallel_exec is not None:
                project_limit = await free_streams_for_grouprun_by_project_id(group_run_case.project_id,
                                                                              current_user,
                                                                              session)
                if update_data.parallel_exec > project_limit:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Requested parallel_exec ({update_data.parallel_exec}) exceeds project limit ({project_limit})")
                group_run_case.parallel_exec = update_data.parallel_exec

            if update_data.background_video_generate is not None:
                group_run_case.background_video_generate = update_data.background_video_generate
            if update_data.name:
                group_run_case.name = update_data.name
            if "description" in update_data_group_run_case:
                group_run_case.description = update_data.description
            if "extra" in update_data_group_run_case:
                group_run_case.extra = update_data.extra

            # env
            if update_data.environment_id:

                query = (
                    select(Environment)
                    .join(ProjectUser, and_(Environment.project_id == ProjectUser.project_id,
                                            ProjectUser.project_id == group_run_case.project_id,
                                            ProjectUser.workspace_id == current_user.active_workspace_id,
                                            ProjectUser.user_id == current_user.user_id))
                    .where(Environment.environment_id == update_data.environment_id)
                )

                result = await session.execute(query)
                environment = result.scalars().one_or_none()

                if not environment:
                    raise HTTPException(status_code=404, detail="Environment not found or not authorized to use this environment")

                group_run_case.environment = update_data.environment_id

            if "deadline" in update_data_group_run_case:
                group_run_case.deadline = update_data.deadline

            if update_data.cases is not None:
                validate_group_run_cases_payload(update_data.cases)

                case_id_to_db_case = {str(case.case_id): case for case in group_run_case.cases}
                current_case_ids = set(case_id_to_db_case.keys())

                new_cases = {str(case.case_id): case for case in update_data.cases}
                new_cases_ids = set(new_cases.keys())

                # кейсы для добавления, но пропускаем те, которые уже есть
                cases_to_add = new_cases_ids - current_case_ids
                # кейсы для удаления, которые остались в БД, но не переданы в списке
                cases_to_remove = current_case_ids - new_cases_ids

                if cases_to_remove:
                    cases_to_remove_response = await delete_cases_in_group_run_case(
                        group_run_id=group_run_id,
                        cases_ids=[UUID4(str(case_id_to_db_case[case_id].id)) for case_id in cases_to_remove],
                        session=session,
                        user=current_user
                    )
                    logger.info(cases_to_remove_response)

                # обновляем execution_mode/order в grcc
                for case_id in new_cases_ids & current_case_ids:
                    req = new_cases[case_id]
                    grcc = case_id_to_db_case[case_id]

                    new_mode_enum = req.execution_mode
                    new_mode = new_mode_enum.value
                    new_order = req.execution_order

                    # если перевели в параллельный, то execution_order должен стать None
                    if new_mode_enum == ExecutionModeEnum.parallel:
                        new_order = None

                    changed = (grcc.execution_mode != new_mode) or (grcc.execution_order != new_order)
                    if changed:
                        grcc.execution_mode = new_mode
                        grcc.execution_order = new_order

                await session.flush()

                # Добавляем новые
                if cases_to_add:
                    add_case_ids = [UUID4(case_id) for case_id in cases_to_add]
                    case_query = (
                        select(Case, Suite)
                        .join(Suite, Case.suite_id == Suite.suite_id)
                        .join(ProjectUser, and_(ProjectUser.project_id == Suite.project_id,
                                                ProjectUser.workspace_id == current_user.active_workspace_id,
                                                ProjectUser.user_id == current_user.user_id))
                        .where(Case.case_id.in_(add_case_ids),
                               Suite.project_id == group_run_case.project_id)
                    )
                    case_result = await session.execute(case_query)
                    rows = case_result.all()
                    db_cases_data = {str(c.case_id): (c, s) for c, s in rows}

                    missing = [case_id for case_id in cases_to_add if case_id not in db_cases_data]
                    if missing:
                        raise HTTPException(status_code=404, detail=f"Case or Suite not found: {missing}")

                    for case_id in cases_to_add:

                        existing_case, suite = db_cases_data[case_id]
                        req = new_cases[case_id]

                        new_mode_enum = req.execution_mode
                        new_mode = new_mode_enum.value
                        new_order = req.execution_order
                        if new_mode_enum == ExecutionModeEnum.parallel:
                            new_order = None

                        if existing_case.type == "manual" and new_mode_enum == ExecutionModeEnum.sequential:
                            raise HTTPException(status_code=400, detail=f"Manual case {existing_case.case_id} cannot be in sequential")

                        # Получение иерархии сьютов
                        suite_hierarchy = []
                        current_suite = suite
                        while current_suite:
                            # Добавляем текущий сьют в начало, чтобы построить путь "сверху вниз"
                            suite_hierarchy.insert(0, SuiteRead.model_validate(current_suite).model_dump(mode='json'))
                            suite_result = await session.execute(
                                select(Suite)
                                .where(Suite.suite_id == current_suite.parent_id)
                            )
                            current_suite = suite_result.scalar_one_or_none()

                        group_run_case_case = GroupRunCaseCase(
                            group_run_id=group_run_case.group_run_id,
                            case_id=existing_case.case_id,
                            case_type_in_run=existing_case.type,
                            current_case_version=CaseRead.model_validate(existing_case).model_dump(mode='json'),
                            suite_hierarchy=suite_hierarchy,
                            execution_mode=new_mode,
                            execution_order=new_order,
                        )
                        session.add(group_run_case_case)
                        await session.flush()
                        group_run_case.cases.append(group_run_case_case)

                        # добавим пустую untested запись, для возможности застопить TASK-2146
                        # current_case_version будет актуальная при запуске
                        record = {"run_id": str(uuid.uuid4()),
                                  "case_id": case_id,
                                  "group_run_case_id": group_run_case_case.id,
                                  "user_id": current_user.user_id,
                                  "status": CaseStatusEnum.UNTESTED.value,
                                  "steps": [],
                                  "current_case_version": CaseRead.model_validate(existing_case).model_dump(mode='json'),
                                  "group_run_id": group_run_id,
                                  "workspace_id": current_user.active_workspace_id,
                                  "extra": group_run_case.extra,
                                  "project_id": group_run_case.project_id,
                                  "start_dt": None,
                                  "background_video_generate": group_run_case.background_video_generate,
                                  "execution_mode": new_mode,
                                  "execution_order": new_order,
                                  "case_type_in_run": existing_case.type,
                                  }
                        await session.execute(insert(RunCase).values(record))
                        await session.flush()

            if update_data.host:
                parsed_host = urlparse(update_data.host)
                if not parsed_host.scheme or not parsed_host.netloc:
                    raise HTTPException(status_code=400, detail="Host must contain only scheme and domain")
                update_data.host = f"{parsed_host.scheme}://{parsed_host.netloc}"
                group_run_case.host = update_data.host
                await session.flush()

                for case in group_run_case.cases:
                    if case.current_case_version.get("url"):
                        parsed_url = urlparse(case.current_case_version["url"])

                        parsed_host = urlparse(group_run_case.host)
                        new_parsed = parsed_url._replace(
                            scheme=parsed_host.scheme,
                            netloc=parsed_host.netloc
                        )
                        new_url = urlunparse(new_parsed)

                        case.current_case_version["url"] = new_url
                    # если урлы нет, ставим чистый хост
                    else:
                        case.current_case_version["url"] = update_data.host

                    flag_modified(case, "current_case_version")
                    await session.flush()

            # перезаписать переменные в кейсах
            if update_data.variables:
                group_run_case.variables = update_data.variables
                await session.flush()

                for case in group_run_case.cases:
                    case.current_case_version["variables"] = update_data.variables
                    flag_modified(case, "current_case_version")
                    await session.flush()

            await session.flush()
            await session.refresh(group_run_case)

            return {"message": cases_to_remove_response,
                    "group_run_case": GroupRunCaseRead.model_validate(group_run_case).model_dump()}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(e, exc_info=True)
        mess = {"status": "error", "message": str(e)}
        raise HTTPException(400, mess)


def insert_case_into_hierarchy(hierarchy, suite_hierarchy, current_case_version):
    """ Рекурсивная функция для вставки кейса в иерархию. """
    suite_info = suite_hierarchy[0]
    suite_id = suite_info["suite_id"]

    # Проверить, существует ли узел для текущего уровня
    if suite_id not in hierarchy:
        hierarchy[suite_id] = {
            "suite_id": suite_id,
            "suite_name": suite_info["name"],
            "suite_description": suite_info["description"],
            "cases": [],
            "children": {},
            "position": suite_info["position"]
        }

    # Если случайно получилась пустая иерархия сьютов, тогда добавляем кейс на этом уровне
    if len(suite_hierarchy) == 1:
        hierarchy[suite_id]["cases"].append(current_case_version)
    else:
        # Иначе спускаемся глубже в "children"
        insert_case_into_hierarchy(hierarchy[suite_id]["children"], suite_hierarchy[1:], current_case_version)


def suite_path_str(suite_hierarchy: list[dict]) -> str:
    return " / ".join([s.get("name") for s in suite_hierarchy if s.get("name")])


def sort_and_flatten(node):
    """Сортирует иерархическую структуру по позиции."""
    node["cases"].sort(key=lambda c: c["position"])
    node["children"] = sorted(node["children"].values(), key=lambda x: x["position"])
    for child in node["children"]:
        sort_and_flatten(child)


def calculate_suite_stats_and_time(suite):
    suite_status_count = {status.value: 0 for status in CaseStatusEnum}
    min_start_dt, max_end_dt = None, None
    all_final_status = True

    for case in suite["cases"]:
        case_status = case["actual_status"]
        suite_status_count[case_status] += 1

        case_start_dt = case.get("actual_start_dt")
        case_end_dt = case.get("actual_end_dt")

        if case_start_dt and case_end_dt:
            min_start_dt = min(min_start_dt or case_start_dt, case_start_dt)
            max_end_dt = max(max_end_dt or case_end_dt, case_end_dt)
        else:
            all_final_status = all_final_status and False

        if case_status in [CaseStatusEnum.IN_PROGRESS, CaseStatusEnum.PREPARATION, CaseStatusEnum.RETEST]:
            all_final_status = False

    for child in suite["children"]:
        child_stats, child_min_start, child_max_end, child_complete = calculate_suite_stats_and_time(child)
        for key in suite_status_count:
            suite_status_count[key] += child_stats[key]
        if child_min_start:
            min_start_dt = min(min_start_dt or child_min_start, child_min_start)
        if child_max_end:
            max_end_dt = max(max_end_dt or child_max_end, child_max_end)
        all_final_status = all_final_status and child_complete

    suite_time = max_end_dt - min_start_dt if all_final_status and min_start_dt and max_end_dt else None
    suite["stats"] = suite_status_count
    suite["complete_time"] = suite_time.total_seconds() if suite_time else None

    return suite_status_count, min_start_dt, max_end_dt, all_final_status


async def get_group_run_case_tree(
    project_id: UUID4,
    current_user: User,
    session: AsyncSession,
    group_run_id=None,
    status: list = None,
    search: str = None,
    filter_cases: str = None,
    order_by: GroupRunCaseOrderBy = GroupRunCaseOrderBy.created_at,
    order_direction: str = "desc",
    limit: int = 10,
    offset: int = 0
):
    try:
        async with session.begin():
            user_id = current_user.user_id

            query = (select(ProjectUser.project_id)
                     .where(ProjectUser.project_id == project_id,
                            ProjectUser.workspace_id == current_user.active_workspace_id,
                            ProjectUser.user_id == current_user.user_id))

            result = await session.execute(query)
            result = result.scalars().one_or_none()

            if not result:
                return JSONResponse(content={"status": "not authorized to use this project"})

            base_count_query = select(func.count(GroupRunCase.group_run_id)).where(GroupRunCase.project_id == project_id)
            if group_run_id:
                base_count_query = base_count_query.where(GroupRunCase.group_run_id == group_run_id)

            if search:
                search_pattern = f"%{search}%"
                base_count_query = base_count_query.where(
                    or_(
                        GroupRunCase.name.ilike(search_pattern),
                        GroupRunCase.description.ilike(search_pattern)
                    )
                )

            total_result = await session.execute(base_count_query)
            total = total_result.scalar_one()

            order_column = getattr(GroupRunCase, order_by.value)
            order_func = desc if order_direction.lower() == "desc" else asc

            subquery = (
                select(GroupRunCase.group_run_id)
                .where(GroupRunCase.project_id == project_id)
                .order_by(order_func(order_column))  # .order_by(desc(GroupRunCase.created_at))
                .offset(offset)
                .limit(limit)
            )
            if group_run_id:
                subquery = subquery.where(GroupRunCase.group_run_id == group_run_id)

            if search:
                search_pattern = f"%{search}%"
                subquery = subquery.where(
                    or_(
                        GroupRunCase.name.ilike(search_pattern),
                        GroupRunCase.description.ilike(search_pattern)
                    )
                )

            aliased_subquery = subquery.alias("fast_filter")

            main_query = (
                select(GroupRunCase)
                .join(aliased_subquery, GroupRunCase.group_run_id == aliased_subquery.c.group_run_id)
                .options(selectinload(GroupRunCase.cases))
                .order_by(order_func(order_column))  # .order_by(desc(GroupRunCase.created_at))
            )

            group_runs_result = await session.execute(main_query)
            group_run_cases = group_runs_result.scalars().all()

            final_entries = []

            for group_run_case in group_run_cases:
                if not group_run_case.cases:
                    final_entries.append({
                        "project_id": group_run_case.project_id,
                        "group_run_id": group_run_case.group_run_id,
                        "user_id": group_run_case.user_id,
                        "author": group_run_case.author,
                        "created_at": group_run_case.created_at,
                        "complete_time": 0,
                        "name": group_run_case.name,
                        "description": group_run_case.description,
                        "status": CaseStatusEnum.UNTESTED.value,
                        "environment": group_run_case.environment,
                        "deadline": group_run_case.deadline,
                        "parallel_exec": group_run_case.parallel_exec,
                        "host": group_run_case.host,
                        "variables": group_run_case.variables,
                        "extra": group_run_case.extra,
                        "background_video_generate": group_run_case.background_video_generate,
                        "tree": [],
                        "parallel": [],
                        "sequential": [],
                        "stats": {status.value: 0 for status in CaseStatusEnum},
                        "complete_count_parallel": 0,
                        "complete_count_sequential": 0
                    })
                    continue

                status_count = {status.value: 0 for status in CaseStatusEnum}
                complete_count_parallel = 0
                complete_count_sequential = 0

                case_ids = [case.id for case in group_run_case.cases]

                # Берём все соответствующие последние раны
                run_cases_subquery = (
                    select(
                        RunCase.group_run_case_id,
                        RunCase.status,
                        RunCase.run_id,
                        RunCase.start_dt,
                        RunCase.end_dt,
                        RunCase.complete_time,
                        RunCase.execution_mode,
                        func.row_number().over(
                            partition_by=RunCase.group_run_case_id,
                            order_by=desc(RunCase.created_at)
                        ).label('row_number')
                    )
                    .where(RunCase.group_run_id == group_run_case.group_run_id)
                    .where(RunCase.group_run_case_id.in_(case_ids))
                ).alias('latest_run_cases')

                run_cases_query = select(run_cases_subquery).where(run_cases_subquery.c.row_number == 1)
                run_cases_result = await session.execute(run_cases_query)
                run_cases = {run_case.group_run_case_id: run_case for run_case in run_cases_result}

                tree_hierarchy = {}
                parallel_hierarchy = {}
                sequential_list = []

                all_statuses = []
                min_end_dt = None
                max_end_dt = None
                min_start_dt = None
                max_start_dt = None

                for case in group_run_case.cases:
                    suite_hierarchy = case.suite_hierarchy or []
                    run_case = run_cases.get(case.id)

                    actual_status = run_case.status if run_case else CaseStatusEnum.UNTESTED.value  # !
                    all_statuses.append(actual_status)  # соберем для вычисления группового
                    if actual_status in [fnl_sts.value for fnl_sts in CaseFinalStatusEnum]:
                        if run_case.execution_mode == ExecutionModeEnum.parallel.value:
                            complete_count_parallel += 1

                        elif run_case.execution_mode == ExecutionModeEnum.sequential.value:
                            complete_count_sequential += 1

                    actual_run_id = str(run_case.run_id) if run_case else None
                    actual_start_dt = run_case.start_dt if run_case else None
                    actual_end_dt = run_case.end_dt if run_case else None

                    if actual_end_dt:
                        min_end_dt = min(min_end_dt or actual_end_dt, actual_end_dt)
                        max_end_dt = max(max_end_dt or actual_end_dt, actual_end_dt)
                    if actual_start_dt:
                        min_start_dt = min(min_start_dt or actual_start_dt, actual_start_dt)
                        max_start_dt = max(max_start_dt or actual_start_dt, actual_start_dt)

                    actual_complete_time = run_case.complete_time if run_case else None

                    if actual_status in status_count:
                        status_count[actual_status] += 1

                    # Фильтр по actual_status, если указан
                    if status and actual_status not in status:
                        continue

                    current_case_version = case.current_case_version or {}

                    # фильтруем
                    if filter_cases:
                        found = search_for_filter_cases(filter_cases, current_case_version)
                        if not found:
                            continue

                    current_case_version.update({
                        "actual_status": actual_status,
                        "actual_run_id": actual_run_id,
                        "actual_start_dt": actual_start_dt,
                        "actual_end_dt": actual_end_dt,
                        "actual_complete_time": actual_complete_time,
                        "case_type_in_run": case.case_type_in_run,
                        "group_run_case_id": case.id,
                        "execution_mode": case.execution_mode,
                        "execution_order": case.execution_order,
                    })

                    # --- сборка tree / parallel / sequential
                    if suite_hierarchy:
                        # tree: как раньше
                        insert_case_into_hierarchy(tree_hierarchy, suite_hierarchy, current_case_version)

                    # parallel
                    if case.execution_mode == ExecutionModeEnum.parallel.value:
                        insert_case_into_hierarchy(parallel_hierarchy, suite_hierarchy, current_case_version)

                    # sequential: плоский список
                    if case.execution_mode == ExecutionModeEnum.sequential.value:
                        sequential_list.append({
                            "group_run_case_id": case.id,
                            "case_id": case.case_id,
                            "execution_mode": case.execution_mode,
                            "execution_order": case.execution_order,
                            "suite_path": suite_path_str(suite_hierarchy),
                            "case": current_case_version,
                        })

                # --- финализация
                sorted_tree = sorted(tree_hierarchy.values(), key=lambda x: x["position"])
                for suite in sorted_tree:
                    sort_and_flatten(suite)
                    calculate_suite_stats_and_time(suite)

                sorted_parallel = sorted(parallel_hierarchy.values(), key=lambda x: x["position"])
                for suite in sorted_parallel:
                    sort_and_flatten(suite)
                    calculate_suite_stats_and_time(suite)

                sequential_list.sort(key=lambda x: x["execution_order"])

                # Вычисляем статус group_run_case
                # если все только созданы в runs, то untested
                # TODO сделать отдельные схемы для категорий статусов и упростить проверки
                if all((status == CaseStatusEnum.UNTESTED.value) for status in all_statuses):
                    calculated_status = CaseStatusEnum.UNTESTED.value
                # если хоть один в работе, то progress
                elif any(status in (CaseStatusEnum.IN_QUEUE.value,
                                    CaseStatusEnum.PREPARATION.value,
                                    CaseStatusEnum.STOP_IN_PROGRESS.value,
                                    CaseStatusEnum.IN_PROGRESS.value,
                                    CaseStatusEnum.RETEST.value) for status in all_statuses):
                    calculated_status = CaseStatusEnum.IN_PROGRESS.value
                # если хоть один в untested, но при этом есть еще хотя бы один в работе или в финальном статусе то Progress
                elif any(status in (CaseStatusEnum.UNTESTED.value) for status in all_statuses) and \
                        any(status in (CaseStatusEnum.PREPARATION.value,
                                       CaseStatusEnum.IN_QUEUE.value,
                                       CaseStatusEnum.STOP_IN_PROGRESS.value,
                                       CaseStatusEnum.IN_PROGRESS.value,
                                       CaseStatusEnum.RETEST.value,
                                       CaseStatusEnum.PASSED.value,
                                       CaseStatusEnum.FAILED.value,
                                       CaseStatusEnum.BLOCKED.value,
                                       CaseStatusEnum.INVALID.value,
                                       CaseStatusEnum.STOPPED.value,
                                       CaseStatusEnum.AFTER_STEP_FAILURE.value) for status in all_statuses):
                    calculated_status = CaseStatusEnum.IN_PROGRESS.value
                # если все в конечном статусе и хотя бы один fail, то fail, иначе все pass
                elif all(status != CaseStatusEnum.IN_QUEUE.value and status != CaseStatusEnum.PREPARATION.value and status != CaseStatusEnum.IN_PROGRESS.value and status != CaseStatusEnum.STOP_IN_PROGRESS.value and status != CaseStatusEnum.RETEST.value for status in all_statuses):
                    if any(status == CaseStatusEnum.FAILED.value for status in all_statuses):
                        calculated_status = CaseStatusEnum.FAILED.value
                    else:
                        calculated_status = CaseStatusEnum.PASSED.value
                else:
                    calculated_status = CaseStatusEnum.UNTESTED.value

                if calculated_status == CaseStatusEnum.IN_PROGRESS.value:
                    complete_time = datetime.now(timezone.utc) - min_start_dt if min_start_dt else None
                else:
                    complete_time = max_end_dt - min_start_dt if min_start_dt and max_end_dt else None

                # current_phase null/sequential/parallel

                if calculated_status in (CaseStatusEnum.UNTESTED.value, CaseStatusEnum.FAILED.value, CaseStatusEnum.PASSED.value):
                    group_run_case.current_phase = None
                    group_run_case.parallel_started_at = None
                    await session.flush()

                if group_run_case.status != calculated_status:
                    group_run_case.status = calculated_status
                    await session.flush()

                final_entries.append({
                    "project_id": group_run_case.project_id,
                    "group_run_id": group_run_case.group_run_id,
                    "user_id": group_run_case.user_id,
                    "author": group_run_case.author,
                    "created_at": group_run_case.created_at,
                    "complete_time": complete_time.total_seconds() if complete_time else None,
                    "name": group_run_case.name,
                    "description": group_run_case.description,
                    "status": calculated_status,  # group_run_case.status,
                    "environment": group_run_case.environment,
                    "deadline": group_run_case.deadline,
                    "parallel_exec": group_run_case.parallel_exec,
                    "host": group_run_case.host,
                    "variables": group_run_case.variables,
                    "extra": group_run_case.extra,
                    "background_video_generate": group_run_case.background_video_generate,
                    "tree": sorted_tree,
                    "parallel": sorted_parallel,
                    "sequential": sequential_list,
                    "stats": status_count,
                    "complete_count_parallel": complete_count_parallel,
                    "complete_count_sequential": complete_count_sequential
                })

            total_pages = (total - 1) // limit + 1
            current_page = (offset // limit) + 1

            pagination_info = {
                "total": total,
                "total_current_page": len(group_run_cases),
                "page": current_page,
                "size": limit,
                "pages": total_pages,
                "limit": limit,
                "offset": offset,
                "items": final_entries
            }

            return pagination_info

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(e, exc_info=True)
        mess = {"status": "error", "message": f"Error: {e}"}
        raise HTTPException(400, mess)


async def delete_group_run_case(group_run_id: UUID4,
                                session: AsyncSession,
                                user: User) -> JSONResponse:
    try:
        async with session.begin():
            query = (
                select(GroupRunCase)
                .options(selectinload(GroupRunCase.cases))
                .join(ProjectUser, and_(ProjectUser.project_id == GroupRunCase.project_id,
                                        ProjectUser.workspace_id == user.active_workspace_id,
                                        ProjectUser.user_id == user.user_id))
                .where(GroupRunCase.group_run_id == group_run_id)
            )
            result = await session.execute(query)
            group_run_case = result.scalars().one_or_none()

            if not group_run_case:
                return JSONResponse(content={"status": "not found or not authorized to delete this GroupRunCase"})

            # последние версии RunCase для каждого case_id
            run_cases_subquery = (
                select(
                    RunCase.group_run_case_id,
                    RunCase.status,
                    RunCase.run_id,
                    func.row_number().over(
                        partition_by=RunCase.group_run_case_id,
                        order_by=desc(RunCase.created_at)
                    ).label('row_number')
                )
                .where(RunCase.group_run_id == group_run_id)
            ).alias('latest_run_cases')

            # run_cases_query = select(run_cases_subquery).where(run_cases_subquery.c.row_number == 1)
            run_cases_query = select(RunCase).join(
                run_cases_subquery, RunCase.run_id == run_cases_subquery.c.run_id
            ).where(run_cases_subquery.c.row_number == 1)

            run_cases_result = await session.execute(run_cases_query)
            latest_run_cases = {run_case.group_run_case_id: run_case for run_case in run_cases_result.scalars()}

            auto_case_not_in_final_statuses = []

            # нужно перевести текущие незапущенные автораны в стоп, или не удалять ран.
            for case in group_run_case.cases:
                run_case = latest_run_cases.get(case.id)
                status = run_case.status if run_case else None
                current_case_type = case.case_type_in_run

                if run_case:
                    # мануал в любом статусе, авто только если еще не взяты
                    if current_case_type == CaseTypeEnum.MANUAL.value or \
                        (current_case_type == CaseTypeEnum.AUTOMATED.value and status in (CaseStatusEnum.IN_QUEUE,
                                                                                          CaseStatusEnum.UNTESTED)):
                        run_case.status = CaseStatusEnum.STOPPED.value
                        run_case.end_dt = datetime.now(timezone.utc)
                        run_case.complete_time = (run_case.end_dt - run_case.start_dt).total_seconds() if run_case.start_dt else 0
                        if not run_case.start_dt:
                            run_case.start_dt = datetime.now(timezone.utc)
                        await session.flush()
                    # авто не в конечном статусе пока что удалить нельзя
                    elif current_case_type == CaseTypeEnum.AUTOMATED.value and status in (CaseStatusEnum.IN_PROGRESS,
                                                                                          CaseStatusEnum.PREPARATION,
                                                                                          CaseStatusEnum.STOP_IN_PROGRESS):
                        auto_case_not_in_final_statuses.append(run_case.group_run_case_id)

            if len(auto_case_not_in_final_statuses) > 0:
                return JSONResponse(status_code=400,
                                    content={"status": "Fail",
                                             "auto_case_not_in_final_statuses": [str(group_run_case_id) for group_run_case_id in auto_case_not_in_final_statuses]})

            await session.delete(group_run_case)
            await session.flush()
            return JSONResponse(content={"status": "OK"})

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(e, exc_info=True)
        mess = {"status": "error", "message": f"Error: {e}"}
        raise HTTPException(400, mess)


async def delete_cases_in_group_run_case(group_run_id: UUID4,
                                         cases_ids: List[UUID4],
                                         session: AsyncSession,
                                         user: User) -> JSONResponse:
    try:
        async with transaction_scope(session):

            query = (
                select(GroupRunCase)
                .options(selectinload(GroupRunCase.cases))
                .join(ProjectUser, and_(
                    ProjectUser.project_id == GroupRunCase.project_id,
                    ProjectUser.workspace_id == user.active_workspace_id,
                    ProjectUser.user_id == user.user_id
                ))
                .where(GroupRunCase.group_run_id == group_run_id)
            )
            result = await session.execute(query)
            group_run_case = result.scalars().one_or_none()

            if not group_run_case:
                return {"status": "not found or not authorized to delete this GroupRunCase"}

            # последние версии RunCase для каждого case_id
            run_cases_subquery = (
                select(
                    RunCase.group_run_case_id,
                    RunCase.status,
                    RunCase.run_id,
                    func.row_number().over(
                        partition_by=RunCase.group_run_case_id,
                        order_by=desc(RunCase.created_at)
                    ).label('row_number')
                )
                .where(RunCase.group_run_id == group_run_id)
            ).alias('latest_run_cases')

            # run_cases_query = select(run_cases_subquery).where(run_cases_subquery.c.row_number == 1)
            run_cases_query = select(RunCase).join(
                run_cases_subquery, RunCase.run_id == run_cases_subquery.c.run_id
            ).where(run_cases_subquery.c.row_number == 1)

            run_cases_result = await session.execute(run_cases_query)
            latest_run_cases = {run_case.group_run_case_id: run_case for run_case in run_cases_result.scalars()}
            # run_cases = run_cases_result.scalars().all()
            # latest_run_cases = {rc.case_id: rc for rc in run_cases}

            cases_to_delete = [case for case in group_run_case.cases if case.id in cases_ids]

            cases_ids_to_delete = []
            auto_case_not_in_final_statuses = []

            for case in cases_to_delete:
                run_case = latest_run_cases.get(case.id)
                status = run_case.status if run_case else None
                current_case_type = case.case_type_in_run
                # нужно перевести текущие незапущенные автораны в стоп, или не удалять их.

                if run_case:
                    # мануал в любом статусе, авто только если еще не взяты
                    if current_case_type == CaseTypeEnum.MANUAL.value or \
                        (current_case_type == CaseTypeEnum.AUTOMATED.value and status in (CaseStatusEnum.IN_QUEUE,
                                                                                          CaseStatusEnum.UNTESTED)):
                        run_case.status = CaseStatusEnum.STOPPED.value
                        run_case.end_dt = datetime.now(timezone.utc)
                        run_case.complete_time = (run_case.end_dt - run_case.start_dt).total_seconds() if run_case.start_dt else 0
                        if not run_case.start_dt:
                            run_case.start_dt = datetime.now(timezone.utc)
                        await session.flush()

                        cases_ids_to_delete.append(case.id)
                    # авто не в конечном статусе пока что удалить нельзя
                    elif current_case_type == CaseTypeEnum.AUTOMATED.value and status in (CaseStatusEnum.IN_PROGRESS,
                                                                                          CaseStatusEnum.PREPARATION,
                                                                                          CaseStatusEnum.STOP_IN_PROGRESS):
                        auto_case_not_in_final_statuses.append(case.id)
                    # конечный статус, можно удалять
                    else:
                        cases_ids_to_delete.append(case.id)
                # ранов нет, можно сразу удалять
                else:
                    cases_ids_to_delete.append(case.id)

            if not cases_ids_to_delete:
                return {"status": "not found cases for delete",
                        "auto_case_not_in_final_statuses": [str(id) for id in auto_case_not_in_final_statuses]}

            # Подсчитываем количество кейсов, которые останутся после удаления
            remaining_cases_count = len(group_run_case.cases) - len(cases_ids_to_delete)

            # Удаление кейсов
            delete_query = (
                delete(GroupRunCaseCase)
                .where(
                    GroupRunCaseCase.id.in_(cases_ids_to_delete),
                    GroupRunCaseCase.group_run_id == group_run_id
                )
            )
            await session.execute(delete_query)
            await session.flush()

            # Если кейсов не осталось, обновляем статус в UNTESTED, чтобы разрешить добавление через апдейт
            if remaining_cases_count == 0:
                group_run_case.status = CaseStatusEnum.UNTESTED.value
                group_run_case.current_phase = None
                group_run_case.parallel_started_at = None
                await session.flush()

            return {"status": "OK",
                    "deleted_group_cases_ids": [str(group_run_case_id) for group_run_case_id in cases_ids_to_delete],
                    "auto_case_not_in_final_statuses": [str(group_run_case_id) for group_run_case_id in auto_case_not_in_final_statuses]}
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(e, exc_info=True)
        mess = {"status": "error", "message": f"Error: {e}"}
        raise HTTPException(400, mess)


async def complete_run_cases(run_ids: List[UUID4],
                             status: CaseFinalStatusEnum,
                             session: AsyncSession,
                             user: User,
                             attachments: Optional[List] = None,
                             comment: Optional[str] = None,
                             failed_step_index: Optional[int] = None):
    try:
        async with session.begin():
            # Получаем все ручные (!) RunCase по списку run_ids

            query = (
                select(RunCase)
                .join(GroupRunCaseCase, and_(
                    RunCase.case_id == GroupRunCaseCase.case_id,
                    RunCase.group_run_id == GroupRunCaseCase.group_run_id,
                    GroupRunCaseCase.case_type_in_run == 'manual'
                ))
                .join(GroupRunCase, GroupRunCase.group_run_id == RunCase.group_run_id)
                .join(ProjectUser, and_(ProjectUser.project_id == GroupRunCase.project_id,
                                        ProjectUser.workspace_id == user.active_workspace_id,
                                        ProjectUser.user_id == user.user_id))
                .where(
                    RunCase.run_id.in_(run_ids),
                    RunCase.status.in_([CaseStatusEnum.IN_QUEUE,
                                        CaseStatusEnum.IN_PROGRESS,
                                        CaseStatusEnum.PREPARATION,
                                        CaseStatusEnum.RETEST])
                )
            )
            result = await session.execute(query)
            run_cases = result.scalars().all()

            if not run_cases:
                raise HTTPException(status_code=404, detail="No runs found or not authorized")

            if failed_step_index is not None:
                # если фэйлим из шага то только один run_id
                run_case = run_cases[0]
                steps = run_case.steps
                step_found = False

                # Поиск шага с заданным index_step
                for step in steps:
                    if step["index_step"] == failed_step_index:
                        step["status_step"] = CaseStatusEnum.FAILED.value
                        if comment:
                            step["comment"] = comment

                        step_found = True
                        break

                if not step_found:
                    raise HTTPException(status_code=400, detail=f"Step with index {failed_step_index} not found")

                # Устанавливаем статус RunCase в failed
                run_case.steps = steps
                flag_modified(run_case, "steps")
                run_case.status = CaseStatusEnum.FAILED.value if step["step_group"] != "after" else CaseStatusEnum.AFTER_STEP_FAILURE.value
                run_case.end_dt = datetime.now(timezone.utc)
                run_case.complete_time = (run_case.end_dt - run_case.start_dt).total_seconds() if run_case.start_dt else 0

                if attachments:
                    run_case.attachments = attachments
                if comment:
                    run_case.run_summary = comment

                await session.flush()
                return JSONResponse(content={"status": "OK", "updated_run_id": str(run_case.run_id), "step_index": failed_step_index})

            else:
                for run_case in run_cases:
                    run_case.status = status.value
                    run_case.end_dt = datetime.now(timezone.utc)
                    run_case.complete_time = (run_case.end_dt - run_case.start_dt).total_seconds() if run_case.start_dt else 0

                    if attachments:
                        run_case.attachments = attachments
                    if comment:
                        run_case.run_summary = comment

                await session.flush()
                return JSONResponse(content={"status": "OK", "updated_run_ids": [str(run_case.run_id) for run_case in run_cases]})

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(e, exc_info=True)
        mess = {"status": "error", "message": f"Error: {e}"}
        raise HTTPException(400, mess)


async def step_passed_run_case(run_id: List[UUID4],
                               passed_step_index: int,
                               session: AsyncSession,
                               user: User,
                               comment: Optional[str] = None,
                               attachments: Optional[List] = None):
    try:
        async with session.begin():

            query = (
                select(RunCase)
                .join(GroupRunCaseCase, and_(
                    RunCase.case_id == GroupRunCaseCase.case_id,
                    RunCase.group_run_id == GroupRunCaseCase.group_run_id,
                    GroupRunCaseCase.case_type_in_run == 'manual'
                ))  # TODO теперь у RunCase есть свое поле case_type_in_run
                .join(GroupRunCase, GroupRunCase.group_run_id == RunCase.group_run_id)
                .join(ProjectUser, and_(ProjectUser.project_id == GroupRunCase.project_id,
                                        ProjectUser.workspace_id == user.active_workspace_id,
                                        ProjectUser.user_id == user.user_id))
                .where(
                    RunCase.run_id == run_id,
                    RunCase.status.in_([CaseStatusEnum.IN_QUEUE,
                                        CaseStatusEnum.IN_PROGRESS,
                                        CaseStatusEnum.PREPARATION,
                                        CaseStatusEnum.RETEST])
                )
            )
            result = await session.execute(query)
            run_case = result.scalars().unique().one_or_none()

            if not run_case:
                raise HTTPException(status_code=404, detail="No run found or not authorized")
            all_steps_passed = False
            steps = run_case.steps
            # Поиск шага с заданным index_step
            step_found = False
            for step in steps:
                if step["index_step"] == passed_step_index:

                    step["status_step"] = CaseStatusEnum.PASSED.value
                    if attachments:
                        step["attachments"] = attachments
                    if comment:
                        step["comment"] = comment

                    step_found = True
                    break
            if not step_found:
                raise HTTPException(status_code=400, detail=f"Step with index {passed_step_index} not found")

            run_case.steps = steps
            flag_modified(run_case, "steps")

            # первый может быть триггером начала прохождения
            if passed_step_index == 0:
                run_case.start_dt = datetime.now(timezone.utc)
                # run_case.status = CaseStatusEnum.IN_PROGRESS.value
            # Устанавливаем статус RunCase в passed если все шаги passed
            if all(s["status_step"] == CaseStatusEnum.PASSED.value for s in steps):
                run_case.status = CaseStatusEnum.PASSED.value
                run_case.end_dt = datetime.now(timezone.utc)
                run_case.complete_time = (run_case.end_dt - run_case.start_dt).total_seconds() if run_case.start_dt else 0
                all_steps_passed = True
            else:
                if not run_case.start_dt:
                    run_case.start_dt = datetime.now(timezone.utc)
                run_case.status = CaseStatusEnum.IN_PROGRESS.value

            await session.flush()
            return JSONResponse(content={"status": "OK",
                                         "updated_run_id": str(run_case.run_id),
                                         "step_index": passed_step_index,
                                         "all_steps_passed": all_steps_passed})

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(e, exc_info=True)
        mess = {"status": "error", "message": f"Error: {e}"}
        raise HTTPException(400, mess)
