import asyncio
import json
import logging
import time
import traceback
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path
from uuid import uuid4

from langfuse import get_client, observe
from langgraph.graph import END, StateGraph
from playwright.async_api import async_playwright
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from agent.config import POST_ACTION_WAIT_TIME
from agent.graph_actions import (
    action_api,
    action_inner_scroll,
    action_new_tab,
    action_paste,
    action_press,
    action_read,
    action_scroll,
    action_select,
    action_switch_tab,
    action_wait,
    coordinate_actions,
    reflection_step,
)
from agent.graph_utils import check_annotated_screenshot_exists, clean_up_directories
from agent.schemas import AgentState, InputState, RetrySettings, StepState
from browser_actions.extract_video_from_trace import process_trace_and_generate_video
from browser_actions.other import process_variables_before_plain_step
from browser_actions.tab_manager import TabManager, is_local_url
from browser_actions.user_storage import UserStorage
from core.celeryconfig import DB_NAME, redis_client
from core.config import INFERENCE_MODEL, LOCALHOST_DISABLED, PROXY_ENABLED, REFLECTION_MODEL
from core.schemas import CaseStatusEnum, Lang
from core.utils import (
    get_file_from_minio,
    select_language,
    upload_buffer_to_minio,
    upload_to_minio,
    validate_and_save_context_image,
)
from infra.db import (
    DB_URL,
    custom_deserialize,
    custom_serialize,
    get_user_host,
    update_run_case_final_record,
    update_run_case_status,
    update_run_case_steps,
    update_run_case_stop,
)
from infra.rabbit_producer import send_to_rabbitmq
from runtime.inference_runtime import InferenceClientRegistry

ACTION_MAP = {
    "CLICK": coordinate_actions,
    "HOVER": coordinate_actions,
    "TYPE": coordinate_actions,
    "PRESS": action_press,
    "SCROLL": action_scroll,
    "INNER_SCROLL": action_inner_scroll,
    "CLEAR": coordinate_actions,
    "WAIT": action_wait,
    "NEW_TAB": action_new_tab,
    "SWITCH_TAB": action_switch_tab,
    "READ": action_read,
    "PASTE": action_paste,
    "SELECT": action_select,
    "API": action_api,
    "expected_result": reflection_step
}

CONTEXT_SCREENSHOT_SEMAPHORE = asyncio.Semaphore(5)


async def prepare_context_screenshots(*,
                                      action_plan: list,
                                      screenshot_base_path: Path,
                                      width: int,
                                      height: int):
    """
    обрабатываем контекстные скриншоты в action_plan

  "action_plan": [
    {
      "action_type": "API",
      "method": "GET",
      "url": "http://just-the-time.appspot.com/",
      "headers": {},
      "data": null,
      "files": {},
      "value": "ORIGINAL STEP curl --request GET  --url http://just-the-time.appspot.com/ ",
      "extra": {
        "value": "ORIGINAL STEP curl --request GET  --url http://just-the-time.appspot.com/ ",
        "method": "GET",
        "url": "http://just-the-time.appspot.com/",
        "set_variables": {
          "login": "123"
        },
        "context_screenshot_path": {
          "bucket": "backend-images",
          "file": "2025-12-17/1a744784-48a8-424a-8b55-9931e8257dfa_context.jpeg"
        },
        "context_screenshot_used": true
      }
    },  =>>>>>>>>>>>

        "context_screenshot_path": {
            "bucket": "backend-images",
            "file": "2025-12-17/1a744784-48a8-424a-8b55-9931e8257dfa_context.jpeg"
        },
        "context_screenshot_used": true,
        "context_screenshot_log": "OK",
        "context_screenshot_path_local": "screenshots\\8bb6ab14-108d-4fc7-92fb-168e03c258a8\\2025-12-17\\1a744784-48a8-424a-8b55-9931e8257dfa_context.jpeg",

    OR

        "context_screenshot_used": false,
        "context_screenshot_log": "Resolution different: 1366x768, expected 1920x1080",
        "context_screenshot_path_local": null,

    """

    # собираем все ссылки
    refs: dict[tuple[str, str], list[dict]] = {}

    for step in action_plan:
        if not isinstance(step, dict):
            continue

        extra = step.get("extra")
        if not isinstance(extra, dict):
            continue

        ctx = extra.get("context_screenshot_path")
        if not isinstance(ctx, dict) or not ctx:
            continue

        bucket = ctx.get("bucket")
        file = ctx.get("file")

        if not bucket or not file:
            extra["context_screenshot_used"] = False
            extra["context_screenshot_log"] = "Invalid context_screenshot_path format"
            continue

        key = (bucket, file)
        refs.setdefault(key, []).append(extra)

    if not refs:
        return

    # процессим только уникальные пути
    tasks = {
        key: asyncio.create_task(
            process_single_context_screenshot(
                bucket=key[0],
                file=key[1],
                screenshot_base_path=screenshot_base_path,
                width=width,
                height=height
            )
        )
        for key in refs.keys()
    }

    results = {key: await task for key, task in tasks.items()}

    # Проставляем результаты в шаги
    for key, extras in refs.items():
        result = results[key]

        for extra in extras:
            extra["context_screenshot_used"] = result["used"]
            extra["context_screenshot_log"] = result["log"]

            if result["used"]:
                extra["context_screenshot_path_local"] = str(result["local_path"])
            else:
                extra["context_screenshot_path_local"] = None


