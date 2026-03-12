
import re
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any
import uuid
from dateutil.relativedelta import relativedelta
from fastapi import HTTPException
from fastapi.responses import JSONResponse
from pydantic import UUID4
from sqlalchemy import and_, select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import TypeAdapter
from config import logger
from db.models import ProjectUser, User, Variables, VariablesDetails
from db.session import transaction_scope
from schemas import (BASE_DEFAULT_FORMAT, SimpleVariableConfig, TimeBaseType,
                     TimeShift, TimeVariableConfig, VariableConfig,
                     VariablesCreate, VariablesDetailsCreate,
                     VariablesDetailsRead, VariablesDetailsUpdate,
                     VariablesRead, VariablesUpdate, parse_format_pattern)


def get_base_local_datetime(base: TimeBaseType,
                            local_now: datetime) -> datetime:
    """
    base считается в ЛОКАЛЬНОМ времени юзера
    local_now — наивный datetime в utc_offset

    "currentDate": "YYYY-MM-DD",
    "today": "YYYY-MM-DD",
    "yesterday": "YYYY-MM-DD",
    "tomorrow": "YYYY-MM-DD",
    "currentTime": "HH:mm:ss",
    "dateTime": "YYYY-MM-DD HH:mm:ss",
    "startOfDay": "YYYY-MM-DD HH:mm:ss",
    "endOfDay": "YYYY-MM-DD HH:mm:ss",
    "timestamp": "X"

    """
    # начало локального дня
    day_start = local_now.replace(hour=0, minute=0, second=0, microsecond=0)

    if base in ("currentTime", "dateTime", "timestamp"):
        dt_local = local_now
    elif base in ("today", "currentDate"):
        dt_local = day_start
    elif base == "yesterday":
        dt_local = day_start - timedelta(days=1)
    elif base == "tomorrow":
        dt_local = day_start + timedelta(days=1)
    elif base == "startOfDay":
        dt_local = day_start
    elif base == "endOfDay":
        dt_local = day_start.replace(hour=23, minute=59, second=59, microsecond=0)
    else:
        dt_local = local_now

    return dt_local


def apply_utc_offset(dt_utc: datetime, utc_offset: Optional[str]) -> datetime:
    """
    Переводим в часовой пояс юзера или utc
    Если utc_offset не задан, считаем, что это +0:00
    """
    if dt_utc.tzinfo is None:
        dt_utc = dt_utc.replace(tzinfo=timezone.utc)

    # если offset не задан — работаем в UTC+0 как локальном времени
    if utc_offset is None:
        return dt_utc.replace(tzinfo=None)

    m = re.fullmatch(r'^([+-])(\d{2}):(\d{2})$', utc_offset)
    if not m:
        return dt_utc.replace(tzinfo=None)

    sign, hh, mm = m.groups()
    hours = int(hh)
    minutes = int(mm)
    delta = timedelta(hours=hours, minutes=minutes)
    if sign == '-':
        delta = -delta

    target_dt = dt_utc + delta
    # локальный datetime юзера без таймзоны, для сдвигов ок
    return target_dt.replace(tzinfo=None)


def apply_shifts(dt: datetime, shifts: Optional[list[TimeShift]]) -> datetime:
    """сдвиги из массива shifts
        применяются от больших к меньшим:
        - y (years) - добавляются/вычитаются годы
        - M (months) - добавляются/вычитаются месяцы
        - d (days) - добавляются/вычитаются дни
        =========
        - h (hours) - добавляются/вычитаются часы
        - m (minutes) - добавляются/вычитаются минуты
        - s (seconds) - добавляются/вычитаются секунды
        Отрицательные значения вычитают соответствующий период."""

    if not shifts:
        return dt

    years = 0
    months = 0
    days = 0
    seconds = 0  # h/m/s в секундах

    for shift in shifts:
        v = shift.value
        u = shift.unit
        if u == "y":
            years += v
        elif u == "M":
            months += v
        elif u == "d":
            days += v
        elif u == "h":
            seconds += v * 3600
        elif u == "m":
            seconds += v * 60
        elif u == "s":
            seconds += v

    if years or months or days:
        dt = dt + relativedelta(years=years, months=months, days=days)

    if seconds:
        dt = dt + timedelta(seconds=seconds)

    return dt


