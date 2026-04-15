"""Прогон кейса по сохранённому JS: один Node-процесс (Playwright API + trace), скрины до/после, MinIO как у VLM."""
from __future__ import annotations

import asyncio
import io
import json
import logging
import os
import shutil
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

from agent.config import POST_ACTION_WAIT_TIME
from agent.graph_utils import check_annotated_screenshot_exists
from codegen.artifact_source import (
    blocks_by_uid,
    extract_inner_js_body,
    inner_body_prefix_before_first_step,
    step_uid_blocks,
)
from codegen.case_steps import case_step_kind, flatten_case_with_run_indices
from codegen.case_viewport import viewport_for_case
from codegen.browser_validate import NODE_RUNNER_DIR
from codegen.effective_browser import (
    apply_playwright_mcp_chrome_user_agent,
    mcp_browser_from_environment,
    playwright_node_environ,
)
from codegen.js_fragment_await import dedupe_const_declarations
from browser_actions.extract_video_from_trace import process_trace_and_generate_video
from core.celeryconfig import DB_NAME
from core.config import BACKEND_BASE_URL, SECRET_KEY_API
from core.schemas import CaseStatusEnum
from core.utils import upload_buffer_to_minio, upload_to_minio
from infra.db import async_session, update_run_case_final_record, update_run_case_status, update_run_case_steps
from infra.rabbit_producer import send_to_rabbitmq

logger = logging.getLogger("clicker")

# Node: один прогон сценария + нативный trace (см. mcp_playwright_js_run.mjs).
PLAYWRIGHT_JS_RUNNER = NODE_RUNNER_DIR / "mcp_playwright_js_run.mjs"


def _playwright_js_mcp_node_env(mcp_browser: str) -> dict[str, str]:
    """Тот же env, что при генерации/валидации JS: ``apply_playwright_mcp_chrome_user_agent`` для Chrome."""
    env = playwright_node_environ()
    if mcp_browser == "chrome":
        apply_playwright_mcp_chrome_user_agent(env)
    return env


def _case_as_dict(case: Any) -> dict:
    """Унифицируем кейс из Pydantic/dict в обычный dict для дальнейшей обработки."""
    if isinstance(case, dict):
        return case
    if hasattr(case, "model_dump"):
        return case.model_dump(mode="json")
    return dict(case)


def _action_for_index(case: dict, flat_item: dict, idx: int) -> str:
    """
    Тип шага для записи в БД (как у VLM): API / expected_result / action из плана или CLICK по умолчанию.
    """
    kind = flat_item.get("kind") or case_step_kind(flat_item.get("raw"))
    if kind == "api":
        return "API"
    if kind == "expected_result":
        return "expected_result"
    plan = case.get("action_plan") or []
    if 0 <= idx < len(plan) and isinstance(plan[idx], dict):
        return str(plan[idx].get("action_type") or "CLICK")
    return "CLICK"


async def _fetch_artifact(artifact_id: str) -> dict:
    """Загрузка артефакта codegen с backend по внутреннему API (исходный JS сценария)."""
    url = f"{BACKEND_BASE_URL}/api/internal/codegen/playwright/artifact/{artifact_id}"
    async with httpx.AsyncClient(timeout=120.0) as client:
        r = await client.get(url, headers={"X-Internal-Token": SECRET_KEY_API})
        r.raise_for_status()
        return r.json()


def _safe_uid_file(uid: str) -> str:
    """Имя файла из step_uid: только безопасные символы (фолбэк имени скрина)."""
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in str(uid))


def _step_time_from_payload(step_times: Any, uid: str) -> str:
    """Как у VLM: длительность шага строкой с двумя знаками после запятой (секунды)."""
    # TODO: при отсутствии/ошибке расчёта времени не подставлять «0.00» — оно неотличимо от реальных ноль секунд;
    # лучше отдельное значение («N/A», пустая строка, null в схеме БД / opt-out поля), согласовать с фронтом и VLM.
    if not isinstance(step_times, dict):
        return "0.00"
    u = str(uid)
    raw = step_times.get(u) or step_times.get(uid)
    if raw is None:
        return "0.00"
    try:
        return f"{float(raw):.2f}"
    except (TypeError, ValueError):
        return "0.00"


