"""Разбор монолитного source_code артефакта на блоки по step_uid (для прогона playwright_js)."""
# TODO: убедиться, что парсинг монолита обоснован — возможно, проще хранить фрагменты по step_uid
# отдельно в артефакте/БД и не восстанавливать блоки регэкспами при каждом playwright_js прогоне.
from __future__ import annotations

import re
from typing import Dict, List, Tuple

_STEP_MARK = re.compile(r"^\s*// step_uid:(\S+)", re.MULTILINE)


def extract_inner_js_body(source_code: str) -> str:
    """Тело async function runScenario(page) без обёртки module.exports."""
    m = re.search(
        r"const\s+request\s*=\s*context\.request\s*;\s*\r?\n(.*)\r?\n\}\s*;\s*$",
        source_code,
        re.DOTALL,
    )
    if m:
        return m.group(1).strip()
    # запасной вариант: от первого step_uid до последней закрывающей скобки сценария
    m2 = re.search(r"(\s*// step_uid:.+)", source_code, re.DOTALL)
    if not m2:
        return ""
    chunk = m2.group(1)
    chunk = re.sub(r"\n\}\s*;\s*$", "", chunk, count=1)
    return chunk.strip()


def step_uid_blocks(inner_body: str) -> List[Tuple[str, str]]:
    """Список (step_uid, текст блока от // step_uid до следующего маркера или конца)."""
    text = inner_body
    matches = list(_STEP_MARK.finditer(text))
    out: List[Tuple[str, str]] = []
    for i, m in enumerate(matches):
        uid = m.group(1)
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        out.append((uid, text[start:end].strip()))
    return out


def blocks_by_uid(source_code: str) -> Dict[str, str]:
    """По одному ключу на step_uid: при повторяющихся маркерах в артефакте остаётся только последний блок."""
    inner = extract_inner_js_body(source_code)
    return {uid: block for uid, block in step_uid_blocks(inner)}


def inner_body_prefix_before_first_step(inner_body: str) -> str:
    """
    Код до первого маркера // step_uid: (например await page.goto после const request).
    Нужен для монолитного прогона: этот фрагмент не входит в blocks_by_uid.
    """
    text = inner_body.strip()
    m = _STEP_MARK.search(text)
    if not m:
        return text
    return text[: m.start()].strip()
