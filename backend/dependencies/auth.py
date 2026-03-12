import hashlib
import hmac
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, Literal, Optional

from fastapi import BackgroundTasks, Depends, HTTPException, Request, status
from fastapi.openapi.models import OAuthFlows as OAuthFlowsModel
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import UUID4
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.flag_catalog_actions import init_user_flags
from api.variables_actions import add_default_variables_kit
from config import (MAX_CONCURRENT_TASKS_DEFAULT, REDIS_PREFIX, SECRET_KEY,
                    SECRET_KEY_API, SECRET_KEY_INVITING, TOKEN_HASH_SECRET, DOMAIN,
                    logger, redis_client)
from db.models import (Case, Project, ProjectUser, Role, Suite, TariffLimits,
                       Tariffs, Templates, User, UserToken, Workspace,
                       WorkspaceMembership)
from db.session import async_session, transaction_scope
from schemas import (Lang, PasswordResetConfirm, Roles, UserIn, UserRead,
                     WorkspaceMembershipStatusEnum, WorkspaceStatusEnum)
from utils import async_request, select_language, send_email_async

ALGORITHM = "HS256"

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def token_hmac(token: str) -> str:
    return hmac.new(
        TOKEN_HASH_SECRET.encode("utf-8"),
        msg=token.encode("utf-8"),
        digestmod=hashlib.sha256
    ).hexdigest()


class CustomOAuth2PasswordBearer(OAuth2):
    def __init__(
        self,
        tokenUrl: str,
        scheme_name: Optional[str] = None,
        scopes: Optional[Dict[str, str]] = None,
        description: Optional[str] = None,
        auto_error: bool = True,
    ):
        if not scopes:
            scopes = {}
        flows = OAuthFlowsModel(
            password={"tokenUrl": tokenUrl, "scopes": scopes}
        )
        super().__init__(
            flows=flows,
            scheme_name=scheme_name,
            description=description,
            auto_error=auto_error,
        )

    async def __call__(self, request: Request) -> Optional[str]:
        authorization = request.headers.get("Authorization")
        if authorization:
            # Always return the full authorization header
            # The prefix "Bearer " will not be stripped
            return authorization
        elif self.auto_error:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return None


oauth2_scheme = CustomOAuth2PasswordBearer(tokenUrl="/api/auth/signin", auto_error=False)


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


async def authenticate_user(username: str, password: str) -> (User | Literal[False]):

    async with async_session() as session:
        results = await session.execute(
            select(User)
            .where(User.email == username, User.is_active == True)
        )
        user = results.scalars().first()

        if not user:
            return False
        if not verify_password(password, user.password):
            return False
        return user


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_user_jwt_token(user_id: str,
                          expires_delta: Optional[timedelta] = None) -> str:

    to_encode = {"sub": user_id, "jti": str(uuid.uuid4())}

    # проверяем в БД
    # вечный токен только если не задан ``expires_delta``
    # if expires_delta:
    #     expire = datetime.now(timezone.utc) + expires_delta
    #     to_encode.update({"exp": expire})

    return jwt.encode(to_encode, SECRET_KEY_API, algorithm=ALGORITHM)


def create_invitation_token(user_id: str, workspace_id: str, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = {"sub": user_id, "workspace_id": workspace_id}
    # вечный токен только если не задан ``expires_delta``
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
        to_encode.update({"exp": expire})

    return jwt.encode(to_encode, SECRET_KEY_INVITING, algorithm=ALGORITHM)


def create_password_reset_token(email: str, expires_delta: Optional[timedelta] = None):
    to_encode = {"sub": email}
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
        to_encode.update({"exp": expire})
    else:
        expire = datetime.now(timezone.utc) + timedelta(hours=1)
        to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_token(token: str, secret: str) -> dict:
    try:
        return jwt.decode(token, secret, algorithms=[ALGORITHM])
    except JWTError as e:
        if 'Signature has expired' in str(e):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )


def extract_user_id(payload: dict) -> str:
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token did not contain a valid user identifier",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user_id


