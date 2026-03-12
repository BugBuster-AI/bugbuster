
import asyncio
import hashlib
import json
import os
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import aiohttp
from fastapi import BackgroundTasks, HTTPException
from fastapi.responses import JSONResponse
from minio import Minio
from pydantic import UUID4
from sqlalchemy import (and_, asc, delete, desc, exists, func, insert, or_,
                        over, select, update)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.orm.attributes import flag_modified
from sqlalchemy.sql import func
from urllib.parse import urlencode, urlparse, urlunparse
import urllib3
from config import (MINIO_ACCESS_KEY, MINIO_HOST, MINIO_PORT, MINIO_SECRET_KEY, MINIO_PUBLIC_URL,
                    MINIO_SECURE, logger, MINIO_USE_INTERNAL_PROXY)
from db.models import PaymentHistory, Tariffs, Usage, User, Workspace
from db.session import async_session, transaction_scope
from schemas import WorkspaceStatusEnum
from utils import (download_file_from_url, generate_presigned_url,
                   select_minio_host, send_simple_email_async, send_telegramm,
                   upload_to_minio)


async def current_tariffs_limits_usage(current_user: User,
                                       session: AsyncSession):
    try:
        async with session.begin():
            # Получаем workspace, tariff и все usage records
            result = await session.execute(
                select(Workspace, Tariffs)
                .join(Tariffs, Workspace.tariff_id == Tariffs.tariff_id)
                .options(selectinload(Tariffs.tariff_limits))
                .where(Workspace.workspace_id == current_user.active_workspace_id)
            )
            workspace, tariff = result.first()

            if not workspace or not tariff:
                raise HTTPException(status_code=404, detail="Workspace or tariff not found")

            # Получаем дату последнего сброса (если есть)
            last_reset = await session.scalar(
                select(Usage.last_reset)
                .where(Usage.workspace_id == current_user.active_workspace_id)
                .order_by(Usage.last_reset.desc())
                .limit(1)
            )

            # Вычисляем дату следующего сброса
            if workspace.tariff_start_date:
                next_reset = workspace.tariff_start_date + timedelta(days=30)
                # Если уже был сброс, вычисляем от последней даты сброса
                if last_reset:
                    next_reset = last_reset + timedelta(days=30)

                # Проверяем, что следующая дата сброса не позже окончания тарифа
                if workspace.tariff_expiration and next_reset > workspace.tariff_expiration:
                    next_reset = None
            else:
                next_reset = None

            # Получаем все usage records для workspace
            usage_records = await session.execute(
                select(Usage)
                .where(Usage.workspace_id == current_user.active_workspace_id)
            )
            usage_records = usage_records.scalars().all()
            usage_dict = {u.feature_name: u.usage_count for u in usage_records}

            # лимит на max_concurrent_tasks
            max_concurrent_tasks_tariff = next(
                (limit.limit_value for limit in tariff.tariff_limits
                 if limit.feature_name == 'max_concurrent_tasks'),
                None
            )

            # Вычисляем additional_streams
            additional_streams = 0
            if (max_concurrent_tasks_tariff is not None and
                workspace.max_concurrent_tasks is not None and
                workspace.max_concurrent_tasks > max_concurrent_tasks_tariff):
                additional_streams = workspace.max_concurrent_tasks - max_concurrent_tasks_tariff

            # Формируем данные о лимитах и их использовании
            limits = []
            for limit in tariff.tariff_limits:
                current_usage = usage_dict.get(limit.feature_name, 0)
                limits.append({
                    "feature_name": limit.feature_name,
                    "feature_full_name": limit.feature_full_name,
                    "feature_full_simple": limit.feature_full_simple,
                    "limit_value": limit.limit_value if limit.limit_value >= 0 else 'unlimited',
                    "current_usage": current_usage,
                })

            # Формируем итоговый ответ
            response = {
                "workspace": {
                    "name": workspace.name,
                    "created_at": workspace.created_at,
                    "tariff_start_date": workspace.tariff_start_date,
                    "status": workspace.status,
                    "tariff_expiration": workspace.tariff_expiration,
                    "workspace_max_concurrent_tasks_fact": workspace.max_concurrent_tasks,
                    "next_reset_usage": next_reset.isoformat() if next_reset else None
                },
                "tariff": {
                    "tariff_id": tariff.tariff_id,
                    "can_buy_streams": tariff.can_buy_streams,
                    "tariff_name": tariff.tariff_name,
                    "tariff_full_name": tariff.tariff_full_name,
                    "is_free": tariff.price < 10,
                    "description": tariff.description,
                    "additional_streams": additional_streams
                },
                "limits": limits,
                "features": [limit.feature_full_name for limit in tariff.tariff_limits]
            }

            return response

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(e, exc_info=True)
        mess = {"status": "error", "message": f"Error: {e}"}
        raise HTTPException(400, mess)


