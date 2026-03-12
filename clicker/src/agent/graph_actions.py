import asyncio
import base64
import io
import time
from typing import Tuple

from langfuse import observe
from PIL import Image, ImageDraw

from agent.config import (
    CLICK_DELAY,
    INNER_SCROLL_CONFIDENCE_THRESHOLD,
    INNER_SCROLL_OVERLAP,
    PAGE_SCROLL_OVERLAP,
    SCROLL_BATCH_SIZE,
    SCROLL_CONFIDENCE_THRESHOLD,
    WAIT_CONFIDENCE_THRESHOLD,
)
from agent.schemas import AgentState, ReflectionResult, ReflectionStepConfig
from browser_actions.other import (
    execute_api_request,
    process_variables_after_response,
    process_variables_before_request,
    validate_response,
)
from core.schemas import ApiStep, CaseStatusEnum


def draw_point_on_screenshot(before_screenshot_path, annotated_screenshot_path, x, y, bbox=None, radius=4):
    """
    Draw a green circle at the specified coordinates on a screenshot and save it as a new image.

    Args:
        before_screenshot_path (str): Path to the original screenshot
        annotated_screenshot_path (str): Path where the annotated screenshot will be saved
        x (int): X-coordinate of the point to draw
        y (int): Y-coordinate of the point to draw
        bbox (list, optional): Bounding box coordinates [x1, y1, x2, y2] to draw a rectangle. Defaults to None.
        radius (int, optional): Radius of the circle to draw. Defaults to 4.

    Returns:
        None
    """
    with Image.open(before_screenshot_path) as img:
        draw = ImageDraw.Draw(img)

        if bbox:
            draw.rectangle([bbox[0], bbox[1], bbox[2], bbox[3]],
                           outline='darkred', width=3)

        draw.ellipse((x - radius, y - radius, x + radius, y +
                      radius), fill='green', outline='green')
        img.save(annotated_screenshot_path)


def draw_point_on_screenshot_base64(image_base64_string: str,
                                    x: int,
                                    y: int,
                                    bbox: tuple = None,
                                    output_format: str = "JPEG") -> str:
    image_bytes = base64.b64decode(image_base64_string)

    with Image.open(io.BytesIO(image_bytes)) as img:
        draw = ImageDraw.Draw(img)

        if bbox:
            draw.rectangle(bbox, outline='red', width=3)

        radius = 5
        draw.ellipse(
            (x - radius, y - radius, x + radius, y + radius),
            fill="green",
            outline="black"
        )

        with io.BytesIO() as output:
            img.save(output, format=output_format)
            output_bytes = output.getvalue()

    return base64.b64encode(output_bytes).decode('utf-8')


async def get_coordinates_with_retries(state: AgentState,
                                       clicker_prompt: str,
                                       no_negative: bool = False) -> Tuple[int, int]:
    """ получаем координаты с механикой ретраев"""

    retry_settings = getattr(state, "retry_settings", None)
    state.retry_messages_buffer = ""

    # Если ретраи выключены — делаем одну попытку
    if not retry_settings or not retry_settings.enabled:
        x, y = await state.inference_client.get_coordinates(str(state.step_state.before_screenshot_path),
                                                            clicker_prompt,
                                                            no_negative=no_negative,
                                                            context_screenshot_image_path=state.step_state.context_screenshot_path)
        return x, y

    timeout = retry_settings.timeout
    interval = retry_settings.interval
    logger = state.logger
    step_id = state.step_state.step_id

    start_time = time.time()

    async def retry_loop() -> Tuple[int, int]:
        """динамическое количество попыток до победы или до таймаута wait_for."""

        attempt = 0

        while True:
            attempt += 1

            # Делаем новый скрин, перезаписываем before, если попытка не первая
            if attempt > 1:
                await state.page.screenshot(
                    path=state.step_state.before_screenshot_path,
                    type="jpeg",
                )

            _cnt_attempt = "First attempt" if attempt == 1 else f"Retry attempt {attempt}"
            elapsed = time.time() - start_time

            logger.info(f"{_cnt_attempt} for step {step_id} (elapsed: {elapsed:.2f}s/{timeout}s)")

            x, y = await state.inference_client.get_coordinates(
                str(state.step_state.before_screenshot_path),
                clicker_prompt,
                no_negative=no_negative,
                context_screenshot_image_path=state.step_state.context_screenshot_path
            )

            # координаты найдены
            if not (x == 0 and y == 0):
                return x, y

            # элемент не найден
            elapsed = time.time() - start_time
            mess = (
                f"[Step_id: {step_id}] [Action: {state.step_state.action}] Element not found within {timeout}s timeout "
                f"after {attempt} attempts (elapsed: {elapsed:.2f}s/{timeout}s). "
                f"wait {interval}s before next attempt...\n")
            state.retry_messages_buffer += mess
            logger.info(mess)

            # ждем пару сек для прогрузки сайта
            await asyncio.sleep(interval)

    try:
        x, y = await asyncio.wait_for(retry_loop(), timeout=timeout)
        return x, y

    except asyncio.TimeoutError:
        elapsed = time.time() - start_time
        logger.info(
            f"[ATTEMPTS TIMEOUT] Could not find element for step {step_id} with {timeout}s timeout (elapsed: {elapsed:.2f}s).")
        return 0, 0