def format_datetime_with_pattern(dt: datetime, pattern: str) -> str:
    """
    dt — ЛОКАЛЬНОЕ время (наивное).
    X / x считаем как Unix-время от этого момента"""

    strftime_pattern, is_unix_seconds, is_unix_millis = parse_format_pattern(pattern)

    if is_unix_seconds:
        # трактуем dt как UTC-момент для timestamp()
        return str(int(dt.replace(tzinfo=timezone.utc).timestamp()))
    if is_unix_millis:
        return str(int(dt.replace(tzinfo=timezone.utc).timestamp() * 1000))

    return dt.strftime(strftime_pattern)


def compute_time_value(config: TimeVariableConfig,
                       now_utc: Optional[datetime] = None) -> str:
    # текущее время в UTC
    if now_utc is None:
        now_utc = datetime.now(timezone.utc)
    elif now_utc.tzinfo is None:
        now_utc = now_utc.replace(tzinfo=timezone.utc)

    # Переводим UTC в часовой пояс юзера, если есть
    local_now = apply_utc_offset(now_utc, config.utc_offset)

    # расчет базового значения, например  yesterday
    base_local = get_base_local_datetime(config.base, local_now)

    # Сдвиги
    dt_shifted = apply_shifts(base_local, config.shifts)

    # Формат (кастомный или дефолтный для base)
    pattern = config.format or BASE_DEFAULT_FORMAT[config.base]
    return format_datetime_with_pattern(dt_shifted, pattern)


def compute_variable_value(variable_config: VariableConfig,
                           now_utc: Optional[datetime] = None) -> Optional[str]:
    if isinstance(variable_config, SimpleVariableConfig):
        return variable_config.value
    if isinstance(variable_config, TimeVariableConfig):
        return compute_time_value(variable_config, now_utc=now_utc)
    return None


variable_config_adapter = TypeAdapter(VariableConfig)


def compute_variable_value_from_raw_config(raw_config: Any,
                                           now_utc: Optional[datetime] = None) -> Optional[str]:
    """
    variable_config  JSON из БД:
      {"type": "time", "base": "...", ...} или {"type": "simple", "value": "..."}.

    Преобразовываем в VariableConfig
    """
    # валидация по нужному подтипу (simple / time)
    variable_config = variable_config_adapter.validate_python(raw_config)

    return compute_variable_value(variable_config, now_utc=now_utc)


async def create_variables_kit(variables_kit: VariablesCreate,
                               user: User,
                               session: AsyncSession) -> VariablesRead:
    try:
        async with transaction_scope(session):

            query = (
                select(ProjectUser.user_id, ProjectUser.project_id)
                .where(ProjectUser.project_id == variables_kit.project_id,
                       ProjectUser.workspace_id == user.active_workspace_id,
                       ProjectUser.user_id == user.user_id)
            )

            result = await session.execute(query)
            result = result.unique().one_or_none()

            if not result:
                raise HTTPException(status_code=404, detail="Project not found or not authorized to create variables kit in this project")

            query = (
                select(Variables)
                .join(ProjectUser, and_(ProjectUser.project_id == Variables.project_id,
                                        ProjectUser.workspace_id == user.active_workspace_id,
                                        ProjectUser.user_id == user.user_id))
                .where(Variables.variables_kit_name == variables_kit.variables_kit_name,
                       Variables.project_id == variables_kit.project_id)
            )
            result = await session.execute(query)
            result = result.scalars().one_or_none()

            if result:
                raise HTTPException(status_code=400, detail="Variables kit with this name already exists for the project")

            new_variables_kit = Variables(variables_kit_name=variables_kit.variables_kit_name,
                                          variables_kit_description=variables_kit.variables_kit_description,
                                          project_id=variables_kit.project_id
                                          )

            session.add(new_variables_kit)
            await session.flush()
            await session.refresh(new_variables_kit)

            return VariablesRead.model_validate(new_variables_kit)

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(e, exc_info=True)
        mess = {"status": "error", "message": f"Error: {e}"}
        raise HTTPException(400, mess)


