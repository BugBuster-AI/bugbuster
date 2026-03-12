# import sentry_sdk
import asyncio
import json
import re
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import uvicorn
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from colorama import Fore, Style
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from prometheus_fastapi_instrumentator import Instrumentator
from pytz import utc
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import JSONResponse, Response

from api.actions import (reset_usage_and_check_tariff_expiration,
                         save_permissions_to_redis,
                         save_workspace_concurrency_limit_to_redis)
from api.routers import (admin_content, auth, billing, content,
                         environments_rout, records, runs, tokens,
                         tools, workspaces, ws, variables, flags)

from background_publisher import publisher
from config import (REDIS_PREFIX, UVICORN_PORT,
                    logger, redis_client)

from workers.user_logs import (LOGGABLE_ENDPOINTS, buffer_lock, log_buffer,
                               log_processor)

# from starlette_exporter import handle_metrics
# from starlette_exporter import PrometheusMiddleware

scheduler = AsyncIOScheduler(timezone=utc)


@asynccontextmanager
async def lifespan(app: FastAPI):

    instrumentator.expose(app)

    scheduler.start()

    await save_workspace_concurrency_limit_to_redis()
    await save_permissions_to_redis()

    asyncio.create_task(publisher())
    asyncio.create_task(log_processor())

    yield

    keys_to_delete = redis_client.keys(f"{REDIS_PREFIX}_workspace_limit:*")
    if keys_to_delete:
        redis_client.delete(*keys_to_delete)

    scheduler.shutdown()


app = FastAPI(title="Self-Executing Test Cases", lifespan=lifespan)
app.mount("/static/emails/img", StaticFiles(directory="templates/emails/img"), name="email_images")


# app.add_middleware(PrometheusMiddleware)
# app.add_route("/metrics", handle_metrics)
instrumentator = Instrumentator(
    should_group_status_codes=True,
    excluded_handlers=["/metrics", "/health", "/favicon.ico"],
    env_var_name="ENVIRONMENT",

).instrument(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)

app.include_router(flags.router)

app.include_router(workspaces.router)
app.include_router(tokens.router)

app.include_router(records.router)
app.include_router(environments_rout.router)
app.include_router(variables.router_variables)
app.include_router(variables.router_variables_details)
app.include_router(content.router)
app.include_router(content.router_shared_steps)
app.include_router(runs.router)

app.include_router(tools.router)

app.include_router(admin_content.router)
app.include_router(billing.router)
app.include_router(ws.router)

# разрешаем запросы только с фронта
# origins = [
#     "http://localhost:3000",
# ]

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=origins,
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )


# 'interval', minutes=2
@scheduler.scheduled_job('cron', hour=8, minute=0)
async def job_reset_usage_and_check_tariff_expiration():
    await reset_usage_and_check_tariff_expiration()


@app.middleware("http")
async def log_requests(request: Request, call_next):
    request_id = str(uuid.uuid4())
    logger.info(f"{'-' * 60}")
    logger.info(f"[{request_id}] Incoming request: {Fore.GREEN} {request.method} {request.url} {Style.RESET_ALL}")
    logger.info(f"[{request_id}] Request headers: {request.headers}")

    # Считать тело запроса один раз и сохранить его
    body = await request.body()

    response = await call_next(request)

    endpoint_path = re.sub(r'/[a-f0-9-]+$', '', request.url.path)
    endpoint_key = (request.method, endpoint_path)

    response_data = None
    if endpoint_key in LOGGABLE_ENDPOINTS:
        response_body = b""
        async for chunk in response.body_iterator:
            response_body += chunk

        response = Response(
            content=response_body,
            status_code=response.status_code,
            headers=dict(response.headers),
            media_type=response.media_type
        )

        try:
            response_data = json.loads(response_body.decode("utf-8"))
        except Exception:
            response_data = None

    response.headers["X-Request-ID"] = request_id
    logger.info(f"[{request_id}] Response headers: {response.headers}\n {'-' * 60}")

    if endpoint_key in LOGGABLE_ENDPOINTS:
        user = getattr(request.state, "user", None)
        if user:
            user_params = dict(request.query_params)
            if request.method in ["POST", "PUT", "DELETE"]:
                try:
                    if body:
                        body_params = json.loads(body)
                        # Обрабатываем случай, когда body_params - это список
                        if isinstance(body_params, list):
                            user_params["items"] = body_params  # Добавляем список как отдельный элемент
                        else:
                            user_params.update(body_params)  # Для словарей как обычно
                except Exception as er:
                    logger.error(er, exc_info=True)

            log_record = {
                "user_id": user.user_id,
                "user_email": user.email,
                "user_username": user.username,
                "workspace_id": user.active_workspace_id,
                "method": request.method,
                "endpoint_path": endpoint_path,
                "status_code": response.status_code,
                "timestamp": datetime.now(timezone.utc),
                "user_params": user_params,
                "response_data": response_data,
            }

            async with buffer_lock:
                log_buffer.append(log_record)

    return response


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request, exc):
    logger.error(f"{repr(exc)}")
    return JSONResponse({"detail": str(exc.detail)}, status_code=exc.status_code)


if __name__ == "__main__":

    uvicorn.run(app, host="0.0.0.0", port=UVICORN_PORT, reload=False, workers=1, proxy_headers=True,
                ws_ping_interval=25, ws_ping_timeout=120, timeout_keep_alive=120)