async def list_tariffs_limits_plan(current_user: User,
                                   session: AsyncSession,
                                   cnt_months: int = 12):
    try:
        async with session.begin():

            current_tariff_name = await session.scalar(
                select(Tariffs.tariff_name)
                .join(Workspace, Workspace.tariff_id == Tariffs.tariff_id)
                .where(Workspace.workspace_id == current_user.active_workspace_id)
            )

            query = (
                select(Tariffs)
                .options(selectinload(Tariffs.tariff_limits))
                .where(Tariffs.visible == True)
                .order_by(Tariffs.price)
            )

            if (current_tariff_name and current_tariff_name != 'starter') or \
               (current_tariff_name and current_tariff_name == 'starter' and current_user.workspace_status == WorkspaceStatusEnum.INACTIVE.value):
                query = query.where(Tariffs.tariff_name != 'starter')

            result = await session.execute(query)
            tariffs = result.scalars().all()

            response = []
            for tariff in tariffs:
                tariff_dict = tariff.__dict__

                # Применяем скидку если 12 месяцев
                discount_amount = 0
                total_before_discount = tariff.price * cnt_months

                if cnt_months == 12 and tariff.discount > 0:
                    discount_amount = total_before_discount * tariff.discount / 100
                    total_price = total_before_discount - discount_amount
                else:
                    total_price = total_before_discount

                total_price_in_month = 0
                if total_price > 0 and cnt_months > 0:
                    total_price_in_month = round(total_price / cnt_months, 2)

                tariff_dict['discount_amount'] = int(discount_amount)
                tariff_dict['discount_percent'] = tariff.discount if cnt_months == 12 else 0
                tariff_dict['total_before_discount'] = int(total_before_discount)
                tariff_dict['total_price'] = int(total_price)
                tariff_dict['total_price_in_month'] = int(total_price_in_month)
                tariff_dict['current_plan'] = (tariff.tariff_name == current_tariff_name)
                tariff_dict['features'] = [limit.feature_full_name for limit in tariff.tariff_limits]

                if tariff.can_buy_streams:
                    tariff_dict['features'].append("ability to purchase additional streams")
                response.append(tariff_dict)

            return response

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(e, exc_info=True)
        mess = {"status": "error", "message": f"Error: {e}"}
        raise HTTPException(400, mess)


async def get_user_transactions(current_user: User,
                                session: AsyncSession,
                                host=None,
                                start_date: Optional[datetime] = None,
                                end_date: Optional[datetime] = None,
                                status=None,
                                limit: int = 10,
                                offset: int = 0) -> JSONResponse:
    try:
        async with session.begin():

            count_query = select(func.count(PaymentHistory.transaction_id)).where(PaymentHistory.workspace_id == current_user.active_workspace_id)
            if start_date:
                count_query = count_query.where(PaymentHistory.created_at >= start_date)
            if end_date:
                count_query = count_query.where(PaymentHistory.created_at <= end_date)
            if status:
                count_query = count_query.where(PaymentHistory.status == status)

            st = time.perf_counter()
            total_result = await session.execute(count_query)
            total = total_result.scalar_one()
            et = time.perf_counter()
            logger.info(f"Query get count user_transactions: {(et - st):.4f} seconds")

            subquery = select(PaymentHistory.transaction_id).where(PaymentHistory.workspace_id == current_user.active_workspace_id)

            if start_date:
                subquery = subquery.where(PaymentHistory.created_at >= start_date)
            if end_date:
                subquery = subquery.where(PaymentHistory.created_at <= end_date)
            if status:
                subquery = subquery.where(PaymentHistory.status == status)

            subquery = subquery.order_by(desc(PaymentHistory.created_at)).limit(limit).offset(offset)
            aliased_subquery = subquery.alias("fast_filter")

            query = (
                select(PaymentHistory)
                .join(aliased_subquery, PaymentHistory.transaction_id == aliased_subquery.c.transaction_id)
                .order_by(desc(PaymentHistory.created_at))
            )

            st = time.perf_counter()
            results = await session.execute(query)
            user_transactions = results.unique().scalars().all()
            et = time.perf_counter()
            logger.info(f"Query get all user_transactions: {(et - st):.4f} seconds")

            final_entries = []

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

            for transaction in user_transactions:
                if isinstance(transaction.pdf, dict) and transaction.pdf.get('bucket', None):
                    transaction.pdf['url'] = await asyncio.to_thread(generate_presigned_url,
                                                                     transaction.pdf['bucket'],
                                                                     transaction.pdf['filename'],
                                                                     host,
                                                                     minio_client)
                final_entries.append({
                    "transaction_id": str(transaction.transaction_id),
                    "status": transaction.status,
                    "invoice_number": transaction.invoice_number,
                    "x_requests_id": str(transaction.x_requests_id),
                    "invoice_id": str(transaction.invoice_id),
                    "payment_id": str(transaction.payment_id),
                    "created_at": transaction.created_at,
                    "payment_dt": transaction.payment_dt,
                    "invoice_date": transaction.invoice_date,
                    "due_date": transaction.due_date,
                    "services": transaction.services,
                    "discount_amount": transaction.discount_amount,
                    "discount_percent": transaction.discount_percent,
                    "amount": transaction.amount,
                    "cur": transaction.cur,
                    "pdf": transaction.pdf,
                    "payment_url": transaction.payment_url,
                    "details": transaction.details
                })

            # Подготовка данных о пагинации
            total_pages = (total - 1) // limit + 1
            current_page = (offset // limit) + 1

            pagination_info = {
                "total": total,
                "total_current_page": len(user_transactions),
                "page": current_page,
                "size": limit,
                "pages": total_pages,
                "limit": limit,
                "offset": offset,
                "items": final_entries
            }

            return pagination_info
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(e, exc_info=True)
        mess = {"status": "error", "message": f"Error: {e}"}
        raise HTTPException(400, mess)