def extract_workspace_id(payload: dict) -> str:
    workspace_id = payload.get("workspace_id")
    if workspace_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token did not contain a valid user identifier",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return workspace_id


async def get_user_by_id(session: AsyncSession, user_id: str) -> User:
    result = await session.execute(select(User, WorkspaceMembership.role,
                                          WorkspaceMembership.avatar,
                                          Workspace.status,
                                          Workspace.max_concurrent_tasks,
                                          Workspace.tariff_expiration)
                                   .join(WorkspaceMembership, and_(WorkspaceMembership.workspace_id == User.active_workspace_id,
                                                                   WorkspaceMembership.user_id == user_id,
                                                                   WorkspaceMembership.status == 'Active'))
                                   .join(Workspace, and_(Workspace.workspace_id == User.active_workspace_id))
                                   .where(User.user_id == user_id, User.is_active == True))
    result = result.first()
    if not result:
        return None
    (user, role, avatar, workspace_status,
     workspace_max_concurrent_tasks,
     workspace_tariff_expiration) = result
    user.role = role
    user.avatar = avatar
    user.workspace_status = workspace_status
    user.max_concurrent_tasks = workspace_max_concurrent_tasks
    user.tariff_expiration = workspace_tariff_expiration

    return user


async def get_current_active_user_ws(token: str = Depends(oauth2_scheme)) -> User:
    if not token:
        raise HTTPException(status_code=401, detail="Invalid or missing authorization token")

    if token.startswith("Bearer "):
        token = token[7:]
        client_type = "web"
        secret_key = SECRET_KEY
    else:
        client_type = "api"
        secret_key = SECRET_KEY_API

    # if client_type == "api" and not api_endpoint:

    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail="This endpoint is available only for web clients."
    #     )
    payload = decode_token(token, secret_key)
    user_id = extract_user_id(payload)

    async with async_session() as session:
        if client_type == "web":
            user = await get_user_by_id(session, user_id)
        else:
            res = await session.execute(select(UserToken).where(UserToken.token == token,
                                                                UserToken.is_active == True))
            token_data = res.scalar_one_or_none()

            if not token_data:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid or inactive token"
                )

            user = await get_user_by_id(session, token_data.user_id)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found or not active this workspace",
        )
    logger.info(f"user: {user.email} | {user.user_id}")
    return user


async def get_current_active_user(request: Request, token: str = Depends(oauth2_scheme)) -> User:
    if not token:
        raise HTTPException(status_code=401, detail="Invalid or missing authorization token")

    if token.startswith("Bearer "):
        token = token[7:]
        client_type = "web"
        secret_key = SECRET_KEY
    else:
        client_type = "api"
        secret_key = SECRET_KEY_API

    # if client_type == "api" and not api_endpoint:

    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail="This endpoint is available only for web clients."
    #     )
    payload = decode_token(token, secret_key)
    user_id = extract_user_id(payload)

    async with async_session() as session:
        if client_type == "web":
            user = await get_user_by_id(session, user_id)
        else:
            digest = token_hmac(token)
            now = datetime.now(timezone.utc)

            res = await session.execute(
                select(UserToken).where(UserToken.user_id == user_id,
                                        UserToken.token_hash == digest,
                                        UserToken.is_active.is_(True),
                                        or_(UserToken.expires_at.is_(None),
                                            UserToken.expires_at > now))
            )
            token_data = res.scalar_one_or_none()

            if not token_data:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid, inactive or expired token"
                )

            user = await get_user_by_id(session, token_data.user_id)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found or not active this workspace",
        )
    logger.info(f"user: {user.email} | {user.user_id}")
    request.state.user = user
    return user


async def check_permissions(endpoint_name: str,
                            role: str,
                            workspace_status: str = WorkspaceStatusEnum.ACTIVE.value):

    # не передаем workspace_status там где можно чекать тарифы, оплачивать продление и тд
    if workspace_status != WorkspaceStatusEnum.ACTIVE.value:
        raise HTTPException(403, "Workspace is not active. Check your tariff")

    if not redis_client.exists(f"{REDIS_PREFIX}_permissions:{role}:{endpoint_name}"):
        raise HTTPException(403, "Unauthorized for this endpoint")