async def process_single_context_screenshot(*,
                                            bucket: str,
                                            file: str,
                                            screenshot_base_path: Path,
                                            width: int,
                                            height: int) -> dict:

    # по 5 картинок
    async with CONTEXT_SCREENSHOT_SEMAPHORE:
        try:
            image_bytes = await asyncio.to_thread(get_file_from_minio, bucket, file)
        except Exception as e:
            return {
                "used": False,
                "local_path": None,
                "log": f"Failed to download from minio: {e}"
            }

        output_path = screenshot_base_path / file

        return await asyncio.to_thread(validate_and_save_context_image,
                                       image_bytes,
                                       output_path=output_path,
                                       width=width,
                                       height=height)


async def copy_context_screenshot_meta_to_case_steps(*,
                                                     action_plan: list,
                                                     case_steps: list) -> None:
    """
    Копируем сформированные context_screenshot_used и context_screenshot_log
    из action_plan -> case_steps
    """

    for idx, (action_plan_step, case_step) in enumerate(zip(action_plan, case_steps)):

        if not isinstance(action_plan_step, dict):
            continue

        action_plan_extra = action_plan_step.get("extra")
        if not isinstance(action_plan_extra, dict):
            continue

        keys_to_copy = {
            k: v
            for k, v in action_plan_extra.items()
            if k in ("context_screenshot_used", "context_screenshot_log")
        }

        if not keys_to_copy:
            continue

        if not isinstance(case_step, dict):
            continue

        case_step_extra = case_step.get("extra")
        if not isinstance(case_step_extra, dict):
            continue

        # добавляем / заменяем
        case_step_extra.update(keys_to_copy)