async def variables_kit_by_id(variables_kit_id: UUID4,
                              user: User,
                              session: AsyncSession) -> VariablesRead:
    try:
        async with transaction_scope(session):
            variables_kit_query = (
                select(Variables)
                .join(ProjectUser, and_(Variables.project_id == ProjectUser.project_id,
                                        ProjectUser.user_id == user.user_id,
                                        ProjectUser.workspace_id == user.active_workspace_id))
                .where(Variables.variables_kit_id == variables_kit_id)
            )

            variables_kit_results = await session.execute(variables_kit_query)
            variables_kit = variables_kit_results.scalars().one_or_none()

            if not variables_kit:
                return []
            return VariablesRead.model_validate(variables_kit)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(e, exc_info=True)
        mess = {"status": "error", "message": f"Error: {e}"}
        raise HTTPException(400, mess)


async def list_variables_kit(project_id: UUID4,
                             user: User,
                             session: AsyncSession,
                             search: Optional[str] = None) -> List:
    try:
        async with transaction_scope(session):
            variables_kit_query = (
                select(Variables)
                .join(ProjectUser, and_(Variables.project_id == ProjectUser.project_id,
                                        ProjectUser.project_id == project_id,
                                        ProjectUser.user_id == user.user_id,
                                        ProjectUser.workspace_id == user.active_workspace_id))
                .where(Variables.project_id == project_id)
            )
            if search:
                s = search.strip()
                if s:
                    search_pattern = f"%{s}%"
                    variables_kit_query = variables_kit_query.where(
                        or_(
                            Variables.variables_kit_name.ilike(search_pattern),
                            Variables.variables_kit_description.ilike(search_pattern),
                        )
                    )
            variables_kit_results = await session.execute(variables_kit_query)
            list_variables_kit = variables_kit_results.scalars().unique().all()

            if not list_variables_kit:
                return []
            return [VariablesRead.model_validate(variables_kit) for variables_kit in list_variables_kit]
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(e, exc_info=True)
        mess = {"status": "error", "message": f"Error: {e}"}
        raise HTTPException(400, mess)


async def update_existing_variables_kit(variables_kit_id: UUID4,
                                        variables_kit_update: VariablesUpdate,
                                        user: User,
                                        session: AsyncSession) -> VariablesRead:
    try:
        async with transaction_scope(session):
            query = (
                select(Variables)
                .join(ProjectUser, and_(Variables.project_id == ProjectUser.project_id,
                                        ProjectUser.user_id == user.user_id,
                                        ProjectUser.workspace_id == user.active_workspace_id))
                .where(Variables.variables_kit_id == variables_kit_id)
            )

            result = await session.execute(query)
            variables_kit = result.scalars().one_or_none()

            if not variables_kit:
                raise HTTPException(status_code=404, detail="variables_kit not found or not authorized")
            if variables_kit.variables_kit_name == 'Default':
                return JSONResponse(content={"status": "Cannot update default kit"})

            if variables_kit_update.variables_kit_name:
                # Проверка уникальности в рамках проекта
                variable_kit_name_check_query = (
                    select(Variables)
                    .where(Variables.variables_kit_name == variables_kit_update.variables_kit_name,
                           Variables.project_id == variables_kit.project_id,
                           Variables.variables_kit_id != variables_kit_id)
                )
                variable_kit_name_check_result = await session.execute(variable_kit_name_check_query)
                conflicting_variable_kit_name = variable_kit_name_check_result.scalars().one_or_none()
                if conflicting_variable_kit_name:
                    raise HTTPException(status_code=400, detail="Another kit with this name already exists in the project")

                variables_kit.variables_kit_name = variables_kit_update.variables_kit_name

            update_data = variables_kit_update.model_dump(exclude_unset=True)

            if "variables_kit_description" in update_data:
                variables_kit.variables_kit_description = variables_kit_update.variables_kit_description

            await session.flush()
            await session.refresh(variables_kit)

            return VariablesRead.model_validate(variables_kit)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(e, exc_info=True)
        mess = {"status": "error", "message": f"Error: {e}"}
        raise HTTPException(400, mess)


