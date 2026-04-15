"""Извлечение подсказок из ошибки Playwright strict mode violation для repair-промптов."""
from __future__ import annotations

import re
from typing import Optional

_STRICT_MODE_MAX_HINT_CHARS = 2000
_STRICT_MODE_MAX_CANDIDATE_LINES = 12
_STRICT_MODE_MAX_LINE_CHARS = 500


def format_strict_mode_hints_from_playwright_error(playwright_error: Optional[str]) -> Optional[str]:
    """
    Если ошибка Playwright содержит strict mode violation и `resolved to N elements:`,
    возвращает компактный текстовый блок для user message repair; иначе None.
    """
    if not playwright_error or not str(playwright_error).strip():
        return None
    ansi = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")
    t = ansi.sub("", playwright_error)
    low = t.lower()
    if "strict mode violation" not in low:
        return None
    m = re.search(r"(?is)resolved\s+to\s+(\d+)\s+elements?\s*:", t)
    if not m:
        return None
    n = int(m.group(1))
    start = m.end()
    end = t.find("Call log:", start)
    if end < 0:
        end = len(t)
    raw_block = t[start:end].strip()
    if not raw_block:
        return None
    lines: list[str] = []
    for ln in raw_block.splitlines():
        s = ln.strip()
        if not s:
            continue
        if len(s) > _STRICT_MODE_MAX_LINE_CHARS:
            s = s[: _STRICT_MODE_MAX_LINE_CHARS - 24] + "…[line truncated]"
        lines.append(s)
        if len(lines) >= _STRICT_MODE_MAX_CANDIDATE_LINES:
            lines.append("... [truncated: more candidate lines omitted]")
            break
    body = "\n".join(lines)
    header = f"strict_mode_violation=true\nresolved_to={n}\n---\n"
    out = header + body
    if len(out) > _STRICT_MODE_MAX_HINT_CHARS:
        out = out[: _STRICT_MODE_MAX_HINT_CHARS - 48] + "\n... [strict mode hints truncated]"
    return out
