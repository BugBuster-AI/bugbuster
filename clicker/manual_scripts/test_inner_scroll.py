import asyncio
from playwright.async_api import async_playwright
import os


async def scroll_and_capture(page, element):
    SCROLL_FACTOR = 2 / 3    # шаг прокрутки (чем меньше, тем больше перекрытие)
    SCROLL_OVERLAP = 5       # перекрытие между скриншотами (px)
    SCROLL_DELAY = 0.2       # задержка между скроллами
    MAX_SCROLL_HEIGHT = 20000  # страховка от бесконечной подгрузки
    MAX_SCROLLS = 30  # максимум скроллов (скринов)

    # встаем в начало элемента
    await element.evaluate("el => el.scrollTop = 0")
    await asyncio.sleep(SCROLL_DELAY)

    log_output = []

    # сразу чекаем что получаем с элемента параметры
    scrollable_info = await element.evaluate(
        """el => el ? {
            scrollHeight: el.scrollHeight,
            clientHeight: el.clientHeight,
            scrollTop: el.scrollTop,
            boundingBox: el.getBoundingClientRect()
        } : null"""
    )

    if not scrollable_info:
        print("Element not found or not scrollable.")
        return

    for scroll_count in range(MAX_SCROLLS):
        real_scroll = await element.evaluate("el => el.scrollTop")  # позиция скролла
        client_height = await element.evaluate("el => el.clientHeight")  # видимая область
        scroll_height = await element.evaluate("el => el.scrollHeight")  # макс высота элемента, на которую можно прокрутить

        screenshot_path = f'scroll_{scroll_count}.png'
        await element.screenshot(path=screenshot_path)
        log_output.append(
            f"screenshot saved: {screenshot_path}, "
            f"scrollTop: {real_scroll}, clientHeight: {client_height}, scrollHeight: {scroll_height}"
        )

        # Лимит на бесконечную ленту
        if scroll_height > MAX_SCROLL_HEIGHT:
            log_output.append(f"Exceeded MAX_SCROLL_HEIGHT ({MAX_SCROLL_HEIGHT}px), stopping.")
            break

        # Дошли до низа?
        if real_scroll + client_height >= scroll_height - 2:
            break

        # следующая позиция скролла
        scroll_step = int(client_height * SCROLL_FACTOR)
        next_scroll = real_scroll + scroll_step - SCROLL_OVERLAP

        # если выйдет за предел, то устанавливаем максимум
        if next_scroll > scroll_height - client_height:
            next_scroll = scroll_height - client_height

        # Прокручиваем
        await element.evaluate("(el, scroll) => el.scrollTop = scroll", next_scroll)
        await asyncio.sleep(SCROLL_DELAY)

        # На самом ли деле прокрутили, или ничего не поменялось?
        new_scroll = await element.evaluate("el => el.scrollTop")
        if new_scroll == real_scroll:
            log_output.append("ScrollTop didn't change, probably at the end.")
            break

    print("\n".join(log_output))


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


async def handle_click(page, x, y):
    print(f"Clicked at: ({x}, {y})")

    scrollable_element = await find_scrollable_element(page, x, y)

    if scrollable_element:
        print("Found scrollable element")
        return await scroll_and_capture(page, scrollable_element)
    else:
        print("No scrollable element found at this position")
        return "No scrollable element found"


async def expose_click_handler(page, function_name):
    await page.expose_function(function_name, lambda event: asyncio.ensure_future(
        handle_click(page, event['clientX'], event['clientY'])
    ))


async def register_click_handler(page, function_name):

    await page.evaluate(f"""
        (() => {{
            document.addEventListener('click', event => window.{function_name}({{
                clientX: event.clientX,
                clientY: event.clientY
            }}));
        }})();
    """)

async def main():
    async with async_playwright() as p:
        browser = await p.firefox.launch(headless=False)
        context = await browser.new_context(viewport={"width": 1500, "height": 800}, locale="en-US")
        page = await context.new_page()

        function_name = f"on_click_handler_{id(page)}"

        await expose_click_handler(page, function_name)
        page.on("load", lambda: asyncio.ensure_future(register_click_handler(page, function_name)))

        file_path = os.path.abspath("complex_test.html")
        #await page.goto(f'file://{file_path}')
        await page.goto(f'https://maps.yandex.ru')

        await asyncio.Event().wait()

#asyncio.run(main())
