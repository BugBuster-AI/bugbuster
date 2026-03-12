import asyncio
import base64
import difflib
import io
import json
from datetime import timedelta
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import aiohttp
from dotenv import load_dotenv
from fastapi import HTTPException
from langfuse import get_client, observe
from md2tgmd import escape
from minio import Minio
from PIL import Image
from pydantic import BaseModel

from agent.rewriter.rewrite_sop import detect_multi_action_steps, rewrite_sop
from core.celeryconfig import (MINIO_ACCESS_KEY, MINIO_HOST, MINIO_PORT,
                               MINIO_SECRET_KEY, MINIO_SECURE, RABBIT_PREFIX)
from core.config import logger
from core.schemas import Lang, MinioObjectPath

load_dotenv()


def validate_and_save_context_image(image_bytes: bytes,
                                    *,
                                    output_path: Path,
                                    width: int,
                                    height: int) -> dict:
    """ сравниваем разрешение браузера и контекстного скрина
        если все ок, сохраняем картинку
    """
    try:
        with Image.open(BytesIO(image_bytes)) as img:
            if img.format not in ("JPEG", "PNG"):
                return {
                    "used": False,
                    "local_path": None,
                    "log": f"Unsupported image format: {img.format}"
                }

            img_w, img_h = img.size
            if (img_w, img_h) != (width, height):
                return {
                    "used": False,
                    "local_path": None,
                    "log": f"Resolution different: {img_w}x{img_h}, expected {width}x{height}"
                }

            # создаём только поддиректории (если object_name содержит path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            img.save(output_path, format=img.format)

            return {
                "used": True,
                "local_path": output_path,
                "log": "OK"
            }

    except Exception as e:
        return {
            "used": False,
            "local_path": None,
            "log": f"Image processing error: {e}"
        }


def check_diff_resolution_between_images_bs_64(first_img_bs_64: str,
                                               second_img_bs_64: str):

    try:
        first_img = Image.open(BytesIO(base64.b64decode(first_img_bs_64)))
        second_img = Image.open(BytesIO(base64.b64decode(second_img_bs_64)))

    except Exception:
        raise ValueError("Failed to decode images from base64")

    first_img_w, first_img_h = first_img.size
    second_img_w, second_img_h = second_img.size

    if (first_img_w, first_img_h) != (second_img_w, second_img_h):
        raise ValueError(f"Different image resolution:"
                         f"first={first_img_w}x{first_img_h}, second={second_img_w}x{second_img_h}")


async def get_image_base64(minio_path=None, image_base64_string=None):

    if not minio_path and not image_base64_string:
        raise TypeError("Either after_minio_path or after_image_base64_string must be provided")

    if not minio_path:
        return image_base64_string

    bucket, file = extract_minio_bucket_and_file(minio_path)
    file_data = await asyncio.to_thread(get_file_from_minio, bucket, file)
    return base64.b64encode(file_data).decode('utf-8')


def extract_minio_bucket_and_file(minio_path: Any) -> Tuple[str, str]:
    if isinstance(minio_path, MinioObjectPath):
        return minio_path.bucket, minio_path.file

    if isinstance(minio_path, BaseModel):
        payload = minio_path.model_dump()
    elif isinstance(minio_path, dict):
        payload = minio_path
    else:
        raise TypeError("minio_path must be MinioObjectPath or dict")

    bucket = payload.get("bucket")
    file = payload.get("file")
    if not bucket or not file:
        raise TypeError("minio_path must contain bucket and file")
    return bucket, file


def select_language(host: str) -> str:

    if host in ['api.example.ru']:
        return Lang.RU.value
    elif host in ['apiexample.com']:
        return Lang.EN.value
    else:
        return Lang.RU.value


minioClient = Minio(f"{MINIO_HOST}:{MINIO_PORT}",
                    access_key=MINIO_ACCESS_KEY,
                    secret_key=MINIO_SECRET_KEY,
                    secure=MINIO_SECURE)


def generate_presigned_url(bucket_name, object_name, host: str = None):

    presigned_url = minioClient.presigned_get_object(bucket_name, object_name, expires=timedelta(days=1))
    return presigned_url