async def get_reflection_with_retries(state: AgentState,
                                      reflection_task: ReflectionStepConfig) -> ReflectionResult:
    state.retry_messages_buffer = ""
    state.retry_temp_result_reflection = None

    retry_settings = getattr(state, "retry_settings", None)
    retries_enabled = retry_settings and retry_settings.enabled

    timeout = retry_settings.timeout if retries_enabled else 0
    interval = retry_settings.interval if retries_enabled else 0

    async def call_reflection() -> ReflectionResult:
        use_two_screenshots = (
            state.step_state.before_screenshot_path
            and state.step_state.after_screenshot_path
            and not reflection_task.use_single_screenshot
        )

        if use_two_screenshots:
            state.logger.info(f"Performing two-screenshot verification for step {state.current_step_index}")
            return await state.reflection_client.verify_two_screenshots(
                state.step_state.before_screenshot_path,
                state.step_state.after_screenshot_path,
                reflection_task.instruction,
                logger=state.logger,
                use_single_screenshot=False
            )
        else:
            state.logger.info(f"Performing one-screenshot verification for step {state.current_step_index}")
            return await state.reflection_client.verify_screenshot(
                state.step_state.after_screenshot_path,
                reflection_task.instruction,
                logger=state.logger
            )

    if not retries_enabled:
        return await call_reflection()

    step_id = state.step_state.step_id
    start_time = time.time()
    attempt = 0

    async def retry_loop() -> ReflectionResult:
        nonlocal attempt

        while True:
            attempt += 1

            if attempt > 1:
                state.step_state.after_screenshot_path = state.screenshot_base_path / \
                    f'screenshot_{step_id}_{attempt}_after.jpeg'

                await state.page.screenshot(
                    path=state.step_state.after_screenshot_path,
                    type="jpeg",
                )

            elapsed = time.time() - start_time
            state.logger.info(f"Reflection attempt {attempt} for step {step_id} (elapsed: {elapsed:.2f}s/{timeout}s)")

            result = await call_reflection()
            state.retry_temp_result_reflection = result

            if result.verification_passed:
                return result

            elapsed = time.time() - start_time
            mess = (
                f"[Step_id: {step_id}] Reflection failed after {attempt} attempts "
                f"(elapsed: {elapsed:.2f}s/{timeout}s). Waiting {interval}s...\n"
                f"Details: {result.details}\n"
            )
            state.retry_messages_buffer += mess
            state.logger.info(mess)

            await asyncio.sleep(interval)

    try:
        return await asyncio.wait_for(retry_loop(), timeout=timeout)
    except asyncio.TimeoutError:
        elapsed = time.time() - start_time
        state.logger.info(f"[TIMEOUT] Reflection failed after {timeout}s ({attempt} attempts, elapsed: {elapsed:.2f}s)")

        if state.retry_temp_result_reflection:
            return state.retry_temp_result_reflection

        return ReflectionResult(
            instruction_language="",
            thought_process="",
            details="ATTEMPTS TIMEOUT",
            verification_passed=False
        )


@observe(as_type="span", capture_input=False, capture_output=False)
async def coordinate_actions(state: AgentState) -> AgentState:
    """
    Execute actions that require coordinates: CLICK, HOVER, TYPE, CLEAR.

    This function performs the appropriate action based on the action type in the step state.
    It first checks if model was able to find the target element, then performs the action
    at the specified coordinates.

    Args:
        state (AgentState): The current state of the agent

    Returns:
        AgentState: Updated agent state after performing the action
    """

    # if state.step_state.action in ["CLICK", "TYPE"]:
    #     clicker_prompt = state.step_state.element_description
    # else:
    clicker_prompt = f"{state.step_state.element_description}"
    state.logger.info(f"Calling model_clicker inference for step {state.step_state.step_id} | {clicker_prompt=}")
    start_time = time.time()
    # state.step_state.coordinates = await state.inference_client.get_coordinates(
    #     str(state.step_state.before_screenshot_path),
    #     clicker_prompt
    #     )
    state.step_state.coordinates = await get_coordinates_with_retries(state, clicker_prompt)
    x, y = state.step_state.coordinates
    state.step_state.model_time += time.time() - start_time
    state.logger.info(
        f"Clicker inference result for step {state.step_state.step_id}: ({x}, {y}) | generate_time: {state.step_state.model_time:.2f}")
    # await asyncio.to_thread(draw_point_on_screenshot, str(state.step_state.before_screenshot_path), state.step_state.annotated_screenshot_path, x, y)

    if x == 0 and y == 0:
        logger_message = f"Could not find the target element in the image for the step {state.step_state.step_id}. Stopping execution..."
        state.run_summary += f"Step {state.step_state.step_id}: Couldn't find the target element.\n{state.retry_messages_buffer}"
        state.logger.info(logger_message)
        state.status = CaseStatusEnum.FAILED
        return state

    await asyncio.to_thread(draw_point_on_screenshot, str(state.step_state.before_screenshot_path),
                            state.step_state.annotated_screenshot_path, x, y)
    state.logger.info(f"Performing {state.step_state.action} action at {x}, {y}")
    state.page = state.tab_manager.current_page()

    if state.step_state.action == "CLICK":
        # чекаем элемент на таргеты
        maybe_will_open_new_tab = await state.tab_manager.check_if_click_opens_new_tab(
            state.page, float(x), float(y)
        )

        await state.page.mouse.click(float(x), float(y), delay=CLICK_DELAY)

        # Если есть вероятнось перехода, ждем что сработает триггер pw
        if maybe_will_open_new_tab:
            state.logger.info("maybe_will_open_new_tab, waiting for event (max 10s)...")

            new_page_opened = await state.tab_manager.wait_for_possible_new_page(timeout=10)

            if new_page_opened:
                state.page = state.tab_manager.current_page()
                state.logger.info(f"Successfully switched to new page: {state.page.url}")
            else:
                state.logger.info("New page not detected, continuing with current page")

    elif state.step_state.action == "HOVER":
        await state.page.mouse.move(float(x), float(y))
    elif state.step_state.action == "TYPE":
        await state.page.mouse.click(float(x), float(y), delay=CLICK_DELAY)
        await state.page.keyboard.press('Home')
        await state.page.keyboard.type(state.step_state.current_step['text_to_type'], delay=20)
    elif state.step_state.action == "CLEAR":
        await state.page.mouse.click(float(x), float(y), delay=CLICK_DELAY)
        await state.page.keyboard.press('Control+A')
        await state.page.keyboard.press("Backspace")
        await state.page.mouse.click(float(x), float(y), delay=CLICK_DELAY)

    return state