async def change_password(user: User, old_password: str, new_password: str, session: AsyncSession):
    async with session.begin():
        if not verify_password(old_password, user.password):
            raise HTTPException(status_code=400, detail="Old password is incorrect")

        user.password = get_password_hash(new_password)

        session.add(user)
        await session.flush()


async def send_password_reset_email(user: User,
                                    reset_token: str,
                                    background_tasks: BackgroundTasks,
                                    host: str = None):
    background_tasks.add_task(send_email_async,
                              email=user.email,
                              template_type="recovery",
                              variables={"reset_token": reset_token,
                                         "email": user.email,
                                         "username": user.username},
                              host=host)


async def password_reset_confirm(data: PasswordResetConfirm, session: AsyncSession):
    try:
        async with transaction_scope(session):
            payload = jwt.decode(data.token, SECRET_KEY, algorithms=[ALGORITHM])
            email = payload.get("sub")
            if not email:
                raise HTTPException(status_code=400, detail="Invalid token")
            result = await session.execute(select(User).where(User.email == email))
            user = result.scalar_one_or_none()

            if not user:
                raise HTTPException(status_code=404, detail="User not found")

            user.password = get_password_hash(data.new_password)
            session.add(user)
            await session.flush()
            return JSONResponse(content={"status": "OK"})
    except JWTError:
        raise HTTPException(status_code=400, detail="Invalid token")
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(e, exc_info=True)
        mess = {"status": "error", "message": f"Error: {e}"}
        raise HTTPException(400, mess)


async def generate_owner_reset_link(owner_email: str) -> str:

    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.email == owner_email)
        )
        user = result.scalar_one_or_none()

        if not user:
            raise RuntimeError(
                f"Owner user '{owner_email}' not found. Run init-owner first."
            )

        token = create_password_reset_token(user.email,
                                            expires_delta=timedelta(hours=24))

        return f"{DOMAIN}/reset-password?token={token}"


async def create_new_user(user: UserIn,
                          session: AsyncSession,
                          background_tasks: BackgroundTasks,
                          extra=None,
                          host=None,
                          tariff_name='corporate',
                          source='signup',
                          template_type="welcome") -> UserRead:

    # async with session.begin():
    async with transaction_scope(session):

        tariff_query = select(Tariffs).where(Tariffs.tariff_name == tariff_name)
        result = await session.execute(tariff_query)
        tariff = result.scalar_one_or_none()

        workspace_id = uuid.uuid4()

        new_user = User(email=user.email,
                        username=user.username,
                        password=get_password_hash(user.password),
                        is_active=True,
                        active_workspace_id=workspace_id,
                        extra=extra,
                        host=host,
                        source=source)

        session.add(new_user)
        await session.flush()

        new_workspace = Workspace(
            workspace_id=workspace_id,
            owner_id=new_user.user_id,
            name=user.email,
            tariff_id=tariff.tariff_id if tariff else None,
            tariff_expiration=datetime.now(timezone.utc) + timedelta(weeks=500 * tariff.cnt_months),
            tariff_start_date=datetime.now(timezone.utc),
            status=WorkspaceStatusEnum.ACTIVE.value
        )
        session.add(new_workspace)
        await session.flush()

        new_workspace_memberships = WorkspaceMembership(
            workspace_id=workspace_id,
            user_id=new_user.user_id,
            role=Roles.ROLE_ADMIN.value,
            role_title='QA Manager',
            status=WorkspaceMembershipStatusEnum.ACTIVE.value,
            email=user.email,
            last_action_date=datetime.now(timezone.utc)
        )
        session.add(new_workspace_memberships)
        await session.flush()

        max_concurrent_tasks = MAX_CONCURRENT_TASKS_DEFAULT
        if tariff:
            query = select(TariffLimits.limit_value).where(TariffLimits.tariff_id == tariff.tariff_id,
                                                           TariffLimits.feature_name == 'max_concurrent_tasks')
            result = await session.execute(query)
            limit_value = result.scalar_one_or_none()
            if limit_value is not None:
                max_concurrent_tasks = limit_value

        redis_client.set(f"{REDIS_PREFIX}_workspace_limit:{workspace_id}", max_concurrent_tasks)
        new_workspace.max_concurrent_tasks = max_concurrent_tasks
        await session.flush()

        # Попытка применить стартовый набор
        await add_start_kit_to_workspace(source, host, session,
                                         new_user, workspace_id,
                                         new_workspace_memberships.role,
                                         parallel_exec=1)

        # добавляем справочник с флагами (онбординги)
        await init_user_flags(new_user.user_id, session)

        background_tasks.add_task(send_email_async,
                                  email=new_user.email,
                                  template_type=template_type,
                                  variables={"username": new_user.username,
                                             "password": user.password,
                                             "email": new_user.email},
                                  host=host)
        await session.refresh(new_user)
        logger.info(f"new user successfully registered: {new_user.email} | {new_user.username}")
        return UserRead.model_validate(new_user)


