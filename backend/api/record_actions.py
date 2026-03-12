import asyncio
import time
from typing import Dict, List, Optional
from urllib.parse import urlencode, urlparse, urlunparse

import urllib3
from fastapi import HTTPException
from fastapi.responses import JSONResponse
from minio import Minio
from pydantic import UUID4
from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.actions import check_usage_limits
from config import (CLICKER_IP, CLICKER_PORT, MINIO_ACCESS_KEY, MINIO_HOST,
                    MINIO_PORT, MINIO_PUBLIC_URL, MINIO_SECRET_KEY,
                    MINIO_SECURE, logger, MINIO_USE_INTERNAL_PROXY)
from db.models import (HappyPass, ProjectUser, User, Workspace,
                       WorkspaceMembership)
from db.session import async_session
from schemas import Roles
from utils import async_request, generate_presigned_url, select_minio_host


async def check_user_workspace_recording_available(workspace_id, session: AsyncSession, user: User):
    try:
        async with session.begin():
            result = await session.execute(
                select(WorkspaceMembership)
                .join(Workspace, Workspace.workspace_id == WorkspaceMembership.workspace_id)
                .where(
                    WorkspaceMembership.user_id == user.user_id,
                    WorkspaceMembership.status == 'Active',
                    WorkspaceMembership.workspace_id == workspace_id
                )
            )

            workspace = result.scalars().one_or_none()
            if not workspace:
                raise HTTPException(status_code=403, detail="User not found or not active")
            if workspace.role == Roles.ROLE_READ_ONLY.value:
                raise HTTPException(status_code=403, detail="This role cant recording")

            remaining = await check_usage_limits(workspace_id, "save_happy_pass", session)

            return JSONResponse(content={"available_recording": remaining})
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(e, exc_info=True)
        mess = {"status": "error", "message": f"Error: {e}"}
        raise HTTPException(400, mess)


async def happy_passes_get_list(project_id: UUID4,
                                session: AsyncSession,
                                user: User):
    try:
        async with session.begin():
            query = await session.execute(select(HappyPass)
                                          .select_from(HappyPass)
                                          .join(ProjectUser, and_(ProjectUser.project_id == project_id,
                                                                  ProjectUser.workspace_id == user.active_workspace_id,
                                                                  ProjectUser.user_id == user.user_id))
                                          .where(and_(HappyPass.workspace_id == user.active_workspace_id,
                                                      HappyPass.project_id == project_id))
                                          .order_by(desc(HappyPass.created_at)))

            st = time.perf_counter()
            happy_passes = query.scalars().all()
            et = time.perf_counter()
            logger.info(f"Query happy_passes_get_list: {(et - st):.4f} seconds")

            if not happy_passes:
                return []
                # raise HTTPException(status_code=404, detail="No HappyPass found for the user")

            result = []
            for happy_pass in happy_passes:
                result.append({
                    "happy_pass_id": happy_pass.happy_pass_id,
                    "project_id": happy_pass.project_id,
                    "created_at": happy_pass.created_at,
                    "action_plan": happy_pass.action_plan,
                    "steps": happy_pass.steps,
                    "name": happy_pass.name,
                    "context": happy_pass.context
                })

            return result
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(e, exc_info=True)
        mess = {"status": "error", "message": f"Error: {e}"}
        raise HTTPException(400, mess)