def get_file_from_minio(bucket_name, object_name):
    """Получаем файл в bytes"""

    response = minioClient.get_object(bucket_name, object_name)
    file_data = response.read()
    response.close()
    response.release_conn()
    return file_data


def upload_buffer_to_minio(buffer, task_id, filename):

    buffer.seek(0)
    data_to_upload = buffer.getvalue().encode('utf-8')

    bucket_name = 'run-cases'
    object_name = f"{task_id}/{filename}"

    minioClient.put_object(
        bucket_name,
        object_name,
        data=io.BytesIO(data_to_upload),
        length=len(data_to_upload),
        content_type='text/plain; charset=utf-8'
    )


def upload_bytes_buffer_to_minio(buffer, task_id, filename):
    buffer.seek(0)

    bucket_name = 'run-cases'
    object_name = f"{task_id}/{filename}"

    data_length = buffer.getbuffer().nbytes

    minioClient.put_object(
        bucket_name,
        object_name,
        data=buffer,
        length=data_length,
        content_type='video/webm'
    )

    return {"bucket": bucket_name, "file": object_name}


def upload_to_minio(file_path, task_id, filename):
    bucket_name = 'run-cases'
    object_name = f"{task_id}/{filename}"

    if filename.endswith('.webm'):
        content_type = 'video/webm'
    elif filename.endswith('.jpeg'):
        content_type = 'image/jpeg'
    elif filename.endswith('.zip'):
        content_type = 'application/zip'
    else:
        content_type = 'application/octet-stream'

    minioClient.fput_object(bucket_name, object_name, file_path, content_type=content_type)
    return {"bucket": bucket_name, "file": object_name}