@observe(as_type="span", capture_input=False, capture_output=False)
async def reflection_step(state: AgentState) -> AgentState:
    """
    Perform post-action verification and reflection tasks.

    This function takes a screenshot after the action is performed and runs any
    reflection tasks defined for the current step. Reflection tasks verify that
    the action had the expected effect on the page. If any reflection task fails,
    the step is marked as failed and the task is stopped immediately.

    Args:
        state (AgentState): The current state of the agent

    Returns:
        AgentState: Updated agent state after performing reflection tasks
    """
    try:

        reflection_task = ReflectionStepConfig(instruction=state.step_state.current_step['value'],
                                               use_single_screenshot=state.step_state.use_single_screenshot)

        state.logger.info(f"Reflection step: use_single_screenshot - {reflection_task.use_single_screenshot} | {reflection_task.instruction}")
        state.logger.info(
            f"Use screenshots:\n{state.step_state.before_screenshot_path}\n{state.step_state.after_screenshot_path}")

        start_time = time.time()

        result = await get_reflection_with_retries(state, reflection_task)

        state.step_state.reflection_time = (time.time() - start_time)
        state.logger.info(f"Reflection result: {result}")
        state.step_state.validation_result = {
            "reflection_step": reflection_task.instruction,
            "reflection_title": "",
            "reflection_description": result.details,
            "reflection_thoughts": result.thought_process,
            "reflection_result": 'passed' if result.verification_passed else 'failed'
        }

        if not result.verification_passed:
            logger_message = f"Stopping execution...failed in reflection_step {state.step_state.step_id}"
            state.run_summary += f"Step {state.step_state.step_id}: reflection_step failed\n{state.retry_messages_buffer}"
            state.logger.info(logger_message)
            state.status = CaseStatusEnum.FAILED

        return state
    except Exception as er:
        logger_message = f"Stopping execution...error in reflection_step {repr(er)}"
        state.run_summary += f"Step {state.step_state.step_id}: reflection_step error {repr(er)}\n"
        state.logger.info(logger_message)
        state.status = CaseStatusEnum.FAILED
        return state


@observe(as_type="span", capture_input=False, capture_output=False)
async def action_scroll(state: AgentState) -> AgentState:
    """
    Perform a page scroll action to find a specific element.

    This function takes a full-page screenshot, divides it into sections, and uses
    model inference to determine which section contains the target element. It then
    scrolls to that section.

    Args:
        state (AgentState): The current state of the agent

    Returns:
        AgentState: Updated agent state after performing the scroll action
    """

    state.page = state.tab_manager.current_page()

    total_height = await state.page.evaluate("document.body.scrollHeight")
    state.logger.info(f"set_viewport_size: {total_height=}")
    # await page.screenshot(full_page=True, path=full_screenshot_path, type='jpeg')
    await state.page.set_viewport_size({"width": state.width, "height": total_height})
    await state.page.screenshot(path=state.step_state.full_screenshot_path, type='jpeg')
    await state.page.set_viewport_size({"width": state.width, "height": state.height})

    start_time = time.time()
    scroll_results = await state.inference_client.get_scroll_scores(
        image_path=state.step_state.full_screenshot_path,
        element_description=state.step_state.current_step['scroll_target'],
        crop_len=state.height
    )
    scroll_model_time = time.time() - start_time
    state.step_state.model_time += scroll_model_time
    state.logger.info(f"Scroll results: {scroll_results} | generate_time: {scroll_model_time:.2f}")
    state.step_state.detection_confidence = scroll_results
    # state.step_state.annotated_screenshot_path = await asyncio.to_thread(draw_point_on_screenshot, str(state.step_state.before_screenshot_path), state.step_state.annotated_screenshot_path, state.width // 2, scroll_amount)

    if max(state.step_state.detection_confidence) < SCROLL_CONFIDENCE_THRESHOLD:
        state.run_summary += f"Step {state.step_state.step_id}: Couldn't find the element to scroll to.\n"
        state.logger.info("No element with high enough confidence found. Stopping execution...")
        state.status = CaseStatusEnum.FAILED
        return state

    max_index = max(range(len(state.step_state.detection_confidence)),
                    key=state.step_state.detection_confidence.__getitem__)
    scroll_amount = max_index * state.height

    state.step_state.scroll_y = scroll_amount

    state.logger.info(f"Performing SCROLL action. Scrolling {scroll_amount} pixels, max_index: {max_index}")
    await state.page.evaluate(f"window.scrollTo(0, {scroll_amount})")
    # обязательно задержка, иначе after скриншот неактуальный, это будет видно на следующем шаге
    await asyncio.sleep(0.5)

    return state


