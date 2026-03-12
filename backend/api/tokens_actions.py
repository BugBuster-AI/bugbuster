
from datetime import date, datetime, timedelta, timezone
from pydantic import UUID4
from fastapi import HTTPException
from sqlalchemy import and_, delete, desc, exists, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from config import logger
from db.models import UserToken
from dependencies.auth import create_user_jwt_token, token_hmac
from schemas import (UserTokenCreate, UserTokenCreated, UserTokenRead,
                     UserTokenUpdate)


def default_token_name() -> str:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M-%S")
    return f"BB_api_key_{ts}"


def date_to_expires_at_utc(d: date) -> datetime:
    """
    2026-12-10 -> 2026-12-11 00:00:00
    """
    return datetime(d.year, d.month, d.day, tzinfo=timezone.utc) + timedelta(days=1)


async def create_stored_user_token(user_id: UUID4,
                                   create_token: UserTokenCreate,
                                   session: AsyncSession) -> UserTokenCreated:
    try:
        async with session.begin():

            name = create_token.name or default_token_name()
            today_utc = datetime.now(timezone.utc).date()

            if create_token.expires_at is not None:
                if create_token.expires_at < today_utc:
                    raise HTTPException(
                        status_code=422,
                        detail="expires_at must be today or later (UTC)"
                    )
                expires_at = date_to_expires_at_utc(create_token.expires_at)
            else:
                expires_at = None

            token_str = create_user_jwt_token(str(user_id))
            new_token = UserToken(user_id=user_id,
                                  name=name,
                                  token_hash=token_hmac(token_str),
                                  is_active=True,
                                  expires_at=expires_at)

            session.add(new_token)
            await session.flush()
            await session.refresh(new_token)

            # return UserTokenCreated.model_validate(new_token)
            return UserTokenCreated(
                token_id=new_token.token_id,
                name=new_token.name,
                token=token_str,  # сырой токен
                is_active=new_token.is_active,
                expires_at=new_token.expires_at,
                created_at=new_token.created_at,
            )

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(e, exc_info=True)
        mess = {"status": "error", "message": f"Error: {e}"}
        raise HTTPException(400, mess)


async def update_user_token(token_id: str,
                            user_id: UUID4,
                            update_token: UserTokenUpdate,
                            session: AsyncSession) -> UserTokenRead:
    try:
        async with session.begin():

            token = await session.get(UserToken, token_id)

            if not token or token.user_id != user_id:
                raise HTTPException(404, detail="Token not found or not authorized")

            update_data = update_token.model_dump(exclude_unset=True)

            if "name" in update_data:
                token.name = update_token.name or default_token_name()

            if "expires_at" in update_data:
                # null => бессрочный
                if update_token.expires_at is None:
                    token.expires_at = None
                else:
                    today_utc = datetime.now(timezone.utc).date()

                    if update_token.expires_at < today_utc:
                        raise HTTPException(status_code=422,
                                            detail="expires_at must be today or later (UTC)")
                    token.expires_at = date_to_expires_at_utc(update_token.expires_at)

            await session.flush()
            await session.refresh(token)
            return UserTokenRead.model_validate(token)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(e, exc_info=True)
        mess = {"status": "error", "message": f"Error: {e}"}
        raise HTTPException(400, mess)


async def get_user_tokens(user_id: UUID4, session: AsyncSession):
    try:
        async with session.begin():
            res = await session.execute(select(UserToken)
                                        .where(UserToken.user_id == user_id)
                                        .order_by(desc(UserToken.created_at)))
            tokens = res.scalars().all()
            return [UserTokenRead.model_validate(t) for t in tokens]
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(e, exc_info=True)
        mess = {"status": "error", "message": f"Error: {e}"}
        raise HTTPException(400, mess)


async def delete_user_token(token_id: str, user_id: UUID4, session: AsyncSession):
    try:
        async with session.begin():
            token = await session.get(UserToken, token_id)
            if not token or token.user_id != user_id:
                raise HTTPException(404, detail="Token not found or not authorized")

            await session.delete(token)
            await session.flush()
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(e, exc_info=True)
        mess = {"status": "error", "message": f"Error: {e}"}
        raise HTTPException(400, mess)


async def activate_user_token(token_id: str, user_id: UUID4, session: AsyncSession):
    try:
        async with session.begin():
            token = await session.get(UserToken, token_id)
            if not token or token.user_id != user_id:
                raise HTTPException(404, "Token not found or not authorized")

            if not token.is_active:
                token.is_active = True
                session.add(token)
                await session.flush()

            return {"detail": "Token activated successfully"}
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(e, exc_info=True)
        mess = {"status": "error", "message": f"Error: {e}"}
        raise HTTPException(400, mess)


async def deactivate_user_token(token_id: str, user_id: UUID4, session: AsyncSession):
    try:
        async with session.begin():
            token = await session.get(UserToken, token_id)
            if not token or token.user_id != user_id:
                raise HTTPException(404, "Token not found or not authorized")

            if token.is_active:
                token.is_active = False
                session.add(token)
                await session.flush()
            return {"detail": "Token deactivated successfully"}
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(e, exc_info=True)
        mess = {"status": "error", "message": f"Error: {e}"}
        raise HTTPException(400, mess)