async def delete_existing_variable_kit(variables_kit_id: UUID4,
                                       user: User,
                                       session: AsyncSession) -> JSONResponse:
    try:
        async with transaction_scope(session):

            query = (
                select(Variables)
                .join(ProjectUser, and_(Variables.project_id == ProjectUser.project_id,
                                        ProjectUser.user_id == user.user_id,
                                        ProjectUser.workspace_id == user.active_workspace_id))
                .where(Variables.variables_kit_id == variables_kit_id)
            )

            result = await session.execute(query)
            variables_kit = result.scalars().one_or_none()

            if not variables_kit:
                return JSONResponse(content={"status": "not found or not authorized to delete this variable_kit"})
            if variables_kit.variables_kit_name == 'Default':
                return JSONResponse(content={"status": "Cannot delete default kit"})

            await session.delete(variables_kit)
            return JSONResponse(content={"status": "OK"})

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(e, exc_info=True)
        mess = {"status": "error", "message": f"Error: {e}"}
        raise HTTPException(400, mess)


async def precalc_variable(variable: VariablesDetailsCreate,
                           date: str,
                           user: User) -> VariablesDetailsRead:
    try:
        try:
            target_date = datetime.strptime(date, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            raise HTTPException(status_code=400, detail="Date format should be YYYY-MM-DD HH:mm:ss")

        new_variable = VariablesDetails(variable_details_id=str(uuid.uuid4()),
                                        variable_name=variable.variable_name,
                                        variable_config=variable.variable_config.model_dump(mode='json'),
                                        variable_description=variable.variable_description,
                                        variables_kit_id=variable.variables_kit_id)

        result_model = VariablesDetailsRead.model_validate(new_variable)
        result_model.computed_value = compute_variable_value(result_model.variable_config, target_date)
        return result_model

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(e, exc_info=True)
        mess = {"status": "error", "message": f"Error: {e}"}
        raise HTTPException(400, mess)


async def create_variable(variable: VariablesDetailsCreate,
                          user: User,
                          session: AsyncSession) -> VariablesDetailsRead:
    try:
        async with transaction_scope(session):
            query = (
                select(Variables)
                .join(ProjectUser, and_(ProjectUser.project_id == Variables.project_id,
                                        ProjectUser.workspace_id == user.active_workspace_id,
                                        ProjectUser.user_id == user.user_id))
                .where(Variables.variables_kit_id == variable.variables_kit_id)
            )
            result = await session.execute(query)
            result = result.scalars().one_or_none()

            if not result:
                raise HTTPException(status_code=400, detail="Variables kit not found or not authorized to create variables in this project")

            # уникальные названия переменных в рамках набора
            query = (
                select(VariablesDetails)
                .where(and_(VariablesDetails.variables_kit_id == variable.variables_kit_id,
                            VariablesDetails.variable_name == variable.variable_name))
            )

            result = await session.execute(query)
            result = result.unique().one_or_none()

            if result:
                raise HTTPException(status_code=404, detail="variable_name exists in this kit")

            new_variable = VariablesDetails(variable_name=variable.variable_name,
                                            variable_config=variable.variable_config.model_dump(mode='json'),
                                            variable_description=variable.variable_description,
                                            variables_kit_id=variable.variables_kit_id)

            session.add(new_variable)
            await session.flush()
            await session.refresh(new_variable)

            result_model = VariablesDetailsRead.model_validate(new_variable)
            result_model.computed_value = compute_variable_value(result_model.variable_config)
            return result_model

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(e, exc_info=True)
        mess = {"status": "error", "message": f"Error: {e}"}
        raise HTTPException(400, mess)


async def update_existing_variable(variable_details_id: UUID4,
                                   variable_update: VariablesDetailsUpdate,
                                   user: User,
                                   session: AsyncSession) -> VariablesDetailsRead:
    try:
        async with transaction_scope(session):
            query = (
                select(VariablesDetails)
                .join(Variables, VariablesDetails.variables_kit_id == Variables.variables_kit_id)
                .join(ProjectUser, and_(Variables.project_id == ProjectUser.project_id,
                                        ProjectUser.user_id == user.user_id,
                                        ProjectUser.workspace_id == user.active_workspace_id))
                .where(VariablesDetails.variable_details_id == variable_details_id)
            )

            result = await session.execute(query)
            variable_details = result.scalars().one_or_none()

            if not variable_details:
                raise HTTPException(status_code=404, detail="variable not found or not authorized")

            if variable_update.variable_name:
                # Проверка уникальности в рамках проекта
                variable_name_check_query = (
                    select(VariablesDetails)
                    .where(VariablesDetails.variable_name == variable_update.variable_name,
                           VariablesDetails.variables_kit_id == variable_details.variables_kit_id,
                           VariablesDetails.variable_details_id != variable_details_id)
                )
                variable_name_check_result = await session.execute(variable_name_check_query)
                conflicting_variable_name = variable_name_check_result.scalars().one_or_none()
                if conflicting_variable_name:
                    raise HTTPException(status_code=400, detail="Another variable with this name already exists")

                variable_details.variable_name = variable_update.variable_name

            update_data = variable_update.model_dump(exclude_unset=True)

            if "variable_description" in update_data:
                variable_details.variable_description = variable_update.variable_description
            if "variable_config" in update_data:
                variable_details.variable_config = variable_update.variable_config.model_dump(mode='json')

            await session.flush()
            await session.refresh(variable_details)

            result_model = VariablesDetailsRead.model_validate(variable_details)
            result_model.computed_value = compute_variable_value(result_model.variable_config)
            return result_model

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(e, exc_info=True)
        mess = {"status": "error", "message": f"Error: {e}"}
        raise HTTPException(400, mess)


async def delete_existing_variable(variable_details_id: UUID4,
                                   user: User,
                                   session: AsyncSession) -> JSONResponse:
    try:
        async with transaction_scope(session):

            query = (
                select(VariablesDetails)
                .join(Variables, VariablesDetails.variables_kit_id == Variables.variables_kit_id)
                .join(ProjectUser, and_(Variables.project_id == ProjectUser.project_id,
                                        ProjectUser.user_id == user.user_id,
                                        ProjectUser.workspace_id == user.active_workspace_id))
                .where(VariablesDetails.variable_details_id == variable_details_id)
                )

            result = await session.execute(query)
            variable_details = result.scalars().one_or_none()

            if not variable_details:
                return JSONResponse(content={"status": "not found or not authorized to delete this variable"})

            await session.delete(variable_details)
            return JSONResponse(content={"status": "OK"})

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(e, exc_info=True)
        mess = {"status": "error", "message": f"Error: {e}"}
        raise HTTPException(400, mess)


async def variable_by_id(variable_details_id: UUID4,
                         user: User,
                         session: AsyncSession) -> VariablesDetailsRead:
    try:
        async with transaction_scope(session):
            query = (
                select(VariablesDetails)
                .join(Variables, VariablesDetails.variables_kit_id == Variables.variables_kit_id)
                .join(ProjectUser, and_(Variables.project_id == ProjectUser.project_id,
                                        ProjectUser.user_id == user.user_id,
                                        ProjectUser.workspace_id == user.active_workspace_id))
                .where(VariablesDetails.variable_details_id == variable_details_id)
            )

            result = await session.execute(query)
            variable_details = result.scalars().one_or_none()

            if not variable_details:
                return []

            result_model = VariablesDetailsRead.model_validate(variable_details)
            result_model.computed_value = compute_variable_value(result_model.variable_config)
            return result_model

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(e, exc_info=True)
        mess = {"status": "error", "message": f"Error: {e}"}
        raise HTTPException(400, mess)


async def list_variables_by_variables_kit_id(variables_kit_id: UUID4,
                                             user: User,
                                             session: AsyncSession,
                                             search: Optional[str] = None) -> Dict:
    try:
        result = {"variables_details": [], "variables_count": 0}
        async with transaction_scope(session):
            query = (
                select(VariablesDetails)
                .join(Variables, VariablesDetails.variables_kit_id == Variables.variables_kit_id)
                .join(ProjectUser, and_(Variables.project_id == ProjectUser.project_id,
                                        ProjectUser.user_id == user.user_id,
                                        ProjectUser.workspace_id == user.active_workspace_id))
                .where(VariablesDetails.variables_kit_id == variables_kit_id)
            )

            if search:
                s = search.strip()
                if s:
                    search_pattern = f"%{s}%"
                    query = query.where(
                        or_(
                            VariablesDetails.variable_name.ilike(search_pattern),
                            VariablesDetails.variable_description.ilike(search_pattern),
                        )
                    )

            variables_details_results = await session.execute(query)
            list_variables = variables_details_results.scalars().unique().all()

            if not list_variables:
                return result

            variables_details = []

            for variable in list_variables:
                result_model = VariablesDetailsRead.model_validate(variable)
                result_model.computed_value = compute_variable_value(result_model.variable_config)
                variables_details.append(result_model)

            variables_count = len(variables_details)
            result["variables_details"] = variables_details
            result["variables_count"] = variables_count
            return result
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(e, exc_info=True)
        mess = {"status": "error", "message": f"Error: {e}"}
        raise HTTPException(400, mess)


async def list_variables_by_variables_kit_name(variables_kit_name: UUID4,
                                               project_id: UUID4,
                                               user: User,
                                               session: AsyncSession) -> Dict:
    try:
        result = {"variables_details": [], "variables_count": 0}

        async with transaction_scope(session):

            variables_kit_names = ["Default"]
            if variables_kit_name != "Default":
                variables_kit_names.insert(0, variables_kit_name)

            all_variables = {}

            for kit_name in variables_kit_names:
                query = (
                    select(Variables)
                    .join(ProjectUser, and_(Variables.project_id == ProjectUser.project_id,
                                            ProjectUser.project_id == project_id,
                                            ProjectUser.user_id == user.user_id,
                                            ProjectUser.workspace_id == user.active_workspace_id))
                    .where(Variables.variables_kit_name == kit_name)
                    )

                res = await session.execute(query)
                variables_kit = res.scalars().one_or_none()

                if not variables_kit:
                    # raise HTTPException(status_code=404, detail="variables_kit not found or not authorized")
                    # return result
                    continue

                query = (
                    select(VariablesDetails)
                    .join(Variables, VariablesDetails.variables_kit_id == Variables.variables_kit_id)
                    .join(ProjectUser, and_(Variables.project_id == ProjectUser.project_id,
                                            ProjectUser.user_id == user.user_id,
                                            ProjectUser.workspace_id == user.active_workspace_id))
                    .where(VariablesDetails.variables_kit_id == variables_kit.variables_kit_id)
                    )

                variables_details_results = await session.execute(query)
                list_variables = variables_details_results.scalars().unique().all()

                # Добавляем переменные в словарь (переменные из дефолта имеют приоритет)
                for variable in list_variables:
                    if variable.variable_name not in all_variables:
                        all_variables[variable.variable_name] = variable

            variables_details = []

            for variable in all_variables.values():
                result_model = VariablesDetailsRead.model_validate(variable)
                result_model.computed_value = compute_variable_value(result_model.variable_config)
                variables_details.append(result_model)

            variables_count = len(variables_details)
            result["variables_details"] = variables_details
            result["variables_count"] = variables_count
            return result
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(e, exc_info=True)
        mess = {"status": "error", "message": f"Error: {e}"}
        raise HTTPException(400, mess)


async def add_default_variables_kit(project_id: UUID4,
                                    user: User,
                                    session: AsyncSession):
    try:
        async with transaction_scope(session):
            variables_kit = VariablesCreate(variables_kit_name="Default",
                                            variables_kit_description="System",
                                            project_id=project_id)

            new_variables_kit = await create_variables_kit(variables_kit, user, session)

            template = [{"login": "test_user"}, {"password": "Pa$$w0rd"}, {"token": None}]

            for t in template:
                (k, v), = t.items()
                variable = VariablesDetailsCreate(variable_name=k,
                                                  variable_config={"type": "simple", "value": v},
                                                  variables_kit_id=new_variables_kit.variables_kit_id)
                await create_variable(variable, user, session)
            logger.info(f"Success creating default_variables_kit for {project_id=}")

    except Exception as e:
        logger.warning(f"Error creating default_variables_kit for {project_id=} {str(e)}", exc_info=True)
