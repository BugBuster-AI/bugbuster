"""Generation log для Playwright codegen в MinIO: run-cases/{run_id}/codegen/job_log.json + screenshots/."""
from __future__ import annotations

import base64
import io
import json
import uuid
from typing import Any, Dict, List, Optional

from minio import Minio
from minio.error import S3Error

from config import (
    MINIO_ACCESS_KEY,
    MINIO_HOST,
    MINIO_PORT,
    MINIO_SECRET_KEY,
    MINIO_SECURE,
    logger,
)

CODEGEN_LOG_BUCKET = "run-cases"


def _minio_client() -> Minio:
    return Minio(
        f"{MINIO_HOST}:{MINIO_PORT}",
        access_key=MINIO_ACCESS_KEY,
        secret_key=MINIO_SECRET_KEY,
        secure=bool(MINIO_SECURE),
    )


def job_log_object_name(run_id: str) -> str:
    return f"{run_id}/codegen/job_log.json"


def load_job_log(run_id: str) -> List[Dict[str, Any]]:
    client = _minio_client()
    key = job_log_object_name(run_id)
    try:
        resp = client.get_object(CODEGEN_LOG_BUCKET, key)
        raw = resp.read()
        resp.close()
        resp.release_conn()
        data = json.loads(raw.decode("utf-8"))
        if isinstance(data, list):
            return data
        return []
    except S3Error as e:
        if getattr(e, "code", None) == "NoSuchKey":
            return []
        logger.error("codegen load_job_log S3Error %s/%s: %s", CODEGEN_LOG_BUCKET, key, e)
        raise
    except json.JSONDecodeError as e:
        logger.warning("codegen load_job_log JSON %s/%s: %s", CODEGEN_LOG_BUCKET, key, e)
        return []
    except Exception as e:
        logger.error("codegen load_job_log %s/%s: %s", CODEGEN_LOG_BUCKET, key, e)
        raise


def save_job_log(run_id: str, log: List[Dict[str, Any]]) -> None:
    client = _minio_client()
    key = job_log_object_name(run_id)
    body = json.dumps(log, ensure_ascii=False, default=str).encode("utf-8")
    client.put_object(
        CODEGEN_LOG_BUCKET,
        key,
        io.BytesIO(body),
        length=len(body),
        content_type="application/json; charset=utf-8",
    )


def init_empty_job_log(run_id: str) -> None:
    save_job_log(run_id, [])


def delete_codegen_log_artifacts(run_id: str) -> None:
    """Удаляет все объекты с префиксом {run_id}/codegen/."""
    client = _minio_client()
    prefix = f"{run_id}/codegen/"
    try:
        for obj in client.list_objects(CODEGEN_LOG_BUCKET, prefix=prefix, recursive=True):
            client.remove_object(CODEGEN_LOG_BUCKET, obj.object_name)
    except Exception as e:
        logger.warning("codegen delete_codegen_log_artifacts %s: %s", prefix, e)


def upload_codegen_screenshot_bytes(
    run_id: str,
    data: bytes,
    *,
    content_type: str = "image/jpeg",
    ext: str = ".jpg",
) -> Dict[str, str]:
    """Загружает JPEG/PNG в codegen/screenshots/; возвращает {bucket, file}."""
    client = _minio_client()
    name = f"{uuid.uuid4().hex}{ext}"
    object_name = f"{run_id}/codegen/screenshots/{name}"
    client.put_object(
        CODEGEN_LOG_BUCKET,
        object_name,
        io.BytesIO(data),
        length=len(data),
        content_type=content_type,
    )
    return {"bucket": CODEGEN_LOG_BUCKET, "file": object_name}


def upload_codegen_screenshot_base64(
    run_id: str,
    b64: str,
    screenshot_mime_type: str = "image/jpeg",
) -> Optional[Dict[str, str]]:
    """Декодирует base64 и заливает в MinIO (legacy internal API)."""
    raw = (b64 or "").strip()
    if not raw:
        return None
    try:
        data = base64.b64decode(raw)
    except Exception:
        logger.warning("codegen upload_codegen_screenshot_base64: invalid base64")
        return None
    ext = ".jpg"
    ct = screenshot_mime_type or "image/jpeg"
    if "png" in ct.lower():
        ext = ".png"
        ct = "image/png"
    return upload_codegen_screenshot_bytes(run_id, data, content_type=ct, ext=ext)
