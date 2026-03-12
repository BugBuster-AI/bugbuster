
import asyncio
import time
import uuid
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode, urlparse, urlunparse

import urllib3
from fastapi import BackgroundTasks, HTTPException
from fastapi.responses import JSONResponse
from jose import JWTError
from minio import Minio
from pydantic import UUID4
from sqlalchemy import (and_, delete, desc, func, insert, or_, over, select,
                        update)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased, selectinload

from api.actions import update_usage_count, usage_summary
from config import (DOMAIN, MINIO_ACCESS_KEY, MINIO_HOST, MINIO_PORT,
                    MINIO_PUBLIC_URL, MINIO_SECRET_KEY, MINIO_SECURE,
                    MINIO_USE_INTERNAL_PROXY, SECRET_KEY_INVITING, logger)
from db.models import (LogEntry, Project, ProjectUser, User, Workspace,
                       WorkspaceMembership)
from db.session import async_session
from dependencies.auth import (create_invitation_token, create_new_user,
                               create_password_reset_token, decode_token,
                               extract_user_id, extract_workspace_id)
from schemas import (EditUserWorkspace, InviteUserRequest, Roles, UserIn,
                     WorkspaceMembershipStatusEnum)
from utils import (create_new_user_message, generate_presigned_url,
                   select_language, select_minio_host, send_email_async,
                   send_telegramm)
from workers.user_logs import endpoint_names


