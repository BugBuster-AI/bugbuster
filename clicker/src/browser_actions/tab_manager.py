import sys

sys.path.append('.')

import asyncio
from typing import List
from urllib.parse import urlparse

from fuzzywuzzy import process
from playwright.async_api import BrowserContext, Page, async_playwright
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from core.config import LOCALHOST_DISABLED, logger


def is_local_url(url):
    parsed = urlparse(url)
    netloc = parsed.netloc.split(':')[0]  # Удаляем порт если есть

    # Список локальных адресов, которые нужно блокировать
    local_netlocs = {
        'localhost',
        '127.0.0.1',
        '::1',
        '0.0.0.0',
        '127.0.0.0',
        '127.'        # Любой адрес, начинающийся с 127.
    }

    # Проверяем IPv6 localhost
    if netloc.startswith('[') and netloc.endswith(']'):
        netloc = netloc[1:-1]

    # Проверяем на точное совпадение или начало с 127.
    return (netloc in local_netlocs or
            netloc.startswith('127.') or
            netloc == '0' or  # Краткая форма 0.0.0.0
            any(netloc == addr for addr in local_netlocs))


async def check_page_loaded(page):
    """
    check page is load.
    """
    try:
        # await page.wait_for_selector("body", state="attached", timeout=30000)
        # одно и то же, но wait_for_selector легаси
        await page.locator("body").wait_for(state="attached", timeout=30000)
        return True
    except (PlaywrightTimeoutError, Exception) as e:
        logger.warning(f"wait_for_selector body failed: {e}", exc_info=True)
        return False


async def goto_with_retries(page, url, retries=3, delay=2):
    """Navigate to URL with retries if fails."""

    if LOCALHOST_DISABLED:
        if is_local_url(url):
            raise Exception('LOCALHOST_DISABLED')
    for attempt in range(retries):
        try:
            await page.goto(url, wait_until="load")
            logger.info("Page opened successfully")
            await asyncio.sleep(2)

            if await check_page_loaded(page):
                return
            else:
                raise Exception('Page did not load correctly.')

        except (PlaywrightTimeoutError, Exception) as e:
            logger.warning(f"Attempt {attempt + 1} failed: {e}", exc_info=True)

            if attempt < retries - 1:
                logger.info(f"Retrying to open the page in {delay} seconds...")
                await asyncio.sleep(delay)
            else:
                raise