async def get_user_by_email(email: str, session: AsyncSession) -> Optional[User]:
    async with transaction_scope(session):
        result = await session.execute(
            select(User).where(User.email == email)
        )
    return result.scalars().first()


async def add_start_kit_to_workspace(source: str,
                                     host: str,
                                     session: AsyncSession,
                                     new_user: User,
                                     workspace_id: UUID4,
                                     role: str,
                                     parallel_exec: int = 0):
    try:
        async with transaction_scope(session):
            if source != 'jira':
                lang = select_language(host)
                template_type = "start_kit_ru" if lang == Lang.RU.value else "start_kit_en"
                res = await session.execute(select(Templates).where(Templates.template_type == template_type))
                start_kit = res.scalar_one_or_none()

                if start_kit:
                    template_data = start_kit.template_data

                    # Проходимся по каждому проекту в шаблоне
                    for project in template_data:
                        new_project = Project(
                            name=project['name'],
                            description=project['description'],
                            user_id=new_user.user_id,
                            workspace_id=workspace_id,
                            parallel_exec=parallel_exec
                        )
                        session.add(new_project)
                        await session.flush()

                        new_project_user = ProjectUser(project_id=new_project.project_id,
                                                       workspace_id=workspace_id,
                                                       user_id=new_user.user_id,
                                                       role=role)
                        session.add(new_project_user)
                        await session.flush()

                        # для нового проекта нужно создать дефолтный справочник переменных
                        await add_default_variables_kit(new_project.project_id, new_user, session)

                        for idx, suite_data in enumerate(project['suites'], 1):
                            new_suite = Suite(
                                name=suite_data['name'],
                                description=suite_data['description'],
                                project=new_project,
                                position=idx
                            )
                            session.add(new_suite)
                            await session.flush()

                            # Проходимся по каждому кейсу
                            for idx, case_data in enumerate(suite_data['cases'], 1):
                                new_case = Case(
                                    name=case_data['name'],
                                    description=case_data['description'],
                                    context=case_data['context'],
                                    before_browser_start=case_data['before_browser_start'],
                                    before_steps=case_data['before_steps'],
                                    steps=case_data['steps'],
                                    after_steps=case_data['after_steps'],
                                    variables=case_data['variables'],
                                    environment_id=case_data['environment_id'],
                                    type=case_data['type'],
                                    status=case_data['status'],
                                    priority=case_data['priority'],
                                    url=case_data['url'],
                                    is_valid=case_data['is_valid'],
                                    validation_reason=case_data['validation_reason'],
                                    action_plan=case_data['action_plan'],
                                    suite=new_suite,
                                    project_id=new_project.project_id,
                                    position=idx
                                )
                                session.add(new_case)
                                await session.flush()
                    logger.info(f"success creating start_kit for user: {new_user.email}")
    except Exception as e:
        logger.warning(f"Error creating start_kit for user: {new_user.email} {str(e)}", exc_info=True)