async def init_browser(input_state: InputState) -> AgentState:
    """
    Initialize the browser environment and set up the agent state.

    This function sets up logging, database connections, browser context, and initializes
    all necessary components for the agent to execute tasks. It creates directories for
    screenshots, configures the browser with appropriate settings, and prepares the initial
    agent state with all required parameters.

    Args:
        input_state (InputState): The initial input state containing run_id, case details,
                                 user_id, and environment settings

    Returns:
        AgentState: The initialized agent state with all components ready for task execution

    Raises:
        ValueError: If required fields are missing in the task
        Exception: If cloud instance or model is not running
    """
    start_dt = datetime.now(timezone.utc)

    # Create initial state with defaults to enable proper cleanup even on early failures
    agent_state = AgentState(
        browser=None,
        context=None,
        session=None,
        tab_manager=None,
        user_storage=None,
        page=None,
        logger=None,
        log_buffer=None,
        log_handler=None,
        action_plan=[],
        steps_descriptions=[],
        screenshot_base_path=Path("screenshots") / input_state.run_id,
        trace_file_path=f"{input_state.run_id}_trace.zip",
        run_id=input_state.run_id,
        case_id="",
        case_name="",
        case_steps=[],
        inference_client=None,
        reflection_client=None,
        start_dt=start_dt,
        width=1920,
        height=1080,
        status=CaseStatusEnum.PASSED,
        run_summary='',
        local_async_engine=None,
        background_video_generate=input_state.background_video_generate

    )

    try:
        logger = logging.getLogger(str(uuid4()))
        log_buffer = StringIO()
        log_handler = logging.StreamHandler(log_buffer)
        formatter = logging.Formatter('%(asctime)s (%(filename)s:%(funcName)s:%(lineno)d) [%(levelname)s] - %(message)s')
        log_handler.setFormatter(formatter)
        logger.addHandler(log_handler)
        logger.setLevel(logging.INFO)

        # Update state with logging components
        agent_state.logger = logger
        agent_state.log_buffer = log_buffer
        agent_state.log_handler = log_handler

        status = CaseStatusEnum.PASSED
        run_summary = ''

        local_async_engine = create_async_engine(DB_URL,
                                                 future=True,
                                                 echo=False,
                                                 pool_size=1,
                                                 max_overflow=0,
                                                 pool_pre_ping=True,
                                                 pool_recycle=1800,
                                                 pool_timeout=90,
                                                 connect_args={"statement_cache_size": 0},
                                                 json_serializer=custom_serialize, json_deserializer=custom_deserialize)
        local_async_session = sessionmaker(local_async_engine, expire_on_commit=True,
                                           autoflush=False, class_=AsyncSession, future=True)
        session = local_async_session()

        # Update state with database components
        agent_state.session = session
        agent_state.local_async_engine = local_async_engine

        await update_run_case_status(run_id=input_state.run_id,
                                     status=CaseStatusEnum.IN_PROGRESS,
                                     start_dt=start_dt,
                                     session=session)

        retry_settings = RetrySettings(
            enabled=input_state.environment.get('retry_enabled', False),
            timeout=input_state.environment.get('retry_timeout', 30)
        )
        agent_state.retry_settings = retry_settings
        logger.info(f"retry_settings: {agent_state.retry_settings}")

        inference_ip, inference_client, reflection_client = await InferenceClientRegistry.get_clients(
            model_type=INFERENCE_MODEL,
            reflection_model=REFLECTION_MODEL,
        )
        logger.info(f"Using inference endpoint: {inference_ip}")
        agent_state.inference_client = inference_client
        agent_state.reflection_client = reflection_client

        # входящие
        case = input_state.case
        case_id = case.get('case_id')
        case_name = case.get('name')
        url = case.get('url') or 'https://www.example.com/'

        # запрет вне контура таких url
        if LOCALHOST_DISABLED:
            if is_local_url(url):
                status = CaseStatusEnum.FAILED
                run_summary = 'LOCALHOST_DISABLED'
                agent_state.status = status
                agent_state.run_summary = run_summary
                return agent_state

        user_storage = case.get('user_storage')
        logger.info(f"user_storage: {user_storage}")

        action_plan = case.get('action_plan')
        case_steps = case.get('before_browser_start', []) + case.get('before_steps', []) + case.get('steps', []) + case.get('after_steps', [])

        # Update state with case information
        agent_state.case_id = case_id or ""
        agent_state.case_name = case_name or ""
        agent_state.action_plan = action_plan or []
        agent_state.case_steps = case_steps

        trace_file_path = f"{input_state.run_id}_trace.zip"
        screenshot_base_path = Path("screenshots") / input_state.run_id
        screenshot_base_path.mkdir(parents=True, exist_ok=True)

        # Update state with file paths
        agent_state.trace_file_path = trace_file_path
        agent_state.screenshot_base_path = screenshot_base_path

        if not all([input_state.run_id, case_id, case_name, action_plan, url]):
            raise ValueError("missing fields are required in the task")

        resolution = input_state.environment.resolution
        width = resolution.width
        height = resolution.height

        # контекстные скриншоты
        await prepare_context_screenshots(action_plan=agent_state.action_plan,
                                          screenshot_base_path=agent_state.screenshot_base_path,
                                          width=width,
                                          height=height)

        await copy_context_screenshot_meta_to_case_steps(action_plan=agent_state.action_plan,
                                                         case_steps=agent_state.case_steps)

        logger.info(f"Action plan: {agent_state.action_plan}")

        browser_type = input_state.environment.get("browser", "firefox")

        agent_state.width = width
        agent_state.height = height

        proxy_settings = None
        use_proxy = False

        p = await async_playwright().start()

        logger.info(f"Launching browser {browser_type}. run_id: {input_state.run_id}. {use_proxy=}")

        if browser_type == 'firefox':
            browser = await p.firefox.launch(headless=True,
                                             proxy=proxy_settings,
                                             firefox_user_prefs={"dom.webdriver.enabled": False})
            user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:132.0) Gecko/20100101 Firefox/132.0"
        elif browser_type == 'chrome':
            browser = await p.chromium.launch(channel='chrome',
                                              proxy=proxy_settings,
                                              headless=True,
                                              args=[
                                                  "--disable-blink-features=AutomationControlled",
                                                  "--disable-web-security"
                                              ])
            user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.6723.58 Safari/537.36"

        else:  # вернуть ошибку что такого нет?
            browser = await p.firefox.launch(headless=True,
                                             proxy=proxy_settings,
                                             firefox_user_prefs={"dom.webdriver.enabled": False})
            user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:132.0) Gecko/20100101 Firefox/132.0"

        context = await browser.new_context(
            viewport={"width": width, "height": height},
            locale="en-US",
            bypass_csp=True,
            ignore_https_errors=True,
            extra_http_headers={
                "Accept": "image/avif,image/webp,image/png,image/svg+xml,image/*;q=0.8,*/*;q=0.5",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br, zstd",
                "Upgrade-Insecure-Requests": "1",
                "User-Agent": user_agent,
                "Cache-Control": "max-age=0"
            }
        )

        agent_state.playwright = p
        agent_state.browser = browser
        agent_state.context = context

        agent_state.user_storage = UserStorage(user_storage)
        agent_state.tab_manager = TabManager(agent_state.context)
        agent_state.page = await agent_state.tab_manager.initialize_pages()

        # пишем трассировку
        await agent_state.context.tracing.start(title=case_name,
                                                screenshots=True,
                                                snapshots=True,
                                                sources=False,
                                                screencast_options={'width': width, 'height': height, 'quality': 90}
                                                )

        # await page.route("**/*", handle_request)
        try:
            await agent_state.tab_manager.navigate(url, agent_state.page)
        except Exception as e:
            logger.error(f"Error navigating to {url}: {e}")
            status = CaseStatusEnum.FAILED
            run_summary = 'Error: could not navigate to the starting url'

        agent_state.status = status
        agent_state.run_summary = run_summary

        logger.info("Finished initialization")

        return agent_state

    except Exception as e:
        # Log the error if logger is available
        if agent_state.logger:
            agent_state.logger.error(f"Error during initialization: {e}", exc_info=True)

        # Update state with error information
        agent_state.status = CaseStatusEnum.FAILED
        agent_state.run_summary = f"Error during initialization: {str(e)}"

        return agent_state


