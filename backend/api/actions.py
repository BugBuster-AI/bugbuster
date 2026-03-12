import asyncio
import io
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from fastapi_pagination import Page
from PIL import Image, UnidentifiedImageError
from pydantic import UUID4
from sqlalchemy import and_, delete, desc, exists, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from config import (MAX_CONCURRENT_TASKS_DEFAULT, REDIS_PREFIX, logger,
                    redis_client)
from db.models import (Role, TariffLimits, Tariffs, Usage, User, UserToken,
                       Workspace)
from db.session import async_session, transaction_scope
from schemas import (TariffCreate, TariffLimitRead, TariffRead, UserRead,
                     WorkspaceStatusEnum)
from utils import send_telegramm


async def refresh_workspace_limits(tariff_id: UUID4, session: AsyncSession):
    # пока что в кэше только max_concurrent_tasks актуалим
    # когда заводим или апдейтим новый лимит тарифа, нужно обновить max_concurrent_tasks
    # у воркспейса на случай если в новом лимите стало больше чем есть у воркспейса
    query = select(Workspace).where(Workspace.tariff_id == tariff_id)
    result = await session.execute(query)
    workspaces = result.scalars().all()

    query = select(TariffLimits.limit_value).where(TariffLimits.tariff_id == tariff_id,
                                                   TariffLimits.feature_name == 'max_concurrent_tasks')
    result = await session.execute(query)
    limit_value = result.scalar_one_or_none()

    # Update Redis for each workspace
    for workspace in workspaces:

        new_limit = None

        # Сравниваем значения из TariffLimits и Workspace
        if limit_value is not None and workspace.max_concurrent_tasks is not None:
            new_limit = max(limit_value, workspace.max_concurrent_tasks)
        elif limit_value is not None:
            new_limit = limit_value
        elif workspace.max_concurrent_tasks is not None:
            new_limit = workspace.max_concurrent_tasks
        else:
            new_limit = MAX_CONCURRENT_TASKS_DEFAULT

        redis_client.set(f"{REDIS_PREFIX}_workspace_limit:{workspace.workspace_id}", new_limit)

        if limit_value is not None and (workspace.max_concurrent_tasks is None or limit_value > workspace.max_concurrent_tasks):
            workspace.max_concurrent_tasks = limit_value
            await session.flush()


async def get_users(offset, limit, session: AsyncSession):

    async with session.begin():

        total_res = await session.execute(select(func.count()).select_from(User))
        total = total_res.scalar_one()

        res = await session.execute(select(User)
                                    .order_by(desc(User.registered_at))
                                    .offset(offset).limit(limit))
        users = res.unique().scalars().all()
        if not users:
            raise HTTPException(status_code=404, detail="Users not found")

        user_reads: List[UserRead] = []
        for user in users:
            user_read = UserRead.model_validate(user)
            user_reads.append(user_read)

        return Page(
            total=total,
            total_current_page=len(user_reads),
            items=user_reads,
            page=offset // limit + 1,
            size=limit,
            pages=(total - 1) // limit + 1,
        )


async def get_user(user_id: str, session: AsyncSession) -> UserRead:
    async with session.begin():
        res = await session.execute(select(User)
                                    .where(User.user_id == user_id))
        user = res.scalars().first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        return UserRead.model_validate(user)


async def block_user(user_id: str, user: User, session: AsyncSession) -> UserRead:
    async with session.begin():

        if user.user_id == user_id:
            raise HTTPException(status_code=404, detail="Kill yourself?")

        res = await session.execute(select(User)
                                    .where(User.user_id == user_id))
        user = res.scalars().first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        user.is_active = False
        await session.flush()

        return UserRead.model_validate(user)


async def unlock_user(user_id: str, session: AsyncSession) -> UserRead:
    async with session.begin():
        res = await session.execute(select(User)
                                    .where(User.user_id == user_id))
        user = res.scalars().first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        user.is_active = True
        await session.flush()

        return UserRead.model_validate(user)


