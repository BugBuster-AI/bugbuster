import asyncio
from collections import deque

from sqlalchemy import insert
from sqlalchemy.exc import SQLAlchemyError

from config import logger
from db.models import LogEntry
from db.session import async_session
from schemas import Lang

# Буфер для логов
log_buffer = deque()
buffer_lock = asyncio.Lock()
log_batch_interval = 60  # Интервал записи в БД накопленных логов


endpoint_names = {
    ("POST", "/api/content/generate_case_from_record/"): {
        Lang.RU.value: "Создание тестового кейса из записи плагина",
        Lang.EN.value: "Create test case from record"
    },
    ("POST", "/api/content/project"): {
        Lang.RU.value: "Создание нового проекта",
        Lang.EN.value: "Create new project"
    },
    ("POST", "/api/content/suite"): {
        Lang.RU.value: "Создание нового сьюта",
        Lang.EN.value: "Create new suite"
    },
    ("POST", "/api/content/case"): {
        Lang.RU.value: "Создание нового тест кейса",
        Lang.EN.value: "Create new test case"
    },
    ("POST", "/api/content/copy_case_by_case_id"): {
        Lang.RU.value: "Создание копии тест кейса",
        Lang.EN.value: "Create copy of test case"
    },
    ("PUT", "/api/content/project"): {
        Lang.RU.value: "Обновление проекта",
        Lang.EN.value: "Update project"
    },
    ("PUT", "/api/content/suite"): {
        Lang.RU.value: "Обновление сьюта",
        Lang.EN.value: "Update suite"
    },
    ("PUT", "/api/content/change_suite_position"): {
        Lang.RU.value: "Изменение позиции сьюта",
        Lang.EN.value: "Change suite position"
    },
    ("PUT", "/api/content/case"): {
        Lang.RU.value: "Обновление тест кейса",
        Lang.EN.value: "Update test case"
    },
    ("PUT", "/api/content/change_case_position"): {
        Lang.RU.value: "Изменение позиции тест кейса",
        Lang.EN.value: "Change test case position"
    },
    ("DELETE", "/api/content/project"): {
        Lang.RU.value: "Удаление проекта",
        Lang.EN.value: "Delete project"
    },
    ("DELETE", "/api/content/suite"): {
        Lang.RU.value: "Удаление сьюта",
        Lang.EN.value: "Delete suite"
    },
    ("DELETE", "/api/content/case"): {
        Lang.RU.value: "Удаление кейса",
        Lang.EN.value: "Delete case"
    },
    ("POST", "/api/environments"): {
        Lang.RU.value: "Создание окружения",
        Lang.EN.value: "Create environment"
    },
    ("PUT", "/api/environments"): {
        Lang.RU.value: "Обновление окружения",
        Lang.EN.value: "Update environment"
    },
    ("DELETE", "/api/environments"): {
        Lang.RU.value: "Удаление окружения",
        Lang.EN.value: "Delete environment"
    },
    ("PUT", "/api/records/happypass_autosop_generate"): {
        Lang.RU.value: "Генерация шагов для записи плагина",
        Lang.EN.value: "Generate steps for plugin record"
    },
    ("PUT", "/api/records/happypass_action_plan_update"): {
        Lang.RU.value: "Изменение экшен плана для записи плагина",
        Lang.EN.value: "Update action plan for plugin record"
    },
    ("DELETE", "/api/records/happypass"): {
        Lang.RU.value: "Удаление записи плагина",
        Lang.EN.value: "Delete plugin record"
    },
    ("POST", "/api/runs/"): {
        Lang.RU.value: "Запуск одиночного рана по тест кейсу",
        Lang.EN.value: "Run single test case"
    },
    ("DELETE", "/api/runs/"): {
        Lang.RU.value: "Остановка одиночного рана",
        Lang.EN.value: "Stop single test run"
    },
    ("POST", "/api/runs/group_runs"): {
        Lang.RU.value: "Создание группового рана",
        Lang.EN.value: "Create group test run"
    },
    ("PUT", "/api/runs/group_runs"): {
        Lang.RU.value: "Обновление группового рана",
        Lang.EN.value: "Update group test run"
    },
    ("DELETE", "/api/runs/group_runs"): {
        Lang.RU.value: "Удаление группового рана",
        Lang.EN.value: "Delete group test run"
    },
    ("POST", "/api/runs/group_runs/start_run_by_group_run_id"): {
        Lang.RU.value: "Запуск группового рана",
        Lang.EN.value: "Start group test run"
    },
    ("DELETE", "/api/runs/group_runs/stop_run_by_group_run_id"): {
        Lang.RU.value: "Остановка группового рана",
        Lang.EN.value: "Stop group test run"
    },
    ("PUT", "/api/runs/complete_run_cases_by_run_id"): {
        Lang.RU.value: "Установка конечных статусов в групповом ране",
        Lang.EN.value: "Set final statuses in group run"
    },
    ("PUT", "/api/runs/step_passed_run_case_by_run_id"): {
        Lang.RU.value: "Установка успешных шагов в ручном прохождении группового рана",
        Lang.EN.value: "Set successful steps in manual group run"
    },
    ("DELETE", "/api/runs/delete_cases_in_group_run"): {
        Lang.RU.value: "Удаление тест кейсов из группового рана",
        Lang.EN.value: "Delete test cases from group run"
    },
    ("POST", "/api/workspace/invite_user"): {
        Lang.RU.value: "Приглашение пользователя в рабочее пространство",
        Lang.EN.value: "Invite user to workspace"
    },
    ("PUT", "/api/workspace/edit_user_workspace_membership"): {
        Lang.RU.value: "Изменение прав пользователя в рабочем пространстве",
        Lang.EN.value: "Edit user workspace rights"
    },
    ("DELETE", "/api/workspace/remove_user_workspace_membership"): {
        Lang.RU.value: "Удаление пользователя из рабочего пространства",
        Lang.EN.value: "Remove user from workspace"
    },
}


# Получаем список логируемых эндпоинтов из ключей словаря
LOGGABLE_ENDPOINTS = list(endpoint_names.keys())


async def log_processor():
    logger.info("start log processor")
    while True:
        await asyncio.sleep(log_batch_interval)
        async with buffer_lock:
            batch = list(log_buffer)
            log_buffer.clear()

        if batch:
            try:
                async with async_session() as session:
                    async with session.begin():
                        await session.execute(insert(LogEntry).values(batch))
                        await session.flush()
            except SQLAlchemyError as e:
                logger.error(f"log_processor SQLAlchemyError: {str(e)}")
            except Exception as e:
                logger.error(f"log_processor error: {str(e)}")