async def happy_passes_get_full(project_id: UUID4,
                                session: AsyncSession,
                                user: User,
                                host: Optional[str] = None,
                                happy_pass_id: Optional[str] = None,
                                name: Optional[str] = None,
                                context: Optional[str] = None,
                                limit: int = 10,
                                offset: int = 0):
    try:
        async with session.begin():

            count_query = (select(func.count(HappyPass.happy_pass_id))
                           .join(ProjectUser, and_(ProjectUser.project_id == project_id,
                                                   ProjectUser.workspace_id == user.active_workspace_id,
                                                   ProjectUser.user_id == user.user_id))
                           .where(and_(HappyPass.workspace_id == user.active_workspace_id,
                                       HappyPass.project_id == project_id)))

            if happy_pass_id:
                count_query = count_query.where(HappyPass.happy_pass_id == happy_pass_id)
            if name:
                count_query = count_query.where(HappyPass.name == name)
            if context:
                count_query = count_query.where(HappyPass.context == context)

            st = time.perf_counter()
            total_result = await session.execute(count_query)
            total = total_result.scalar_one()
            et = time.perf_counter()
            logger.info(f"Query get count happy passes: {(et - st):.4f} seconds")

            subquery = (select(HappyPass.happy_pass_id)
                        .join(ProjectUser, and_(ProjectUser.project_id == project_id,
                                                ProjectUser.workspace_id == user.active_workspace_id,
                                                ProjectUser.user_id == user.user_id))
                        .where(and_(HappyPass.workspace_id == user.active_workspace_id,
                                    HappyPass.project_id == project_id)))

            if happy_pass_id:
                subquery = subquery.where(HappyPass.happy_pass_id == happy_pass_id)
            if name:
                subquery = subquery.where(HappyPass.name == name)
            if context:
                subquery = subquery.where(HappyPass.context == context)

            subquery = subquery.order_by(desc(HappyPass.created_at)).limit(limit).offset(offset)
            aliased_subquery = subquery.alias("fast_filter")

            query = select(HappyPass).join(aliased_subquery, HappyPass.happy_pass_id == aliased_subquery.c.happy_pass_id).order_by(desc(HappyPass.created_at))

            st = time.perf_counter()
            res = await session.execute(query)
            happy_passes = res.scalars().all()
            et = time.perf_counter()
            logger.info(f"Query get all happy passes: {(et - st):.4f} seconds")

            if not happy_passes:
                raise HTTPException(status_code=404, detail="HappyPass not found")

            result = []

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

            for happy_pass in happy_passes:

                full_data_with_urls = happy_pass.full_data
                filename_to_url_map = {}

                for activity in full_data_with_urls.get('steps', []):
                    for key in ["beforeScreenshot", "beforeAnnotatedScreenshot", "afterScreenshot"]:
                        if key in activity:
                            presigned_url = await asyncio.to_thread(generate_presigned_url,
                                                                    activity[key]['bucket'],
                                                                    activity[key]['filename'],
                                                                    host,
                                                                    minio_client)
                            activity[key]['url'] = presigned_url
                            if key == "beforeAnnotatedScreenshot":
                                filename_to_url_map[activity[key]['filename']] = presigned_url

                image_urls = [{
                    "bucket": img['bucket'],
                    "filename": img['filename'],
                    "url": filename_to_url_map.get(img['filename'], '')
                } for img in happy_pass.images if img['filename'] in filename_to_url_map]

                result.append({
                    "happy_pass_id": happy_pass.happy_pass_id,
                    "created_at": happy_pass.created_at,
                    "action_plan": happy_pass.action_plan,
                    "steps": happy_pass.steps,
                    "name": happy_pass.name,
                    "context": happy_pass.context,
                    "full_data": full_data_with_urls,
                    "images": image_urls
                })

            total_pages = (total - 1) // limit + 1
            current_page = (offset // limit) + 1

            pagination_info = {
                "total": total,
                "total_current_page": len(happy_passes),
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


async def happy_pass_update_autosop(workspace_id: str, user_id: str, happy_pass_id: str,
                                    timeout: int = 120, host: str = None):
    try:
        async with async_session() as session:
            async with session.begin():
                query = await session.execute(select(HappyPass)
                                              .select_from(HappyPass)
                                              .join(ProjectUser, and_(ProjectUser.project_id == HappyPass.project_id,
                                                                      ProjectUser.workspace_id == workspace_id,
                                                                      ProjectUser.user_id == user_id))
                                              .where(HappyPass.workspace_id == workspace_id,
                                                     HappyPass.happy_pass_id == happy_pass_id))

                happy_pass: HappyPass = query.scalars().one_or_none()

                if not happy_pass:
                    raise HTTPException(status_code=404, detail="HappyPass not found")

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

                full_data_with_urls = happy_pass.full_data

                filename_to_url_map = {}
                for activity in full_data_with_urls.get('steps', []):
                    for key in ["beforeScreenshot", "beforeAnnotatedScreenshot", "afterScreenshot"]:
                        if key in activity:
                            presigned_url = await asyncio.to_thread(generate_presigned_url,
                                                                    activity[key]['bucket'],
                                                                    activity[key]['filename'],
                                                                    host,
                                                                    minio_client)
                            activity[key]['url'] = presigned_url
                            if key == "beforeAnnotatedScreenshot":
                                filename_to_url_map[activity[key]['filename']] = presigned_url
                # копируем ссылки для beforeAnnotatedScreenshot
                image_urls = [{
                    "bucket": img['bucket'],
                    "filename": img['filename'],
                    "url": filename_to_url_map.get(img['filename'], '')
                } for img in happy_pass.images if img['filename'] in filename_to_url_map]

                result = [{
                    "happy_pass_id": str(happy_pass.happy_pass_id),
                    "created_at": happy_pass.created_at.isoformat(),
                    "action_plan": happy_pass.action_plan,
                    "steps": happy_pass.steps,
                    "name": happy_pass.name,
                    "context": happy_pass.context,
                    "full_data": full_data_with_urls,
                    "images": image_urls}]

                # clicker_ip = await model_ip_store.get_model_ip_clicker()
                # if clicker_ip is None:
                #     raise HTTPException(status_code=400, detail="server is unavailable")

                data = {
                    "record": result,
                    "context": happy_pass.context
                }

                status, res = await async_request(f"http://{CLICKER_IP}:{CLICKER_PORT}/convert_to_sop",
                                                  method='post',
                                                  params=data, timeout=timeout)

                if status != 200:
                    raise HTTPException(status_code=400, detail="autosop error")

                try:
                    # action_plan, steps = res
                    steps = res
                except ValueError as er:
                    raise HTTPException(status_code=400, detail=f"autosop error {er}")

                if not steps:
                    raise HTTPException(status_code=400, detail="autosop error")

                # happy_pass.action_plan = action_plan
                happy_pass.steps = steps
                # result[0]["action_plan"] = action_plan
                result[0]["steps"] = steps

                session.add(happy_pass)
                await session.flush()
                await session.refresh(happy_pass)

                return result
                # return HappyPassRead.model_validate(happy_pass)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(e, exc_info=True)
        mess = {"status": "error", "message": f"Error: {e}"}
        raise HTTPException(400, mess)


async def happypass_update_action_plan(user: User, happy_pass_id: str,
                                       action_plan: Optional[List[Dict]] = None,
                                       host: str = None):
    async with async_session() as session:
        async with session.begin():
            query = await session.execute(select(HappyPass)
                                          .where(HappyPass.workspace_id == user.active_workspace_id,
                                                 HappyPass.happy_pass_id == happy_pass_id))

            happy_pass: HappyPass = query.scalars().one_or_none()

            if not happy_pass:
                raise HTTPException(status_code=404, detail="HappyPass not found")

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

            full_data_with_urls = happy_pass.full_data

            filename_to_url_map = {}
            for activity in full_data_with_urls.get('steps', []):
                for key in ["beforeScreenshot", "beforeAnnotatedScreenshot", "afterScreenshot"]:
                    if key in activity:
                        presigned_url = await asyncio.to_thread(generate_presigned_url,
                                                                activity[key]['bucket'],
                                                                activity[key]['filename'],
                                                                host,
                                                                minio_client)
                        activity[key]['url'] = presigned_url
                        if key == "beforeAnnotatedScreenshot":
                            filename_to_url_map[activity[key]['filename']] = presigned_url
            # копируем ссылки для beforeAnnotatedScreenshot
            image_urls = [{
                "bucket": img['bucket'],
                "filename": img['filename'],
                "url": filename_to_url_map.get(img['filename'], '')
            } for img in happy_pass.images if img['filename'] in filename_to_url_map]

            result = [{
                "happy_pass_id": str(happy_pass.happy_pass_id),
                "created_at": happy_pass.created_at.isoformat(),
                "action_plan": happy_pass.action_plan,
                "steps": happy_pass.steps,
                "name": happy_pass.name,
                "context": happy_pass.context,
                "full_data": full_data_with_urls,
                "images": image_urls}]

            # clicker_ip = await model_ip_store.get_model_ip_clicker()
            # if clicker_ip is None:
            #     raise HTTPException(status_code=400, detail="server is unavailable")

            if action_plan:
                data = {"record": action_plan}
                status, res = await async_request(f"http://{CLICKER_IP}:{CLICKER_PORT}/convert_to_sop?steps_only=True",
                                                  method='post',
                                                  params=data, timeout=60)

                if status != 200:
                    raise HTTPException(status_code=400, detail="update_action_plan error")

                steps = res

                if not action_plan or not steps:
                    raise HTTPException(status_code=400, detail="update_action_plan error")

                happy_pass.action_plan = action_plan
                happy_pass.steps = steps
                result[0]["action_plan"] = action_plan
                result[0]["steps"] = steps

                session.add(happy_pass)
                await session.flush()
                await session.refresh(happy_pass)

            return result


async def delete_happy_pass(session: AsyncSession, user: User, happy_pass_id: str):
    try:
        async with session.begin():
            result = await session.execute(select(HappyPass)
                                           .select_from(HappyPass)
                                           .join(ProjectUser, and_(ProjectUser.project_id == HappyPass.project_id,
                                                                   ProjectUser.workspace_id == user.active_workspace_id,
                                                                   ProjectUser.user_id == user.user_id))
                                           .where(HappyPass.workspace_id == user.active_workspace_id,
                                                  HappyPass.happy_pass_id == happy_pass_id))
            happy_pass = result.scalars().one_or_none()

            if not happy_pass:
                raise HTTPException(status_code=404, detail="HappyPass not found")

            await session.delete(happy_pass)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(e, exc_info=True)
        mess = {"status": "error", "message": f"Error: {e}"}
        raise HTTPException(400, mess)
