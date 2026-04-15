"""Единый предикат can_start_codegen и связанные проверки (без дублирования на фронте)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, Tuple
from uuid import UUID

from sqlalchemy import and_, delete, desc, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Case, CasePlaywrightCodegen, ProjectUser, RunCase
from schemas import CaseFinalStatusEnum, CaseTypeEnum


@dataclass
class CodegenEligibilityResult:
    allowed: bool
    reason_code: Optional[str]


def is_successful_terminal_run(run: RunCase) -> bool:
    return bool(run.status and run.status == CaseFinalStatusEnum.PASSED.value)


async def can_run_playwright_js(session: AsyncSession, case_id: UUID) -> bool:
    q = select(CasePlaywrightCodegen).where(
        CasePlaywrightCodegen.case_id == case_id,
        CasePlaywrightCodegen.is_current.is_(True),
    )
    res = await session.execute(q)
    row = res.scalars().first()
    if not row:
        return False
    cq = select(Case.codegen_regeneration_required).where(Case.case_id == case_id)
    cr = await session.execute(cq)
    required = cr.scalar_one()
    return not bool(required)


class CodegenEligibilityService:
    @staticmethod
    async def can_start_codegen(
        session: AsyncSession,
        case_id: UUID,
        run_id: UUID,
        workspace_id: UUID,
        user_id: UUID,
        *,
        codegen_job_running: bool = False,
    ) -> Tuple[bool, Optional[str]]:
        if codegen_job_running:
            return False, "codegen_in_progress"

        case_q = (
            select(Case)
            .join(ProjectUser, and_(ProjectUser.project_id == Case.project_id,
                                     ProjectUser.workspace_id == workspace_id,
                                     ProjectUser.user_id == user_id))
            .where(Case.case_id == case_id)
        )
        cr = await session.execute(case_q)
        case = cr.scalars().first()
        if not case:
            return False, "case_not_found"

        run_q = (
            select(RunCase)
            .join(ProjectUser, and_(ProjectUser.project_id == RunCase.project_id,
                                     ProjectUser.workspace_id == workspace_id,
                                     ProjectUser.user_id == user_id))
            .where(RunCase.run_id == run_id, RunCase.case_id == case_id)
        )
        rr = await session.execute(run_q)
        run = rr.scalars().first()
        if not run:
            return False, "run_not_found"

        if not is_successful_terminal_run(run):
            return False, "run_not_passed"

        if (run.execution_engine or "vlm") != "vlm":
            return False, "run_not_vlm"

        if case.codegen_regeneration_required and case.codegen_regeneration_since is not None:
            finished = run.end_dt
            if finished is None:
                return False, "reference_run_stale_after_nl_edit"
            finished_utc = finished if finished.tzinfo else finished.replace(tzinfo=timezone.utc)
            since = case.codegen_regeneration_since
            since_utc = since if since.tzinfo else since.replace(tzinfo=timezone.utc)
            if finished_utc < since_utc:
                return False, "reference_run_stale_after_nl_edit"

        return True, None

    @staticmethod
    async def eligibility_result(
        session: AsyncSession,
        case_id: UUID,
        run_id: UUID,
        workspace_id: UUID,
        user_id: UUID,
        *,
        codegen_job_running: bool = False,
    ) -> CodegenEligibilityResult:
        ok, reason = await CodegenEligibilityService.can_start_codegen(
            session, case_id, run_id, workspace_id, user_id, codegen_job_running=codegen_job_running,
        )
        return CodegenEligibilityResult(allowed=ok, reason_code=reason if not ok else None)

    @staticmethod
    async def codegen_reference_available(
        session: AsyncSession,
        case_id: UUID,
        workspace_id: UUID,
        user_id: UUID,
        *,
        codegen_job_running: bool = False,
    ) -> Tuple[bool, Optional[str]]:
        """True if there is (or user could pick) a VLM reference run that passes can_start_codegen.

        Used for repository list / CaseRead: show when code generation cannot be started at all.
        """
        if codegen_job_running:
            return False, "codegen_in_progress"

        case_q = (
            select(Case)
            .join(ProjectUser, and_(ProjectUser.project_id == Case.project_id,
                                     ProjectUser.workspace_id == workspace_id,
                                     ProjectUser.user_id == user_id))
            .where(Case.case_id == case_id)
        )
        cr = await session.execute(case_q)
        case = cr.scalars().first()
        if not case:
            return False, "case_not_found"

        ctype = (case.type or CaseTypeEnum.AUTOMATED.value)
        if ctype != CaseTypeEnum.AUTOMATED.value:
            return False, "case_not_automated"

        vlm_engine = func.coalesce(RunCase.execution_engine, "vlm")

        base = (
            select(RunCase)
            .join(ProjectUser, and_(ProjectUser.project_id == RunCase.project_id,
                                     ProjectUser.workspace_id == workspace_id,
                                     ProjectUser.user_id == user_id))
            .where(
                RunCase.case_id == case_id,
                RunCase.status == CaseFinalStatusEnum.PASSED.value,
                vlm_engine == "vlm",
            )
        )

        any_passed = await session.execute(base.order_by(desc(RunCase.end_dt), desc(RunCase.created_at)).limit(1))
        any_run = any_passed.scalars().first()
        if not any_run:
            return False, "no_passed_vlm_run"

        q = base
        if case.codegen_regeneration_required and case.codegen_regeneration_since is not None:
            since = case.codegen_regeneration_since
            q = q.where(RunCase.end_dt.isnot(None)).where(RunCase.end_dt >= since)

        res = await session.execute(q.order_by(desc(RunCase.end_dt), desc(RunCase.created_at)).limit(1))
        run = res.scalars().first()
        if not run:
            return False, "reference_run_stale_after_nl_edit"

        ok, reason = await CodegenEligibilityService.can_start_codegen(
            session,
            case_id,
            run.run_id,
            workspace_id,
            user_id,
            codegen_job_running=False,
        )
        if ok:
            return True, None
        return False, reason or "invalid_run"


async def invalidate_codegen_artifact(session: AsyncSession, case_id: UUID) -> bool:
    """Удаляет текущий codegen-артефакт и очищает ссылки в RunCase.

    **Контракт транзакции**: должна вызываться внутри уже активной транзакции
    (``session.begin()`` / ``transaction_scope``). Границу транзакции контролирует
    вызывающий код; функция НЕ делает commit и НЕ открывает свою транзакцию.
    Если сессия не в транзакции, изменения не будут сохранены.

    Возвращает ``True``, если артефакт существовал и был удалён.
    """
    q = select(CasePlaywrightCodegen).where(
        CasePlaywrightCodegen.case_id == case_id,
        CasePlaywrightCodegen.is_current.is_(True),
    )
    r = await session.execute(q)
    art = r.scalars().first()
    if not art:
        return False

    await session.execute(
        update(RunCase)
        .where(RunCase.playwright_codegen_artifact_id == art.id)
        .values(playwright_codegen_artifact_id=None)
    )
    await session.execute(
        delete(CasePlaywrightCodegen).where(CasePlaywrightCodegen.id == art.id)
    )
    return True