class TabManager:
    def __init__(self, context: BrowserContext):
        self.context = context
        self.pages: List[Page] = []
        self._current_page = None
        self.new_page_loading = asyncio.Event()
        # Сигнал что событие new page сработало в фоне
        self._new_page_detected = asyncio.Event()
        # Сигнал что страница полностью загружена
        self._new_page_loaded = asyncio.Event()

        self.context.on("page", self.handle_new_page)
        self.stealth_script = """

            (() => {
                // Сохраняем оригинальные значения
                const originalLanguages = navigator.languages;
                const originalPlugins = navigator.plugins;

                try {
                    delete Object.getPrototypeOf(navigator).webdriver;
                } catch (e) {}

                if (!window.chrome) {
                    window.chrome = {runtime: {}};
                }

                Object.defineProperty(navigator, 'languages', {
                    get: () => originalLanguages || ['en-US', 'en'],
                    configurable: true
                });

                Object.defineProperty(navigator, 'plugins', {
                    get: () => originalPlugins.length > 0 ? originalPlugins : [
                        {
                            name: 'PDF Viewer',
                            filename: 'internal-pdf-viewer',
                            description: 'Portable Document Format'
                        }
                    ],
                    configurable: true
                });

                Object.defineProperty(navigator, 'webdriver', {
                    configurable: true,
                    get: () => false
                });
            })();
        """

    async def _apply_stealth(self, page: Page):
        """не палит автоматизацию"""
        await page.add_init_script(self.stealth_script)
        await page.evaluate("""() => {
            if (window.navigator.__proto__.mozIsLocallyAvailable) {
                delete window.navigator.__proto__.mozIsLocallyAvailable;
            }
        }""")

    async def _handle_page_close(self, page: Page):
        """Обработчик закрытия страницы"""
        logger.info(f"Page closed: {page.url}")
        if page in self.pages:
            self.pages.remove(page)

            # Если закрытая страница была текущей, выбираем новую текущую
            if self._current_page == page:
                if self.pages:
                    self._current_page = self.pages[-1]  # Последняя вкладка по умолчанию
                else:
                    self._current_page = None

    async def initialize_pages(self):
        self.pages = self.context.pages
        if not self.pages:
            page = await self.context.new_page()
            await self._apply_stealth(page)
            self.pages.append(page)
            self._current_page = page
            return self._current_page
        else:
            for page in self.pages:
                page.on("close", lambda: asyncio.create_task(self._handle_page_close(page)))
            return self.pages[0]

    async def handle_new_page(self, page: Page, retries=3, delay=2):

        if page.url == "about:blank":
            logger.info("Ignored new page: about:blank")
            self._new_page_detected.set()
            self._new_page_loaded.set()
            return

        if LOCALHOST_DISABLED:
            if is_local_url(page.url):
                self._new_page_detected.set()
                self._new_page_loaded.set()
                raise Exception('LOCALHOST_DISABLED')

        logger.info(f"Trigger new page, loading...: {page.url}")
        # сигнализируем, что событие сработало
        self._new_page_detected.set()

        try:
            self.pages.append(page)
            self._current_page = page
            await self._apply_stealth(page)
            page.on("close", lambda: asyncio.create_task(self._handle_page_close(page)))

            for attempt in range(retries):
                try:

                    await page.wait_for_load_state('load', timeout=30000)
                    logger.info("New page loaded successfully")
                    await asyncio.sleep(2)

                    if await check_page_loaded(page):
                        logger.info(f"New page opened and appended: {page.url}")
                        self._new_page_loaded.set()  # Страница полностью готова
                        return
                    else:
                        raise Exception('New page did not load correctly.')

                except (PlaywrightTimeoutError, Exception) as e:
                    logger.warning(f"Attempt {attempt + 1} to load new page failed: {e}")

                    if attempt < retries - 1:
                        logger.info(f"Retrying page load in {delay} seconds...")
                        await asyncio.sleep(delay)
                    else:
                        logger.error(f"Failed to load new page after {retries} attempts")
                        self._new_page_loaded.set()
                        raise
        except Exception as e:
            logger.error(f"Unexpected error in handle_new_page: {e}")
            self._new_page_loaded.set()
            raise

    async def wait_for_new_page_to_load(self):
        await self.new_page_loading.wait()

    async def navigate(self, url, page=None, retries=3, delay=2):
        logger.info(f"Navigating to {url=}")
        if page is None:
            page = self.current_page()
        await self._apply_stealth(page)
        await goto_with_retries(page, url, retries=retries, delay=delay)
        page.on("close", lambda: asyncio.create_task(self._handle_page_close(page)))
        self._current_page = page

    async def create_new_tab_and_navigate(self, url, retries=3, delay=2):
        logger.info(f"Creating new tab and navigating to {url=}")
        page = await self.context.new_page()
        await self._apply_stealth(page)
        await goto_with_retries(page, url, retries=retries, delay=delay)
        self.pages.append(page)
        self._current_page = page
        page.on("close", lambda: asyncio.create_task(self._handle_page_close(page)))
        return page

    def list_tabs(self):
        logger.info([page.url for page in self.pages])
        return [page for page in self.pages]

    async def find_tab(self, partial_name, how="all"):
        """
        Args:
            how: all - find in urls and titles
                 url - find in only urls
                 title - find in only titles
        """
        urls = [page.url for page in self.pages]
        titles = [await page.title() for page in self.pages]

        best_match = None

        if how == "all":
            url_match = process.extractOne(partial_name, urls)
            title_match = process.extractOne(partial_name, titles)

            # best score between urls and titles
            if url_match and (best_match is None or url_match[1] > best_match[1]):
                best_match = (url_match[0], url_match[1], urls.index(url_match[0]))

            if title_match and (best_match is None or title_match[1] > best_match[1]):
                best_match = (title_match[0], title_match[1], titles.index(title_match[0]))

        elif how == "url":
            url_match = process.extractOne(partial_name, urls)
            if url_match:
                best_match = (url_match[0], url_match[1], urls.index(url_match[0]))

        elif how == "title":
            title_match = process.extractOne(partial_name, titles)
            if title_match:
                best_match = (title_match[0], title_match[1], titles.index(title_match[0]))

        print("best_match", best_match)

        if best_match:
            return self.pages[best_match[2]]
        return None

    async def switch_to_tab(self, tab: Page):
        if tab in self.pages:
            self._current_page = tab
        else:
            raise ValueError("tab not found")

    async def go_back(self, page: Page = None):
        if page is None:
            page = self.current_page()
        await page.go_back(wait_until="load")

    async def go_forward(self, page: Page = None):
        if page is None:
            page = self.current_page()
        await page.go_forward(wait_until="load")

    async def close_tab(self, page: Page = None):
        logger.info("closing current tab...")
        if page is None:
            page = self.current_page()
        if page:
            await page.close()
        # self.pages.remove(page)

    def current_page(self):
        if hasattr(self, '_current_page'):
            return self._current_page
        if self.pages:
            return self.pages[-1]
        return None

    # async def check_if_click_opens_new_tab(self, page: Page, x: int, y: float) -> bool:
    #     """
    #     Проверяет, откроет ли клик по координатам (x,y) новую вкладку.
    #     Анализирует элемент на наличие target="_blank" или других признаков.
    #     """
    #     try:
    #         # Получаем элемент по координатам
    #         element_info = await page.evaluate("""
    #         ({ x, y }) => {
    #             const element = document.elementFromPoint(x, y);
    #             if (!element) return null;

    #             return {
    #                 tagName: element.tagName,
    #                 href: element.href || element.getAttribute('href') || '',
    #                 target: element.target || element.getAttribute('target') || '',
    #                 onclick: element.getAttribute('onclick') || '',
    #                 hasTargetBlank: element.target === '_blank' || element.getAttribute('target') === '_blank',
    #                 isAnchor: element.tagName === 'A',
    #                 isButton: element.tagName === 'BUTTON' || element.type === 'button',
    #                 hasExternalLink: element.href && !element.href.startsWith(window.location.origin)
    #             };
    #         }
    #         """, {"x": x, "y": y})

    #         if not element_info:
    #             return False

    #         # Признаки, что элемент откроет новую вкладку
    #         indicators = [
    #             element_info.get('hasTargetBlank', False),
    #             element_info.get('isAnchor', False) and element_info.get('href', ''),
    #             'window.open' in element_info.get('onclick', ''),
    #             element_info.get('hasExternalLink', False)
    #         ]

    #         will_open_new_tab = any(indicators)
    #         logger.info(f"Element analysis: {element_info} -> will_open_new_tab: {will_open_new_tab}")

    #         return will_open_new_tab

    #     except Exception as e:
    #         logger.warning(f"Could not analyze element at ({x}, {y}): {e}")
    #         return False  # В случае ошибки предполагаем, что новая вкладка не откроется

    async def check_if_click_opens_new_tab(self, page: Page, x: int, y: float) -> bool:
        """
        Проверяет, откроет ли клик по координатам (x, y) новую вкладку или страницу.
        Анализирует элемент по координатам в браузере.
        """
        try:
            element_info = await page.evaluate("""
            ({ x, y }) => {
                const element = document.elementFromPoint(x, y);
                if (!element) return null;

                const tagName = element.tagName;
                const href = element.href || element.getAttribute('href') || '';
                const target = element.target || element.getAttribute('target') || '';
                const onclick = element.getAttribute('onclick') || '';

                const hasTargetBlank = target === '_blank';
                const isAnchor = tagName === 'A';
                const isButton = tagName === 'BUTTON' || element.type === 'button';
                const hasExternalLink = href && !href.startsWith(window.location.origin);
                const hasJsNavigation = onclick && (
                    onclick.includes('window.open') ||
                    onclick.includes('location.href') ||
                    onclick.includes('document.location')
                );

                // Определяем тип перехода
                const opensNewTab = hasTargetBlank || onclick.includes('window.open');
                const willNavigateSameTab =
                    (isAnchor && href && !hasTargetBlank) ||
                    (hasJsNavigation && !onclick.includes('window.open'));

                return {
                    tagName,
                    href,
                    target,
                    onclick,
                    isAnchor,
                    isButton,
                    hasTargetBlank,
                    hasExternalLink,
                    hasJsNavigation,
                    opensNewTab,
                    willNavigateSameTab
                };
            }
            """, {"x": x, "y": y})

            if not element_info:
                return False

            # Если элемент явно открывает новую вкладку — возвращаем True
            opens_new_tab = bool(element_info.get("opensNewTab", False))

            # Если это переход на этой же вкладке — не считаем как новую вкладку
            if element_info.get("willNavigateSameTab", False):
                opens_new_tab = False

            logger.info(f"[check_if_click_opens_new_tab] Element: {element_info} -> opens_new_tab={opens_new_tab}")
            return opens_new_tab

        except Exception as e:
            logger.warning(f"Error in check_if_click_opens_new_tab at ({x}, {y}): {e}")
            return False

    async def wait_for_possible_new_page(self, timeout=10, load_timeout=120) -> bool:
        """
        Ждет новую страницу с таймаутами на оба этапа.
        """
        self._new_page_detected.clear()
        self._new_page_loaded.clear()

        logger.info(f"Waiting for new page event (max {timeout}s)...")

        try:
            # 1. Ждем срабатывания триггера от pw 10 сек
            await asyncio.wait_for(self._new_page_detected.wait(), timeout=timeout)
            logger.info("New page event detected, waiting for loading...")

            # 2. Ждем загрузки страницы (максимум load_timeout секунд)
            await asyncio.wait_for(self._new_page_loaded.wait(), timeout=load_timeout)
            return True

        except asyncio.TimeoutError as e:
            if not self._new_page_detected.is_set():
                # 1. триггер не пришел
                logger.info(f"No new page event within {timeout} seconds")
                return False
            else:
                # 2. триггер пришел, но загрузка не завершилась
                logger.error(f"New page detected but failed to load within {load_timeout} seconds")
                raise Exception(f"New page loading timeout after {load_timeout} seconds") from e

        except Exception as e:
            logger.error(f"Error waiting for new page: {e}")
            raise


