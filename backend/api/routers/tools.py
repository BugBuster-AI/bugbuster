import asyncio
import base64

import mimetypes
import time
import uuid

from fastapi import (APIRouter, Depends, File, Header, HTTPException,
                     UploadFile, status)
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from config import CLICKER_IP, CLICKER_PORT, logger
from db.models import User
from dependencies.auth import get_current_active_user

from schemas import (ContextScreenshotRequestCreate,
                     ContextScreenshotRequestDelete, CoordinatesRequest,
                     ElementDescriptionRequest, Lang, ReflectionRequest)
from utils import (async_request, draw_bbox_on_image,
                   draw_point_on_screenshot_base64, generate_presigned_url,
                   get_file_from_minio, process_image, remove_file_from_minio,
                   upload_to_minio)

router = APIRouter(prefix="/api/tools", tags=["tools"])

ALLOWED_EXTENSIONS = {"jpeg", "jpg", "png", "pdf", "docx", "xlsx", "txt"}
MAX_FILE_SIZE_MB = 50
MAX_FILES = 10


@router.get("/list_languages")
async def list_languages():
    return [lang.value for lang in Lang]


@router.post("/upload_files")
async def upload_files(files: list[UploadFile] = File(...),
                       current_user: User = Depends(get_current_active_user),
                       host: str = Header(None)):
    """Upload up to 10 files in ("jpeg", "jpeg", "png", "pdf", "docx", "xlsx", "txt") formats and size <= 50MB each"""

    if len(files) > MAX_FILES:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Too many files")

    responses = []

    for file in files:
        file_bytes = await file.read()
        file_size_mb = len(file_bytes) / (1024 * 1024)
        if file_size_mb > MAX_FILE_SIZE_MB:
            raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=f"File too large: {file.filename}")

        file_extension = file.filename.split(".")[-1].lower()
        if file_extension not in ALLOWED_EXTENSIONS:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"File format not allowed: {file.filename}")

        try:

            content_type, _ = mimetypes.guess_type(file.filename)
            content_type = content_type if content_type else 'application/octet-stream'

            bucket = "backend-files"
            filename = f"{uuid.uuid4()}_{file.filename}"

            obj = await asyncio.to_thread(upload_to_minio, bucket, file_bytes,
                                          "task_id", filename, content_type)

            presigned_url = await asyncio.to_thread(generate_presigned_url, bucket, obj["filename"], host)

            responses.append({
                "bucket": bucket,
                "file": obj["filename"],
                "url": presigned_url
            })

        except Exception as e:
            logger.error(e, exc_info=True)
            mess = {"status": "error", "message": str(e), "file": file.filename}
            raise HTTPException(status_code=400, detail=mess)

    return JSONResponse(content=jsonable_encoder(responses))


@router.post("/upload_image")
async def upload_image(image: UploadFile = File(...),
                       current_user: User = Depends(get_current_active_user),
                       host: str = Header(None)):
    """JPEG/PNG <= 20MB"""
    if image.size > 20 * 1024 * 1024:  # 20 MB
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="File too large")

    try:
        image_bytes = await asyncio.to_thread(process_image, image.file)
        bucket = "backend-images"
        filename = f"{uuid.uuid4()}_converted.jpeg"
        obj = await asyncio.to_thread(upload_to_minio, bucket, image_bytes, str(uuid.uuid4()), filename)

        presigned_url = await asyncio.to_thread(generate_presigned_url, bucket, obj["filename"], host)

        return JSONResponse(content=jsonable_encoder({"bucket": bucket,
                                                      "file": obj["filename"],
                                                      "url": presigned_url}))

    except Exception as e:
        logger.error(e, exc_info=True)
        mess = {"status": "error", "message": str(e)}
        raise HTTPException(400, mess)


@router.post("/get_coordinates")
async def get_coordinates(request_data: CoordinatesRequest,
                          current_user: User = Depends(get_current_active_user)):
    """image_base64 or minio_path  {"bucket": "", "file": ""}"""

    try:
        if not request_data.minio_path and not request_data.image_base64_string:
            raise HTTPException(status_code=400,
                                detail="Either minio_path or image_base64_string must be provided")

        prompt = request_data.prompt

        if not prompt.strip():
            raise HTTPException(status_code=400,
                                detail="string cannot be empty")

        if request_data.use_rewriter is True:
            # сначала прогоняем через rewriter

            post_data = {'sop': [prompt]}
            is_valid = True
            validation_reason = {}
            action_plan = []

            status, res = await async_request(f"http://{CLICKER_IP}:{CLICKER_PORT}/sop_validation",
                                              method='post',
                                              params=post_data, timeout=60)
            if status != 200:
                raise HTTPException(status_code=400, detail=f"sop_validation error: {res}")
            else:
                is_valid = res.get("is_valid", False)
                validation_reason = res.get("validation_reason", {})
                action_plan = res.get("action_plan", [])

                if is_valid is False:
                    raise HTTPException(status_code=400, detail=f"{validation_reason}")

            element_description = None
            if isinstance(action_plan, list) and len(action_plan) > 0 and isinstance(action_plan[0], dict):
                element_description = action_plan[0].get("element_description", None)
            else:
                raise HTTPException(status_code=400, detail=f"uncorrected action_plan {action_plan}")

            if not element_description:
                raise HTTPException(status_code=400, detail="element_description is None")

            request_data.prompt = element_description

        status, res = await async_request(f"http://{CLICKER_IP}:{CLICKER_PORT}/get_coordinates",
                                          method='post',
                                          params=request_data.model_dump())

        # if status != 200:
        #     raise HTTPException(status_code=400, detail=res)

        return res

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(e, exc_info=True)
        mess = {"status": "error", "message": f"Error: {e}"}
        raise HTTPException(400, mess)


