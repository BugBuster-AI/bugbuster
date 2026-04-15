"""Постобработка JS-фрагментов codegen: добавление `await` к типичным Promise-вызовам Playwright."""
from __future__ import annotations

import re
from typing import Final, Optional, Set

# Цепочки, завершающиеся промисом (locator actions).
_TERMINAL_ASYNC: Final[re.Pattern[str]] = re.compile(
    r"\.(click|dblclick|fill|type|press|check|uncheck|selectOption|setInputFiles|hover|tap|focus)\s*\("
)

# Прямые вызовы page|context|frame → Promise.
_DIRECT_ASYNC: Final[re.Pattern[str]] = re.compile(
    r"^(page|context|frame)\.(goto|reload|goBack|goForward|waitForURL|waitForLoadState|waitForTimeout|waitForSelector|waitForFunction|setViewportSize|addInitScript|evaluate|bringToFront|screenshot|pdf|pause|route|unroute|addCookies|clearCookies|grantPermissions|clearPermissions)\s*\("
)

_SKIP_LINE_PREFIXES: Final[tuple[str, ...]] = (
    "await ",
    "return ",
    "//",
    "if ",
    "for ",
    "while ",
    "try",
    "catch",
    "else",
    "switch",
    "case ",
    "throw ",
    "function",
    "async ",
    "import ",
    "export ",
    "*",
)


def _strip_trailing_semicolon(s: str) -> str:
    s = s.rstrip()
    if s.endswith(";"):
        return s[:-1].rstrip()
    return s


def _needs_await(expr: str) -> bool:
    e = expr.strip()
    if not e or e.startswith("await "):
        return False
    if _DIRECT_ASYNC.match(e):
        return True
    if (e.startswith("page.") or e.startswith("context.") or e.startswith("frame.")) and _TERMINAL_ASYNC.search(e):
        return True
    return False


def _normalize_one_line(line: str) -> str:
    indent = line[: len(line) - len(line.lstrip())]
    s = line.lstrip()
    if not s:
        return line
    if s.startswith("//"):
        return line
    if s.startswith("}"):
        return line
    if any(s.startswith(p) for p in _SKIP_LINE_PREFIXES):
        return line

    m = re.match(r"^(const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*(.+)$", s)
    if m:
        rhs = m.group(3).strip()
        rhs_core = _strip_trailing_semicolon(rhs)
        if rhs_core.startswith("await "):
            return line
        if _needs_await(rhs_core):
            new_rhs = f"await {rhs_core}"
            if rhs.rstrip().endswith(";"):
                new_rhs += ";"
            return indent + f"{m.group(1)} {m.group(2)} = {new_rhs}"
        return line

    had_semi = s.rstrip().endswith(";")
    core = _strip_trailing_semicolon(s)
    if _needs_await(core):
        out = indent + "await " + core
        if had_semi:
            out += ";"
        return out
    return line


def normalize_playwright_await_fragment(fragment: str) -> str:
    """Добавляет отсутствующий `await` к строкам с типичными async-вызовами Playwright."""
    if not (fragment or "").strip():
        return fragment
    return "\n".join(_normalize_one_line(ln) for ln in fragment.splitlines())


_BINDING = re.compile(r"^(\s*)(?:const|let)\s+([A-Za-z_$][\w$]*)\s*=\s*(.+)$")


def _dedupe_const_after_semicolon_same_line(js: str, declared: set[str]) -> str:
    """
    Строка вида `const text = await a(); const text = await b();` даёт один матч _BINDING на всю
    строку: второй `const text` оказывается внутри group(3) и не дедупится. Заменяем повторные
    `; const name =` / `; let name =` на `; name =` для имён, уже есть в declared.
    """
    if not (js or "").strip() or not declared:
        return js
    out = js
    for name in sorted(declared, key=len, reverse=True):
        esc = re.escape(name)
        out = re.sub(
            rf"(?<=;)(\s*)const\s+{esc}\b\s*=",
            rf"\1{name} =",
            out,
        )
        out = re.sub(
            rf"(?<=;)(\s*)let\s+{esc}\b\s*=",
            rf"\1{name} =",
            out,
        )
    return out


def _collect_declared_bindings(js: str) -> set[str]:
    """Имена, уже объявленные через const/let в накопленном сценарии (одна область видимости)."""
    out: set[str] = set()
    for line in (js or "").splitlines():
        line = line.replace("\r", "")
        s = line.strip()
        if not s or s.startswith("//"):
            continue
        m = _BINDING.match(line)
        if m:
            out.add(m.group(2))
    return out


def dedupe_const_declarations(
    prior_js: str,
    fragment: str,
    *,
    extra_declared: Optional[Set[str]] = None,
) -> str:
    """
    Весь сценарий — один async (page)=>{...}; повторный `const x` / `let x` даёт SyntaxError.
    Заменяет повторные объявления на присваивание `x = ...` (имя уже есть в prior_js или в этом же фрагменте выше).

    extra_declared: имена, уже связанные литеральной преамбулой codegen (`const name = "..."`), если разбор prior_js их не уловил.
    """
    if not (fragment or "").strip():
        return fragment
    declared = set(_collect_declared_bindings(prior_js))
    if extra_declared:
        declared |= extra_declared
    out_lines: list[str] = []
    for line in fragment.splitlines():
        line = line.replace("\r", "")
        s = line.strip()
        if not s or s.startswith("//"):
            out_lines.append(line)
            continue
        m = _BINDING.match(line)
        if m and m.group(2) in declared:
            indent, name, rhs = m.group(1), m.group(2), m.group(3)
            out_lines.append(f"{indent}{name} = {rhs}")
            continue
        if m:
            declared.add(m.group(2))
        out_lines.append(line)
    merged = "\n".join(out_lines)
    return _dedupe_const_after_semicolon_same_line(merged, declared)
