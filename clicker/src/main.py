import asyncio
import base64
import time
import uuid
from typing import Tuple, List

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse

from agent.graph_actions import draw_point_on_screenshot_base64
from agent.schemas import ReflectionStepConfig
from core.config import INFERENCE_MODEL, REFLECTION_MODEL, UVICORN_PORT, logger
from core.schemas import (
    ColorEnum,
    ConvertToSopResponse,
    CoordinatesRequest,
    CoordinatesResponse,
    ElementDescriptionRequest,
    ElementDescriptionResponse,
    RecordModel,
    ReflectionRequest,
    ReflectionResponse,
    SOPValidationRequest,
)
from core.utils import (
    check_diff_resolution_between_images_bs_64,
    extract_minio_bucket_and_file,
    get_file_from_minio,
    get_image_base64,
    sop_validation,
)
from recorder.convert_to_sop import generate_sop_from_demo
from runtime.inference_runtime import InferenceClientRegistry


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/convert_to_sop", response_model=List[str])
async def convert_record_to_sop(request: RecordModel) -> List[str]:
    try:
        logger.info("start convert_to_sop stage 1")
        record = request.record
        context = request.context
        lang = record[0]["full_data"]["language"]
        steps = await generate_sop_from_demo(record, context, language=lang)
        # steps = await rewrite_sop("\n".join(instructions))
        logger.info(f" {steps=}")
        return steps
    except Exception as er:
        raise HTTPException(status_code=400, detail=f"Error convert_to_sop: {repr(er)}")


@app.post("/sop_validation")
async def validation(request: SOPValidationRequest):
    try:
        return await sop_validation(request.sop,
                                    request.action_plan_id,
                                    request.user_id,
                                    request.case_id)
    except Exception as er:
        raise HTTPException(status_code=400, detail=f"Error sop_validation: {repr(er)}")


@app.post("/get_coordinates", response_model=CoordinatesResponse)
async def get_coordinates(request: CoordinatesRequest) -> CoordinatesResponse:
    try:
        original_image_base64 = await get_image_base64(
            request.minio_path, request.image_base64_string
        )

        context_screenshot_image_base64 = None
        if request.context_screenshot_path:
            context_screenshot_bucket, context_screenshot_file = extract_minio_bucket_and_file(
                request.context_screenshot_path
            )
            context_screenshot_file_data = await asyncio.to_thread(
                get_file_from_minio,
                context_screenshot_bucket,
                context_screenshot_file,
            )
            context_screenshot_image_base64 = base64.b64encode(
                context_screenshot_file_data
            ).decode("utf-8")

        prompt = request.prompt

        if not original_image_base64.strip() or not prompt.strip():
            raise TypeError("string cannot be empty")

        image_base64_string = original_image_base64
        if original_image_base64.startswith("data:image"):
            image_base64_string = original_image_base64.split(",")[1]

        if context_screenshot_image_base64:
            await asyncio.to_thread(check_diff_resolution_between_images_bs_64,
                                    image_base64_string,
                                    context_screenshot_image_base64)

        _, inference_client = await InferenceClientRegistry.get_model_client(
            model_type=INFERENCE_MODEL
        )

        start_generate_time = time.time()
        coordinates = await inference_client.get_coordinates(image_path=image_base64_string,
                                                             task=prompt,
                                                             is_base64=True,
                                                             context_screenshot_image_path=context_screenshot_image_base64,
                                                             context_screenshot_is_base64=True)
        x, y = coordinates
        end_generate_time = time.time() - start_generate_time

        if x == 0 and y == 0:
            raise ValueError("Could not find the target element in the image")

        anhnotated_image_base64 = await asyncio.to_thread(draw_point_on_screenshot_base64, image_base64_string, x, y)

        result = CoordinatesResponse(
            result_id=str(uuid.uuid4()),
            generate_time=f"{end_generate_time:.2f}",
            original_prompt=prompt,
            final_prompt=prompt,
            coords=(x, y),
            original_image_base64=original_image_base64,
            annotated_image_base64=f"data:image/jpeg;base64,{anhnotated_image_base64}",
            context_screenshot_path=request.context_screenshot_path,
        )

        return result

    except Exception as er:
        raise HTTPException(status_code=400, detail=f"get_cordinates error: {repr(er)}")


async def _get_reflection_result(
    reflection_client,
    before_image_base64_string: str,
    after_image_base64_string: str,
    prompt: str,
    use_single_screenshot: bool,
) -> ReflectionResponse:

    start_generate_time = time.time()

    result_id = str(uuid.uuid4())

    reflection_task = ReflectionStepConfig(instruction=prompt,
                                           use_single_screenshot=use_single_screenshot)
    if (hasattr(reflection_client, 'verify_two_screenshots')
            and before_image_base64_string
            and after_image_base64_string
            and use_single_screenshot is False):

        logger.info(f"Performing two-screenshot verification for {result_id=}")
        result = await reflection_client.verify_two_screenshots(before_image_base64_string,
                                                                after_image_base64_string,
                                                                reflection_task.instruction,
                                                                logger=logger,
                                                                use_single_screenshot=reflection_task.use_single_screenshot,
                                                                is_base64=True)
    else:
        logger.info(f"Performing one-screenshot verification for {result_id=}")
        result = await reflection_client.verify_screenshot(after_image_base64_string,
                                                           reflection_task.instruction,
                                                           logger=logger,
                                                           is_base64=True)

    end_generate_time = time.time() - start_generate_time

    validation_result = ReflectionResponse(
        result_id=result_id,
        reflection_time=f"{end_generate_time:.2f}s",
        reflection_step=prompt,
        reflection_title="",
        reflection_description=result.details,
        reflection_thoughts=result.thought_process,
        reflection_result="passed" if result.verification_passed else "failed",
    )
    return validation_result


