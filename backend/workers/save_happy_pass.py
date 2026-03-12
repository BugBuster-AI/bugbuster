import asyncio
import base64
import io
import json
from datetime import datetime, timezone
from uuid import UUID

from fastapi import WebSocket
from fastapi.responses import JSONResponse
from minio import Minio
from PIL import Image, ImageDraw, ImageFont

from api.actions import check_usage_limits, update_usage_count
from api.content_actions import happy_pass_update_autosop
from config import (MINIO_ACCESS_KEY, MINIO_HOST, MINIO_PORT, MINIO_SECRET_KEY,
                    MINIO_SECURE, logger)
from connections import ConnectionManager
from db.models import HappyPass
from db.session import async_session
from schemas import Task, UserRead
from utils import correct_base64_padding, save_image_to_minio


def filter_consecutive_scrolls(steps):
    """убираем промежуточные скроллы"""
    steps.sort(key=lambda x: x['timestamp'])

    filtered_steps = []
    last_scroll = None

    for step in steps:
        if step['action'] == 'click':
            coords = step.get('coords', {})
            if not coords or (coords.get('x') == 0 and coords.get('y') == 0):
                continue  # Skip empty coords

        if step['action'] == 'scroll':
            # Проверяем, является ли это действие скроллом с таким же исходником, как и предыдущий
            if last_scroll and last_scroll['coords']['scrollData'][0]['source'] == step['coords']['scrollData'][0]['source']:
                last_scroll = step
            else:
                if last_scroll:
                    filtered_steps.append(last_scroll)
                last_scroll = step
        else:
            if last_scroll:
                filtered_steps.append(last_scroll)
                last_scroll = None
            filtered_steps.append(step)

    if last_scroll:
        filtered_steps.append(last_scroll)

    return filtered_steps


def filter_click_followed_by_quick_input(activities):
    """
    Удаляем "input", если перед ним был "click" на том же элементе
    и разница между их временными метками составляет <= 200 мс.
    это автоинпуты в чекбоксах
    """
    filtered_activities = []
    previous_activity = None

    for activity in activities:
        if activity['action'] == 'input':
            if previous_activity and previous_activity['action'] == 'click' and \
                'elementDetails' in previous_activity and \
                    'elementDetails' in activity and previous_activity['elementDetails'] == activity['elementDetails']:

                time_diff = datetime.fromisoformat(activity['timestamp'][:-1]) - datetime.fromisoformat(previous_activity['timestamp'][:-1])

                if time_diff.total_seconds() <= 0.2:
                    continue

        if previous_activity:
            filtered_activities.append(previous_activity)

        previous_activity = activity

    if previous_activity:
        filtered_activities.append(previous_activity)

    return filtered_activities


def group_activities(activities):
    grouped_activities = []
    previous_activity = None

    for activity in activities:
        if previous_activity and previous_activity['action'] == 'input' and activity['action'] == 'input':
            # Если оба действия 'input' и относятся к одному элементу - объединяем их.
            if 'elementDetails' in previous_activity and 'elementDetails' in activity:
                if previous_activity['elementDetails']['elementId'] == activity['elementDetails']['elementId']:
                    previous_activity['inputText'] += activity['inputText'][-1]
                    # previous_activity['afterScreenshot'] = activity['afterScreenshot']
                    previous_activity['beforeScreenshot'] = activity['beforeScreenshot']
                    continue
        if previous_activity:
            grouped_activities.append(previous_activity)
        previous_activity = activity

    if previous_activity:
        grouped_activities.append(previous_activity)

    return grouped_activities


async def handle_save_happy_pass(manager: ConnectionManager, task: Task, user: UserRead, ws: WebSocket):
    task_id = str(task.task_id)

    if task.chunk:
        manager.append_chunk_for_task(task_id, task.chunk)

        if task.end:
            combined_message = "".join(manager.get_chunks_for_task(task_id))
            manager.delete_chunks_for_task(task_id)
            full_data = json.loads(combined_message)
            full_data = {
                "user_id": str(user.user_id),
                "task_id": task_id
            } | full_data

            if task.extra:
                full_data.update(task.extra)

            save_response = await save_happy_pass(task.task_id, manager, ws, full_data, user)

            if save_response.status_code == 200:
                await manager.send_personal_message({
                    "task_id": task_id,
                    "type": "save_happy_pass",
                    "status": "success",
                    "message": save_response.body.decode()
                }, ws)
            else:
                await manager.send_personal_message({
                    "task_id": task_id,
                    "type": "save_happy_pass",
                    "status": "error",
                    "message": save_response.body.decode()
                }, ws)
    else:
        full_data = {
            "user_id": str(user.user_id),
            "task_id": str(task.task_id)
        } | task.dict()

        if task.extra:
            full_data.update(task.extra)

        save_response = await save_happy_pass(task.task_id, manager, ws, full_data, user)

        if save_response.status_code == 200:
            await manager.send_personal_message({
                "task_id": str(task.task_id),
                "type": "save_happy_pass",
                "status": "success",
                "message": save_response.body.decode()
            }, ws)
        else:
            await manager.send_personal_message({
                "task_id": str(task.task_id),
                "type": "save_happy_pass",
                "status": "error",
                "message": save_response.body.decode()
            }, ws)