@observe(as_type="span", capture_input=False, capture_output=False)
async def action_inner_scroll(state: AgentState) -> AgentState:
    """
    Perform a scroll action within a scrollable element.

    This function identifies a scrollable element by predicting coordinates of the element and then looking for the closest scrollable ancestor,
    then takes multiple screenshots as it scrolls through the element, and uses model inference to determine which screenshot contains the target item.
    It then scrolls to the position where the target item is located.

    There is a special case for the page element, where the scrollable element is the whole page.
    In this case, the function identifies the scrollable element as the whole page and scrolls it.

    Args:
        state (AgentState): The current state of the agent

    Returns:
        AgentState: Updated agent state after performing the inner scroll action
    """

    SCROLL_FACTOR = 2 / 3  # шаг прокрутки (чем меньше, тем больше перекрытие)
    SCROLL_DELAY = 0.2  # задержка между скроллами
    MAX_SCROLL_HEIGHT = 20000  # страховка от бесконечной подгрузки
    MAX_SCROLLS = 30  # максимум скроллов (скринов)

    async def find_scrollable_element(page, x, y):
        return await page.evaluate_handle("""({x, y}) => {
            const elements = document.elementsFromPoint(x, y);

            for (const el of elements) {
                const style = window.getComputedStyle(el);
                const isScrollableY = (
                    el.scrollHeight > el.clientHeight &&
                    (style.overflowY === 'scroll' || style.overflowY === 'auto')
                );

                if (isScrollableY) {
                    return el;
                }

                // Check if element is inside iframe
                let frameElement = el;
                while (frameElement) {
                    if (frameElement.tagName === 'IFRAME') {
                        try {
                            const rect = frameElement.getBoundingClientRect();
                            const frameX = x - rect.left;
                            const frameY = y - rect.top;

                            const frameDoc = frameElement.contentDocument ||
                                        (frameElement.contentWindow && frameElement.contentWindow.document);

                            if (frameDoc) {
                                const frameElements = frameDoc.elementsFromPoint(frameX, frameY);
                                for (const frameEl of frameElements) {
                                    const frameStyle = window.getComputedStyle(frameEl);
                                    const frameIsScrollableY = (
                                        frameEl.scrollHeight > frameEl.clientHeight &&
                                        (frameStyle.overflowY === 'scroll' || frameStyle.overflowY === 'auto')
                                    );

                                    if (frameIsScrollableY) {
                                        return frameEl;
                                    }
                                }
                            }
                        } catch (e) {
                            console.log('Cannot access iframe content:', e);
                        }
                    }
                    frameElement = frameElement.parentElement;
                }
            }

            return null;
        }""", {"x": x, "y": y})

    state.step_state.annotated_screenshot_path = state.step_state.before_screenshot_path
    if state.step_state.current_step['container_description'].lower() == "page":
        state.step_state.coordinates = (state.width // 2, state.height // 2)
        state.step_state.model_time = 0
    else:
        clicker_prompt = f"Click at the center of opened scrollable element described as: {state.step_state.current_step['container_description']}"
        state.logger.info(f"Calling model_clicker inference for step {state.step_state.step_id} | {clicker_prompt=}")
        start_time = time.time()
        state.step_state.coordinates = await get_coordinates_with_retries(state, clicker_prompt, no_negative=True)
        state.step_state.model_time = time.time() - start_time
    state.logger.info(f"Predicted coordinates of the element to scroll: {state.step_state.coordinates}")

    # identifying the playwright element to scroll
    state.page = state.tab_manager.current_page()
    scrollable_element = await find_scrollable_element(state.page,
                                                       state.step_state.coordinates[0],
                                                       state.step_state.coordinates[1])

    if scrollable_element is None:
        state.run_summary += f"Step {state.step_state.step_id}: Scrollable element not found at {state.step_state.coordinates}.\n{state.retry_messages_buffer}"
        state.logger.info("Element not found. Stopping execution...")
        state.status = CaseStatusEnum.FAILED
        return state

    scrollable_info = await scrollable_element.evaluate(
        """el => el ? {
            scrollHeight: el.scrollHeight,
            clientHeight: el.clientHeight,
            scrollTop: el.scrollTop,
            boundingBox: el.getBoundingClientRect()
        } : null"""
    )

    if scrollable_info is None:
        # iframe_info = await state.page.evaluate("""({x, y}) => {
        #     const iframe = document.elementsFromPoint(x, y).find(el => el.tagName === 'IFRAME');
        #     if (!iframe) return null;

        #     return {
        #         src: iframe.src,
        #         scrolling: iframe.scrolling,
        #         styleOverflow: window.getComputedStyle(iframe).overflowY,
        #         scrollHeight: iframe.scrollHeight,
        #         clientHeight: iframe.clientHeight,
        #         contentDocument: !!iframe.contentDocument
        #     };
        # }""", {"x": state.step_state.coordinates[0], "y": state.step_state.coordinates[1]})

        # state.logger.info(f"Iframe info: {iframe_info}")

        state.run_summary += f"Step {state.step_state.step_id}: Couldn't get scrollable element info.\n"
        state.logger.info("Scrollable element not found. Stopping execution...")
        state.status = CaseStatusEnum.FAILED
        return state

    scroll_height = scrollable_info['scrollHeight']
    client_height = scrollable_info['clientHeight']
    bounding_box = scrollable_info['boundingBox']
    first_scroll_position = scrollable_info['scrollTop']

    state.logger.info(f"Scrollable element info: \n {bounding_box=} \n {scroll_height=} \n {client_height=}")

    # scrolling and capturing screenshots
    crops = []
    scroll_positions = []

    # встаем в начало элемента
    await scrollable_element.evaluate("el => el.scrollTop = 0")
    await asyncio.sleep(SCROLL_DELAY)

    for scroll_count in range(MAX_SCROLLS):
        # нужно запрашивать каждый раз, так как  высота элемента может динамически меняться
        real_scroll = await scrollable_element.evaluate("el => el.scrollTop")  # позиция скролла
        scroll_positions.append(real_scroll)

        client_height = await scrollable_element.evaluate("el => el.clientHeight")  # видимая область
        scroll_height = await scrollable_element.evaluate(
            "el => el.scrollHeight")  # макс высота элемента, на которую можно прокрутить

        screenshot_path = state.screenshot_base_path / f'scroll_{scroll_count}.jpeg'
        await scrollable_element.screenshot(path=screenshot_path, type='jpeg')
        state.logger.info(
            f"screenshot saved: {screenshot_path}, "
            f"scroll_count: {scroll_count}, scrollTop: {real_scroll}, clientHeight: {client_height}, scrollHeight: {scroll_height}"
        )
        crops.append(screenshot_path)

        # Лимит на бесконечную ленту
        if scroll_height > MAX_SCROLL_HEIGHT:
            state.logger.info(f"Exceeded MAX_SCROLL_HEIGHT ({MAX_SCROLL_HEIGHT}px), stopping.")
            break

        # Дошли до низа?
        if real_scroll + client_height >= scroll_height - 2:
            break

        # следующая позиция скролла
        scroll_step = int(client_height * SCROLL_FACTOR)
        next_scroll = real_scroll + scroll_step - INNER_SCROLL_OVERLAP

        # если выйдет за предел, то устанавливаем максимум
        if next_scroll > scroll_height - client_height:
            next_scroll = scroll_height - client_height

        # Прокручиваем
        await scrollable_element.evaluate("(el, scroll) => el.scrollTop = scroll", next_scroll)
        await asyncio.sleep(SCROLL_DELAY)

        # На самом ли деле прокрутили, или ничего не поменялось?
        new_scroll = await scrollable_element.evaluate("el => el.scrollTop")
        if new_scroll == real_scroll:
            state.logger.info("ScrollTop not change")
            break

    state.logger.info(f"Scrolled and captured {len(crops)} screenshots")

    if state.step_state.current_step['container_description'].lower() == "page":
        crop_len = client_height - PAGE_SCROLL_OVERLAP
    else:
        crop_len = client_height - INNER_SCROLL_OVERLAP

    # predicting the best scroll amount
    # TODO: move to separate node?
    state.logger.info(f"Calling scroll inference for step {state.step_state.step_id}")
    scroll_results = []
    start_time = time.time()
    for i in range(0, len(crops), SCROLL_BATCH_SIZE):  # TODO: investigate inference server OOMs with concurent requests
        scroll_results.extend(await state.inference_client.get_scroll_scores(
            image_path="",
            element_description=state.step_state.current_step['scroll_target'],
            crop_len=crop_len,
            crops=crops[i:i + SCROLL_BATCH_SIZE]
        ))
    state.step_state.model_time += time.time() - start_time
    state.logger.info(f"Scroll results: {scroll_results} | generate_time: {state.step_state.model_time:.2f}")
    state.step_state.detection_confidence = scroll_results

    if max(state.step_state.detection_confidence) < INNER_SCROLL_CONFIDENCE_THRESHOLD:
        state.run_summary += f"Step {state.step_state.step_id}: Couldn't find the option to scroll to.\n"
        state.logger.info("No element with high enough confidence found. Stopping execution...")
        state.status = CaseStatusEnum.FAILED

        # в случае ошибок, возвращаем изначальную позицию, для корректного before, иначе он будет с прокруткой до конца
        await scrollable_element.evaluate("(el, scroll) => el.scrollTop = scroll", first_scroll_position)
        return state

    max_index = max(range(len(state.step_state.detection_confidence)),
                    key=state.step_state.detection_confidence.__getitem__)
    scroll_amount = scroll_positions[max_index]
    state.logger.info(f"Performing INNER_SCROLL action. Scrolling {scroll_amount} pixels, max_index: {max_index}")
    await scrollable_element.evaluate(f'el => el.scrollTop = {scroll_amount};')

    state.step_state.scroll_y = scroll_amount
    state.step_state.scroll_element = await scrollable_element.evaluate("el => el.tagName")

    return state


@observe(as_type="span", capture_input=False, capture_output=False)
async def action_new_tab(state: AgentState) -> AgentState:
    """
    Create a new browser tab and navigate to the specified URL.

    Args:
        state (AgentState): The current state of the agent

    Returns:
        AgentState: Updated agent state after creating a new tab
    """
    state.logger.info(f"Performing NEW_TAB action. Navigating to {state.step_state.current_step['tab_name']}")
    new_tab_url = state.step_state.current_step['tab_name']
    _ = await state.tab_manager.create_new_tab_and_navigate(new_tab_url)
    state.page = state.tab_manager.current_page()
    return state


@observe(as_type="span", capture_input=False, capture_output=False)
async def action_switch_tab(state: AgentState) -> AgentState:
    """
    Switch to an existing browser tab with the specified name.
    The search is performed by url and title.

    Args:
        state (AgentState): The current state of the agent

    Returns:
        AgentState: Updated agent state after switching tabs
    """
    state.logger.info(f"Performing SWITCH_TAB action. Switching to tab {state.step_state.current_step['tab_name']}")
    tab_name = state.step_state.current_step['tab_name']
    tab = await state.tab_manager.find_tab(tab_name, how="all")
    if tab is None:
        state.run_summary += f"Step {state.step_state.step_id}: Couldn't find the tab to switch to.\n"
        state.logger.info(f"Tab with name {tab_name} not found. Stopping execution...")
        state.status = CaseStatusEnum.FAILED
        return state
    await state.tab_manager.switch_to_tab(tab)
    state.page = state.tab_manager.current_page()
    return state


@observe(as_type="span", capture_input=False, capture_output=False)
async def action_press(state: AgentState) -> AgentState:
    """
    Simulate pressing a keyboard key.

    Args:
        state (AgentState): The current state of the agent

    Returns:
        AgentState: Updated agent state after pressing the key
    """
    state.logger.info(f"Performing PRESS action. Pressing {state.step_state.current_step['key_to_press']}")
    key = state.step_state.current_step['key_to_press']
    state.page = state.tab_manager.current_page()
    await state.page.keyboard.press(key)
    await asyncio.sleep(0.5)
    return state


@observe(as_type="span", capture_input=False, capture_output=False)
async def action_api(state: AgentState) -> AgentState:
    """
    api requests.

    Args:
        state (AgentState): The current state of the agent

    Returns:
        AgentState: Updated agent state after request
    """

    if not state.step_state.extra or not isinstance(state.step_state.extra, dict):
        state.step_state.extra = {}
    state.step_state.extra.setdefault("api_response", None)
    state.step_state.extra.setdefault("api_status_code", None)
    # state.step_state.extra.setdefault("validations_log", [])

    # статичные переменные заменяем сразу
    await process_variables_before_request(state)
    state.logger.info(f"Performing API action. Request {state.step_state.current_step['value']}")
    try:
        current_step = state.step_state.current_step
        if isinstance(current_step, dict):
            current_step_payload = current_step
        elif hasattr(current_step, "model_dump"):
            # StepPayload (pydantic model) -> dict for ApiStep(**payload)
            current_step_payload = current_step.model_dump(exclude_none=True)
        else:
            current_step_payload = dict(current_step)

        request_raw = ApiStep(**current_step_payload)
        state.logger.info(f"API step request_raw: {request_raw}")
    except Exception as er:
        logger_message = "Stopping execution...curl_validate error"
        state.run_summary += f"Step {state.step_state.step_id}: curl_validate error {er}\n"
        state.logger.info(logger_message)
        state.status = CaseStatusEnum.FAILED
        return state

    try:
        response_pw = await execute_api_request(state.context, request_raw)
    except Exception as er:
        logger_message = f"Stopping execution...error in api_request {repr(er)}"
        state.run_summary += f"Step {state.step_state.step_id}: api_request error {repr(er)}\n"
        state.logger.info(logger_message)
        state.status = CaseStatusEnum.FAILED
        return state

    # устанавливаем динамические переменные {{}}
    try:
        await process_variables_after_response(state, response_pw)
    except Exception as er:
        logger_message = f"Stopping execution...error in JSONPath {repr(er)}"
        state.run_summary += f"Step {state.step_state.step_id}: JSONPath error {repr(er)}\n"
        state.logger.info(logger_message)
        state.status = CaseStatusEnum.FAILED
        state.step_state.extra["api_status_code"] = response_pw["status"]
        # state.step_state.extra["api_response"] = response_pw["text"][:1000]
        state.step_state.extra["api_response"] = response_pw["json"]
        return state

    try:
        await validate_response(state, response_pw)
    except Exception as er:
        logger_message = f"Stopping execution...error in validation: {repr(er)}"
        state.run_summary += f"\nStep {state.step_state.step_id}: validation error {repr(er)}\n"
        state.logger.info(logger_message)
        state.status = CaseStatusEnum.FAILED
        state.step_state.extra["api_status_code"] = response_pw["status"]
        # state.step_state.extra["api_response"] = response_pw["text"][:1000]
        state.step_state.extra["api_response"] = response_pw["json"]
        return state

    state.step_state.extra["api_status_code"] = response_pw["status"]
    # state.step_state.extra["api_response"] = response_pw["text"][:1000]
    state.step_state.extra["api_response"] = response_pw["json"]

    return state


@observe(as_type="span", capture_input=False, capture_output=False)
async def action_wait(state: AgentState) -> AgentState:
    """
    Wait for an element to appear on the page, but no more than a specified amount of time.
    If the element is not found, the step will fail.
    If element description is not specified, the step will just wait for the specified amount of time.

    Args:
        state (AgentState): The current state of the agent

    Returns:
        AgentState: Updated agent state after waiting
    """
    state.logger.info(f"Performing WAIT action. Waiting for {state.step_state.wait_time} seconds")

    if state.step_state.element_description is None:
        state.logger.info(f"Element description is not specified, waiting for {state.step_state.wait_time} seconds")
        await asyncio.sleep(state.step_state.wait_time)
        return state

    await asyncio.sleep(state.step_state.wait_time // 3)
    # обновляем скрин после прогрузки, в модель отдаем актуальный
    # исходный before остается для фронта
    temp_screenshot_path=state.screenshot_base_path / \
        f'screenshot_{state.step_state.step_id}_temp.jpeg'
    await state.page.screenshot(path=temp_screenshot_path,
                                type="jpeg")

    detection_confidence = await state.inference_client.get_detection_confidence(
        image_path=temp_screenshot_path,
        element_description=state.step_state.current_step['element_description'],
    )

    state.step_state.detection_confidence = [detection_confidence]
    if detection_confidence < WAIT_CONFIDENCE_THRESHOLD:
        state.run_summary += f"Step {state.step_state.step_id}: Couldn't find the target element.\n"
        state.logger.info(
            f"Element presence detection confidence {detection_confidence}% is too low for the step {state.step_state.step_id}. Stopping execution...")
        state.status = CaseStatusEnum.FAILED

    return state


@observe(as_type="span", capture_input=False, capture_output=False)
async def action_read(state: AgentState) -> AgentState:
    """
    Extract text from the screenshot using OCR and store it in user storage.

    This function performs OCR on the current screenshot using the provided instruction,
    then stores the extracted text in user storage with the specified storage key.

    Args:
        state (AgentState): The current state of the agent

    Returns:
        AgentState: Updated agent state after reading and storing text
    """
    instruction = state.step_state.current_step.get('instruction')
    storage_key = state.step_state.current_step.get('storage_key')
    if isinstance(storage_key, str):
        storage_key = storage_key.strip()
        if storage_key.startswith("{{") and storage_key.endswith("}}"):
            storage_key = storage_key[2:-2].strip()

    if not storage_key:
        state.run_summary += f"Step {state.step_state.step_id}: storage_key is missing for READ action.\n"
        state.logger.info(
            f"Missing storage_key for READ action at step {state.step_state.step_id}. Stopping execution..."
        )
        state.status = CaseStatusEnum.FAILED
        return state

    state.logger.info(f"Performing READ action. Instruction: {instruction}, Storage key: {storage_key}")

    start_time = time.time()
    try:
        ocr_result = await state.inference_client.ocr(
            str(state.step_state.before_screenshot_path),
            instruction
        )
        state.step_state.model_time += time.time() - start_time
        state.logger.info(
            f"OCR inference result for step {state.step_state.step_id}: '{ocr_result}...' | generate_time: {state.step_state.model_time:.2f}")

        if not ocr_result or ocr_result.strip() == "":
            state.run_summary += f"Step {state.step_state.step_id}: OCR failed to extract text.\n"
            state.logger.info(
                f"OCR returned empty result for instruction '{instruction}' in step {state.step_state.step_id}. Stopping execution...")
            state.status = CaseStatusEnum.FAILED
            return state

        # Store the result in user storage
        state.user_storage.set(storage_key, ocr_result.strip())
        state.logger.info(f"Stored text under key '{storage_key}': '{ocr_result}...'")

    except Exception as e:
        state.run_summary += f"Step {state.step_state.step_id}: OCR error.\n"
        state.logger.info(f"OCR error for step {state.step_state.step_id}: {str(e)} Stopping execution...")
        state.status = CaseStatusEnum.FAILED

    return state


@observe(as_type="span", capture_input=False, capture_output=False)
async def action_paste(state: AgentState) -> AgentState:
    """
    Retrieve stored text and paste it into an input field.

    This function retrieves text from user storage using the provided storage key,
    finds the target input field using coordinate inference, and types the stored text.

    Args:
        state (AgentState): The current state of the agent

    Returns:
        AgentState: Updated agent state after pasting text
    """
    storage_key = state.step_state.current_step.get('storage_key')
    element_description = state.step_state.current_step.get('element_description')
    state.logger.info(f"Performing PASTE action. Storage key: {storage_key}, Element: {element_description}")

    # Retrieve text from storage
    stored_text = state.user_storage.get_value(storage_key)
    if stored_text is None:
        state.run_summary += f"Step {state.step_state.step_id}: Storage key not found.\n"
        state.logger.info(
            f"Storage key '{storage_key}' not found for step {state.step_state.step_id}. Stopping execution...")
        state.status = CaseStatusEnum.FAILED
        return state

    # Find coordinates of the input field
    state.logger.info(f"Calling model_clicker inference for step {state.step_state.step_id} | {element_description=}")
    start_time = time.time()
    state.step_state.coordinates = await get_coordinates_with_retries(state, element_description)
    x, y = state.step_state.coordinates
    state.step_state.model_time += time.time() - start_time
    state.logger.info(
        f"Clicker inference result for step {state.step_state.step_id}: ({x}, {y}) | generate_time: {state.step_state.model_time:.2f}")

    if x == 0 and y == 0:
        state.run_summary += f"Step {state.step_state.step_id}: Couldn't find the target element.\n{state.retry_messages_buffer}"
        state.logger.info(
            f"Could not find the target element in the image for the step {state.step_state.step_id}. Stopping execution...")
        state.status = CaseStatusEnum.FAILED
        return state

    await asyncio.to_thread(draw_point_on_screenshot, str(state.step_state.before_screenshot_path),
                            state.step_state.annotated_screenshot_path, x, y)

    # Click on the field and paste the stored text
    state.logger.info(f"Performing PASTE action at {x}, {y} with text: '{stored_text}...'")
    state.page = state.tab_manager.current_page()
    await state.page.mouse.click(float(x), float(y), delay=CLICK_DELAY)
    await state.page.keyboard.type(stored_text, delay=20)

    return state


@observe(as_type="span", capture_input=False, capture_output=False)
async def action_select(state: AgentState) -> AgentState:
    """
    Select an option from a dropdown/select element.

    This function finds the select element using coordinate inference and then
    selects the specified option by value or text.

    Алгоритм выбора опции:
    1) По координатам находим <select> (с поддержкой вложенных iframe) и проверяем доступность.
    2) Нормализуем ввод и опции (trim, lower, схлопывание пробелов).
    3) Ищем точное совпадение: сначала по value, затем по тексту — приоритетный этап.
    4) Если точного нет — ищем по includes.
    5) При нескольких includes применяем tie-breaker через startsWith. (выбираем опцию, у которой текст или value начинается с введённого значения).
    6) При неоднозначности возвращаем multiple_options с перечнем конфликтов.

    """

    async def select_option_by_coordinates(page, x, y, value):
        return await page.evaluate(
            """({ x, y, value }) => {

                // ---------- helpers ----------
                const norm = (s) => {
                    if (s === null || s === undefined) return "";
                    return String(s)
                        .replace(/\\u00A0/g, " ")
                        .trim()
                        .toLowerCase()
                        .replace(/\\s+/g, " ");
                };

                const fmtOption = (opt) => "- " + opt.textContent.trim() + " (value: " + opt.value + ")";

                const buildConflict = (stageName, queryNorm, candidates) => {
                    const optionsInfo = candidates.map(c => fmtOption(c.raw)).join("\\n  ");
                    return {
                        error: "multiple_options",
                        message:
                            "Multiple options found (" + stageName + ") matching '" + queryNorm +
                            "'. Please specify the exact option:\\n  " + optionsInfo
                    };
                };

                const selectOne = (selectEl, opt) => {
                    selectEl.value = opt.raw.value;
                    opt.raw.selected = true;

                    selectEl.dispatchEvent(new Event("input", { bubbles: true }));
                    selectEl.dispatchEvent(new Event("change", { bubbles: true }));
                    return true;
                };

                // ---------- find element (iframe recursion) ----------
                let element = document.elementFromPoint(x, y);

                while (element && element.tagName === "IFRAME") {
                    const rect = element.getBoundingClientRect();
                    x = x - rect.left;
                    y = y - rect.top;

                    const doc = element.contentDocument;
                    if (!doc) return null;

                    element = doc.elementFromPoint(x, y);
                }

                if (!element || element.tagName !== "SELECT") return null;

                if (element.offsetWidth === 0 || element.offsetHeight === 0 || element.disabled) {
                    console.log("Select is hidden or disabled");
                    return null;
                }

                const q = norm(value);
                if (!q) return null;

                // ---------- prepare options ----------
                const options = Array.from(element.options).map(o => ({
                    raw: o,
                    value: norm(o.value),
                    text: norm(o.textContent)
                }));

                // ---------- stage 1: exact match (value first) ----------
                const exactByValue = options.filter(o => o.value && o.value === q);
                if (exactByValue.length === 1) return selectOne(element, exactByValue[0]);
                if (exactByValue.length > 1) return buildConflict("exact value", q, exactByValue);

                const exactByText = options.filter(o => o.text && o.text === q);
                if (exactByText.length === 1) return selectOne(element, exactByText[0]);
                if (exactByText.length > 1) return buildConflict("exact text", q, exactByText);

                // ---------- stage 2: includes ----------
                const includesCandidates = options.filter(o =>
                    (o.value && o.value.includes(q)) ||
                    (o.text && o.text.includes(q))
                );

                if (includesCandidates.length === 0) {
                    console.log("No options found matching:", value);
                    return null;
                }

                if (includesCandidates.length === 1) {
                    return selectOne(element, includesCandidates[0]);
                }

                // ---------- tie-breaker: startsWith ----------
                const startsWithCandidates = includesCandidates.filter(o =>
                    (o.value && o.value.startsWith(q)) ||
                    (o.text && o.text.startsWith(q))
                );

                if (startsWithCandidates.length === 1) {
                    return selectOne(element, startsWithCandidates[0]);
                }

                if (startsWithCandidates.length > 1) {
                    return buildConflict("startsWith (tie-breaker)", q, startsWithCandidates);
                }

                return buildConflict("includes", q, includesCandidates);
            }""",
            {"x": x, "y": y, "value": value}
        )

    option_value = state.step_state.current_step.get('option_value')

    clicker_prompt = state.step_state.element_description

    state.logger.info(f"Calling model_clicker inference for step {state.step_state.step_id} | {clicker_prompt=}")
    start_time = time.time()
    state.step_state.coordinates = await get_coordinates_with_retries(state, clicker_prompt)
    x, y = state.step_state.coordinates
    state.step_state.model_time += time.time() - start_time
    state.logger.info(
        f"Clicker inference result for step {state.step_state.step_id}: ({x}, {y}) | generate_time: {state.step_state.model_time:.2f}")

    if x == 0 and y == 0:
        state.run_summary += f"Step {state.step_state.step_id}: Couldn't find the target element.\n{state.retry_messages_buffer}"
        state.logger.info(
            f"Could not find the target element in the image for the step {state.step_state.step_id}. Stopping execution...")
        state.status = CaseStatusEnum.FAILED
        return state

    await asyncio.to_thread(draw_point_on_screenshot, str(state.step_state.before_screenshot_path),
                            state.step_state.annotated_screenshot_path, x, y)

    state.logger.info(f"Performing SELECT action at {x}, {y} with option '{option_value}'")
    state.page = state.tab_manager.current_page()
    result = await select_option_by_coordinates(state.page, x, y, option_value)

    if result is None:
        state.run_summary += f"Step {state.step_state.step_id}: Couldn't select the specified option.\n"
        state.logger.info(
            f"Could not select option '{option_value}' from the select element for step {state.step_state.step_id}. Stopping execution...")
        state.status = CaseStatusEnum.FAILED
        return state

    # Проверка на множественные совпадения
    if isinstance(result, dict) and result.get('error') == 'multiple_options':
        state.run_summary += f"Step {state.step_state.step_id}: {result.get('message')}\n"
        state.logger.info(
            f"Multiple options found for '{option_value}' in step {state.step_state.step_id}. Stopping execution...")
        state.status = CaseStatusEnum.FAILED
        return state

    state.logger.info(f"Option '{option_value}' successfully selected")
    await asyncio.sleep(0.2)

    return state
