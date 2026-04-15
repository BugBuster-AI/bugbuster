"""Нормализация NL шагов для steps_content_hash и детекта смены текста (PATCH кейca)."""
from __future__ import annotations

import hashlib
import json
import uuid
from typing import Any, List, Optional

def _normalize_step_value(step: Any) -> str:
    if isinstance(step, str):
        return step.strip()
    if isinstance(step, dict):
        v = step.get("value")
        if v is None:
            return ""
        return str(v).strip()
    return ""


def normalized_nl_vectors(
    before_browser_start: Optional[List],
    before_steps: Optional[List],
    steps: Optional[List],
    after_steps: Optional[List],
) -> List[tuple]:
    """Детерминированное представление только NL-полей исполняемых шагов (_value_ по шагам в порядке секций)."""
    out: List[tuple] = []
    sections = [
        ("before_browser_start", before_browser_start or []),
        ("before_steps", before_steps or []),
        ("steps", steps or []),
        ("after_steps", after_steps or []),
    ]
    for section_name, arr in sections:
        for i, step in enumerate(arr):
            out.append((section_name, i, _normalize_step_value(step)))
    return out


def compute_steps_content_hash(
    before_browser_start: Optional[List],
    before_steps: Optional[List],
    steps: Optional[List],
    after_steps: Optional[List],
) -> str:
    payload = normalized_nl_vectors(before_browser_start, before_steps, steps, after_steps)
    raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _new_step_uid() -> str:
    return str(uuid.uuid4())


def _merge_uids_for_list(old_list: Optional[List], new_list: List) -> None:
    old_list = old_list or []
    for i, step in enumerate(new_list):
        if not isinstance(step, dict):
            continue
        if step.get("step_uid"):
            continue
        if i < len(old_list) and isinstance(old_list[i], dict) and old_list[i].get("step_uid"):
            step["step_uid"] = old_list[i]["step_uid"]
        else:
            step["step_uid"] = _new_step_uid()


def ensure_step_uids_on_case_payload(
    existing_before_browser_start: Optional[List],
    existing_before_steps: Optional[List],
    existing_steps: Optional[List],
    existing_after_steps: Optional[List],
    before_browser_start: Optional[List],
    before_steps: Optional[List],
    steps: Optional[List],
    after_steps: Optional[List],
) -> None:
    """Стабильные step_uid: копируем с прежнего шага по индексу секции, иначе новый UUID."""
    pairs = [
        (existing_before_browser_start, before_browser_start),
        (existing_before_steps, before_steps),
        (existing_steps, steps),
        (existing_after_steps, after_steps),
    ]
    for old, new in pairs:
        if new is None:
            continue
        _merge_uids_for_list(old, new)
    ensure_unique_step_uids_across_case(
        before_browser_start,
        before_steps,
        steps,
        after_steps,
    )


def ensure_unique_step_uids_across_case(
    before_browser_start: Optional[List],
    before_steps: Optional[List],
    steps: Optional[List],
    after_steps: Optional[List],
) -> None:
    """
    Во всех секциях шагов step_uid должен быть уникален. Повтор второго и далее шага с тем же uid
    (часто из-за ручного редактирования или бага клиента) ломает codegen/playwright_js, где uid
    используется как ключ. Первое вхождение оставляем, дубликатам выдаём новые UUID.
    """
    seen: set[str] = set()
    for arr in (before_browser_start, before_steps, steps, after_steps):
        if not arr:
            continue
        for step in arr:
            if not isinstance(step, dict):
                continue
            uid = step.get("step_uid")
            if not uid:
                continue
            s = str(uid).strip()
            if not s:
                step["step_uid"] = _new_step_uid()
                seen.add(str(step["step_uid"]))
                continue
            if s in seen:
                step["step_uid"] = _new_step_uid()
                seen.add(str(step["step_uid"]))
            else:
                seen.add(s)


def assign_step_uids_new_case(
    before_browser_start: Optional[List],
    before_steps: Optional[List],
    steps: Optional[List],
    after_steps: Optional[List],
) -> None:
    for arr in (before_browser_start, before_steps, steps, after_steps):
        if not arr:
            continue
        for step in arr:
            if isinstance(step, dict) and not step.get("step_uid"):
                step["step_uid"] = _new_step_uid()
    ensure_unique_step_uids_across_case(
        before_browser_start,
        before_steps,
        steps,
        after_steps,
    )


def ensure_unique_step_uids_in_list(steps: Optional[List]) -> None:
    """
    Уникальность step_uid внутри одного списка (shared_steps.steps).
    Дубликаты заменяются новыми UUID.
    """
    if not steps:
        return
    seen: set[str] = set()
    for step in steps:
        if not isinstance(step, dict):
            continue
        uid = step.get("step_uid")
        if not uid:
            continue
        s = str(uid).strip()
        if not s:
            step["step_uid"] = _new_step_uid()
            seen.add(str(step["step_uid"]))
            continue
        if s in seen:
            step["step_uid"] = _new_step_uid()
            seen.add(str(step["step_uid"]))
        else:
            seen.add(s)


def assign_step_uids_new_shared_steps(steps: Optional[List]) -> None:
    """Новые shared_steps: каждому dict-шагу без step_uid выдать UUID, затем убрать дубликаты."""
    if not steps:
        return
    for step in steps:
        if isinstance(step, dict) and not step.get("step_uid"):
            step["step_uid"] = _new_step_uid()
    ensure_unique_step_uids_in_list(steps)


def ensure_step_uids_on_shared_steps_update(
    old_steps: Optional[List],
    new_steps: Optional[List],
) -> None:
    """PATCH shared_steps: стабильный uid по индексу из old_steps, новые шаги получают UUID."""
    if new_steps is None:
        return
    _merge_uids_for_list(old_steps, new_steps)
    ensure_unique_step_uids_in_list(new_steps)