class ActionValidator:
    VALID_KEYS = [
        "Backquote", "Minus", "Equal", "Backslash", "Backspace", "Tab", "Delete",
        "Escape", "ArrowDown", "End", "Enter", "Home", "Insert", "PageDown",
        "PageUp", "ArrowRight", "ArrowUp", "Period", ".",
        "F1","F2","F3","F4","F5","F6","F7","F8","F9","F10","F11","F12",
        "Digit0","Digit1","Digit2","Digit3","Digit4","Digit5","Digit6","Digit7","Digit8","Digit9",
        "KeyA","KeyB","KeyC","KeyD","KeyE","KeyF","KeyG","KeyH","KeyI","KeyJ","KeyK","KeyL","KeyM",
        "KeyN","KeyO","KeyP","KeyQ","KeyR","KeyS","KeyT","KeyU","KeyV","KeyW","KeyX","KeyY","KeyZ",
        "Shift", "Control", "Alt", "Meta",
        "ShiftLeft", "ControlOrMeta"
    ]

    def validate_UNSUPPORTED(self, step, non_empty_fields):
        return f"Unsupported action: {step['reason']}"

    def validate_PRESS(self, step, non_empty_fields):
        if step.get('key_to_press') == '[MISSING]':
            return "Model wasn't able to parse the key_to_press field from the instruction"
        if 'key_to_press' not in non_empty_fields:
            return "When action is PRESS, key_to_press is required"

        original_keys = step['key_to_press']
        keys_to_press = original_keys.split('+')
        corrected_keys = []

        for key in keys_to_press:
            # 1. Direct match
            if key in self.VALID_KEYS:
                corrected_keys.append(key)
                continue

            # 2. Shortcut match (e.g., 'A' -> 'KeyA', '5' -> 'Digit5')
            potential_key = None
            if len(key) == 1:
                if key.isdigit():
                    potential_key = f"Digit{key}"
                elif key.isalpha():
                    potential_key = f"Key{key.upper()}"

            if potential_key and potential_key in self.VALID_KEYS:
                corrected_keys.append(potential_key)
                continue

            # 3. Case-insensitive match
            found_match = False
            for valid_key in self.VALID_KEYS:
                if key.lower() == valid_key.lower():
                    corrected_keys.append(valid_key)
                    found_match = True
                    break
            if found_match:
                continue

            # 4. Fuzzy match for typos
            close_matches = difflib.get_close_matches(key, self.VALID_KEYS, n=1, cutoff=0.8)
            if close_matches:
                suggestion = close_matches[0]
                corrected_keys.append(suggestion)
                continue
            else:
                return f"Invalid key '{key}' in '{original_keys}'. No close match found."

        corrected_combination = "+".join(corrected_keys)
        if corrected_combination != original_keys:
            return f"Invalid key/combination '{original_keys}', did you mean '{corrected_combination}'?"

        return None

    def validate_NEW_TAB(self, step, non_empty_fields):
        if step.get('tab_name') == '[MISSING]':
            return "Model wasn't able to parse the tab_name field from the instruction"
        if 'tab_name' not in non_empty_fields:
            return "When action is NEW_TAB or SWITCH_TAB, tab_name is required"
        return None

    def validate_SWITCH_TAB(self, step, non_empty_fields):
        if step.get('tab_name') == '[MISSING]':
            return "Model wasn't able to parse the tab_name field from the instruction"
        if 'tab_name' not in non_empty_fields:
            return "When action is NEW_TAB or SWITCH_TAB, tab_name is required"
        return None

    def validate_WAIT(self, step, non_empty_fields):
        if step.get('wait_time') == '[MISSING]':
            return "Model wasn't able to parse the wait_time field from the instruction"
        if 'wait_time' not in non_empty_fields:
            step['wait_time'] = 30
        if step['wait_time'] <= 0:
            return "Wait time should be a positive number"
        elif step['wait_time'] > 30:
            return "Wait time cannot exceed 30 seconds"
        return None

    def validate_INNER_SCROLL(self, step, non_empty_fields):
        if step.get('container_description') == '[MISSING]':
            return "Model wasn't able to parse the container_description field from the instruction"
        if step.get('scroll_target') == '[MISSING]':
            return "Model wasn't able to parse the scroll_target field from the instruction"
        if 'scroll_target' not in non_empty_fields:
            return "When action is INNER_SCROLL, scroll_target is required"
        elif 'container_description' not in non_empty_fields:
            return "When action is INNER_SCROLL, container_description is required"
        return None

    def validate_CLICK(self, step, non_empty_fields):
        if step.get('element_description') == '[MISSING]':
            return "Model wasn't able to parse the element_description field from the instruction"
        if 'element_description' not in non_empty_fields:
            return "When action is CLICK, element_description is required"
        return None

    def validate_HOVER(self, step, non_empty_fields):
        if step.get('element_description') == '[MISSING]':
            return "Model wasn't able to parse the element_description field from the instruction"
        if 'element_description' not in non_empty_fields:
            return "When action is HOVER, element_description is required"
        return None

    def validate_TYPE(self, step, non_empty_fields):
        if step.get('element_description') == '[MISSING]':
            return "Model wasn't able to parse the element_description field from the instruction"
        if step.get('text_to_type') == '[MISSING]':
            return "Model wasn't able to parse the text_to_type field from the instruction"
        if 'element_description' not in non_empty_fields:
            return "When action is TYPE, element_description is required"
        elif 'text_to_type' not in non_empty_fields:
            return "When action is TYPE, text_to_type is required"
        return None

    def validate_CLEAR(self, step, non_empty_fields):
        if step.get('element_description') == '[MISSING]':
            return "Model wasn't able to parse the element_description field from the instruction"
        if 'element_description' not in non_empty_fields:
            return "When action is CLEAR, element_description is required"
        return None

    def validate_SCROLL(self, step, non_empty_fields):
        if step.get('scroll_target') == '[MISSING]':
            return "Model wasn't able to parse the scroll_target field from the instruction"
        if 'scroll_target' not in non_empty_fields:
            return "When action is SCROLL, scroll_target is required"
        return None

    def validate_READ(self, step, non_empty_fields):
        if step.get('instruction') == '[MISSING]':
            return "Model wasn't able to parse the instruction field from the instruction"
        if step.get('storage_key') == '[MISSING]':
            return "Model wasn't able to generate the storage_key to store the read text under, please provide a storage key"
        if 'instruction' not in non_empty_fields:
            return "When action is READ, instruction is required"
        elif 'storage_key' not in non_empty_fields:
            return "When action is READ, storage_key is required"
        return None

    def validate_PASTE(self, step, non_empty_fields):
        if step.get('element_description') == '[MISSING]':
            return "Model wasn't able to parse the element_description field from the instruction"
        if step.get('storage_key') == '[MISSING]':
            return "Model wasn't able to generate the storage_key to store the read text under, please provide a storage key"
        if 'element_description' not in non_empty_fields:
            return "When action is PASTE, element_description is required"
        elif 'storage_key' not in non_empty_fields:
            return "When action is PASTE, storage_key is required"
        return None

    def validate_SELECT(self, step, non_empty_fields):
        if step.get('element_description') == '[MISSING]':
            return "Model wasn't able to parse the element_description field from the instruction"
        if step.get('option_value') == '[MISSING]':
            return "Model wasn't able to parse the option_value field from the instruction"
        if 'element_description' not in non_empty_fields:
            return "When action is SELECT, element_description is required"
        elif 'option_value' not in non_empty_fields:
            return "When action is SELECT, option_value is required"
        return None

    def validate(self, step, non_empty_fields):
        method_name = f"validate_{step['action_type']}"
        if hasattr(self, method_name):
            return getattr(self, method_name)(step, non_empty_fields)
        else:
            return f"Unknown action type: {step['action_type']}"