async def step_preparation(state: AgentState):
    """
    Prepare the agent state for executing the current step in the action plan.

    This function serves as the entry point for each iteration of the step execution loop.
    It performs common preparations for all action types, including:
    - Setting up step-specific state variables
    - Taking a screenshot before the action
    - Checking if the task should be stopped
    - Updating the current page reference

    Args:
        state (AgentState): The current state of the agent

    Returns:
        AgentState: Updated agent state prepared for the current step execution
    """
    current_step = state.action_plan[state.current_step_index]

    step_id = f"{state.current_step_index}_{state.current_attempt}"
    step_extra = current_step.get("extra")
    if not isinstance(step_extra, dict):
        step_extra = {}

    step_state = StepState(
        step_id=step_id,
        current_step=current_step,
        action=current_step['action_type'],
        element_description=current_step.get('element_description', None),
        container_description=current_step.get('container_description', None),
        before_screenshot_path=state.screenshot_base_path / \
            f'screenshot_{step_id}_before.jpeg',
        annotated_screenshot_path=state.screenshot_base_path / \
            f'screenshot_{step_id}_annotated.jpeg',
        after_screenshot_path=state.screenshot_base_path / \
            f'screenshot_{step_id}_after.jpeg',
        full_screenshot_path=state.screenshot_base_path / \
            f'screenshot_{step_id}_full.jpeg',
        context_screenshot_path=step_extra.get("context_screenshot_path_local", None),
        use_single_screenshot=step_extra.get("use_single_screenshot", True),
        start_time=time.time(),
        text_to_type=current_step.get('text_to_type', None),
        wait_time=int(current_step.get('wait_time') if current_step.get('wait_time') else 30),
        key_to_press=current_step.get('key_to_press', None),
        tab_name=current_step.get('tab_name', None),
        extra=current_step.get('extra', None),
    )
    state.step_state = step_state
    state.status = CaseStatusEnum.PASSED

    await process_variables_before_plain_step(state)

    if redis_client.sismember("stop_task", state.run_id):
        state.logger.info(f"Stopping task {state.run_id}")
        await update_run_case_stop(state.run_id, state.start_dt, state.session)
        state.status = CaseStatusEnum.STOPPED
        return state

    state.page = state.tab_manager.current_page()
    state.logger.info(
        f"======== Iteration Start ========\n"
        f"Step: {state.current_step_index}\n"
        f"Attempt: {state.current_attempt}\n"
        f"Action: {state.step_state.action}\n"
        f"Active page: {state.page}\n"
        f"Capturing before screenshot..."
    )

    current_action_type = state.step_state.action

    if current_action_type == "expected_result":
        # expected_result: используем скриншоты ПРЕДЫДУЩЕГО шага
        # completed_steps может быть пустым, если перешли в after из первого ошибочного степа
        if state.current_step_index == 0 or not state.completed_steps:
            # если первый шаг — рефлексия делает скриншоты
            await state.page.screenshot(path=state.step_state.before_screenshot_path, type='jpeg')
            # рефлексии нужен after
            state.step_state.after_screenshot_path = state.step_state.before_screenshot_path
            state.step_state.annotated_screenshot_path = state.step_state.before_screenshot_path
            state.logger.info("First step is expected_result — took initial screenshot")
        else:
            # Берём скрины последнего завершённого шага
            prev_step = state.completed_steps[-1]

            state.step_state.before_screenshot_path = prev_step.before_screenshot_path
            state.step_state.after_screenshot_path = prev_step.after_screenshot_path
            state.step_state.annotated_screenshot_path = prev_step.annotated_screenshot_path
            state.logger.info(f"expected_result reuses screenshots from step {prev_step.action} | {prev_step.step_id}")

    else:
        # Обычные шаги (CLICK, API) — ДЕЛАЕМ СВОЙ before-скриншот
        await state.page.screenshot(path=state.step_state.before_screenshot_path, type='jpeg')
        # after скриншот будет в конце шага в finish_iteration или send_error_message
        state.logger.info(f"Simple step {state.current_step_index} took before screenshot")

    return state


def step_preparation_router(state: AgentState):
    """
    Route the execution flow based on the current step's action type.

    This function determines which node(s) in the execution graph should be called next
    based on the action type of the current step. It handles special routing for actions
    that require coordinate inference or direct action execution.

    Args:
        state (AgentState): The current state of the agent

    Returns:
        str or list: The name(s) of the next node(s) to execute, or END if the task should stop
    """
    if state.status == CaseStatusEnum.STOPPED:
        return END
    else:
        return [ACTION_MAP[state.step_state.action].__name__]