def _step_times_after_run_for_flat(
    flat: list,
    step_times_map: Any,
    run_sec_total: Any,
) -> dict[str, str]:
    """
    Итоговые step_time по шагам — только после успешного завершения Node-прогона.

    Почему не во время прогона (в вотчере по появлению скринов):
    - один вызов browser_run_code выполняет все шаги подряд; корректные доли времени известны только
      когда runner в mcp_playwright_js_run.mjs отработал и записал _result.json (step_times + run_sec_total);
    - ожидание файлов на диске не равно длительности шага в браузере и может отставать от реального прогона.

    Логика: пропорции берём из step_times в _result.json, сумму масштабируем к run_sec_total (wall-clock
    одного browser_run_code), чтобы сумма шагов совпадала с фактической длительностью прогона кода.
    Если run_sec_total нет (старый артефакт) — оставляем сырые значения из payload.
    """
    n = len(flat)
    if n == 0:
        return {}
    total: float | None = None
    if run_sec_total is not None:
        try:
            total = float(run_sec_total)
        except (TypeError, ValueError):
            total = None
    if total is not None and total < 0:
        total = None

    raw: list[float] = []
    for item in flat:
        uid = str(item["step_uid"])
        try:
            raw.append(float(_step_time_from_payload(step_times_map, uid)))
        except (TypeError, ValueError):
            raw.append(0.0)

    out: dict[str, str] = {}
    if total is not None and total > 0:
        s = sum(raw)
        if s > 0:
            for item, r in zip(flat, raw):
                uid = str(item["step_uid"])
                out[uid] = f"{(r / s) * total:.2f}"
        else:
            per = total / n
            for item in flat:
                out[str(item["step_uid"])] = f"{per:.2f}"
    else:
        for item, r in zip(flat, raw):
            out[str(item["step_uid"])] = f"{r:.2f}"

    return out


async def _wait_file_stable(path: Path, poll: float = 0.3, stable_rounds: int = 2, max_wait: float = 120) -> bool:
    """Return True once *path* exists with non-zero size unchanged for *stable_rounds* consecutive checks.

    Returns False if *max_wait* seconds elapse without the file stabilising.
    """
    prev_size = -1
    stable = 0
    deadline = asyncio.get_event_loop().time() + max_wait
    while asyncio.get_event_loop().time() < deadline:
        try:
            sz = path.stat().st_size
        except OSError:
            await asyncio.sleep(poll)
            continue
        if sz > 0 and sz == prev_size:
            stable += 1
            if stable >= stable_rounds:
                return True
        else:
            stable = 0
        prev_size = sz
        await asyncio.sleep(poll)
    return False


async def _flush_one_step(
    *,
    run_id_str: str,
    idx: int,
    item: dict,
    case: dict,
    work_dir: str,
    uid: str,
    step_time: str = "0.00",
    status_step: CaseStatusEnum = CaseStatusEnum.PASSED,
    comment: str | None = None,
) -> None:
    """Upload before/after screenshots to MinIO and persist one step result to DB.

    Для playwright_js при инкрементальном flush step_time часто «0.00» до финального прохода с _result.json.
    """
    safe = _safe_uid_file(uid)
    before_path = Path(work_dir) / f"b_{safe}.jpeg"
    after_path = Path(work_dir) / f"a_{safe}.jpeg"

    if not before_path.is_file():
        raise RuntimeError(f"missing before screenshot for step {uid}")
    # После действия скрина «нет», если шаг упал до успешного завершения — только before (состояние до шага).
    is_failed = status_step == CaseStatusEnum.FAILED
    if not is_failed and not after_path.is_file():
        raise RuntimeError(f"missing after screenshot for step {uid}")

    pw_log = logging.getLogger("playwright_js")
    before_url = await asyncio.to_thread(upload_to_minio, before_path, run_id_str, before_path.name)
    annotated_guess = before_path.parent / f"annot_{before_path.name}"
    before_annotated_path = check_annotated_screenshot_exists(annotated_guess, before_path, pw_log)
    before_annotated_url = await asyncio.to_thread(
        upload_to_minio, before_annotated_path, run_id_str, before_annotated_path.name
    )
    after_url: str | None = None
    if not is_failed:
        after_url = await asyncio.to_thread(upload_to_minio, after_path, run_id_str, after_path.name)

    raw = item.get("raw") if isinstance(item.get("raw"), dict) else {}
    extra = raw.get("extra") if isinstance(raw, dict) else None
    action = _action_for_index(case, item, idx)
    od = raw.get("value") if isinstance(raw, dict) else item.get("nl", "")

    mess = {
        "status_step": status_step,
        "index_step": idx,
        "original_step_description": od,
        "validation_result": None,
        "reflection_times": "0",
        "extra": extra,
        "model_time": "0",
        "step_time": step_time,
        "action": action,
        "action_details": {
            "coords": None,
            "text": None,
            "wait_time": None,
            "scroll_data": {"x": 0, "deltaX": 0, "y": 0, "deltaY": 0, "source": "body"},
            "key_to_press": None,
            "new_tab_url": None,
            "switch_tab_name": None,
        },
        "before": before_url,
        "before_annotated_url": before_annotated_url,
        "after": after_url,
    }
    if comment is not None:
        mess["comment"] = comment
    async with async_session() as session:
        await update_run_case_steps(session, run_id_str, mess)