@router.post("/get_reflection")
async def get_reflection(request_data: ReflectionRequest,
                         current_user: User = Depends(get_current_active_user)):
    """image_base64 or minio_path  {"bucket": "", "file": ""}"""

    try:
        if not request_data.after_minio_path and not request_data.after_image_base64_string:
            raise HTTPException(status_code=400,
                                detail="Either after_minio_path or after_image_base64_string must be provided")

        prompt = request_data.reflection_instruction

        if not prompt.strip():
            raise HTTPException(status_code=400,
                                detail="string cannot be empty")

        status, res = await async_request(f"http://{CLICKER_IP}:{CLICKER_PORT}/get_reflection",
                                          method='post',
                                          params=request_data.model_dump())

        if status != 200:
            raise HTTPException(status_code=400, detail=res)

        return res

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(e, exc_info=True)
        mess = {"status": "error", "message": f"Error: {e}"}
        raise HTTPException(400, mess)


@router.post("/describe_element")
async def describe_element(request_data: ElementDescriptionRequest,
                           current_user: User = Depends(get_current_active_user)):
    """Get description of UI element in specified bounding box. Accepts image_base64_string or minio_path with coordinates."""

    try:
        if not request_data.minio_path and not request_data.image_base64_string:
            raise HTTPException(status_code=400,
                                detail="Either minio_path or image_base64_string must be provided")

        # Validate bounding box coordinates
        if request_data.x1 < 0 or request_data.y1 < 0 or request_data.x2 < 0 or request_data.y2 < 0:
            raise HTTPException(status_code=400,
                                detail="Coordinates must be non-negative")

        if request_data.x1 >= request_data.x2 or request_data.y1 >= request_data.y2:
            raise HTTPException(status_code=400,
                                detail="Invalid bounding box: x1 must be < x2 and y1 must be < y2")

        # Forward request to portal-clicker describe_element endpoint

        status, res = await async_request(f"http://{CLICKER_IP}:{CLICKER_PORT}/describe_element",
                                          method='post',
                                          params=request_data.model_dump())

        if status != 200:
            raise HTTPException(status_code=400, detail=f"describe_element service error: {res}")

        return res

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(e, exc_info=True)
        mess = {"status": "error", "message": f"Error: {e}"}
        raise HTTPException(400, mess)


@router.post("/create_context_screenshot")
async def create_context_screenshot(request_data: ContextScreenshotRequestCreate,
                                    current_user: User = Depends(get_current_active_user),
                                    host: str = Header(None)):
    """Draw point on screenshot and upload to minio"""

    try:
        # Validate source
        if not request_data.minio_path and not request_data.image_base64_string:
            raise HTTPException(status_code=400,
                                detail="Either minio_path or image_base64_string must be provided")

        # Validate bounding box coordinates
        if min(request_data.x1, request_data.y1, request_data.x2, request_data.y2) < 0:
            raise HTTPException(status_code=400, detail="Coordinates must be non-negative")

        if request_data.x1 >= request_data.x2 or request_data.y1 >= request_data.y2:
            raise HTTPException(status_code=400, detail="Invalid bounding box")

        # Get image in bytes
        if request_data.minio_path:
            bucket = request_data.minio_path.get("bucket")
            file = request_data.minio_path.get("file")

            if not bucket or not file:
                raise HTTPException(status_code=400,
                                    detail="minio_path must contain bucket and file")

            image_bytes = await asyncio.to_thread(get_file_from_minio, bucket, file)
        else:
            if request_data.image_base64_string.startswith("data:image"):
                request_data.image_base64_string = request_data.image_base64_string.split(",")[1]
            image_bytes = base64.b64decode(request_data.image_base64_string)

        # draw bbox
        bbox = (
            request_data.x1,
            request_data.y1,
            request_data.x2,
            request_data.y2,
        )

        result_bytes = await asyncio.to_thread(draw_bbox_on_image,
                                               image_bytes,
                                               bbox,
                                               request_data.color.value)

        # upload minio
        bucket = "backend-images"
        filename = f"{uuid.uuid4()}_context.jpeg"
        obj = await asyncio.to_thread(upload_to_minio,
                                      bucket,
                                      result_bytes,
                                      str(uuid.uuid4()),
                                      filename,
                                      content_type="image/jpeg")

        presigned_url = await asyncio.to_thread(generate_presigned_url, obj["bucket"], obj["filename"], host)

        return JSONResponse(content=jsonable_encoder({"bucket": obj["bucket"],
                                                      "file": obj["filename"],
                                                      "url": presigned_url}))

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(e, exc_info=True)
        mess = {"status": "error", "message": f"Error: {e}"}
        raise HTTPException(400, mess)


@router.delete("/delete_context_screenshot")
async def delete_context_screenshot(request_data: ContextScreenshotRequestDelete,
                                    current_user: User = Depends(get_current_active_user),
                                    host: str = Header(None)):
    """Delete screenshot from minio
    minio_path  {"bucket": "", "file": ""}
    """

    try:
        # Validate source
        if not request_data.minio_path:
            raise HTTPException(status_code=400,
                                detail="Either minio_path or image_base64_string must be provided")
        bucket = request_data.minio_path.get("bucket")
        file = request_data.minio_path.get("file")

        if not bucket or not file:
            raise HTTPException(
                status_code=400,
                detail="minio_path must contain bucket and file"
            )
        if bucket != "backend-images":
            raise HTTPException(status_code=400,
                                detail="this enpoint only for the backend-images bucket")

        await asyncio.to_thread(remove_file_from_minio, bucket, file)

        return JSONResponse(content={"status": "OK"})

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(e, exc_info=True)
        mess = {"status": "error", "message": f"Error: {e}"}
        raise HTTPException(400, mess)
