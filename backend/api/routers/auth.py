import asyncio
import uuid
from datetime import timedelta
from urllib.parse import urlparse

from fastapi import (APIRouter, BackgroundTasks, Depends, Header,
                     HTTPException, Request, status)
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import (and_, delete, desc, func, insert, or_, over, select,
                        update)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from config import ACCESS_TOKEN_EXPIRE_MINUTES, DOMAIN, logger
from db.models import User, WorkspaceMembership
from db.session import get_session
from dependencies.auth import (authenticate_user, change_password,
                               check_permissions, create_access_token,
                               create_new_user, create_password_reset_token,
                               get_current_active_user, password_reset_confirm,
                               send_password_reset_email)
from schemas import (PasswordChange, PasswordResetConfirm,
                     PasswordResetRequest, Roles, Token, UserIn, UserRead,
                     WorkspaceMembershipStatusEnum)
from utils import (create_new_user_message, generate_presigned_url,
                   send_telegramm)

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/signin", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = await authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.user_id)}, expires_delta=access_token_expires
    )

    return Token(access_token=access_token, token_type="bearer", user_id=user.user_id)


@router.get("/users/me", response_model=UserRead)
async def read_users_me(current_user: User = Depends(get_current_active_user),
                        host: str = Header(None)):

    avatar_url = None

    if current_user.avatar is not None:
        bucket = current_user.avatar.get('bucket', '')
        file_key = current_user.avatar.get('file', '')

        if bucket and file_key:
            avatar_url = await asyncio.to_thread(
                generate_presigned_url,
                current_user.avatar.get('bucket', ''),
                current_user.avatar.get('file', ''),
                host
            )

    current_user.avatar = avatar_url
    return UserRead.model_validate(current_user)


@router.post("/password_change")
async def password_change(password_change: PasswordChange,
                          current_user: User = Depends(get_current_active_user),
                          session: AsyncSession = Depends(get_session)):
    await change_password(current_user, password_change.old_password, password_change.new_password, session)
    return {"detail": "Password successfully changed"}


@router.post("/password_reset_request")
async def password_reset_request(request: PasswordResetRequest,
                                 background_tasks: BackgroundTasks,
                                 session: AsyncSession = Depends(get_session),
                                 host: str = Header(None)):

    try:
        result = await session.execute(select(User).where(User.email == request.email))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        reset_token = create_password_reset_token(user.email, timedelta(hours=24))
        await send_password_reset_email(user, reset_token, background_tasks, host)

        return JSONResponse(content={"status": "OK"})
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(e, exc_info=True)
        mess = {"status": "error", "message": f"Error: {e}"}
        raise HTTPException(400, mess)


@router.post("/password_reset_request_by_user_email")
async def password_reset_request_by_user_email(request: PasswordResetRequest,
                                               background_tasks: BackgroundTasks,
                                               current_user: UserRead = Depends(get_current_active_user),
                                               session: AsyncSession = Depends(get_session),
                                               host: str = Header(None)):

    await check_permissions("password_reset_request_by_user_email", current_user.role, current_user.workspace_status)

    try:
        if not current_user.role == Roles.ROLE_ADMIN.value:
            raise HTTPException(status_code=403, detail="You do not have permission to reset password.")

        # юзер должен быть в этом же воркспейсе
        result = await session.execute(select(User)
                                       .join(WorkspaceMembership, and_(WorkspaceMembership.user_id == User.user_id,
                                                                       WorkspaceMembership.workspace_id == current_user.active_workspace_id,
                                                                       WorkspaceMembership.status == WorkspaceMembershipStatusEnum.ACTIVE.value))
                                       .where(User.email == request.email, User.is_active == True))
        user = result.scalars().first()
        if not user:
            raise HTTPException(status_code=403, detail="User not found")

        reset_token = create_password_reset_token(user.email, timedelta(hours=24))
        link = f"{DOMAIN}/reset-password?token={reset_token}"

        await send_password_reset_email(user, reset_token, background_tasks, host)
        res = {"status": "OK", "link": link}
        logger.info(res)
        return JSONResponse(content=res)

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(e, exc_info=True)
        mess = {"status": "error", "message": f"Error: {e}"}
        raise HTTPException(400, mess)


@router.post("/user_password_reset_confirm")
async def user_password_reset_confirm(data: PasswordResetConfirm,
                                      session: AsyncSession = Depends(get_session)):
    return await password_reset_confirm(data, session)


@router.post("/signup", response_model=UserRead)
async def sign_up(user: UserIn,
                  background_tasks: BackgroundTasks,
                  session: AsyncSession = Depends(get_session),
                  host: str = Header(None)) -> UserRead:
    try:
        new_user = await create_new_user(user=user,
                                         session=session,
                                         background_tasks=background_tasks,
                                         host=host,
                                         source='signup')
        await send_telegramm(create_new_user_message('signup', new_user))
        return new_user
    except IntegrityError as er:
        logger.error(er)
        if "users_email_key" in str(er):
            raise HTTPException(status_code=400, detail="A user with this email already exists")
        raise HTTPException(status_code=503, detail={"action": "signup", "error": f"Database error: {er}"})
    except Exception as er:
        logger.error(er, exc_info=True)
        raise HTTPException(status_code=500, detail={"action": "signup", "error": str(er)})
