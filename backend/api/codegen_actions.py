from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import HTTPException
from pydantic import UUID4
from sqlalchemy import and_, delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from api.codegen_minio_log import (
    delete_codegen_log_artifacts,
    init_empty_job_log,
    load_job_log,
    save_job_log,
    upload_codegen_screenshot_base64,
)
from api.services.codegen_eligibility import CodegenEligibilityService, invalidate_codegen_artifact
from background_publisher import send_to_rabbitmq
from config import RABBIT_PREFIX, REDIS_PREFIX, logger, redis_client
from db.models import Case, CasePlaywrightCodegen, ProjectUser, RunCase
from db.session import transaction_scope
from schemas import PlaywrightCodegenStartBody, RunSingleCase


CODEGEN_REDIS_KEY = f"{REDIS_PREFIX}_codegen_status"
CODEGEN_LOG_MAX = 800
CODEGEN_START_LOCK_TTL = 30


def _redis_key(case_id: str) -> str:
    return f"{CODEGEN_REDIS_KEY}:{case_id}"


def _start_lock_key(case_id: str) -> str:
    return f"{CODEGEN_REDIS_KEY}:start_lock:{case_id}"


def _get_codegen_job(case_id: UUID) -> Optional[dict]:
    raw = redis_client.get(_redis_key(str(case_id)))
    if not raw:
        return None
    try:
        return json.loads(raw.decode("utf-8"))
    except Exception:
        return None


def get_codegen_job_snapshot(case_id: UUID) -> Optional[dict]:
    """Read-only snapshot of codegen job from Redis (same payload as internal _get_codegen_job)."""
    return _get_codegen_job(case_id)


def _job_payload_for_redis(payload: dict) -> dict:
    """Лог хранится в MinIO; в Redis не кладём поле log."""
    out = dict(payload)
    out.pop("log", None)
    return out


CODEGEN_JOB_TTL_SECONDS = 7200  # 2h safety net; worker updates on each log append

def _set_codegen_job(case_id: UUID, payload: dict) -> None:
    redis_client.set(
        _redis_key(str(case_id)),
        json.dumps(_job_payload_for_redis(payload), default=str),
        ex=CODEGEN_JOB_TTL_SECONDS,
    )


def codegen_job_running(case_id: UUID) -> bool:
    job = _get_codegen_job(case_id)
    return bool(job and job.get("state") in ("queued", "running"))


def clear_codegen_job_data(case_id: UUID) -> None:
    """Remove the codegen job record from Redis (log, status, etc.)."""
    redis_client.delete(_redis_key(str(case_id)))


def _message_key_for_reason(reason: Optional[str]) -> str:
    mapping = {
        "run_not_passed": "codegen.error.run_not_passed",
        "run_not_vlm": "codegen.error.run_not_vlm",
        "run_not_found": "codegen.error.run_not_found",
        "case_not_found": "codegen.error.case_not_found",
        "codegen_in_progress": "codegen.error.in_progress",
    }
    return mapping.get(reason or "", "codegen.error.invalid_run")


async def post_start_playwright_codegen(
    case_id: UUID4,
    body: PlaywrightCodegenStartBody,
    session: AsyncSession,
    user,
) -> dict:
    lock_key = _start_lock_key(str(case_id))
    acquired = redis_client.set(lock_key, "1", nx=True, ex=CODEGEN_START_LOCK_TTL)
    if not acquired:
        raise HTTPException(
            status_code=409,
            detail={"reason_code": "codegen_in_progress", "message_key": "codegen.error.in_progress"},
        )
    try:
        return await _post_start_playwright_codegen_inner(case_id, body, session, user)
    finally:
        redis_client.delete(lock_key)


