"""Map Environment.browser (backend) to Playwright MCP / Node runner values.

Backend :class:`BrowserEnum` ``chrome`` | ``firefox`` — везде один смысл:

- **chrome** → **Google Chrome** через Playwright (``chromium.launch(channel='chrome')`` / MCP ``--browser chrome``).
  Тот же бинарник, что ставит ``playwright install chrome`` в ``PLAYWRIGHT_BROWSERS_PATH``.
- **firefox** → **Firefox** Playwright (``--browser firefox``).

Playwright MCP CLI: ``--browser chrome|firefox`` (не встроенный Chromium без channel).

Единая логика десктопного Chrome UA (без ``HeadlessChrome`` в Интернетометре):

- ``chrome_desktop_user_agent(browser.version)`` — VLM (версия из уже запущенного браузера).
- ``chrome_desktop_user_agent()`` — генерация/валидация JS и режим Code (кэш Playwright + ``chrome --version``).
- ``apply_playwright_mcp_chrome_user_agent(env)`` — кладёт тот же UA в ``PLAYWRIGHT_MCP_USER_AGENT`` для Node MCP
  (``mcp_run_fragment.mjs``, ``mcp_playwright_js_run.mjs`` + ``--user-agent``).
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import threading
from pathlib import Path
from typing import Any, Dict, Literal, MutableMapping

from playwright.sync_api import sync_playwright

McpBrowserName = Literal["chrome", "firefox"]

# В Docker браузеры лежат здесь (см. Dockerfile ENV PLAYWRIGHT_BROWSERS_PATH).
_DEFAULT_PLAYWRIGHT_BROWSERS_PATH = "/ms-playwright"


def playwright_node_environ() -> Dict[str, str]:
    """Окружение для процессов Node (MCP, trace): без PLAYWRIGHT_BROWSERS_PATH Playwright ищет ~/.cache/ms-playwright — в clicker-контейнере пусто → «Browser firefox is not installed»."""
    env = dict(os.environ)
    if not (env.get("PLAYWRIGHT_BROWSERS_PATH") or "").strip():
        env["PLAYWRIGHT_BROWSERS_PATH"] = _DEFAULT_PLAYWRIGHT_BROWSERS_PATH
    return env


def mcp_browser_from_environment(env: Any) -> McpBrowserName:
    """Return the value for Playwright MCP ``--browser`` from an environment payload dict."""
    if not isinstance(env, dict):
        return "chrome"
    b = str(env.get("browser") or "").strip().lower()
    if b == "firefox":
        return "firefox"
    return "chrome"


_CHROME_VERSION_RE = re.compile(r"(\d+\.\d+\.\d+\.\d+)")


def format_desktop_chrome_user_agent(browser_version: str) -> str | None:
    """Собрать строку UA из текста версии (``Browser.version``, вывод ``chrome --version``).

    Returns ``None`` if no ``major.minor.patch.build`` tuple is found.
    """
    raw = (browser_version or "").strip()
    if not raw:
        return None
    m = _CHROME_VERSION_RE.search(raw)
    if not m:
        return None
    ver = m.group(1)
    return (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        f"(KHTML, like Gecko) Chrome/{ver} Safari/537.36"
    )


_ua_lock = threading.Lock()
_desktop_chrome_ua_resolved: bool = False
_desktop_chrome_ua_cached: str | None = None


def _chrome_binary_for_desktop_ua() -> str | None:
    """Путь к бинарнику Google Chrome: PATH или каталог Playwright (``PLAYWRIGHT_BROWSERS_PATH``)."""
    for name in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser"):
        p = shutil.which(name)
        if p:
            return p
    base = (os.environ.get("PLAYWRIGHT_BROWSERS_PATH") or "").strip() or _DEFAULT_PLAYWRIGHT_BROWSERS_PATH
    root = Path(base)
    if not root.is_dir():
        return None
    for pattern in ("chrome-*/chrome-linux64/chrome", "chrome-*/chrome-linux/chrome"):
        for p in sorted(root.glob(pattern)):
            if p.is_file():
                return str(p)
    return None


def _desktop_chrome_user_agent_via_cli() -> str | None:
    """UA из ``<chrome> --version``, если Playwright launch недоступен (воркер, гонка, первый сбой)."""
    exe = _chrome_binary_for_desktop_ua()
    if not exe:
        return None
    try:
        cp = subprocess.run(
            [exe, "--version"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        text = (cp.stdout or "") + (cp.stderr or "")
        return format_desktop_chrome_user_agent(text)
    except Exception:
        return None


def desktop_chrome_user_agent_sync() -> str | None:
    """Return cached desktop Chrome UA for the installed Chrome channel, or ``None`` if unavailable.

    Сначала ``browser.version`` через sync Playwright (как VLM); при ошибке — ``chrome --version`` из
    ``PLAYWRIGHT_BROWSERS_PATH``. Иначе в Code-воркере первый сбой Playwright давал кэш ``None`` и
    MCP без ``--user-agent`` → ``HeadlessChrome`` в Интернетометре.
    """
    global _desktop_chrome_ua_resolved, _desktop_chrome_ua_cached
    with _ua_lock:
        if _desktop_chrome_ua_resolved:
            return _desktop_chrome_ua_cached
        _desktop_chrome_ua_resolved = True
        ua: str | None = None
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(
                    channel="chrome",
                    headless=True,
                    args=[
                        "--no-sandbox",
                        "--disable-dev-shm-usage",
                    ],
                )
                try:
                    ver = browser.version
                finally:
                    browser.close()
            ua = format_desktop_chrome_user_agent(ver)
        except Exception:
            pass
        if not ua:
            ua = _desktop_chrome_user_agent_via_cli()
        _desktop_chrome_ua_cached = ua
        return ua


def chrome_desktop_user_agent(browser_version: str | None = None) -> str | None:
    """Один и тот же десктопный UA для Chrome во всех режимах (VLM, генерация/валидация JS, Code).

    - С ``browser_version`` (VLM после ``launch``): сначала ``format_desktop_chrome_user_agent``, иначе общий кэш.
    - Без аргумента (MCP): ``desktop_chrome_user_agent_sync`` (Playwright + fallback CLI).
    """
    if browser_version:
        ua = format_desktop_chrome_user_agent(browser_version)
        if ua:
            return ua
    return desktop_chrome_user_agent_sync()


def apply_playwright_mcp_chrome_user_agent(env: MutableMapping[str, str]) -> str | None:
    """Прокинуть тот же UA, что и в VLM, в env для Playwright MCP: ключ ``PLAYWRIGHT_MCP_USER_AGENT``."""
    ua = chrome_desktop_user_agent()
    if ua:
        env["PLAYWRIGHT_MCP_USER_AGENT"] = ua
    return ua