@observe(as_type="span")
async def sop_validation(sop: List[str],
                         action_plan_id: Optional[str] = None,
                         user_id: Optional[str] = None,
                         case_id: Optional[str] = None):

    logger.info(f"sop_validation {user_id=} {case_id=}: {sop=}")
    langfuse = get_client()
    # Set up Langfuse trace context
    if action_plan_id:
        langfuse.update_current_trace(
            session_id=case_id,
            user_id=user_id,
            metadata={"action_plan_id": action_plan_id, "user_id": user_id}
        )

    if len(sop) == 0:
        raise HTTPException(status_code=400, detail="sop is empty!")

    action_plan = await rewrite_sop(('\n').join(sop))

    if len(action_plan) == 0:
        raise HTTPException(status_code=400, detail="action_plan is empty!")

    if len(action_plan) != len(sop):
        logger.info(f"sop_validation: rewritten sop has {len(action_plan)} steps, but original sop has {len(sop)} steps")

        # Log step count mismatch to Langfuse
        try:
            langfuse.score_current_trace(
                name="validation_passed",
                value=0,
                data_type="BOOLEAN"
            )
            langfuse.score_current_trace(
                name="validation_reason",
                value="step_count_mismatch",
                data_type="CATEGORICAL"
            )
        except Exception as e:
            logger.warning(f"Failed to log validation results to Langfuse: {e}")

        multi_action_step_numbers = await detect_multi_action_steps('\n'.join(sop), action_plan)

        invalid_steps = {}
        for step_num in multi_action_step_numbers:
            idx = step_num - 1
            if 0 <= idx < len(sop):
                invalid_steps[idx] = f"Step {idx} contains multiple actions!"

        if invalid_steps:
            return {"is_valid": False, "validation_reason": invalid_steps, "action_plan": action_plan}
        else:
            raise ValueError("rewritten sop has different number of steps than original sop")

    # если хотя бы один степ некорректен
    # флаг False, в словаре ключ = индекс степа, значение описание что не так с ним
    validator = ActionValidator()
    invalid_steps = {}
    for i, step in enumerate(action_plan):
        non_empty_fields = [field for field in step.keys() if step[field] is not None and step[field] != "null" and step[field] != ""]
        error = validator.validate(step, non_empty_fields)
        if error:
            invalid_steps[i] = error

    logger.info(f"sop_validation: SOP is {'not valid' if len(invalid_steps) else 'valid'}, {invalid_steps=}\n {action_plan=}")

    # Log validation results to Langfuse
    try:
        validation_passed = len(invalid_steps) == 0

        # Determine validation reason category
        if validation_passed:
            reason = "correct"
            comment = None
        elif len(action_plan) != len(sop):
            reason = "step_count_mismatch"
            comment = None
        else:
            # Check for specific error types in invalid_steps
            unsupported_steps = []
            missing_field_steps = []
            storage_key_steps = []

            for step_idx, error_msg in invalid_steps.items():
                error_msg = str(error_msg).lower()
                if "unsupported action" in error_msg:
                    unsupported_steps.append(step_idx)
                elif "storage key" in error_msg:
                    storage_key_steps.append(step_idx)
                else:
                    missing_field_steps.append(step_idx)

            # Prioritize error types: unsupported > missing_field > storage_key
            if unsupported_steps:
                reason = "unsupported_action"
                comment = f"Step(s) {unsupported_steps}"
            elif missing_field_steps:
                reason = "missing_field"
                comment = f"Step(s) {missing_field_steps}"
            elif storage_key_steps:
                reason = "storage_key_errors"
                comment = None
            else:
                reason = "missing_field"  # fallback
                comment = f"Step {list(invalid_steps.keys())[0]}" if invalid_steps else None

        # Log validation_passed score
        langfuse.score_current_trace(
            name="validation_passed",
            value=1 if validation_passed else 0,
            data_type="BOOLEAN"
        )

        # Log reason score
        langfuse.score_current_trace(
            name="validation_reason",
            value=reason,
            data_type="CATEGORICAL",
            comment=comment
        )

    except Exception as e:
        # Don't break validation if Langfuse logging fails
        logger.warning(f"Failed to log validation results to Langfuse: {e}")


    if len(invalid_steps):
        return {"is_valid": False, "validation_reason": invalid_steps, "action_plan": action_plan}

    # прошли проверку, СОП полностью валидный
    # remove ['MISSING'] from not required fields
    for step in action_plan:
        for key in step.keys():
            if step[key] == '[MISSING]':
                step[key] = None

    for i, step in enumerate(action_plan):
        action_type = step['action_type']
        if action_type in ['CLICK', 'TYPE', 'HOVER', 'CLEAR', 'PASTE', 'SELECT']:
            step['element_description'] = sop[i]
        elif action_type == 'READ':
            step['instruction'] = sop[i]

    return {"is_valid": True, "validation_reason": {}, "action_plan": action_plan}