def step_actions_router(state: AgentState):
    """
    Determine the next step in the execution flow based on the outcome of the current action.

    This function routes the execution flow based on the success or failure of the current step:
    - If the step has failed 3 times, it routes to send an error message
    - If the step failed but has been attempted fewer than 3 times, it retries the step
    - If the step passed, it proceeds to the reflection step

    Args:
        state (AgentState): The current state of the agent

    Returns:
        str: The name of the next node to execute
    """

    # if state.current_attempt > 2:  # шаг упал 3 раза
    #     if is_after_step(state):
    #         state.logger.info(f"After step {state.current_step_index} failed 3 times → mark after_step_failed")
    #         # return "send_error_message"   # завершаем
    #         return "mark_after_step_failed"
    #     else:
    #         state.logger.info(f"Step {state.current_step_index} failed 3 times → send_error_message")
    #         return "send_error_message"

    # elif state.status != CaseStatusEnum.PASSED:  # упал, но < 3 попыток, ретраим
    #     state.logger.info(f"Step {state.current_step_index} failed, retrying")
    #     return "step_preparation"

    # else:
    #     return "finish_iteration"

    if state.status != CaseStatusEnum.PASSED:  # шаг упал
        if is_after_step(state):
            state.logger.info(f"After step {state.current_step_index} failed → mark after_step_failed")
            # return "send_error_message"   # завершаем
            return "mark_after_step_failed"
        else:
            state.logger.info(f"Step {state.current_step_index} failed → send_error_message")
            return "send_error_message"
    else:
        return "finish_iteration"


def is_after_step(state: AgentState) -> bool:
    if state.current_step_index >= len(state.action_plan):
        return False
    current_step = state.action_plan[state.current_step_index]
    return current_step.get('step_group') == 'after_steps'


async def mark_after_step_failed(state: AgentState) -> AgentState:
    state.logger.info(f"Marking after_step_failed=True at step {state.current_step_index}")
    state.after_step_failed = True
    return state


def send_error_router(state: AgentState):
    # если вызвали для after-шагов — сразу END
    # с оыбчного шага переход в after
    # True -> END

    if state.status == CaseStatusEnum.STOPPED:
        return True

    if is_after_step(state) or state.after_step_failed:
        return True
    # если есть after_steps — False -> jump_to_after
    has_after = any(step.get("step_group") == "after_steps" for step in state.action_plan)

    return not has_after


async def jump_to_after(state: AgentState) -> AgentState:
    after_index = next(
        (i for i, step in enumerate(state.action_plan) if step.get("step_group") == "after_steps"),
        None
    )

    if after_index is not None:
        state.logger.info(f"Jumping to after_steps starting at index {after_index}")
        state.current_step_index = after_index
        state.current_attempt = 0
        # сбрасываем, чтобы не выйти в END
        if state.status != CaseStatusEnum.STOPPED:
            state.status = CaseStatusEnum.PASSED
    else:
        state.logger.info("No after_steps found, finishing")
        state.current_step_index = len(state.action_plan)
    return state


async def finish_iteration(state: AgentState) -> AgentState:
    """
    Complete the current step iteration and prepare for the next step.

    This function finalizes the current step by:
    - Ensuring the current page reference is up to date
    - Checking for and handling annotated screenshots
    - Uploading screenshots to storage
    - Updating the database with step results
    - Incrementing the step counter for the next iteration

    Args:
        state (AgentState): The current state of the agent

    Returns:
        AgentState: Updated agent state ready for the next step
    """
    state.logger.info("Step succesfully completed, finishing iteration")

    # making post-action screenshot after
    if state.step_state.action not in ["SCROLL", "INNER_SCROLL", "CLEAR", "WAIT", "expected_result"]:  # no need to wait after those actions
        await asyncio.sleep(POST_ACTION_WAIT_TIME)

    await state.tab_manager.current_page().screenshot(path=state.step_state.after_screenshot_path, type='jpeg')
    state.step_state.annotated_screenshot_path = check_annotated_screenshot_exists(state.step_state.annotated_screenshot_path,
                                                                                   state.step_state.before_screenshot_path, state.logger)

    before_filename = state.step_state.before_screenshot_path.name
    annotated_filename = state.step_state.annotated_screenshot_path.name
    after_filename = state.step_state.after_screenshot_path.name

    before_url = await asyncio.to_thread(upload_to_minio, state.step_state.before_screenshot_path, state.run_id, before_filename)
    before_annotated_url = await asyncio.to_thread(upload_to_minio, state.step_state.annotated_screenshot_path, state.run_id, annotated_filename)
    after_url = await asyncio.to_thread(upload_to_minio, state.step_state.after_screenshot_path, state.run_id, after_filename)

    # обычный степ содержит строку со значением, но в его экшен плане она раскладывается на параметры, поэтому их не берем
    api_extra = state.step_state.extra
    step_extra = state.case_steps[state.current_step_index].get("extra") if isinstance(state.case_steps[state.current_step_index], dict) else None

    extra = api_extra if state.step_state.action == 'API' else step_extra

    step_original_step_description = state.case_steps[state.current_step_index].get("value") if isinstance(state.case_steps[state.current_step_index], dict) else state.case_steps[state.current_step_index]
    api_original_step_description = state.step_state.extra.get("value") if isinstance(state.step_state.extra, dict) else state.case_steps[state.current_step_index]

    original_step_description = api_original_step_description if state.step_state.action == 'API' else step_original_step_description

    mess = {
        "status_step": state.status,
        "index_step": state.current_step_index,
        "original_step_description": original_step_description,
        #"raw_step_description": state.case_steps[state.current_step_index].get("raw_step_description"),  # not used anymore
        "validation_result": state.step_state.validation_result,
        "reflection_times": f"{state.step_state.reflection_time:.2f}",
        "extra": extra,
        # "part_num": state.current_step_index + 1,
        # "part_all": len(state.action_plan),
        "model_time": f"{state.step_state.model_time:.2f}",
        "step_time": f"{time.time() - state.step_state.start_time:.2f}",
        "action": state.step_state.action,
        "action_details": {
            "coords": state.step_state.coordinates,
            "text": state.step_state.text_to_type,
            "wait_time": state.step_state.wait_time,
            "scroll_data": {
                "x": 0,
                "deltaX": 0,
                "y": 0,
                "deltaY": state.step_state.scroll_y,
                "source": state.step_state.scroll_element if state.step_state.action == "INNER_SCROLL" else "body"
            },
            "key_to_press": state.step_state.key_to_press,
            "new_tab_url": state.step_state.tab_name,
            "switch_tab_name": state.step_state.tab_name
        },
        "before": before_url,
        "before_annotated_url": before_annotated_url,
        "after": after_url
    }
    await update_run_case_steps(state.session, state.run_id, mess)
    state.completed_steps.append(state.step_state)

    state.logger.info("Step completed \n-----------------------------")
    state.current_attempt = 0
    state.current_step_index += 1
    return state


