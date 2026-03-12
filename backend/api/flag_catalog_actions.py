from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified
from config import logger
from db.models import FlagCatalog, User, UserFlags
from db.session import transaction_scope
from schemas import FlagCatalogRead, UserFlagsRead, UserFlagsUpdate


async def get_flag_catalog(session: AsyncSession) -> List[FlagCatalogRead]:
    try:
        async with session.begin():
            query = select(FlagCatalog)
            result = await session.execute(query)
            flags = result.scalars().all()

            if not flags:
                return []
            return [FlagCatalogRead.model_validate(flag) for flag in flags]

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(e, exc_info=True)
        mess = {"status": "error", "message": f"Error: {e}"}
        raise HTTPException(400, mess)


async def init_user_flags(user_id: UUID, session: AsyncSession) -> UserFlagsRead:
    try:
        async with transaction_scope(session):

            catalog_query = select(FlagCatalog).where(FlagCatalog.is_active == True)
            catalog_result = await session.execute(catalog_query)
            active_flags = catalog_result.scalars().all()

            flags = {
                flag.flag_name: {
                    "shown": flag.default_shown,
                    "view_count": flag.default_view_count,
                    "last_update": datetime.now(timezone.utc).isoformat()
                }
                for flag in active_flags
            }

            # Создаем или обновляем запись пользователя
            user_flags = await session.get(UserFlags, user_id)
            if not user_flags:
                user_flags = UserFlags(user_id=user_id, flags=flags)
                session.add(user_flags)
            else:
                # Обновляем только отсутствующие флаги
                for flag_name, flag_data in flags.items():
                    if flag_name not in user_flags.flags:
                        user_flags.flags[flag_name] = flag_data

            await session.flush()
            await session.refresh(user_flags)

            return UserFlagsRead.model_validate(user_flags)

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(e, exc_info=True)
        mess = {"status": "error", "message": f"Error: {e}"}
        raise HTTPException(400, mess)


async def user_flags(user: User,
                     session: AsyncSession) -> UserFlagsRead:
    try:
        async with session.begin():
            user_flags = await session.get(UserFlags, user.user_id)
            if not user_flags:
                # Если флагов нет - инициализируем
                return await init_user_flags(user.user_id, session)
            return UserFlagsRead.model_validate(user_flags)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(e, exc_info=True)
        mess = {"status": "error", "message": f"Error: {e}"}
        raise HTTPException(400, mess)


async def update_user_flag(flag_name: str,
                           user_flag_update: UserFlagsUpdate,
                           user: User,
                           session: AsyncSession) -> UserFlagsRead:
    try:
        async with session.begin():
            # Ищем флаг в справочнике
            catalog_flag = await session.execute(
                select(FlagCatalog)
                .where(FlagCatalog.flag_name == flag_name)
                .where(FlagCatalog.is_active == True)
            )
            if not catalog_flag.scalar_one_or_none():
                raise HTTPException(404, detail="Flag not found in catalog")

            # Получаем или создаем флаги пользователя
            user_flags = await session.get(UserFlags, user.user_id)
            if not user_flags:
                raise HTTPException(404, detail="Not found user_flags")

            # Инициализируем флаг, если его нет
            if flag_name not in user_flags.flags:
                user_flags.flags[flag_name] = {
                    "shown": False,
                    "view_count": 0,
                    "last_update": datetime.now(timezone.utc).isoformat()
                }
                flag_modified(user_flags, "flags")
                await session.flush()
            # Обновляем значения
            if user_flag_update.shown is not None:
                user_flags.flags[flag_name]["shown"] = user_flag_update.shown

            if user_flag_update.view_count is not None:
                if user_flag_update.view_count < 0:
                    raise HTTPException(400, detail="View count cannot be negative")

                user_flags.flags[flag_name]["view_count"] = user_flag_update.view_count
            elif user_flag_update.increment_view:
                user_flags.flags[flag_name]["view_count"] += 1

            # Обновляем timestamp
            user_flags.flags[flag_name]["last_update"] = datetime.now(timezone.utc).isoformat()

            flag_modified(user_flags, "flags")
            await session.flush()
            await session.refresh(user_flags)
            return UserFlagsRead.model_validate(user_flags)

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(e, exc_info=True)
        mess = {"status": "error", "message": f"Error: {e}"}
        raise HTTPException(400, mess)