async def save_workspace_concurrency_limit_to_redis():
    st = time.perf_counter()
    async with async_session() as session:
        stmt = (select(Workspace.workspace_id, Workspace.max_concurrent_tasks, TariffLimits.limit_value)
                .join(TariffLimits, and_(
                    TariffLimits.tariff_id == Workspace.tariff_id,
                    TariffLimits.feature_name == 'max_concurrent_tasks'
                )))
        result = await session.execute(stmt)
        for row in result:
            new_limit = None

            # Сравниваем значения из TariffLimits и Workspace
            if row.limit_value is not None and row.max_concurrent_tasks is not None:
                new_limit = max(row.limit_value, row.max_concurrent_tasks)
            elif row.limit_value is not None:
                new_limit = row.limit_value
            elif row.max_concurrent_tasks is not None:
                new_limit = row.max_concurrent_tasks
            else:
                new_limit = MAX_CONCURRENT_TASKS_DEFAULT

            redis_client.set(f"{REDIS_PREFIX}_workspace_limit:{row.workspace_id}", new_limit)
    et = time.perf_counter()
    logger.info(f"success save_workspace_concurrency_limit_to_redis for: {(et - st):.4f} seconds")


async def save_permissions_to_redis():
    try:
        st = time.perf_counter()
        async with async_session() as session:
            stmt = (select(Role.role, Role.permission).where(Role.permission.isnot(None)))
            result = await session.execute(stmt)
            for row in result:
                permissions = row.permission.get("endpoints", [])
                for endpoint in permissions:
                    redis_client.set(f"{REDIS_PREFIX}_permissions:{row.role}:{endpoint}", endpoint)
        et = time.perf_counter()
        logger.info(f"success save_permissions_to_redis for: {(et - st):.4f} seconds")
    except Exception as e:
        logger.error(e, exc_info=True)
        mess = {"status": "error", "message": f"Error: {e}"}
        raise HTTPException(400, mess)


async def reset_usage_and_check_tariff_expiration():
    try:
        async with async_session() as session:
            async with session.begin():
                current_utc_time = datetime.now(timezone.utc)

                # 1. Находим и деактивируем workspace с истекшим тарифом
                expired_query = select(Workspace.workspace_id).where(
                    Workspace.tariff_expiration < current_utc_time,
                    Workspace.status == WorkspaceStatusEnum.ACTIVE.value
                )
                expired_result = await session.execute(expired_query)
                expired_workspaces = expired_result.scalars().all()

                if expired_workspaces:
                    await session.execute(
                        update(Workspace)
                        .where(Workspace.workspace_id.in_(expired_workspaces))
                        .values(status=WorkspaceStatusEnum.INACTIVE.value)
                    )

                    await session.flush()
                    await send_telegramm(f"Следующие workspaces деактивированы в связи с истекшим тарифом:\n{expired_workspaces}")

                # Сброс лимитов, если прошло 30 дней с начала тарифа
                thirty_days_ago = current_utc_time - timedelta(days=30)

                reset_query = select(Workspace.workspace_id).join(Usage).where(
                    Workspace.tariff_expiration > current_utc_time,
                    or_(
                        and_(
                            Workspace.tariff_start_date <= thirty_days_ago,
                            Usage.last_reset.is_(None)
                        ),
                        Usage.last_reset <= thirty_days_ago
                    )
                ).distinct()

                workspace_ids_for_reset_result = await session.execute(reset_query)
                workspace_ids_for_reset = workspace_ids_for_reset_result.scalars().all()

                if workspace_ids_for_reset:
                    await session.execute(
                        update(Usage)
                        .where(Usage.workspace_id.in_(workspace_ids_for_reset))
                        .values(usage_count=0, last_reset=current_utc_time)
                    )
                    await session.flush()
                    # await send_telegramm(f"Следующим workspaces сброшены лимиты по истечении 30 дней сначала тарифа:\n{workspace_ids_for_reset}")

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(e, exc_info=True)
        mess = {"status": "error", "message": f"Error: {e}"}
        raise HTTPException(400, mess)


async def update_usage_count(workspace_id: UUID4,
                             feature_name: str,
                             increment: int):
    try:
        async with async_session() as session:
            async with session.begin():
                usage_query = select(Usage).where(
                    Usage.workspace_id == workspace_id,
                    Usage.feature_name == feature_name
                )

                result = await session.execute(usage_query)
                usage_record = result.scalar_one_or_none()

                if usage_record:
                    # Обновить существующую запись
                    new_usage_count = usage_record.usage_count + increment
                    await session.execute(
                        update(Usage)
                        .where(
                            Usage.usage_id == usage_record.usage_id
                        )
                        .values(
                            usage_count=new_usage_count
                        )
                    )
                else:
                    # Создать новую запись
                    new_usage = Usage(
                        workspace_id=workspace_id,
                        feature_name=feature_name,
                        usage_count=increment,
                        last_reset=datetime.now(timezone.utc)
                    )
                    session.add(new_usage)
                await session.flush()
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(e, exc_info=True)
        mess = {"status": "error", "message": f"Error: {e}"}
        raise HTTPException(400, mess)


