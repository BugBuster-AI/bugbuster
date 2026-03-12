import asyncio
import os
from datetime import datetime, timezone

import asyncpg.exceptions
from celery import Celery
from celery.signals import worker_ready, worker_shutdown
from langfuse import get_client

from agent.graph import run_graph
from core.celeryconfig import RABBIT_PREFIX, logger, redis_client, server_ident
from infra.db import async_engine, check_run_case_status, update_run_case_status, update_run_case_stop

if os.name == 'nt':
    os.environ.setdefault('FORKED_BY_MULTIPROCESSING', '1')

app = Celery()
app.config_from_object("core.celeryconfig")

RUNNING_TASKS_KEY = f"celery:running_tasks:{server_ident}"


def is_db_error(exc):
    return (
        isinstance(exc, asyncpg.exceptions.PostgresError) or
        exc.__class__.__module__ == 'asyncpg.exceptions' or
        isinstance(exc, (ConnectionError, TimeoutError))
    )


def run_async(coro):
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    if loop.is_closed():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(coro)


@app.task(name=f'{RABBIT_PREFIX}_celery.portal-clicker.run_single_case_queue')
def run_single_case_queue(**kwargs):

    run_id = kwargs['run_id']
    case = kwargs['case']
    user_id = kwargs['user_id']
    environment = kwargs.get("environment", {})
    background_video_generate = kwargs.get("background_video_generate", True)
    db_error = False

    try:
        if redis_client.sismember("stop_task", run_id):
            logger.info(f"Stopping task {run_id}")
            run_async(update_run_case_stop(run_id, datetime.now(timezone.utc)))

            redis_client.srem("stop_task", run_id)
            return

        logger.info(f"Starting task {run_id} for user {user_id}\n{case=}")
        redis_client.sadd(RUNNING_TASKS_KEY, run_id)

        # playwright
        run_case_status = run_async(check_run_case_status(run_id))
        if run_case_status is False:
            logger.info(f"Task {run_id} in final status for user {user_id}")
            return
        run_async(run_graph(run_id, case, user_id, environment, background_video_generate))
        langfuse = get_client()
        langfuse.flush()
        logger.info(f"Task {run_id} completed successfully for user {user_id}")
    except Exception as er:
        if is_db_error(er):
            logger.critical(f"Database error in task {run_id} for user {user_id}: {er}", exc_info=True)
            db_error = True

        logger.error(f"Error in task {run_id} for user {user_id}: {er}", exc_info=True)

        try:
            run_async(
                update_run_case_status(
                    run_id=run_id,
                    status='failed',
                    run_summary=f"Error: {repr(er)}",
                    start_dt=datetime.now(timezone.utc),
                    end_dt=datetime.now(timezone.utc),
                    complete_time=0
                )
            )
        except Exception as er:
            if is_db_error(er):
                logger.critical(f"Failed to update failed status for {run_id}: {er}")
                db_error = True
            logger.error(f"Error in task {run_id}: {er}")
        raise  # Пробрасываем для Celery что задача завершилась с ошибкой
    finally:
        try:
            if not db_error:
                redis_client.srem(RUNNING_TASKS_KEY, run_id)
            logger.info(f"Task {run_id} cleanup completed")
        except Exception as redis_error:
            logger.error(f"Redis cleanup error for {run_id}: {redis_error}")


@worker_shutdown.connect
def handle_worker_shutdown(sender, **kwargs):
    logger.info("Worker is shutting down. Updating running tasks to failed...")

    running_tasks = redis_client.smembers(RUNNING_TASKS_KEY)

    for task_id in running_tasks:
        task_id = task_id.decode('utf-8')
        logger.info(f"Updating task {task_id} to failed status")
        try:
            run_async(update_run_case_status(task_id, 'failed', 'service shutdown',
                                             datetime.now(timezone.utc), datetime.now(timezone.utc), 0))
            run_async(async_engine.dispose())
        except Exception as er:
            logger.error(f"Error updating task {task_id}: {er}")

    redis_client.delete(RUNNING_TASKS_KEY)


@worker_ready.connect
def handle_worker_startup(**kwargs):
    logger.info("Worker startup initiated. Checking for stale tasks...")

    running_tasks = redis_client.smembers(RUNNING_TASKS_KEY)
    stopped_tasks = redis_client.smembers("stop_task")

    for task_id in running_tasks:
        task_id = task_id.decode('utf-8')
        logger.info(f"Updating task {task_id} to failed status due to startup")
        try:
            run_async(update_run_case_status(task_id, 'failed', 'service restart',
                                             datetime.now(timezone.utc), datetime.now(timezone.utc), 0))
        except Exception as er:
            logger.error(f"Error updating task {task_id} during startup: {er}")

    redis_client.delete(RUNNING_TASKS_KEY)

    for task_id in stopped_tasks:
        task_id = task_id.decode('utf-8')
        logger.info(f"Updating task {task_id} to stopped status due to startup")
        try:
            run_async(update_run_case_status(task_id, 'stopped', 'service restart',
                                             datetime.now(timezone.utc), datetime.now(timezone.utc), 0))
        except Exception as er:
            logger.error(f"Error updating task {task_id} during startup: {er}")

    redis_client.delete("stop_task")

    # посмотреть redis_client.sismember("stop_task", run_id), сравнить с БД стопнутые и почистить


if __name__ == "__main__":
    worker = app.Worker(
        # можно указать список модулей с тасками
        # include=['main_celery'],
        loglevel='INFO',
        pool='solo',  # Используем solo pool вместо prefork
        concurrency=1
    )
    worker.start()
    # celery -A main_celery worker --loglevel=info --autoscale=1,1