async def _post_start_playwright_codegen_inner(
    case_id: UUID4,
    body: PlaywrightCodegenStartBody,
    session: AsyncSession,
    user,
) -> dict:
    if codegen_job_running(case_id):
        raise HTTPException(
            status_code=409,
            detail={"reason_code": "codegen_in_progress", "message_key": "codegen.error.in_progress"},
        )

    run_id = body.run_id
    ok, reason = await CodegenEligibilityService.can_start_codegen(
        session,
        case_id,
        run_id,
        user.active_workspace_id,
        user.user_id,
        codegen_job_running=False,
    )
    if not ok:
        if reason == "reference_run_stale_after_nl_edit":
            raise HTTPException(
                status_code=409,
                detail={"reason_code": reason, "message_key": "codegen.error.stale_reference_run"},
            )
        if reason in ("run_not_found", "case_not_found"):
            raise HTTPException(status_code=404, detail={"reason_code": reason, "message_key": f"codegen.error.{reason}"})
        raise HTTPException(
            status_code=422,
            detail={"reason_code": reason or "invalid_run", "message_key": _message_key_for_reason(reason)},
        )

    task_id = str(uuid.uuid4())
    queue_name = f"{RABBIT_PREFIX}_celery.portal-clicker.run_playwright_codegen_queue"
    payload = RunSingleCase(
        id=uuid.UUID(task_id),
        task=queue_name,
        args=[],
        kwargs={
            "case_id": str(case_id),
            "run_id": str(run_id),
            "user_id": str(user.user_id),
            "workspace_id": str(user.active_workspace_id),
            "task_id": task_id,
            "max_validation_attempts": body.max_validation_attempts,
        },
    ).model_dump(mode="json")
    message = json.dumps(payload).encode("utf-8")

    async with transaction_scope(session):
        cq = (
            select(Case)
            .join(ProjectUser, and_(ProjectUser.project_id == Case.project_id,
                                    ProjectUser.workspace_id == user.active_workspace_id,
                                    ProjectUser.user_id == user.user_id))
            .where(Case.case_id == case_id)
        )
        cr = await session.execute(cq)
        case_row = cr.scalars().first()
        if not case_row:
            raise HTTPException(status_code=404, detail="Case not found")
        if case_row.codegen_first_requested_at is None:
            case_row.codegen_first_requested_at = datetime.now(timezone.utc)
        await invalidate_codegen_artifact(session, case_id)

    try:
        init_empty_job_log(str(run_id))
    except Exception:
        pass

    _set_codegen_job(
        case_id,
        {
            "task_id": task_id,
            "run_id": str(run_id),
            "state": "queued",
            "error": None,
            "max_validation_attempts": body.max_validation_attempts,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
    )

    try:
        await send_to_rabbitmq(queue_name, message, task_id)
    except Exception:
        clear_codegen_job_data(case_id)
        raise

    return {"task_id": task_id, "case_id": str(case_id), "run_id": str(run_id)}


def enrich_codegen_log_entries(
    log: List[Dict[str, Any]],
    host: Optional[str],
) -> List[Dict[str, Any]]:
    """Добавляет presigned screenshot_url для записей с screenshot_minio."""
    from utils import generate_presigned_url

    out: List[Dict[str, Any]] = []
    for row in log:
        r = dict(row)
        sm = r.get("screenshot_minio")
        if isinstance(sm, dict) and sm.get("bucket") and sm.get("file"):
            try:
                r["screenshot_url"] = generate_presigned_url(
                    str(sm["bucket"]),
                    str(sm["file"]),
                    host,
                )
            except Exception:
                r["screenshot_url"] = None
        out.append(r)
    return out


async def get_playwright_codegen_status(
    case_id: UUID4,
    session: AsyncSession,
    user,
    run_id: Optional[UUID4] = None,
    host: Optional[str] = None,
) -> dict:
    """Статус codegen для UI: флаги кейса, Redis job и привязка к текущему артефакту.

    Поле ``source_run_id`` — UUID эталонного VLM-прогона из строки
    ``CasePlaywrightCodegen`` с ``is_current == True`` (последняя успешная
    финализация ``internal_finalize_codegen``). Если текущей строки нет, значение
    ``None``: например после успешного ``POST .../codegen/playwright``, когда
    ``invalidate_codegen_artifact`` логически удалил предыдущий артефакт, до прихода
    новой успешной финализации; при ``failure`` воркера после повторного запуска
    артефакт не создаётся и ``source_run_id`` остаётся ``None``.
    """
    q = (
        select(Case, CasePlaywrightCodegen)
        .join(ProjectUser, and_(ProjectUser.project_id == Case.project_id,
                                 ProjectUser.workspace_id == user.active_workspace_id,
                                 ProjectUser.user_id == user.user_id))
        .outerjoin(
            CasePlaywrightCodegen,
            and_(CasePlaywrightCodegen.case_id == Case.case_id, CasePlaywrightCodegen.is_current.is_(True)),
        )
        .where(Case.case_id == case_id)
    )
    r = await session.execute(q)
    row = r.first()
    if not row:
        raise HTTPException(status_code=404, detail="Case not found")
    case, artifact = row[0], row[1]

    job = _get_codegen_job(case_id) or {}
    jr = job.get("run_id")
    if jr:
        try:
            raw_log = await asyncio.to_thread(load_job_log, str(jr))
            job_log = enrich_codegen_log_entries(raw_log, host)
        except Exception:
            job_log = []
    else:
        job_log = []

    # Redis-потеря (рестарт контейнера, TTL): снимка задачи нет, но в Postgres остаётся
    # текущий артефакт — UI иначе не подгружает код (ждёт job.state == success) и лог
    # (run_id в Redis). Восстанавливаем финальное состояние и лог из MinIO по source_run_id.
    if artifact is not None and artifact.source_run_id and not job.get("state"):
        recover_rid = str(artifact.source_run_id)
        job = {
            "task_id": job.get("task_id"),
            "state": "success",
            "error": None,
            "run_id": recover_rid,
            "updated_at": job.get("updated_at")
            or (
                artifact.updated_at.isoformat()
                if getattr(artifact, "updated_at", None) is not None
                else None
            ),
            "max_validation_attempts": job.get("max_validation_attempts"),
        }
        try:
            raw_log = await asyncio.to_thread(load_job_log, recover_rid)
            job_log = enrich_codegen_log_entries(raw_log, host)
        except Exception:
            job_log = []

    out: Dict[str, Any] = {
        "codegen_regeneration_required": case.codegen_regeneration_required,
        "codegen_regeneration_since": case.codegen_regeneration_since,
        "codegen_first_requested_at": case.codegen_first_requested_at,
        # Только текущий артефакт в БД; после invalidate — None до успешной финализации.
        "source_run_id": str(artifact.source_run_id) if artifact else None,
        "job": {
            "task_id": job.get("task_id"),
            "state": job.get("state"),
            "error": job.get("error"),
            "run_id": job.get("run_id"),
            "log": job_log,
            "updated_at": job.get("updated_at"),
            "max_validation_attempts": job.get("max_validation_attempts"),
        },
    }
    if run_id is not None:
        elig = await CodegenEligibilityService.eligibility_result(
            session,
            case_id,
            run_id,
            user.active_workspace_id,
            user.user_id,
            codegen_job_running=codegen_job_running(case_id),
        )
        out["codegen_eligibility"] = {
            "allowed": elig.allowed,
            "reason_code": elig.reason_code,
        }
    return out


async def clear_playwright_codegen_job(case_id: UUID4, session: AsyncSession, user) -> dict:
    """Удаляет запись о задаче codegen в Redis (например, после сбоя воркера или потери сообщения в очереди)."""
    cq = (
        select(Case.case_id)
        .join(
            ProjectUser,
            and_(
                ProjectUser.project_id == Case.project_id,
                ProjectUser.workspace_id == user.active_workspace_id,
                ProjectUser.user_id == user.user_id,
            ),
        )
        .where(Case.case_id == case_id)
    )
    cr = await session.execute(cq)
    if cr.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Case not found")
    job = _get_codegen_job(case_id)
    rid = job.get("run_id") if job else None
    if rid:
        try:
            delete_codegen_log_artifacts(str(rid))
        except Exception:
            pass
    redis_client.delete(_redis_key(str(case_id)))
    return {"cleared": True}


async def delete_playwright_codegen_artifact(case_id: UUID4, session: AsyncSession, user) -> dict:
    async with session.begin():
        from sqlalchemy import func as sa_func
        q = (
            select(CasePlaywrightCodegen)
            .join(Case, Case.case_id == CasePlaywrightCodegen.case_id)
            .join(
                ProjectUser,
                and_(
                    ProjectUser.project_id == Case.project_id,
                    ProjectUser.workspace_id == user.active_workspace_id,
                    ProjectUser.user_id == user.user_id,
                ),
            )
            .where(Case.case_id == case_id, CasePlaywrightCodegen.is_current.is_(True))
            .with_for_update()
        )
        r = await session.execute(q)
        art = r.scalars().first()
        if not art:
            raise HTTPException(status_code=404, detail="No current codegen artifact")
        aid = art.id
        await session.execute(
            update(RunCase)
            .where(RunCase.playwright_codegen_artifact_id == aid)
            .values(playwright_codegen_artifact_id=None)
        )
        await session.execute(delete(CasePlaywrightCodegen).where(CasePlaywrightCodegen.id == aid))
    return {"deleted": True, "artifact_id": str(aid)}


async def get_playwright_codegen_artifact(case_id: UUID4, session: AsyncSession, user) -> dict:
    q = (
        select(CasePlaywrightCodegen, Case.codegen_regeneration_required)
        .join(Case, Case.case_id == CasePlaywrightCodegen.case_id)
        .join(ProjectUser, and_(ProjectUser.project_id == Case.project_id,
                                 ProjectUser.workspace_id == user.active_workspace_id,
                                 ProjectUser.user_id == user.user_id))
        .where(Case.case_id == case_id, CasePlaywrightCodegen.is_current.is_(True))
    )
    r = await session.execute(q)
    row = r.first()
    if not row:
        raise HTTPException(status_code=404, detail="No current codegen artifact")
    art, regen_required = row[0], row[1]
    if regen_required:
        raise HTTPException(
            status_code=409,
            detail={
                "reason_code": "playwright_js_stale_artifact",
                "message_key": "codegen.error.stale_artifact",
            },
        )
    return {
        "source_code": art.source_code,
        "step_spans": art.step_spans,
        "source_run_id": str(art.source_run_id),
        "artifact_id": str(art.id),
    }


async def get_playwright_codegen_artifact_by_id(
    case_id: UUID4,
    artifact_id: UUID4,
    session: AsyncSession,
    user,
) -> dict:
    """Артефакт codegen по id (для просмотра кода шага в /running по run.playwright_codegen_artifact_id)."""
    q = (
        select(CasePlaywrightCodegen)
        .join(Case, Case.case_id == CasePlaywrightCodegen.case_id)
        .join(
            ProjectUser,
            and_(
                ProjectUser.project_id == Case.project_id,
                ProjectUser.workspace_id == user.active_workspace_id,
                ProjectUser.user_id == user.user_id,
            ),
        )
        .where(
            Case.case_id == case_id,
            CasePlaywrightCodegen.id == artifact_id,
        )
    )
    r = await session.execute(q)
    art = r.scalars().first()
    if not art:
        raise HTTPException(status_code=404, detail="Artifact not found")
    return {
        "source_code": art.source_code,
        "step_spans": art.step_spans,
        "source_run_id": str(art.source_run_id),
        "artifact_id": str(art.id),
    }


async def internal_get_artifact_by_id(session: AsyncSession, artifact_id: UUID) -> CasePlaywrightCodegen:
    r = await session.execute(select(CasePlaywrightCodegen).where(CasePlaywrightCodegen.id == artifact_id))
    row = r.scalars().first()
    if not row:
        raise HTTPException(status_code=404, detail="Artifact not found")
    return row


async def internal_finalize_codegen(
    session: AsyncSession,
    *,
    case_id: UUID,
    source_run_id: UUID,
    source_code: str,
    step_spans: list,
    steps_content_hash: str,
    generator_meta: Optional[dict],
) -> UUID:
    async with session.begin():
        await session.execute(
            update(CasePlaywrightCodegen)
            .where(CasePlaywrightCodegen.case_id == case_id, CasePlaywrightCodegen.is_current.is_(True))
            .values(is_current=False)
        )
        new_id = uuid.uuid4()
        row = CasePlaywrightCodegen(
            id=new_id,
            case_id=case_id,
            source_run_id=source_run_id,
            source_code=source_code,
            step_spans=step_spans,
            steps_content_hash=steps_content_hash,
            generator_meta=generator_meta,
            is_current=True,
            updated_at=datetime.now(timezone.utc),
        )
        session.add(row)
        await session.execute(
            update(Case)
            .where(Case.case_id == case_id)
            .values(
                codegen_regeneration_required=False,
                codegen_regeneration_since=None,
            )
        )
    prev = _get_codegen_job(case_id) or {}
    prev.update(
        {
            "state": "success",
            "error": None,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    _set_codegen_job(case_id, prev)
    return new_id


async def internal_report_codegen_failure(
    case_id: UUID,
    *,
    message: str,
    step_uid: Optional[str] = None,
    reason_code: str = "codegen_step_failed",
) -> None:
    prev = _get_codegen_job(case_id) or {}
    prev.update(
        {
            "state": "failure",
            "error": {"message": message, "step_uid": step_uid, "reason_code": reason_code},
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    _set_codegen_job(case_id, prev)


def internal_append_codegen_log(
    case_id: UUID,
    *,
    message: str,
    level: str = "info",
    step_uid: Optional[str] = None,
    phase: Optional[str] = None,
    screenshot_base64: Optional[str] = None,
    screenshot_mime_type: str = "image/jpeg",
    screenshot_minio: Optional[Dict[str, str]] = None,
) -> None:
    """Добавляет запись в лог codegen-задачи, хранящийся в MinIO.

    ВНИМАНИЕ: функция выполняет load-modify-save без распределённой блокировки.
    При параллельных вызовах для одного case_id возможна потеря записей.
    Для логов это допустимо (eventual consistency), но вызывающий код не должен
    допускать высокочастотные параллельные записи для одного кейса.
    """
    prev = _get_codegen_job(case_id) or {}
    rid = prev.get("run_id")
    if not rid:
        logger.warning("internal_append_codegen_log: missing run_id for case_id=%s", case_id)
        return
    run_id = str(rid)
    if prev.get("state") == "queued":
        prev["state"] = "running"

    log = load_job_log(run_id)
    entry: Dict[str, Any] = {
        "t": datetime.now(timezone.utc).isoformat(),
        "level": level,
        "message": message,
        "step_uid": step_uid,
        "phase": phase,
    }
    sm = screenshot_minio or {}
    b = sm.get("bucket") if isinstance(sm, dict) else None
    f = sm.get("file") if isinstance(sm, dict) else None
    if b and f and str(b).strip() and str(f).strip():
        entry["screenshot_minio"] = {"bucket": str(b).strip(), "file": str(f).strip()}
    elif screenshot_base64 and str(screenshot_base64).strip():
        ref = upload_codegen_screenshot_base64(run_id, str(screenshot_base64), screenshot_mime_type)
        if ref:
            entry["screenshot_minio"] = ref
    log.append(entry)
    if len(log) > CODEGEN_LOG_MAX:
        log = log[-CODEGEN_LOG_MAX:]
    try:
        save_job_log(run_id, log)
    except Exception as e:
        logger.warning("internal_append_codegen_log: save_job_log failed: %s", e)
        return

    prev.pop("log", None)
    prev["updated_at"] = datetime.now(timezone.utc).isoformat()
    _set_codegen_job(case_id, prev)