async def activate_or_renew_workspace_tariff(workspace_id: UUID4,
                                             session: AsyncSession,
                                             additional_months: Optional[int] = 1,
                                             streams_count: Optional[int] = None,
                                             stream_only: Optional[bool] = None):
    try:
        async with transaction_scope(session):

            workspace = await session.get(Workspace, workspace_id)
            if not workspace:
                raise HTTPException(status_code=404, detail="Workspace not found")

            tariff_query = select(Tariffs).where(Tariffs.tariff_id == workspace.tariff_id)
            result = await session.execute(tariff_query)
            tariff = result.scalar_one_or_none()

            if not tariff:
                raise HTTPException(status_code=404, detail="Tariff not found")

            # Получаем limit_value из тарифа
            limit_query = select(TariffLimits.limit_value).where(
                TariffLimits.tariff_id == workspace.tariff_id,
                TariffLimits.feature_name == 'max_concurrent_tasks'
            )
            limit_result = await session.execute(limit_query)
            limit_value = limit_result.scalar_one_or_none()

            base_limit = limit_value if limit_value is not None else MAX_CONCURRENT_TASKS_DEFAULT
            # текущее количество добавленных потоков (если покупались)
            current_added_streams = 0
            if workspace.max_concurrent_tasks is not None and limit_value is not None:
                current_added_streams = workspace.max_concurrent_tasks - limit_value
                current_added_streams = max(current_added_streams, 0)

            # Рассчитываем новое значение с учетом:
            # 1. Базового лимита тарифа
            # 2. Уже докупленных потоков
            # 3. Новых потоков (если переданы)
            new_max_concurrent_tasks = base_limit + current_added_streams
            if streams_count is not None:
                new_max_concurrent_tasks += streams_count

            if not stream_only:
                current_time = datetime.now(timezone.utc)
                # Обновляем даты подписки и лимиты

                # Если тариф уже активен и не истек, добавляем к оставшемуся времени
                if workspace.tariff_expiration and workspace.tariff_expiration > current_time:
                    remaining_time = workspace.tariff_expiration - current_time
                    new_expiration = current_time + remaining_time + timedelta(weeks=500 * additional_months or tariff.cnt_months)
                else:
                    # Иначе устанавливаем новый срок от текущей даты
                    new_expiration = current_time + timedelta(weeks=500 * additional_months or tariff.cnt_months)
                    # те потоки что покупались ранее тогда не учитывать
                    # только те что положены по тарифу + которые докупают сейчас
                    new_max_concurrent_tasks -= current_added_streams

                # workspace.tariff_start_date = datetime.now(timezone.utc)
                workspace.tariff_expiration = new_expiration
                workspace.status = WorkspaceStatusEnum.ACTIVE.value

            workspace.max_concurrent_tasks = new_max_concurrent_tasks
            await session.flush()

            # Обновляем Redis
            redis_key = f"{REDIS_PREFIX}_workspace_limit:{workspace.workspace_id}"
            redis_client.set(redis_key, new_max_concurrent_tasks)

            return JSONResponse(content={"status": "OK"})

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(e, exc_info=True)
        mess = {"status": "error", "message": f"Error: {e}"}
        raise HTTPException(400, mess)


async def deactivate_workspace(workspace_id: UUID4,
                               session: AsyncSession):
    try:
        async with transaction_scope(session):
            result = await session.execute(
                update(Workspace)
                .where(Workspace.workspace_id == workspace_id)
                .values(status=WorkspaceStatusEnum.INACTIVE.value)
            )

            if result.rowcount == 0:
                raise HTTPException(status_code=404, detail="Workspace not found")
            return JSONResponse(content={"status": "OK"})
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(e, exc_info=True)
        mess = {"status": "error", "message": f"Error: {e}"}
        raise HTTPException(400, mess)


async def create_tariff(tariff: TariffCreate,
                        user: User,
                        session: AsyncSession):
    try:
        async with transaction_scope(session):
            new_tariff = Tariffs(tariff_name=tariff.tariff_name,
                                 tariff_full_name=tariff.tariff_full_name,
                                 description=tariff.description,
                                 cnt_months=tariff.cnt_months,
                                 price=tariff.price,
                                 cur=tariff.cur,
                                 discount=tariff.discount,
                                 period=tariff.period,
                                 buy_tariff_manual_only=tariff.buy_tariff_manual_only,
                                 best_value=tariff.best_value,
                                 can_buy_streams=tariff.can_buy_streams,
                                 visible=tariff.visible)

            session.add(new_tariff)
            await session.flush()
            await session.refresh(new_tariff)

            logger.info(f"User {user.email} created new tariff: {new_tariff.tariff_name}")
            return TariffRead.model_validate(new_tariff)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(e, exc_info=True)
        mess = {"status": "error", "message": f"Error: {e}"}
        raise HTTPException(400, mess)