def action_plan_to_steps(action_plan: List[Dict[str, str]]) -> List[str]:
    steps = []
    for action in action_plan:
        step = ""
        if action['action_type'] == "CLICK":
            step = f"Click on {action['element_description']}"
        elif action['action_type'] == 'HOVER':
            step = f"Hover over {action['element_description']}"
        elif action['action_type'] == 'TYPE':
            step = f"Type '{action['text_to_type']}' in {action['element_description']}"
        elif action['action_type'] == 'PRESS':
            step = f"Press {action['key_to_press']} key"
        elif action['action_type'] == 'SCROLL':
            step = f"Scroll to {action['scroll_target']}"
        elif action['action_type'] == 'INNER_SCROLL':
            if action['container_description'].lower() == "page":
                step = f"Inner scroll page to {action['scroll_target']}"
            else:
                step = f"Inner scroll {action['container_description']} to {action['scroll_target']}"
        elif action['action_type'] == 'CLEAR':
            step = f"Clear {action['element_description']}"
        elif action['action_type'] == 'WAIT':
            if 'element_description' in action.keys() and action['element_description']:
                step = f"Wait for {action['element_description']} to load, but no longer than {action['wait_time'] if action['wait_time'] else 30} seconds"
            else:
                step = f"Wait for {action['wait_time'] if action['wait_time'] else 30} seconds"
        elif action['action_type'] == 'NEW_TAB':
            step = f"Open new tab and navigate to {action['tab_name']}"
        elif action['action_type'] == 'SWITCH_TAB':
            step = f"Switch to tab with name or url {action['tab_name']}"
        elif action['action_type'] == 'READ':
            step = f"Read {action['instruction']} and store as {action['storage_key']}"
        elif action['action_type'] == 'PASTE':
            step = f"Paste {action['storage_key']} into {action['element_description']}"
        elif action['action_type'] == 'SELECT':
            step = f"Select option '{action['option_value']}' from {action['element_description']}"
        else:
            step = f"UNKNOWN ACTION: {action['action_type']}"
        steps.append(step)
    return steps