async def send_error_message(state: AgentState) -> AgentState:
    """
    Handle error reporting when a step fails after multiple attempts.

    This function takes a final screenshot after the failed action, uploads
    the before and after screenshots to storage, and updates the database
    with information about the failed step.

    Args:
        state (AgentState): The current state of the agent

    Returns:
        AgentState: Updated agent state with error information
    """

    if not is_after_step(state):
        state.logger.info(f"Non-after step failed at index {state.current_step_index} → mark main_steps_failed=True")
        state.main_steps_failed = True

    # making post-action screenshot after
    await state.tab_manager.current_page().screenshot(path=state.step_state.after_screenshot_path, type='jpeg')
    state.step_state.annotated_screenshot_path = check_annotated_screenshot_exists(state.step_state.annotated_screenshot_path,
                                                                                   state.step_state.before_screenshot_path, state.logger)

    before_filename = state.step_state.before_screenshot_path.name
    annotated_filename = state.step_state.annotated_screenshot_path.name
    after_filename = state.step_state.after_screenshot_path.name

    before_url = await asyncio.to_thread(upload_to_minio, state.step_state.before_screenshot_path, state.run_id, before_filename)
    before_annotated_url = await asyncio.to_thread(upload_to_minio, state.step_state.annotated_screenshot_path, state.run_id, annotated_filename)
    after_url = await asyncio.to_thread(upload_to_minio, state.step_state.after_screenshot_path, state.run_id, after_filename)

    # у апи степов одинаковый шаг и его экшен план
    # у обычного степа экшен план отличается, своя структура и позиции с переменными, на фронт надо обычный.
    api_extra = state.step_state.extra
    step_extra = state.case_steps[state.current_step_index].get("extra") if isinstance(state.case_steps[state.current_step_index], dict) else None
    extra = api_extra if state.step_state.action == 'API' else step_extra

    step_original_step_description = state.case_steps[state.current_step_index].get("value") if isinstance(state.case_steps[state.current_step_index], dict) else state.case_steps[state.current_step_index]
    api_original_step_description = state.step_state.extra.get("value") if isinstance(state.step_state.extra, dict) else state.case_steps[state.current_step_index]
    original_step_description = api_original_step_description if state.step_state.action == 'API' else step_original_step_description

    mess = {
        "status_step": state.status,
        "index_step": state.current_step_index,
        "original_step_description": original_step_description,
        #"raw_step_description": state.case_steps[state.current_step_index].get("raw_step_description"),  # not used anymore
        "validation_result": state.step_state.validation_result,
        "reflection_times": f"{state.step_state.reflection_time:.2f}",
        "extra": extra,
        # "part_num": state.current_step_index + 1,
        # "part_all": len(state.action_plan),
        "model_time": f"{state.step_state.model_time:.2f}",
        "step_time": f"{time.time() - state.step_state.start_time:.2f}",
        "action": state.step_state.action,
        "action_details": {
            "coords": state.step_state.coordinates,
            "text": state.step_state.text_to_type,
            "wait_time": state.step_state.wait_time,
            "scroll_data": {
                "x": 0,
                "deltaX": 0,
                "y": 0,
                "deltaY": state.step_state.scroll_y,
                "source": state.step_state.scroll_element if state.step_state.action == "INNER_SCROLL" else "body"
            },
            "key_to_press": state.step_state.key_to_press,
            "new_tab_url": state.step_state.tab_name,
            "switch_tab_name": state.step_state.tab_name
        },
        "before": before_url,
        "before_annotated_url": before_annotated_url,
        "after": after_url
    }
    await update_run_case_steps(state.session, state.run_id, mess)
    return state