@app.post("/get_reflection", response_model=ReflectionResponse)
async def get_reflection(request: ReflectionRequest) -> ReflectionResponse:
    try:

        after_original_image_base64 = await get_image_base64(request.after_minio_path,
                                                             request.after_image_base64_string)

        if request.before_minio_path or request.before_image_base64_string:
            before_original_image_base64 = await get_image_base64(request.before_minio_path,
                                                                  request.before_image_base64_string)
        else:
            before_original_image_base64 = after_original_image_base64

        prompt = request.reflection_instruction

        if not after_original_image_base64.strip() or not prompt.strip():
            raise TypeError("string cannot be empty")

        after_image_base64_string = after_original_image_base64
        if after_original_image_base64.startswith("data:image"):
            after_image_base64_string = after_original_image_base64.split(",")[1]

        before_image_base64_string = before_original_image_base64
        if before_original_image_base64.startswith("data:image"):
            before_image_base64_string = before_original_image_base64.split(",")[1]

        _, reflection_client = await InferenceClientRegistry.get_reflection_client(
            reflection_model=REFLECTION_MODEL
        )

        try:
            result = await asyncio.wait_for(
                _get_reflection_result(
                    reflection_client,
                    before_image_base64_string,
                    after_image_base64_string,
                    prompt,
                    request.use_single_screenshot,
                ),
                timeout=90,
            )
            return result

        except asyncio.TimeoutError:
            raise ValueError("timed out after 90 seconds")

    except Exception as er:
        raise HTTPException(status_code=400, detail=f"get_reflection error: {repr(er)}")


def _is_valid_description(description: str) -> bool:
    return description and description.strip() and len(description.strip()) < 200


def _are_coordinates_in_region(x: int, y: int, x1: int, y1: int, x2: int, y2: int) -> bool:
    return x1 <= x <= x2 and y1 <= y <= y2


async def _get_element_description_with_validation(
    inference_client,
    image_base64_string: str,
    x1: int,
    y1: int,
    x2: int,
    y2: int,
    color: ColorEnum,
    thinking_mode: bool,
    max_attempts: int = 4
) -> Tuple[str, bool]:
    last_description = None
    previous_failed_description = None
    hit_status = False

    for attempt in range(max_attempts):
        adjusted_thinking_mode = thinking_mode
        if attempt > 0:
            adjusted_thinking_mode = True

        description = await inference_client.describe_element(
            image_path=image_base64_string,
            x1=x1,
            y1=y1,
            x2=x2,
            y2=y2,
            color=color,
            is_base64=True,
            thinking_mode=adjusted_thinking_mode,
            previous_description=previous_failed_description
        )

        if _is_valid_description(description):
            try:
                coords = await inference_client.get_coordinates(
                    image_path=image_base64_string,
                    task=description,
                    is_base64=True
                )
                x, y = coords

                if _are_coordinates_in_region(x, y, x1, y1, x2, y2):
                    hit_status = True
                    return description, hit_status

                previous_failed_description = description
            except Exception:
                previous_failed_description = description
                pass

        last_description = description
        if not previous_failed_description:
            previous_failed_description = description

    return (last_description if last_description else "Unable to describe this element", hit_status)


@app.post("/describe_element", response_model=ElementDescriptionResponse)
async def describe_element(request: ElementDescriptionRequest) -> ElementDescriptionResponse:
    try:
        original_image_base64 = await get_image_base64(
            request.minio_path, request.image_base64_string
        )

        if not original_image_base64.strip():
            raise TypeError("image cannot be empty")

        x1 = request.x1
        y1 = request.y1
        x2 = request.x2
        y2 = request.y2

        if x1 < 0 or y1 < 0 or x2 <= x1 or y2 <= y1:
            raise ValueError("Invalid bounding box coordinates: x2 and y2 must be greater than x1 and y1, and all must be non-negative")

        image_base64_string = original_image_base64
        if original_image_base64.startswith("data:image"):
            image_base64_string = original_image_base64.split(",")[1]

        _, inference_client = await InferenceClientRegistry.get_model_client(
            model_type=INFERENCE_MODEL
        )

        start_generate_time = time.time()
        description, hit_status = await _get_element_description_with_validation(
            inference_client,
            image_base64_string,
            x1,
            y1,
            x2,
            y2,
            request.color,
            request.thinking_mode,
            max_attempts=4,
        )
        end_generate_time = time.time() - start_generate_time

        result = ElementDescriptionResponse(
            result_id=str(uuid.uuid4()),
            generate_time=f"{end_generate_time:.2f}",
            bounding_box={"x1": x1, "y1": y1, "x2": x2, "y2": y2},
            description=description,
            color=request.color,
            success=hit_status,
            original_image_base64=original_image_base64,
        )
        return result

    except Exception as er:
        raise HTTPException(status_code=400, detail=f"describe_element error: {repr(er)}")


@app.get("/healthcheck")
async def healthcheck():
    return {"status": "ok"}


@app.exception_handler(HTTPException)
async def exception_handler(request, exc):
    logger.error(f"HTTP error: {repr(exc)}")
    return JSONResponse({"detail": str(exc.detail)}, status_code=exc.status_code)


# @app.on_event('startup')
# async def init_app():
#     await model_ip_store.initialize()


if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=UVICORN_PORT,
        reload=False,
        workers=1,
        proxy_headers=True,
        ws_ping_interval=25,
        ws_ping_timeout=120,
        timeout_keep_alive=120,
    )