async def tariff_by_id(tariff_id: UUID4, session: AsyncSession):
    try:
        async with transaction_scope(session):
            result = await session.execute(select(Tariffs).where(Tariffs.tariff_id == tariff_id))
            tariff = result.scalar_one_or_none()

            if not tariff:
                raise HTTPException(status_code=404, detail="Tariff not found")

            return TariffRead.model_validate(tariff)

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(e, exc_info=True)
        mess = {"status": "error", "message": f"Error: {e}"}
        raise HTTPException(400, mess)


async def list_tariffs(session: AsyncSession):
    try:
        async with transaction_scope(session):
            result = await session.execute(select(Tariffs))
            tariffs = result.scalars().all()

            return [TariffRead.model_validate(tariff) for tariff in tariffs]

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(e, exc_info=True)
        mess = {"status": "error", "message": f"Error: {e}"}
        raise HTTPException(400, mess)


async def tariff_limit_by_id(limit_id: UUID4, session: AsyncSession):
    try:
        async with transaction_scope(session):
            result = await session.execute(select(TariffLimits)
                                           .where(TariffLimits.limit_id == limit_id))
            limit = result.scalar_one_or_none()

            if not limit:
                raise HTTPException(status_code=404, detail="Tariff limit not found")

            return TariffLimitRead.model_validate(limit)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(e, exc_info=True)
        mess = {"status": "error", "message": f"Error: {e}"}
        raise HTTPException(400, mess)


async def tariff_all_limits_by_tariff_id(tariff_id: UUID4, session: AsyncSession):
    try:
        async with transaction_scope(session):
            result = await session.execute(select(TariffLimits)
                                           .where(TariffLimits.tariff_id == tariff_id))
            limits = result.scalars().all()
            return [TariffLimitRead.model_validate(limit) for limit in limits]

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(e, exc_info=True)
        mess = {"status": "error", "message": f"Error: {e}"}
        raise HTTPException(400, mess)


async def check_usage_limits(workspace_id: UUID4, feature_name: str, session: AsyncSession):
    try:
        async with transaction_scope(session):

            tariff_query = select(Workspace.tariff_id).where(Workspace.workspace_id == workspace_id)
            result = await session.execute(tariff_query)
            tariff_id = result.scalar_one_or_none()

            if tariff_id is None:
                raise HTTPException(status_code=404, detail="Workspace not properly configured with a tariff")

            # лимит по тарифу
            tariff_limit_query = select(TariffLimits.limit_value).where(
                TariffLimits.tariff_id == tariff_id,
                TariffLimits.feature_name == feature_name
            )
            result = await session.execute(tariff_limit_query)
            limit_value = result.scalar_one_or_none()

            # Если лимит отсутствует, указываем, что он неограничен
            if limit_value is None:
                limit_value = -1

            # Неограниченный лимит
            if limit_value == -1:
                return -1

            # текущий расход
            usage_query = select(Usage.usage_count).where(
                Usage.workspace_id == workspace_id,
                Usage.feature_name == feature_name
            )
            result = await session.execute(usage_query)
            current_usage = result.scalar_one_or_none() or 0

            remaining = limit_value - current_usage
            # Проверка, не превышен ли лимит
            if remaining <= 0:
                raise HTTPException(status_code=403,
                                    detail=f"Limit for {feature_name} exceeded. Remaining attempts: 0")
            return remaining
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(e, exc_info=True)
        mess = {"status": "error", "message": f"Error: {e}"}
        raise HTTPException(400, mess)


