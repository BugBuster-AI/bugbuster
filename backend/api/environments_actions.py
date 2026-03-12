
from typing import List

from fastapi import HTTPException
from fastapi.responses import JSONResponse
from pydantic import UUID4
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from config import logger
from db.models import Environment, Project, User, ProjectUser
from schemas import EnvironmentCreate, EnvironmentRead, EnvironmentUpdate, Resolution


async def create_new_environment(environment: EnvironmentCreate,
                                 user: User,
                                 session: AsyncSession) -> EnvironmentRead:
    try:
        async with session.begin():
            query = (
                select(Environment)
                .join(ProjectUser, and_(ProjectUser.project_id == Environment.project_id,
                                        ProjectUser.workspace_id == user.active_workspace_id,
                                        ProjectUser.user_id == user.user_id))
                .where(Environment.title == environment.title,
                       Environment.project_id == environment.project_id)
            )
            result = await session.execute(query)
            result = result.scalars().one_or_none()

            if result:
                raise HTTPException(status_code=400, detail="Environment with this title already exists for the project")

            query = (
                select(ProjectUser.user_id, ProjectUser.project_id)
                .where(ProjectUser.project_id == environment.project_id,
                       ProjectUser.workspace_id == user.active_workspace_id,
                       ProjectUser.user_id == user.user_id)
            )

            result = await session.execute(query)
            result = result.unique().one_or_none()

            if not result:
                raise HTTPException(status_code=404, detail="Project not found or not authorized to create env in this project")

            new_environment = Environment(title=environment.title,
                                          description=environment.description,
                                          browser=environment.browser,
                                          operation_system=environment.operation_system,
                                          resolution=environment.resolution.model_dump(),
                                          project_id=environment.project_id,
                                          retry_enabled=environment.retry_enabled,
                                          retry_timeout=environment.retry_timeout
                                          )

            session.add(new_environment)
            await session.flush()
            await session.refresh(new_environment)

            return EnvironmentRead.model_validate(new_environment)

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(e, exc_info=True)
        mess = {"status": "error", "message": f"Error: {e}"}
        raise HTTPException(400, mess)


async def environments_by_id(environment_id: UUID4,
                             user: User,
                             session: AsyncSession) -> EnvironmentRead:
    try:
        async with session.begin():
            environment_query = (
                select(Environment)
                .join(ProjectUser, and_(Environment.project_id == ProjectUser.project_id,
                                        ProjectUser.user_id == user.user_id,
                                        ProjectUser.workspace_id == user.active_workspace_id))
                .where(Environment.environment_id == environment_id)
            )

            environment_results = await session.execute(environment_query)
            environment = environment_results.scalars().one_or_none()

            if not environment:
                return []
            return EnvironmentRead.model_validate(environment)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(e, exc_info=True)
        mess = {"status": "error", "message": f"Error: {e}"}
        raise HTTPException(400, mess)


async def list_environments(project_id: UUID4,
                            user: User,
                            session: AsyncSession) -> List:
    try:
        async with session.begin():
            environment_query = (
                select(Environment)
                .join(ProjectUser, and_(Environment.project_id == ProjectUser.project_id,
                                        ProjectUser.project_id == project_id,
                                        ProjectUser.user_id == user.user_id,
                                        ProjectUser.workspace_id == user.active_workspace_id))
            )
            environment_results = await session.execute(environment_query)
            list_environments = environment_results.scalars().unique().all()

            if not list_environments:
                return []
            return [EnvironmentRead.model_validate(environment) for environment in list_environments]
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(e, exc_info=True)
        mess = {"status": "error", "message": f"Error: {e}"}
        raise HTTPException(400, mess)


async def update_existing_environment(environment_id: UUID4,
                                      environment_update: EnvironmentUpdate,
                                      user: User,
                                      session: AsyncSession) -> EnvironmentRead:
    try:
        async with session.begin():
            query = (
                select(Environment)
                .join(ProjectUser, and_(Environment.project_id == ProjectUser.project_id,
                                        ProjectUser.user_id == user.user_id,
                                        ProjectUser.workspace_id == user.active_workspace_id))
                .where(Environment.environment_id == environment_id)
                )

            result = await session.execute(query)
            environment = result.scalars().one_or_none()

            if not environment:
                raise HTTPException(status_code=404, detail="environment not found or not authorized")

            if environment_update.title:
                # Проверка уникальности в рамках проекта
                title_check_query = (
                    select(Environment)
                    .where(Environment.title == environment_update.title,
                           Environment.project_id == environment.project_id,
                           Environment.environment_id != environment_id)
                )
                title_check_result = await session.execute(title_check_query)
                conflicting_environment = title_check_result.scalars().one_or_none()
                if conflicting_environment:
                    raise HTTPException(status_code=400, detail="Another environment with this title already exists in the project")

                environment.title = environment_update.title

            update_data = environment_update.model_dump(exclude_unset=True)
            if "description" in update_data:
                environment.description = environment_update.description
            if environment_update.browser:
                environment.browser = environment_update.browser
            if environment_update.operation_system:
                environment.operation_system = environment_update.operation_system
            if environment_update.resolution:
                environment.resolution = environment_update.resolution.model_dump()
            if "retry_enabled" in update_data:
                environment.retry_enabled = environment_update.retry_enabled
            if "retry_timeout" in update_data:
                environment.retry_timeout = environment_update.retry_timeout
            await session.flush()
            await session.refresh(environment)

            return EnvironmentRead.model_validate(environment)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(e, exc_info=True)
        mess = {"status": "error", "message": f"Error: {e}"}
        raise HTTPException(400, mess)


async def delete_existing_environments(environment_id: UUID4,
                                       user: User,
                                       session: AsyncSession) -> JSONResponse:
    try:
        async with session.begin():

            query = (
                select(Environment)
                .join(ProjectUser, and_(Environment.project_id == ProjectUser.project_id,
                                        ProjectUser.user_id == user.user_id,
                                        ProjectUser.workspace_id == user.active_workspace_id))
                .where(Environment.environment_id == environment_id)
                )

            result = await session.execute(query)
            environment = result.scalars().one_or_none()

            if not environment:
                return JSONResponse(content={"status": "not found or not authorized to delete this environment"})

            await session.delete(environment)
            return JSONResponse(content={"status": "OK"})

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(e, exc_info=True)
        mess = {"status": "error", "message": f"Error: {e}"}
        raise HTTPException(400, mess)