async def main():
    width = 1024
    height = 768
    async with async_playwright() as p:
        browser = await p.firefox.launch(headless=False)
        context = await browser.new_context(
            viewport={"width": width, "height": height},
            locale="en-US",
            bypass_csp=True,
            ignore_https_errors=True,
            # record_video_dir=f"test_video",
            # record_video_size={"width": width, "height": height},
            extra_http_headers={
                "Accept": "image/avif,image/webp,image/png,image/svg+xml,image/*;q=0.8,*/*;q=0.5",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br, zstd",
                "Upgrade-Insecure-Requests": "1",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:132.0) Gecko/20100101 Firefox/132.0"
            }
        )
        # await context.tracing.start(title="test", screenshots=True, snapshots=True, sources=False)
        tab_manager = TabManager(context)
        page = await tab_manager.initialize_pages()

        #########################################
        # navigate in current tab
        await tab_manager.navigate("https://google.com", page)
        #await tab_manager.navigate("https://localhost/123", page)


        # # await page.set_viewport_size({"width": 500, "height": 500})
        # # await page.screenshot(path="test_page1.jpeg", type='jpeg')
        # #########################################


        # # navigate in current tab
        # await tab_manager.create_new_tab_and_navigate("https://vc.ru")
        # await tab_manager.create_new_tab_and_navigate("https://vc.ru")

        # # look all tabs
        # print("all tabs:", tab_manager.list_tabs())

        # await asyncio.sleep(3)
        # # Close tab
        # page = tab_manager.current_page()  # остается гугл и vc
        # await tab_manager.close_tab(page)
        # print("закрыть руками")
        # await asyncio.sleep(10)
        # page = tab_manager.current_page()
        # print("all tabs after close:", tab_manager.list_tabs(), "current page:",page.url)

        # await asyncio.sleep(30)
        # # await context.tracing.stop(path=f"test_trace.zip")
        # await browser.close()

        await asyncio.sleep(3600)  # ctrl-c
        await browser.close()
        await p.stop()

if __name__ == "__main__":
    asyncio.run(main())