async def usage_summary(workspace_id: UUID4, session: AsyncSession, feature_name: str = None):
    try:
        async with transaction_scope(session):
            tariff_query = select(Workspace.tariff_id).where(Workspace.workspace_id == workspace_id)
            result = await session.execute(tariff_query)
            tariff_id = result.scalar_one_or_none()

            if tariff_id is None:
                raise HTTPException(status_code=404, detail="Workspace not properly configured with a tariff")

            # Получаем информацию о лимитах и использовании
            limits_query = (
                select(TariffLimits.feature_name, TariffLimits.limit_value, func.coalesce(Usage.usage_count, 0))
                .outerjoin(Usage, and_(
                    Usage.workspace_id == workspace_id,
                    Usage.feature_name == TariffLimits.feature_name
                ))
                .where(TariffLimits.tariff_id == tariff_id)
            )
            if feature_name:
                limits_query = limits_query.where(TariffLimits.feature_name == feature_name)

            result = await session.execute(limits_query)
            usage_info = result.fetchall()

            usage_summary = []
            for feature_name, limit_value, usage_count in usage_info:
                # Рассчитываем остаток
                remaining = limit_value - usage_count if limit_value != -1 else -1  # float('inf')
                usage_summary.append({
                    "feature_name": feature_name,
                    "limit_value": limit_value,
                    "usage_count": usage_count,
                    "remaining": remaining
                })

            return usage_summary

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(e, exc_info=True)
        mess = {"status": "error", "message": f"Error: {e}"}
        raise HTTPException(400, mess)


async def change_workspace_tariff(workspace_id: UUID4,
                                  additional_months: int,
                                  new_tariff_id: UUID4,
                                  session: AsyncSession,
                                  streams_count: Optional[int] = None):
    try:
        async with transaction_scope(session):
            # Проверяем, существует ли новый тариф
            tariff_query = select(Tariffs).where(Tariffs.tariff_id == new_tariff_id)
            result = await session.execute(tariff_query)
            new_tariff = result.scalar_one_or_none()

            if not new_tariff:
                raise HTTPException(status_code=404, detail="Tariff not found")

            # новые даты начала и окончания действия тарифа
            new_tariff_start_date = datetime.now(timezone.utc)
            new_tariff_expiration_date = new_tariff_start_date + timedelta(weeks=500 * additional_months or new_tariff.cnt_months)

            # Update Redis with new max_concurrent_tasks limit
            query = select(TariffLimits.limit_value).where(TariffLimits.tariff_id == new_tariff_id,
                                                           TariffLimits.feature_name == 'max_concurrent_tasks')
            result = await session.execute(query)
            limit_value = result.scalar_one_or_none()
            max_concurrent_tasks = limit_value if limit_value is not None else MAX_CONCURRENT_TASKS_DEFAULT
            if streams_count is not None:
                max_concurrent_tasks += streams_count
            redis_client.set(f"{REDIS_PREFIX}_workspace_limit:{workspace_id}", max_concurrent_tasks)

            # Обновляем workspace с новым тарифом
            await session.execute(
                update(Workspace)
                .where(Workspace.workspace_id == workspace_id)
                .values(
                    tariff_id=new_tariff_id,
                    tariff_start_date=new_tariff_start_date,
                    tariff_expiration=new_tariff_expiration_date,
                    max_concurrent_tasks=max_concurrent_tasks,
                    status=WorkspaceStatusEnum.ACTIVE.value
                )
            )

            # Перезапуск лимитов в соответствии с новым тарифом
            await session.execute(
                update(Usage)
                .where(Usage.workspace_id == workspace_id)
                .values(usage_count=0, last_reset=new_tariff_start_date)
            )

            await session.flush()
            return {"detail": "Tariff changed successfully"}

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(e, exc_info=True)
        raise HTTPException(status_code=400, detail=f"Error: {e}")


async def check_workspace_tariff_is_current(workspace_id: UUID4,
                                            tariff_id: UUID4,
                                            session: AsyncSession):

    async with transaction_scope(session):
        workspace = await session.get(Workspace, workspace_id)
        if not workspace:
            raise HTTPException(status_code=404, detail="Workspace not found")
        if workspace.tariff_id != tariff_id:
            return False
        return True


def search_for_filter_cases(filter_cases: str, current_case_version: dict) -> bool:
    filter_lower = filter_cases.lower()
    found = False

    # Проверяем name (строка)
    name = current_case_version.get("name", "")
    if filter_lower in name.lower():
        found = True

    # Проверяем url (строка)
    url = current_case_version.get("url", "") or ""
    if not found and filter_lower in url.lower():
        found = True

    # Проверяем списки (before_steps, steps, after_steps, before_browser_start)
    list_fields = [
        "before_steps",
        "steps",
        "after_steps",
        "before_browser_start"
    ]

    for field in list_fields:
        if found:
            return True

        items = current_case_version.get(field, [])
        for item in items:
            if isinstance(item, str):
                if filter_lower in item.lower():
                    found = True
                    return True
            elif isinstance(item, dict):
                for value in item.values():
                    if isinstance(value, str) and filter_lower in value.lower():
                        found = True
                        return True
                if found:
                    return True
    return False