async def clean_up_and_finish(state: AgentState):
    """
    Perform final cleanup and reporting at the end of task execution.

    This function:
    - Stops browser tracing and generates a video from the trace
    - Updates the final task status in the database
    - Closes browser sessions and database connections
    - Uploads logs to storage
    - Cleans up temporary files and directories

    Args:
        state (AgentState): The current state of the agent

    Returns:
        None
    """

    video_url = None

    try:
        langfuse = get_client()
        langfuse.score_current_trace(
            name="Success",
            value=state.status == CaseStatusEnum.PASSED,
            data_type="BOOLEAN")
        langfuse.flush()
    except Exception as e:
        if state.logger:
            state.logger.error(f"Error shutting down langfuse: {e}")

    if state.context:
        try:
            await state.context.tracing.stop(path=state.trace_file_path)
            if state.logger:
                state.logger.info(f"Trace file saved: {state.trace_file_path}")

            if state.logger:
                state.logger.info("generate_video started...")
            start_generate_video_time = time.time()
            if state.background_video_generate is False:
                video_url = await process_trace_and_generate_video(state.trace_file_path, state.run_id)
            if state.logger:
                state.logger.info(f"generate_video done: {time.time() - start_generate_video_time:.2f}")
        except Exception as video_error:
            if state.logger:
                state.logger.error(f"Error during video generation: {video_error}")

    if state.status == CaseStatusEnum.STOPPED:
        final_status = CaseStatusEnum.STOPPED
    else:
        # main_steps_failed в приоритете над after_step_failed
        if state.main_steps_failed is True:
            final_status = CaseStatusEnum.FAILED
        elif state.after_step_failed is True:
            final_status = CaseStatusEnum.AFTER_STEP_FAILURE
        elif state.status == CaseStatusEnum.PASSED:
            final_status = CaseStatusEnum.PASSED
        else:
            final_status = CaseStatusEnum.FAILED

    state.status = final_status

    end_dt = datetime.now(timezone.utc)
    if state.session:
        try:
            await update_run_case_final_record(run_id=state.run_id,
                                               video=video_url,
                                               end_dt=end_dt,
                                               complete_time=(end_dt - state.start_dt).total_seconds(),
                                               status=state.status,
                                               run_summary=state.run_summary,
                                               session=state.session)
        except Exception as db_error:
            if state.logger:
                state.logger.error(f"Error updating final record: {db_error}")

    mess = {"run_id": state.run_id,
            "video": video_url,
            "start_dt": state.start_dt,
            "end_dt": end_dt,
            "complete_time": (end_dt - state.start_dt).total_seconds(),
            "status": state.status,
            "run_summary": state.run_summary}

    if state.logger:
        state.logger.info(f"Task completed: {mess}")

    try:
        redis_client.srem("stop_task", state.run_id)
    except Exception as redis_error:
        if state.logger:
            state.logger.error(f"Error cleaning up Redis: {redis_error}")

    if state.logger and state.log_handler:
        try:
            state.logger.removeHandler(state.log_handler)
            state.log_handler.close()
        except Exception as log_error:
            print(f"Error closing log handler: {log_error}")

    if state.session:
        try:
            await state.session.close()
        except Exception as session_error:
            if state.logger:
                state.logger.error(f"Error closing session: {session_error}")

    if state.local_async_engine:
        try:
            await state.local_async_engine.dispose()
        except Exception as engine_error:
            if state.logger:
                state.logger.error(f"Error disposing engine: {engine_error}")

    # пишем трассировку
    if state.context:
        try:
            trace_path = await asyncio.to_thread(upload_to_minio,
                                                 state.trace_file_path,
                                                 state.run_id,
                                                 state.trace_file_path)

            # отправляем таск в сервис генерации видео
            if state.background_video_generate is True:
                message = json.dumps({"args": [], "kwargs": {"db_name": DB_NAME, "trace_file_path": trace_path, "run_id": state.run_id}},
                                     ensure_ascii=False).encode('utf-8')
                await send_to_rabbitmq(queue_name='video_generation',
                                       message=message,
                                       correlation_id=state.run_id)
                if state.logger:
                    state.logger.info("Trace sent to rabbitmq")
        except Exception as trace_error:
            if state.logger:
                state.logger.error(f"Error while uploading trace: {trace_error}")

    try:
        if state.context:
            await state.context.close()
        if state.browser:
            await state.browser.close()
            if state.logger:
                state.logger.info("Browser closed")
        if state.playwright:
            await state.playwright.stop()
            if state.logger:
                state.logger.info("playwright closed")

    except Exception as close_error:
        if state.logger:
            state.logger.error(f"Error while closing browser: {close_error}")

    # Upload logs to Minio
    if state.log_buffer:
        try:
            await asyncio.to_thread(
                upload_buffer_to_minio,
                state.log_buffer,
                state.run_id,
                f"{state.run_id}.log"
            )
        except Exception as er:
            if state.logger:
                state.logger.error(f"Error while uploading log to minio: {er}")

    # Clean up directories
    try:
        await clean_up_directories(state.screenshot_base_path, state.trace_file_path)
    except Exception as cleanup_error:
        if state.logger:
            state.logger.error(f"Error cleaning up directories: {cleanup_error}")


