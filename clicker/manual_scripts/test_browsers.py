

import sys
sys.path.append('.')


import asyncio
from playwright.async_api import async_playwright
import os
#from browser_actions.tab_manager import TabManager, is_local_url
import asyncio
from fuzzywuzzy import process
from playwright.async_api import async_playwright
from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from playwright.async_api import BrowserContext, Page
from typing import List
from config import logger, LOCALHOST_DISABLED
import time
from urllib.parse import urlparse


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
            return

        if LOCALHOST_DISABLED:
            if is_local_url(page.url):
                raise Exception('LOCALHOST_DISABLED')

        logger.info(f"New page opened and appended: {page.url}")
        await self._apply_stealth(page)
        self.pages.append(page)
        self._current_page = page
        page.on("close", lambda: asyncio.create_task(self._handle_page_close(page)))
        # try:
        #     await page.wait_for_load_state('load')
        # except PlaywrightTimeoutError:
        #     logger.warning("Timeout waiting for handle_new_page load.")
        await asyncio.sleep(5)
        if not await check_page_loaded(page):
            raise Exception('Page did not load correctly.')

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





async def main(browser_type: str = "firefox", url: str = "https://google.com"):

    p = await async_playwright().start()

    if browser_type == 'firefox':
        browser = await p.firefox.launch(headless=False,
                                         firefox_user_prefs={"dom.webdriver.enabled": False})
        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:132.0) Gecko/20100101 Firefox/132.0"
    elif browser_type == 'chrome':
        browser = await p.chromium.launch(channel='chrome',
                                            headless=False,
                                            args=[
                                                "--disable-blink-features=AutomationControlled",
                                                "--disable-web-security",
   

                                            ])
        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.7390.54 Safari/537.36"


    context = await browser.new_context(
        viewport={"width": 1024, "height": 768},
        locale="en-US",
        bypass_csp=True,
        ignore_https_errors=True,
        extra_http_headers={
            "Accept": "image/avif,image/webp,image/png,image/svg+xml,image/*;q=0.8,*/*;q=0.5",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Upgrade-Insecure-Requests": "1",
            "User-Agent": user_agent,
            # "Sec-Ch-Ua": '"Google Chrome";v="127", "Chromium";v="127", "Not.A/Brand";v="24"',
            # "Sec-Ch-Ua-Mobile": "?0",

            "Cache-Control": "max-age=0"

        }
    )

    tab_manager = TabManager(context)
    page = await tab_manager.initialize_pages()

    await tab_manager.navigate(url, page)

    await asyncio.sleep(3600)  # ctrl-c

    await browser.close()
    await p.stop()


#asyncio.run(main("chrome", "https://2gis.ru/moscow"))
#asyncio.run(main("chrome", "https://www.amazon.com/"))