async def _watch_and_flush_steps(
    *,
    run_id_str: str,
    flat: list,
    case: dict,
    work_dir: str,
    flushed: set,
) -> None:
    """
    Инкрементально пишет шаги в БД по мере появления after-скринов (скрины, статус, медиа).

    step_time здесь намеренно 0.00: реальные секунды на шаг проставляются постфактум в run_playwright_js_case
    после чтения _result.json — см. _step_times_after_run_for_flat и комментарий у цикла обновления.
    """
    for idx, item in enumerate(flat):
        uid = str(item["step_uid"])
        safe = _safe_uid_file(uid)
        after_path = Path(work_dir) / f"a_{safe}.jpeg"
        await _wait_file_stable(after_path)
        try:
            await _flush_one_step(
                run_id_str=run_id_str,
                idx=idx,
                item=item,
                case=case,
                work_dir=work_dir,
                uid=uid,
                step_time="0.00",
            )
            flushed.add(uid)
        except Exception:
            logger.warning("playwright_js: incremental flush failed for step %s", uid, exc_info=True)


async def run_playwright_js_case(
    run_id,
    case,
    user_id,
    environment,
    background_video_generate,
    **kwargs,
):
    """
    Полный прогон run по готовому Playwright JS из codegen-артефакта:
    Node + MCP, скрины в MinIO, шаги в БД, trace/log — по аналогии с VLM-прогоном.
    """
    _ = user_id
    case = _case_as_dict(case)
    run_id_str = str(run_id)
    artifact_id = kwargs.get("codegen_artifact_id")
    if not artifact_id:
        logger.error("playwright_js: missing codegen_artifact_id")
        async with async_session() as session:
            await update_run_case_status(
                run_id_str,
                CaseStatusEnum.FAILED,
                run_summary="playwright_js: no codegen_artifact_id",
                start_dt=None,
                end_dt=None,
                complete_time=0,
                session=session,
            )
        return

    real_start = datetime.now(timezone.utc)
    work_dir: str | None = None

    # Переводим run в IN_PROGRESS в начале реальной работы.
    async with async_session() as session:
        await update_run_case_status(
            run_id_str,
            CaseStatusEnum.IN_PROGRESS,
            start_dt=real_start,
            session=session,
        )

    try:
        # --- Артефакт и соответствие шагам кейса ---
        art = await _fetch_artifact(str(artifact_id))
        source = art.get("source_code") or ""
        inner = extract_inner_js_body(source)
        ordered = step_uid_blocks(inner)
        prefix_code = inner_body_prefix_before_first_step(inner)
        flat = flatten_case_with_run_indices(case)
        by_uid = blocks_by_uid(source)
        use_ordered = len(ordered) == len(flat)
        if not use_ordered:
            logger.warning(
                "playwright_js: artifact has %s // step_uid markers but case flat has %s steps; "
                "falling back to uid→block map (duplicate step_uid may mis-resolve)",
                len(ordered),
                len(flat),
            )

        steps_payload = []
        accum_js = prefix_code or ""
        for i, item in enumerate(flat):
            uid = item["step_uid"]
            if use_ordered:
                mark_uid, block = ordered[i]
                if mark_uid != uid:
                    logger.warning(
                        "playwright_js: step index %s step_uid mismatch (case=%s, artifact=%s)",
                        i,
                        uid,
                        mark_uid,
                    )
                block = dedupe_const_declarations(accum_js, block)
            else:
                block = by_uid.get(uid)
                if block is None:
                    logger.warning("playwright_js: no block for step_uid %s", uid)
                    block = f"  // step_uid:{uid} (missing in artifact)\n"
                else:
                    block = dedupe_const_declarations(accum_js, block)
            accum_js = accum_js + "\n" + block
            steps_payload.append({"step_uid": uid, "code": block})

        # --- Viewport: case.environment.resolution (Environment привязанный к кейсу); иначе 1920×1080 ---
        vw, vh = viewport_for_case(case, environment=environment)
        mcp_browser = mcp_browser_from_environment(environment)

        start_url = str(case.get("url") or "about:blank")
        work_dir = tempfile.mkdtemp(prefix="pwjs_")
        trace_zip_name = f"{run_id_str}_trace.zip"
        trace_build = Path(work_dir) / trace_zip_name
        cfg_path = Path(work_dir) / "cfg.json"
        # Env и UA до записи cfg: ``apply_playwright_mcp_chrome_user_agent``.
        mcp_env = _playwright_js_mcp_node_env(mcp_browser)
        cfg_payload: dict[str, Any] = {
            "startUrl": start_url,
            "viewportW": vw,
            "viewportH": vh,
            "outputDir": work_dir,
            "prefixCode": prefix_code,
            "steps": steps_payload,
            "postActionWaitSec": POST_ACTION_WAIT_TIME,
            "browser": mcp_browser,
            "traceZipPath": str(trace_build.resolve()),
        }
        ua_mcp = (mcp_env.get("PLAYWRIGHT_MCP_USER_AGENT") or "").strip()
        if mcp_browser == "chrome" and ua_mcp:
            cfg_payload["desktopChromeUserAgent"] = ua_mcp
        cfg_path.write_text(
            json.dumps(cfg_payload, ensure_ascii=False),
            encoding="utf-8",
        )

        if not PLAYWRIGHT_JS_RUNNER.is_file():
            raise RuntimeError(f"mcp_playwright_js_run.mjs not found at {PLAYWRIGHT_JS_RUNNER}")

        # Node пишет скрины; вотчер параллельно заливает шаги в БД без step_time (см. _watch_and_flush_steps).
        proc = await asyncio.create_subprocess_exec(
            os.environ.get("NODE_BINARY", "node"), str(PLAYWRIGHT_JS_RUNNER), str(cfg_path),
            cwd=str(NODE_RUNNER_DIR),
            env=mcp_env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        flushed_uids: set[str] = set()
        watcher = asyncio.create_task(
            _watch_and_flush_steps(
                run_id_str=run_id_str,
                flat=flat,
                case=case,
                work_dir=work_dir,
                flushed=flushed_uids,
            )
        )

        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(proc.communicate(), timeout=3600)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            raise RuntimeError("Node process timed out after 3600s")
        finally:
            watcher.cancel()
            try:
                await watcher
            except asyncio.CancelledError:
                pass

        stdout_tail = (stdout_bytes or b"").decode("utf-8", errors="replace")[-120_000:]
        stderr_tail = (stderr_bytes or b"").decode("utf-8", errors="replace")[-120_000:]
        result_path = Path(work_dir) / "_result.json"
        if not result_path.is_file():
            err = (stderr_tail or stdout_tail or "").strip() or f"exit {proc.returncode}"
            raise RuntimeError(err)

        result = json.loads(result_path.read_text(encoding="utf-8"))
        run_success = bool(result.get("ok"))
        fail_summary = ""

        if run_success:
            # --- step_time по шагам: только здесь, после успешного прогона ---
            # До этого момента в БД у шагов 0.00 (см. _watch_and_flush_steps). Источник правды —
            # _result.json от Node: step_times и run_sec_total (длительность combined runner).
            step_times_map: Any = result.get("step_times") or {}
            uid_to_time = _step_times_after_run_for_flat(
                flat,
                step_times_map,
                result.get("run_sec_total"),
            )

            # Уже записанным шагам — только step_time; пропущенным вотчером — полный flush с итоговым временем.
            for idx, item in enumerate(flat):
                uid = str(item["step_uid"])
                st = uid_to_time.get(uid, "0.00")
                if uid not in flushed_uids:
                    await _flush_one_step(
                        run_id_str=run_id_str,
                        idx=idx,
                        item=item,
                        case=case,
                        work_dir=work_dir,
                        uid=uid,
                        step_time=st,
                    )
                else:
                    async with async_session() as session:
                        await update_run_case_steps(session, run_id_str, {
                            "index_step": idx,
                            "step_time": st,
                        })
        else:
            # Частичный результат: шаг падения — FAILED + comment + медиа (перетирает PASSED от вотчера).
            fail_summary = str(result.get("error") or "playwright_js run failed")
            failed_idx_raw = result.get("failed_step_index")
            failed_idx: int | None = None
            if failed_idx_raw is not None:
                try:
                    failed_idx = int(failed_idx_raw)
                except (TypeError, ValueError):
                    failed_idx = None
            if failed_idx is not None and 0 <= failed_idx < len(flat):
                uid = str(flat[failed_idx]["step_uid"])
                st = _step_time_from_payload(result.get("step_times"), uid)
                try:
                    await _flush_one_step(
                        run_id_str=run_id_str,
                        idx=failed_idx,
                        item=flat[failed_idx],
                        case=case,
                        work_dir=work_dir,
                        uid=uid,
                        step_time=st,
                        status_step=CaseStatusEnum.FAILED,
                        comment=fail_summary,
                    )
                except Exception:
                    logger.warning(
                        "playwright_js: failed to persist failed step %s",
                        uid,
                        exc_info=True,
                    )

        # --- Trace.zip: пишется в том же Node-процессе, что и прогон (context.tracing) ---
        trace_ok = trace_build.is_file() and trace_build.stat().st_size > 0
        if not trace_ok:
            logger.warning(
                "playwright_js: trace zip missing or empty after run (path=%s)",
                trace_build,
            )

        video_url = None
        trace_path_minio: dict | None = None
        try:
            if trace_ok:
                trace_path_minio = await asyncio.to_thread(
                    upload_to_minio, trace_build, run_id_str, trace_zip_name,
                )
            else:
                if trace_build.is_file():
                    try:
                        trace_build.unlink()
                    except OSError:
                        pass
                with zipfile.ZipFile(trace_build, "w", zipfile.ZIP_DEFLATED) as zf:
                    if result_path.is_file():
                        zf.write(result_path, arcname="_result.json")
                    zf.writestr("node_stdout.txt", stdout_tail)
                    zf.writestr("node_stderr.txt", stderr_tail)
                    for p in sorted(Path(work_dir).glob("*.jpeg")):
                        zf.write(p, arcname=p.name)
                if trace_build.is_file():
                    await asyncio.to_thread(upload_to_minio, trace_build, run_id_str, trace_zip_name)
        except OSError as zerr:
            logger.warning("playwright_js: trace zip failed: %s", zerr)
        except Exception as up_tr:
            logger.warning("playwright_js: trace upload failed: %s", up_tr)

        # --- Генерация видео из нативного trace (как у VLM) ---
        if trace_ok and trace_path_minio:
            try:
                if background_video_generate is True and trace_path_minio:
                    message = json.dumps(
                        {"args": [], "kwargs": {"db_name": DB_NAME, "trace_file_path": trace_path_minio, "run_id": run_id_str}},
                        ensure_ascii=False,
                    ).encode("utf-8")
                    await send_to_rabbitmq(
                        queue_name="video_generation",
                        message=message,
                        correlation_id=run_id_str,
                    )
                    logger.info("playwright_js: trace sent to video_generation queue")
                else:
                    logger.info("playwright_js: inline video generation started")
                    video_url = await process_trace_and_generate_video(str(trace_build), run_id_str)
                    logger.info("playwright_js: inline video generation done")
            except Exception as vid_err:
                logger.warning("playwright_js: video generation/enqueue failed: %s", vid_err, exc_info=True)

        # --- Текстовый лог прогона в MinIO (stdout/stderr Node, флаг нативного trace) ---
        log_buf = io.StringIO()
        log_buf.write("playwright_js execution_engine=playwright_js\n")
        log_buf.write(f"exit_code={proc.returncode}\n--- stdout ---\n{stdout_tail}\n--- stderr ---\n{stderr_tail}\n")
        log_buf.write(f"native_trace_uploaded={trace_ok}\n")
        try:
            await asyncio.to_thread(
                upload_buffer_to_minio,
                log_buf,
                run_id_str,
                f"{run_id_str}.log",
            )
        except Exception as up_log:
            logger.warning("playwright_js: log upload failed: %s", up_log)

        # --- Завершение run в БД (успех или падение сценария по _result.json) ---
        end_dt = datetime.now(timezone.utc)
        complete = (end_dt - real_start).total_seconds()
        async with async_session() as session:
            await update_run_case_final_record(
                run_id_str,
                video_url,
                end_dt,
                complete,
                CaseStatusEnum.PASSED if run_success else CaseStatusEnum.FAILED,
                "" if run_success else fail_summary,
                session=session,
            )
    except Exception as e:
        logger.exception("playwright_js run failed")
        end_dt = datetime.now(timezone.utc)
        complete = (end_dt - real_start).total_seconds() if real_start else 0
        async with async_session() as session:
            await update_run_case_final_record(
                run_id_str,
                None,
                end_dt,
                complete,
                CaseStatusEnum.FAILED,
                str(e),
                session=session,
            )
    finally:
        # Временная директория с cfg, скринами и trace — удаляем всегда.
        # TODO: оценить верхнюю границу ресурсов: занимаемый объём на диске и пик RAM
        # (число шагов × скрины, trace.zip, буферы при заливке в MinIO) для лимитов/мониторинга.
        if work_dir:
            shutil.rmtree(work_dir, ignore_errors=True)