def build_graph():
    """
    Build and configure the execution graph for the agent.

    Currently, the graph only contains the action execution loop.
    Initialization and cleanup are handled in the main function, to better handle errors and exceptions.

    Returns:
        StateGraph: The compiled execution graph ready for invocation
    """
    # adding nodes
    action_nodes = [coordinate_actions, action_scroll, action_inner_scroll, action_press,
                    action_new_tab, action_switch_tab, action_wait, action_read,
                    action_paste, action_select, action_api, reflection_step]

    agent_graph = StateGraph(AgentState)
    agent_graph.add_node("step_preparation", step_preparation)

    for action_node in action_nodes:
        agent_graph.add_node(action_node.__name__, action_node)

    agent_graph.add_node("jump_to_after", jump_to_after)
    agent_graph.add_node("send_error_message", send_error_message)
    agent_graph.add_node("finish_iteration", finish_iteration)
    agent_graph.add_node("mark_after_step_failed", mark_after_step_failed)

    # adding edges
    agent_graph.set_entry_point("step_preparation")
    agent_graph.add_edge("mark_after_step_failed", "send_error_message")

    agent_graph.add_conditional_edges(
        "step_preparation",
        step_preparation_router,
        ["coordinate_actions", "action_scroll", "action_new_tab", "action_switch_tab", "action_press",
         "action_wait", "action_inner_scroll", "action_read", "action_paste",
         "action_select", "action_api", "reflection_step", "send_error_message", END]
    )

    for action_node in action_nodes:
        agent_graph.add_conditional_edges(
            action_node.__name__,
            step_actions_router,
            ["step_preparation", "finish_iteration", "send_error_message", "jump_to_after", "mark_after_step_failed"]
        )

    # если это after-step (или уже помечено after_step_failed) -> END
    # иначе -> jump_to_after (если after есть) или END (если after нет)

    agent_graph.add_conditional_edges(
        "send_error_message",
        send_error_router,
        {
            True: END,
            False: "jump_to_after"
        }
    )

    # jump_to_after должен вести в step_preparation, чтобы начать выполнять after-шаги
    agent_graph.add_edge("jump_to_after", "step_preparation")

    agent_graph.add_conditional_edges(
        "finish_iteration",
        lambda state: state.current_step_index >= len(state.action_plan) or state.status != CaseStatusEnum.PASSED,
        {
            True: END,
            False: "step_preparation"
        }
    )

    # agent_graph.add_edge("send_error_message", END)

    agent_graph = agent_graph.compile()

    return agent_graph


agent_graph = build_graph()


@observe(as_type="span", capture_input=False, capture_output=False)
async def run_graph(run_id, case, user_id, environment, background_video_generate):
    """
    Execute the agent's workflow graph with the provided inputs.

    This function is the main entry point for running the agent. It:
    1. Creates an InputState from the provided parameters
    2. Initializes the browser environment
    3. Invokes the execution graph to perform the task
    4. Handles any exceptions that occur during execution
    5. Ensures cleanup is performed regardless of success or failure

    Args:
        run_id (str): Unique identifier for this run
        case (dict): Case details including action plan, URL, and validation steps
        user_id (str): Identifier for the user running the task
        environment (dict): Environment settings like screen resolution

    Returns:
        None
    """
    inputs = InputState(
        run_id=run_id,
        case=case,
        user_id=user_id,
        environment=environment,
        background_video_generate=background_video_generate
    )
    state = None
    try:
        langfuse = get_client()
        state = await init_browser(inputs)
        if state.status == CaseStatusEnum.FAILED:
            return
        langfuse.update_current_trace(
            user_id=inputs.user_id,
            session_id=inputs.case['case_id'],
            metadata={"run_id": inputs.run_id, "user_id": inputs.user_id},
            input=(state.action_plan),
        )

        total_timeout = 3600  # максимум час на весь ран
        try:
            state = await asyncio.wait_for(agent_graph.ainvoke(state, config={"recursion_limit": len(state.action_plan) * 3 * 10 + 10}),
                                           timeout=total_timeout)
        except asyncio.TimeoutError:
            raise Exception(f"TASK execution timed out after {total_timeout} seconds")
        # state = await agent_graph.ainvoke(state, config={"recursion_limit": len(state.action_plan) * 3 * 10 + 10})
        if not isinstance(state, AgentState):
            state = AgentState(**state)
    except Exception as e:
        error_trace = traceback.format_exc()
        print(f"Error: {e}")
        print(f"Error trace: {error_trace}")

        # If state was not created yet, create a minimal state for cleanup
        if state is None:
            state = AgentState(
                browser=None,
                context=None,
                session=None,
                tab_manager=None,
                user_storage=None,
                page=None,
                logger=None,
                log_buffer=None,
                log_handler=None,
                action_plan=[],
                steps_descriptions=[],
                screenshot_base_path=Path("screenshots") / run_id,
                trace_file_path=f"{run_id}_trace.zip",
                run_id=run_id,
                case_id="",
                case_name="",
                case_steps=[],
                inference_client=None,
                reflection_client=None,
                start_dt=datetime.now(timezone.utc),
                width=1920,
                height=1080,
                status=CaseStatusEnum.FAILED,
                run_summary=f"Error during execution: {str(e)}",
                local_async_engine=None,
                background_video_generate=True
            )
        elif not isinstance(state, AgentState):
            state = AgentState(**state)

        # Ensure error information is set
        state.status = CaseStatusEnum.FAILED
        if not state.run_summary:
            state.run_summary = "Error during execution: " + str(e)
    finally:
        if state is not None:
            await clean_up_and_finish(state)