def annotate_screenshot(image_data, coords, label):
    img_data = base64.b64decode(correct_base64_padding(image_data))
    image = Image.open(io.BytesIO(img_data)).convert("RGBA")
    draw = ImageDraw.Draw(image)
    cross_size = 10
    font = ImageFont.truetype("ARIAL.TTF", 15)
    draw.line((coords['x'] - cross_size, coords['y'], coords['x'] + cross_size, coords['y']), fill='red', width=2)
    draw.line((coords['x'], coords['y'] - cross_size, coords['x'], coords['y'] + cross_size), fill='red', width=2)
    text_position = (coords['x'], coords['y'] + cross_size + 5)
    draw.text(text_position, label, fill='red', font=font)
    buffer = io.BytesIO()
    image.save(buffer, format='PNG')
    buffer.seek(0)
    return buffer


async def save_happy_pass(task_id: UUID, manager: ConnectionManager, ws: WebSocket, data: dict, user: UserRead):
    try:
        async with async_session() as session:
            async with session.begin():

                workspace_id = data.get('workspace_id')
                if not workspace_id:
                    raise ValueError("workspace_id is missing in the request.")

                language = data.get('language')
                if not language:
                    raise ValueError("language is missing in the request.")

                project_id = data.get('project_id')
                if not project_id:
                    raise ValueError("project_id is missing in the request.")

                recording_name = data.get('recording_name')
                if not recording_name:
                    raise ValueError("Recording name is missing in the request.")

                context = data.get('context', '')
                # if not context:
                #     raise ValueError("Context is missing in the request.")

                activities = data.get('activities')
                if not activities:
                    raise ValueError("No activities found in the request.")

                minioClient = Minio(
                    f"{MINIO_HOST}:{MINIO_PORT}",
                    access_key=MINIO_ACCESS_KEY,
                    secret_key=MINIO_SECRET_KEY,
                    secure=MINIO_SECURE
                )

                # grouped_activities = group_activities(activities)
                # grouped_activities.sort(key=lambda x: x['timestamp'])

                filtered_activities = filter_consecutive_scrolls(activities)
                filtered_activities = filter_click_followed_by_quick_input(filtered_activities)

                if len(filtered_activities) == 0:
                    logger.error(f"empty steps!\n{activities=}\n{filtered_activities=}")
                    raise ValueError("empty steps!")
                logger.info(f"{task_id=} | cnt activities: {len(activities)} | cnt filtered_activities: {len(filtered_activities)}")

                # filtered_activities.sort(key=lambda x: x['timestamp'])
                bucket_name = 'happypass'
                images = []
                # for activity in grouped_activities:
                for activity in filtered_activities:
                    coords = activity.get("coords", {})
                    if not coords or 'x' not in coords or 'y' not in coords:
                        logger.warning(f"No coordinates found for activity {activity['id']}")
                        continue

                    for key in ["beforeScreenshot", "beforeAnnotatedScreenshot", "afterScreenshot"]:
                        screenshot_id = activity.get(key)
                        screenshot_data = [s['data'] for s in data['screenshots'] if s['id'] == screenshot_id]
                        if screenshot_data:
                            filename = f"{screenshot_id}.png"
                            object_name = f"{task_id}/{filename}"
                            if key == "beforeAnnotatedScreenshot":
                                annotated_image_buffer = await asyncio.to_thread(annotate_screenshot,
                                                                                 screenshot_data[0],
                                                                                 coords,
                                                                                 f'{activity["action"]}')
                                await asyncio.to_thread(minioClient.put_object,
                                                        bucket_name, object_name,
                                                        annotated_image_buffer,
                                                        length=len(annotated_image_buffer.getvalue()),
                                                        content_type='image/png')
                            else:
                                await asyncio.to_thread(save_image_to_minio,
                                                        minioClient,
                                                        screenshot_data[0],
                                                        bucket_name, object_name)
                            activity[key] = {"bucket": bucket_name, "filename": object_name}
                            if key == "beforeAnnotatedScreenshot":
                                images.append({"bucket": bucket_name, "filename": object_name})
                del data['screenshots']
                del data['timestamp_start']
                del data['timestamp_end']
                # data["steps"] = data.pop("activities")
                data["steps"] = filtered_activities
                data.pop("activities")

                full_data = json.dumps(data, ensure_ascii=False, indent=4)

                new_happy_pass = HappyPass(
                    happy_pass_id=task_id,
                    user_id=user.user_id,
                    name=recording_name,
                    context=context,
                    images=images,
                    full_data=json.loads(full_data),
                    created_at=datetime.now(timezone.utc),
                    workspace_id=workspace_id,  # user.active_workspace_id
                    language=language,
                    project_id=project_id
                )

                session.add(new_happy_pass)
                await session.flush()
                await session.refresh(new_happy_pass)
                await update_usage_count(user.active_workspace_id, "save_happy_pass", 1)
        try:
            await happy_pass_update_autosop(user.active_workspace_id, user.user_id,
                                            new_happy_pass.happy_pass_id, 600, 'api.example.com')
        except Exception as e:
            logger.warning(f"Error on happy_pass_update_autosop: {e}", exc_info=True)

        return JSONResponse(status_code=200, content={"status": "success"})

    except Exception as e:
        logger.error(f"Error on save_happy_pass: {e}", exc_info=True)
        return JSONResponse(status_code=500, content={"status": "error", "reason": f"Unexpected error: {str(e)}"})
