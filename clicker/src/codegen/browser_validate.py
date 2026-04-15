"""Проверка сгенерированного JS: по умолчанию [microsoft/playwright-mcp](https://github.com/microsoft/playwright-mcp) (stdio MCP + browser_run_code), запасной режим — run_fragment.mjs."""
from __future__ import annotations

import logging
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from codegen.effective_browser import apply_playwright_mcp_chrome_user_agent, playwright_node_environ

logger = logging.getLogger("clicker")

NODE_RUNNER_DIR = Path(__file__).resolve().parent / "node_runner"
RUN_FRAGMENT = NODE_RUNNER_DIR / "run_fragment.mjs"
MCP_RUN_FRAGMENT = NODE_RUNNER_DIR / "mcp_run_fragment.mjs"
PLAYWRIGHT_MCP_PKG = NODE_RUNNER_DIR / "node_modules" / "@playwright" / "mcp"

USE_PLAYWRIGHT_MCP = os.getenv("CODEGEN_USE_PLAYWRIGHT_MCP", "1").strip().lower() not in ("0", "false", "no", "")

# Playwright MCP иногда пишет markdown-секцию `### Error` в stdout при returncode=0.
MCP_ERROR_MARKER = "### Error"
_MAX_ERR_MSG_CHARS = 8000


def _proc_output_has_mcp_error_marker(proc: subprocess.CompletedProcess) -> bool:
    combined = f"{proc.stdout or ''}\n{proc.stderr or ''}"
    return MCP_ERROR_MARKER in combined


def _error_text_from_proc(proc: subprocess.CompletedProcess) -> str:
    err = (proc.stderr or "").strip() or (proc.stdout or "").strip() or "playwright fragment failed"
    if len(err) > _MAX_ERR_MSG_CHARS:
        total = len(err)
        err = err[:_MAX_ERR_MSG_CHARS] + f"... (truncated, {total} chars total)"
    return err


def mcp_runner_ready() -> bool:
    return MCP_RUN_FRAGMENT.is_file() and PLAYWRIGHT_MCP_PKG.is_dir()


def legacy_runner_ready() -> bool:
    return RUN_FRAGMENT.is_file() and (NODE_RUNNER_DIR / "node_modules").is_dir()


def node_runner_ready() -> bool:
    if USE_PLAYWRIGHT_MCP and mcp_runner_ready():
        return True
    return legacy_runner_ready()


def _subprocess_io_dict(proc: subprocess.CompletedProcess) -> Dict[str, Any]:
    out = (proc.stdout or "")[:16000]
    err = (proc.stderr or "")[:16000]
    return {
        "returncode": proc.returncode,
        "stdout": out,
        "stderr": err,
    }


def run_js_prefix_with_failshot_ex(
    *,
    prefix_body: str,
    start_url: str,
    viewport_w: int,
    viewport_h: int,
    failshot_path: Path,
    timeout_sec: int = 180,
    browser: str = "chrome",
) -> Tuple[str, Optional[str], Dict[str, Any]]:
    """Пустая строка и (опционально) a11y snapshot = успех; иначе текст ошибки. Третий элемент — stdout/stderr node-процесса (MCP/legacy).

    ``browser``: ``chrome`` или ``firefox`` (MCP ``--browser chrome|firefox``). Устаревшее ``chromium`` трактуется как ``chrome``.
    """
    failshot_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".js",
        delete=False,
        encoding="utf-8",
    ) as f:
        f.write(prefix_body)
        tmp = f.name
    b = (browser or "chrome").strip().lower()
    if b == "chromium":
        b = "chrome"
    if b not in ("chrome", "firefox"):
        b = "chrome"
    env = {
        **playwright_node_environ(),
        "CODEGEN_START_URL": start_url,
        "CODEGEN_VIEWPORT_W": str(viewport_w),
        "CODEGEN_VIEWPORT_H": str(viewport_h),
        "CODEGEN_FAILSHOT": str(failshot_path),
        "CODEGEN_BROWSER": b,
    }
    if b == "chrome" and USE_PLAYWRIGHT_MCP and mcp_runner_ready():
        apply_playwright_mcp_chrome_user_agent(env)
    node_bin = os.environ.get("NODE_BINARY", "node")
    try:
        if USE_PLAYWRIGHT_MCP and mcp_runner_ready():
            proc = subprocess.run(
                [node_bin, str(MCP_RUN_FRAGMENT), tmp],
                cwd=str(NODE_RUNNER_DIR),
                env=env,
                capture_output=True,
                text=True,
                timeout=timeout_sec,
            )
        elif legacy_runner_ready():
            proc = subprocess.run(
                [node_bin, str(RUN_FRAGMENT), tmp],
                cwd=str(NODE_RUNNER_DIR),
                env=env,
                capture_output=True,
                text=True,
                timeout=timeout_sec,
            )
        else:
            raise RuntimeError(
                "codegen runner not installed: `npm install` in clicker/src/codegen/node_runner "
                "(Microsoft Playwright MCP: @playwright/mcp + @modelcontextprotocol/sdk)"
            )
        failed = proc.returncode != 0 or _proc_output_has_mcp_error_marker(proc)
        if failed:
            err = _error_text_from_proc(proc)
            return err, _read_a11y_sidecar(failshot_path), _subprocess_io_dict(proc)
        return "", None, _subprocess_io_dict(proc)
    finally:
        try:
            os.unlink(tmp)
        except OSError:
            pass


def _read_a11y_sidecar(failshot_path: Path) -> Optional[str]:
    side = failshot_path.parent / (failshot_path.stem + ".a11y.txt")
    if not side.is_file():
        return None
    try:
        text = side.read_text(encoding="utf-8", errors="replace")
        return text if text.strip() else None
    except OSError:
        return None
