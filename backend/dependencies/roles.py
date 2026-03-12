from typing import Optional
from fastapi import Depends, HTTPException
from jose import JWTError
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from config import SECRET_KEY_API
from db.models import User, UserToken
from db.session import async_session, get_session
from dependencies.auth import get_current_active_user, get_current_active_user_ws
from schemas import Roles


async def user_role_with_api_support(current_user: User = Depends(get_current_active_user)):
    return current_user


async def get_current_active_user_with_roles_ws(token: str, client_type: str = None):
    try:

        current_user: User = await get_current_active_user_ws(token)
        # можно сменить на admin_role или любую другую
        # current_user: User = await user_role_with_api_support(async_session(), current_user)
        return True, current_user

    except JWTError as e:
        if 'Signature has expired' in str(e):
            return False, {"detail": "Token has expired"}

        else:
            return False, {"detail": "Could not validate credentials"}

    except HTTPException as er:
        return False, {"detail": str(er)}

    except Exception as er:
        return False, {"detail": str(er)}