async def get_workspace_memberships(current_user: User,
                                    session: AsyncSession,
                                    host: str = None,
                                    role_filter: str = None,
                                    status_filter: str = None,
                                    role_title_filter: str = None,
                                    last_action_filter_start_dt: datetime = None,
                                    last_action_filter_end_dt: datetime = None,
                                    limit: int = 10,
                                    offset: int = 0):
    try:
        st = time.perf_counter()

        # workspace один к однму, поэтому отдельный запрос
        workspace_query = select(Workspace.name, Workspace.owner_id).where(
            Workspace.workspace_id == current_user.active_workspace_id
        )
        workspace_result = await session.execute(workspace_query)
        workspace_name, workspace_owner_id = workspace_result.one_or_none()

        usage = await usage_summary(current_user.active_workspace_id, session, 'invite_user_workspace')

        # Prepare filters
        filters = [WorkspaceMembership.workspace_id == current_user.active_workspace_id]
        if role_filter:
            filters.append(WorkspaceMembership.role == role_filter)
        if status_filter:
            filters.append(WorkspaceMembership.status == status_filter)
        if role_title_filter:
            filters.append(WorkspaceMembership.role_title == role_title_filter)
        if last_action_filter_start_dt:
            filters.append(WorkspaceMembership.last_action_date >= last_action_filter_start_dt)
        if last_action_filter_end_dt:
            filters.append(WorkspaceMembership.last_action_date <= last_action_filter_end_dt)

        project_ids_subquery = select(ProjectUser.project_id).where(
            ProjectUser.user_id == current_user.user_id,
            ProjectUser.workspace_id == current_user.active_workspace_id
        )
        user_project_ids = (await session.execute(project_ids_subquery)).scalars().all()

        # Role specific queries
        if current_user.role == Roles.ROLE_ADMIN.value:
            base_query = select(WorkspaceMembership.id).where(and_(*filters))

        elif current_user.role == Roles.ROLE_MEMBER.value:

            base_query = (
                select(WorkspaceMembership.id)
                .where(
                    WorkspaceMembership.workspace_id == current_user.active_workspace_id,
                    WorkspaceMembership.status == WorkspaceMembershipStatusEnum.ACTIVE.value
                )
                .join(ProjectUser,
                      and_(ProjectUser.user_id == WorkspaceMembership.user_id,
                           ProjectUser.workspace_id == WorkspaceMembership.workspace_id,
                           ProjectUser.project_id.in_(user_project_ids)
                           ))
                .group_by(WorkspaceMembership.id)
                .order_by(WorkspaceMembership.last_action_date.desc())
            )

        elif current_user.role == Roles.ROLE_READ_ONLY.value:
            base_query = select(WorkspaceMembership.id).where(
                WorkspaceMembership.workspace_id == current_user.active_workspace_id,
                WorkspaceMembership.status == WorkspaceMembershipStatusEnum.ACTIVE.value,
                or_(
                    WorkspaceMembership.role == Roles.ROLE_ADMIN.value,
                    WorkspaceMembership.user_id == current_user.user_id
                )
            )

        else:
            raise HTTPException(status_code=403, detail="Invalid role")

        # Total count query
        count_query = select(func.count().label('total')).select_from(base_query.subquery())
        total_result = await session.execute(count_query)
        total = total_result.scalar()

        # Subquery for fast filtering
        subquery = base_query.order_by(desc(WorkspaceMembership.last_action_date)).limit(limit).offset(offset)
        aliased_subquery = subquery.alias("fast_filter")

        # Main query execution with join
        main_query = (
            select(WorkspaceMembership, Project.project_id, Project.name)
            .join(ProjectUser, and_(
                WorkspaceMembership.user_id == ProjectUser.user_id,
                WorkspaceMembership.workspace_id == ProjectUser.workspace_id
            ))
            .join(Project, and_(
                Project.project_id == ProjectUser.project_id,
                WorkspaceMembership.workspace_id == ProjectUser.workspace_id,
                ProjectUser.project_id.in_(user_project_ids)
            ))
            .join(aliased_subquery, WorkspaceMembership.id == aliased_subquery.c.id)
            .order_by(desc(WorkspaceMembership.last_action_date))
        )
        results = await session.execute(main_query)
        memberships_with_projects = results.fetchall()

        et = time.perf_counter()
        logger.info(f"Query get_workspace_memberships: {(et - st):.4f} seconds")

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
        # Process results
        response_data = {}
        for membership, project_id, project_name in memberships_with_projects:
            if membership.user_id not in response_data:
                avatar_url = None
                if membership.avatar:
                    avatar_url = await asyncio.to_thread(
                        generate_presigned_url,
                        membership.avatar.get('bucket', ''),
                        membership.avatar.get('file', ''),
                        host,
                        minio_client
                    )

                response_data[membership.user_id] = {
                    "workspace_id": str(membership.workspace_id),
                    "user_id": str(membership.user_id),
                    "first_name": membership.first_name,
                    "last_name": membership.last_name,
                    "email": membership.email,
                    "avatar_url": avatar_url,
                    "role": membership.role,
                    "role_title": membership.role_title,
                    "status": membership.status,
                    "last_action_date": membership.last_action_date,
                    "workspace_name": workspace_name,
                    "workspace_owner": workspace_owner_id,
                    "projects": set()
                }

            if project_id:
                response_data[membership.user_id]["projects"].add((str(project_id), project_name))

        final_data = [
            dict(item, projects=[{"project_id": pid, "project_name": pname} for pid, pname in item["projects"]])
            for item in response_data.values()
        ]
        total_pages = (total - 1) // limit + 1
        current_page = (offset // limit) + 1

        return {
            "total": total,
            "total_current_page": len(final_data),
            "page": current_page,
            "size": limit,
            "pages": total_pages,
            "limit": limit,
            "offset": offset,
            "workspace_limits": usage,
            "items": final_data
        }

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(e, exc_info=True)
        mess = {"status": "error", "message": f"Error: {e}"}
        raise HTTPException(400, mess)


async def workspace_log(current_user: User,
                        session: AsyncSession,
                        host: str = None,
                        user_email: str = None,
                        start_dt: datetime = None,
                        end_dt: datetime = None,
                        limit: int = 10,
                        offset: int = 0):
    try:
        async with session.begin():

            count_query = select(func.count(LogEntry.id)).where(LogEntry.workspace_id == current_user.active_workspace_id)

            # админ видит по всем в workspace, остальные по себе
            if current_user.role != Roles.ROLE_ADMIN.value:
                count_query = count_query.where(LogEntry.user_id == current_user.user_id)

            if start_dt:
                count_query = count_query.where(LogEntry.timestamp >= start_dt)
            if end_dt:
                count_query = count_query.where(LogEntry.timestamp <= end_dt)
            if user_email:
                count_query = count_query.where(LogEntry.user_email == user_email)

            st = time.perf_counter()
            total_result = await session.execute(count_query)
            total = total_result.scalar()

            et = time.perf_counter()
            logger.info(f"Query get count workspace_log: {(et - st):.4f} seconds")

            subquery = select(LogEntry.id).where(LogEntry.workspace_id == current_user.active_workspace_id)

            if current_user.role != Roles.ROLE_ADMIN.value:
                subquery = subquery.where(LogEntry.user_id == current_user.user_id)
            if start_dt:
                subquery = subquery.where(LogEntry.timestamp >= start_dt)
            if end_dt:
                subquery = subquery.where(LogEntry.timestamp <= end_dt)
            if user_email:
                subquery = subquery.where(LogEntry.user_email == user_email)

            subquery = subquery.order_by(desc(LogEntry.timestamp)).limit(limit).offset(offset)
            aliased_subquery = subquery.alias("fast_filter")

            query = select(LogEntry).join(aliased_subquery, LogEntry.id == aliased_subquery.c.id).order_by(desc(LogEntry.timestamp))

            st = time.perf_counter()
            res = await session.execute(query)
            logs = res.scalars().all()
            et = time.perf_counter()
            logger.info(f"Query get all workspace_log: {(et - st):.4f} seconds")

            result = []
            language = select_language(host)
            for log in logs:
                endpoint_name = endpoint_names.get((log.method, log.endpoint_path), {}).get(language, log.endpoint_path)
                result.append({
                    "id": log.id,
                    "timestamp": log.timestamp,
                    "user_id ": log.user_id,
                    "user_email": log.user_email,
                    "user_username": log.user_username,
                    "workspace_id": log.workspace_id,
                    "method": log.method,
                    "endpoint_path": log.endpoint_path,
                    "endpoint_name": endpoint_name,
                    "status_code": log.status_code,
                    "params": log.user_params
                })

            total_pages = (total - 1) // limit + 1
            current_page = (offset // limit) + 1

            pagination_info = {
                "total": total,
                "total_current_page": len(logs),
                "page": current_page,
                "size": limit,
                "pages": total_pages,
                "limit": limit,
                "offset": offset,
                "items": result
            }

            return pagination_info
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(e, exc_info=True)
        mess = {"status": "error", "message": f"Error: {e}"}
        raise HTTPException(400, mess)


async def accept_invite(token: str, session: AsyncSession):
    try:
        async with session.begin():
            payload = decode_token(token, SECRET_KEY_INVITING)
            user_id = extract_user_id(payload)
            workspace_id = extract_workspace_id(payload)

            res = await session.execute(select(WorkspaceMembership).where(
                WorkspaceMembership.workspace_id == workspace_id,
                WorkspaceMembership.user_id == user_id,
                WorkspaceMembership.status == WorkspaceMembershipStatusEnum.INVITED.value
            ))
            membership = res.scalar_one_or_none()
            if not membership:
                raise HTTPException(status_code=404, detail="User or Invite not found")

            membership.status = WorkspaceMembershipStatusEnum.ACTIVE.value
            membership.last_action_date = datetime.now(timezone.utc)
            await session.flush()
            await session.refresh(membership)

            return {"detail": "User invited successfully"}
    except JWTError:
        raise HTTPException(status_code=400, detail="Invalid token")
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(e, exc_info=True)
        mess = {"status": "error", "message": f"Error: {e}"}
        raise HTTPException(400, mess)


async def invite_user(user: User, invite: InviteUserRequest,
                      session: AsyncSession, owner: User, invitation_link: str = None):

    res = await session.execute(
        select(WorkspaceMembership)
        .where(WorkspaceMembership.workspace_id == owner.active_workspace_id,
               WorkspaceMembership.user_id == user.user_id))

    membership = res.scalars().one_or_none()
    if membership:
        if membership == WorkspaceMembershipStatusEnum.ACTIVE.value:
            raise HTTPException(status_code=400, detail="User is already invited.")
        else:
            # уже в инвайте, письмо повторное шлем, запись не делаем
            # Обновляем ссылку при повторном приглашении

            membership.first_name = invite.first_name
            membership.last_name = invite.last_name
            membership.role = invite.role
            membership.role_title = invite.role_title
            membership.invitation_link = invitation_link
            membership.last_action_date = datetime.now(timezone.utc)
            await session.flush()
            return

    new_membership = WorkspaceMembership(
        workspace_id=owner.active_workspace_id,
        user_id=user.user_id,
        first_name=invite.first_name,
        last_name=invite.last_name,
        email=invite.email,
        role=invite.role,
        role_title=invite.role_title,
        status="Invited",
        invitation_link=invitation_link,
        last_action_date=datetime.now(timezone.utc)
    )
    session.add(new_membership)


async def list_user_workspace(current_user: User, session: AsyncSession):
    try:
        async with session.begin():
            result = await session.execute(
                select(WorkspaceMembership, Workspace)
                .join(Workspace, Workspace.workspace_id == WorkspaceMembership.workspace_id)
                .where(
                    WorkspaceMembership.user_id == current_user.user_id,
                    WorkspaceMembership.status == WorkspaceMembershipStatusEnum.ACTIVE.value
                )
            )

            rows = result.fetchall()

            result_list = []
            for membership, workspace in rows:
                result_list.append({
                    "workspace_id": membership.workspace_id,
                    "workspace_name": workspace.name,
                    "owner": workspace.owner_id,
                    "role": membership.role,
                    "role_title": membership.role_title
                })

            return result_list

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(e, exc_info=True)
        mess = {"status": "error", "message": f"Error: {e}"}
        raise HTTPException(400, mess)


async def user_workspace_by_id(workspace_id: UUID4,
                               current_user: User,
                               session: AsyncSession):
    try:
        async with session.begin():
            result = await session.execute(
                select(WorkspaceMembership, Workspace)
                .join(Workspace, Workspace.workspace_id == WorkspaceMembership.workspace_id)
                .where(
                    WorkspaceMembership.user_id == current_user.user_id,
                    WorkspaceMembership.status == WorkspaceMembershipStatusEnum.ACTIVE.value,
                    WorkspaceMembership.workspace_id == workspace_id
                )
            )

            rows = result.fetchall()

            result_list = []
            for membership, workspace in rows:
                result_list.append({
                    "workspace_id": membership.workspace_id,
                    "workspace_name": workspace.name,
                    "workspace_tariff_id": workspace.tariff_id,
                    "workspace_tariff_expiration": workspace.tariff_expiration,
                    "workspace_tariff_start_date": workspace.tariff_start_date,
                    "workspace_status": workspace.status,
                    "owner": workspace.owner_id,
                    "role": membership.role,
                    "role_title": membership.role_title
                })

            return result_list

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(e, exc_info=True)
        mess = {"status": "error", "message": f"Error: {e}"}
        raise HTTPException(400, mess)


async def change_user_workspace(workspace_id: UUID4,
                                current_user: User,
                                session: AsyncSession):
    try:
        async with session.begin():

            result = await session.execute(select(User)
                                           .join(WorkspaceMembership, and_(WorkspaceMembership.user_id == User.user_id,
                                                                           WorkspaceMembership.workspace_id == workspace_id,
                                                                           WorkspaceMembership.status == WorkspaceMembershipStatusEnum.ACTIVE.value))
                                           .where(User.user_id == current_user.user_id,
                                                  User.is_active == True))
            user = result.scalars().first()
            if not user:
                raise HTTPException(status_code=403, detail="You do not have this workspace")

            user.active_workspace_id = workspace_id
            await session.flush()
            await session.refresh(user)
            return JSONResponse(content={"status": "OK"})

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(e, exc_info=True)
        mess = {"status": "error", "message": f"Error: {e}"}
        raise HTTPException(400, mess)


async def change_user_workspace_name(new_name: str,
                                     current_user: User,
                                     session: AsyncSession):
    try:
        async with session.begin():

            result = await session.execute(select(Workspace)
                                           .where(Workspace.owner_id == current_user.user_id))
            workspace = result.scalars().first()
            if not workspace:
                raise HTTPException(status_code=403, detail="You do not have this workspace")

            workspace.name = new_name
            await session.flush()
            await session.refresh(workspace)
            return JSONResponse(content={"status": "OK"})

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(e, exc_info=True)
        mess = {"status": "error", "message": f"Error: {e}"}
        raise HTTPException(400, mess)


async def change_user_avatar_workspace(avatar: dict,
                                       current_user: User,
                                       session: AsyncSession):
    try:
        async with session.begin():

            if not isinstance(avatar, dict) or \
               not avatar.get('bucket') or \
               not avatar.get('file'):
                raise HTTPException(status_code=403, detail="No valid format attach")

            result = await session.execute(select(WorkspaceMembership)
                                           .where(WorkspaceMembership.user_id == current_user.user_id,
                                                  WorkspaceMembership.workspace_id == current_user.active_workspace_id,
                                                  WorkspaceMembership.status == WorkspaceMembershipStatusEnum.ACTIVE.value))

            membership = result.scalars().first()
            if not membership:
                raise HTTPException(status_code=403, detail="You do not have this workspace")

            membership.avatar = avatar
            await session.flush()
            await session.refresh(membership)
            return JSONResponse(content={"status": "OK"})

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(e, exc_info=True)
        mess = {"status": "error", "message": f"Error: {e}"}
        raise HTTPException(400, mess)


async def edit_user_workspace(edit_membership: EditUserWorkspace,
                              current_user: User,
                              session: AsyncSession):

    try:
        async with session.begin():
            if not current_user.role == Roles.ROLE_ADMIN.value:
                raise HTTPException(status_code=403, detail="You do not have permission to invite users.")

            if (edit_membership.project_ids is None or len(edit_membership.project_ids) == 0) and \
                    (edit_membership.role is None or edit_membership.role != Roles.ROLE_ADMIN.value):
                raise HTTPException(status_code=403, detail="Empty project_ids with new role!")

            if current_user.email == edit_membership.email:
                raise HTTPException(status_code=403, detail="You can't edit yourself from the workspace.")

            # если даем админа, то даем все проекты
            if edit_membership.role == Roles.ROLE_ADMIN.value:
                stmt = select(ProjectUser.project_id).where(
                    and_(
                        ProjectUser.user_id == current_user.user_id,
                        ProjectUser.workspace_id == current_user.active_workspace_id,
                        ProjectUser.role == Roles.ROLE_ADMIN.value
                    )
                ).distinct()

                result = await session.execute(stmt)
                project_ids = [row[0] for row in result.fetchall()]
                edit_membership.project_ids = project_ids

            elif edit_membership.project_ids and len(edit_membership.project_ids) > 0 and edit_membership.role != Roles.ROLE_ADMIN.value:
                # все project_id из списка принадлежат текущему пользователю как "Admin"
                stmt = select(ProjectUser.project_id).where(
                    and_(
                        ProjectUser.user_id == current_user.user_id,
                        ProjectUser.workspace_id == current_user.active_workspace_id,
                        ProjectUser.role == Roles.ROLE_ADMIN.value,
                        ProjectUser.project_id.in_(edit_membership.project_ids)
                    )
                ).distinct()
                result = await session.execute(stmt)
                allowed_project_ids = {row[0] for row in result.fetchall()}  # множество разрешенных project_id

                if not set(edit_membership.project_ids).issubset(allowed_project_ids):
                    raise HTTPException(status_code=403, detail="You do not have permission to add users to some projects")

            # есть ли кандидат в системе
            existing_user_query = select(User).where(User.email == edit_membership.email)
            existing_user_result = await session.execute(existing_user_query)
            existing_user = existing_user_result.scalar_one_or_none()

            if not existing_user:
                raise HTTPException(status_code=404, detail="User not found")

            res = await session.execute(select(WorkspaceMembership).where(
                WorkspaceMembership.workspace_id == current_user.active_workspace_id,
                WorkspaceMembership.user_id == existing_user.user_id,
                WorkspaceMembership.status == WorkspaceMembershipStatusEnum.ACTIVE.value
            ))
            membership = res.scalars().one_or_none()
            if not membership:
                raise HTTPException(status_code=400, detail="User not found or not active")

            if edit_membership.first_name is not None:
                membership.first_name = edit_membership.first_name
            if edit_membership.last_name is not None:
                membership.last_name = edit_membership.last_name
            if edit_membership.role is not None:
                membership.role = edit_membership.role
            if edit_membership.role_title is not None:
                membership.role_title = edit_membership.role_title

            await session.flush()
            await session.refresh(membership)

            if edit_membership.project_ids and len(edit_membership.project_ids) > 0:
                await session.execute(
                    delete(ProjectUser).where(
                        ProjectUser.workspace_id == current_user.active_workspace_id,
                        ProjectUser.user_id == existing_user.user_id
                    )
                )
                await session.flush()

                for project_id in edit_membership.project_ids:
                    new_project_user = ProjectUser(project_id=project_id,
                                                   workspace_id=current_user.active_workspace_id,
                                                   user_id=existing_user.user_id,
                                                   role=membership.role)  # если будет под каждый проект своя, переделать

                    session.add(new_project_user)
                await session.flush()

            return JSONResponse(content={"status": "OK"})
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(e, exc_info=True)
        mess = {"status": "error", "message": f"Error: {e}"}
        raise HTTPException(400, mess)


async def remove_user_workspace(email: str,
                                current_user: User,
                                session: AsyncSession):

    try:
        async with session.begin():
            if not current_user.role == Roles.ROLE_ADMIN.value:
                raise HTTPException(status_code=403, detail="You do not have permission to invite users.")

            if current_user.email == email:
                raise HTTPException(status_code=403, detail="You can't remove yourself from the workspace.")

            existing_user_query = select(User).where(User.email == email)
            existing_user_result = await session.execute(existing_user_query)
            existing_user = existing_user_result.scalar_one_or_none()

            if not existing_user:
                raise HTTPException(status_code=404, detail="User not found")

            await session.execute(
                delete(WorkspaceMembership).where(
                    WorkspaceMembership.workspace_id == current_user.active_workspace_id,
                    WorkspaceMembership.user_id == existing_user.user_id
                )
            )
            await session.flush()

            await session.execute(
                delete(ProjectUser).where(
                    ProjectUser.workspace_id == current_user.active_workspace_id,
                    ProjectUser.user_id == existing_user.user_id
                )
            )
            await session.flush()

            # вернуть юзера в его базовый workspace

            base_workspace_query = select(Workspace).where(Workspace.owner_id == existing_user.user_id)
            base_workspace_result = await session.execute(base_workspace_query)
            base_workspace_user = base_workspace_result.scalar_one_or_none()
            existing_user.active_workspace_id = base_workspace_user.workspace_id

            return JSONResponse(content={"status": "OK"})
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(e, exc_info=True)
        mess = {"status": "error", "message": f"Error: {e}"}
        raise HTTPException(400, mess)


async def invite_user_workspace(invite: InviteUserRequest,
                                background_tasks: BackgroundTasks,
                                current_user: User,
                                session: AsyncSession,
                                host: str = None):

    try:
        async with session.begin():
            if not current_user.role == Roles.ROLE_ADMIN.value:
                raise HTTPException(status_code=403, detail="You do not have permission to invite users.")

            if (invite.project_ids is None or len(invite.project_ids) == 0) and \
                    (invite.role is None or invite.role != Roles.ROLE_ADMIN.value):
                raise HTTPException(status_code=403, detail="Empty project_ids with new role!")

            if current_user.email == invite.email:
                raise HTTPException(status_code=403, detail="You can't invite yourself.")

            # если даем админа, то даем все проекты
            if invite.role == Roles.ROLE_ADMIN.value:
                stmt = select(ProjectUser.project_id).where(
                    and_(
                        ProjectUser.user_id == current_user.user_id,
                        ProjectUser.workspace_id == current_user.active_workspace_id,
                        ProjectUser.role == Roles.ROLE_ADMIN.value
                    )
                ).distinct()

                result = await session.execute(stmt)
                project_ids = [row[0] for row in result.fetchall()]
                invite.project_ids = project_ids
            else:
                if invite.project_ids is None:
                    raise HTTPException(status_code=403, detail="project_ids empty!")

                # все project_id из списка принадлежат текущему пользователю как "Admin"
                stmt = select(ProjectUser.project_id).where(
                    and_(
                        ProjectUser.user_id == current_user.user_id,
                        ProjectUser.workspace_id == current_user.active_workspace_id,
                        ProjectUser.role == Roles.ROLE_ADMIN.value,
                        ProjectUser.project_id.in_(invite.project_ids)
                    )
                ).distinct()

                result = await session.execute(stmt)
                allowed_project_ids = {row[0] for row in result.fetchall()}  # множество разрешенных project_id

                if not set(invite.project_ids).issubset(allowed_project_ids):
                    raise HTTPException(status_code=403, detail="You do not have permission to add users to some projects")

            # есть ли кандидат в системе
            existing_user_query = select(User).where(User.email == invite.email)
            existing_user_result = await session.execute(existing_user_query)
            existing_user = existing_user_result.scalar_one_or_none()

            # workspace name
            existing_workspace_query = select(Workspace.name).where(Workspace.owner_id == current_user.user_id)
            existing_workspace_result = await session.execute(existing_workspace_query)
            existing_workspace = existing_workspace_result.scalar_one_or_none()

            if existing_user:

                activate_member_token = create_invitation_token(str(existing_user.user_id),
                                                                str(current_user.active_workspace_id),
                                                                timedelta(weeks=1))
                invitation_link = f"{DOMAIN}/accept-invite?token={activate_member_token}"
                print(invitation_link)
                await invite_user(existing_user, invite, session, current_user, invitation_link)
                background_tasks.add_task(send_email_async,
                                          email=invite.email,
                                          template_type="invite",
                                          variables={"username_owner": current_user.username,
                                                     "workspace_name": existing_workspace,
                                                     "token": activate_member_token},
                                          host=host)
                reset_link = ""
            else:
                password = uuid.uuid4().hex[:8]
                user_in = UserIn(username=invite.last_name,
                                 email=invite.email,
                                 password=password)

                new_user = await create_new_user(user=user_in,
                                                 session=session,
                                                 background_tasks=background_tasks,
                                                 host=host,
                                                 source=f'invite from {current_user.email}')

                reset_token = create_password_reset_token(new_user.email, timedelta(hours=24))
                reset_link = f"{DOMAIN}/reset-password?token={reset_token}"

                await send_telegramm(create_new_user_message(f'invite from {current_user.email}',
                                                             new_user))

                activate_member_token = create_invitation_token(str(new_user.user_id),
                                                                str(current_user.active_workspace_id),
                                                                timedelta(weeks=1))
                invitation_link = f"{DOMAIN}/accept-invite?token={activate_member_token}"
                print(invitation_link)
                await invite_user(new_user, invite, session, current_user, invitation_link)
                background_tasks.add_task(send_email_async,
                                          email=invite.email,
                                          template_type="invite",
                                          variables={"username_owner": current_user.username,
                                                     "workspace_name": existing_workspace,
                                                     "token": activate_member_token},
                                          host=host)
            await session.execute(
                delete(ProjectUser).where(
                    ProjectUser.workspace_id == current_user.active_workspace_id,
                    ProjectUser.user_id == (existing_user.user_id if existing_user else new_user.user_id)
                )
            )
            await session.flush()

            for project_id in invite.project_ids:
                new_project_user = ProjectUser(project_id=project_id,
                                               workspace_id=current_user.active_workspace_id,
                                               user_id=existing_user.user_id if existing_user else new_user.user_id,
                                               role=invite.role)
                session.add(new_project_user)
            await session.flush()

            await update_usage_count(current_user.active_workspace_id, "invite_user_workspace", 1)
            res = {"status": "OK",
                   "link": invitation_link,
                   "reset_link": reset_link}
            logger.info(res)
            return JSONResponse(content=res)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(e, exc_info=True)
        mess = {"status": "error", "message": f"Error: {e}"}
        raise HTTPException(400, mess)
