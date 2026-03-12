import json
import os
import subprocess
import zipfile
from io import BytesIO
from subprocess import CalledProcessError, TimeoutExpired
from tempfile import mkdtemp

from celeryconfig import logger
from utils.db_utils import update_video_path
from utils.minio_utils import (download_from_minio, get_minio_client,
                               upload_bytes_buffer_to_minio)


def extract_zip_to_dir(zip_file_path, extract_to_path):
    with zipfile.ZipFile(zip_file_path, 'r') as z:
        z.extractall(extract_to_path)


def read_trace_file(trace_file_path, trace_filename='trace.trace'):
    full_trace_path = os.path.join(trace_file_path, trace_filename)
    with open(full_trace_path, 'r', encoding='utf-8') as trace_file:
        lines = trace_file.readlines()
    return [json.loads(line) for line in lines if line.strip()]


def find_matching_screenshots(log_data):
    before_actions = {}
    after_actions = {}

    # Собираем события "before" и "after"
    for entry in log_data:
        if entry['type'] == 'before':
            before_actions[entry['callId']] = entry
        elif entry['type'] == 'after':
            after_actions[entry['callId']] = entry

    detailed_screenshots = []
    all_call_ids = list(before_actions.keys())

    for i, before_call_id in enumerate(all_call_ids):
        before_entry = before_actions[before_call_id]

        if before_call_id in after_actions:
            after_entry = after_actions[before_call_id]

            if 'pageId' in before_entry:
                page_id = before_entry['pageId']
                start_time = before_entry['startTime']
                end_time = after_entry['endTime']

                matching_screenshots = [
                    entry for entry in log_data
                    if entry['type'] == 'screencast-frame' and entry['pageId'] == page_id and start_time <= entry['timestamp'] <= end_time
                ]

                # Для последнего события добавляем все оставшиеся скриншоты
                if i == len(all_call_ids) - 1:
                    remaining_screenshots = [
                        entry for entry in log_data
                        if entry['type'] == 'screencast-frame' and entry['pageId'] == page_id and entry['timestamp'] > end_time
                    ]
                    matching_screenshots.extend(remaining_screenshots)

                for j, screenshot in enumerate(matching_screenshots):
                    if j < len(matching_screenshots) - 1:
                        duration = (matching_screenshots[j + 1]['timestamp'] - screenshot['timestamp']) / 1000
                    else:
                        duration = (end_time - screenshot['timestamp']) / 1000
                        if duration < 0:
                            continue  # пропускаем самую последнюю картинку с неизвестным dur

                    duration_rounded = round(duration, 6)
                    if duration_rounded < 0.001:  # Минимальная длительность 1ms
                        duration_rounded = 0.001

                    detailed_screenshots.append({
                        "sha1": screenshot['sha1'],
                        "timestamp": screenshot['timestamp'],
                        "duration": duration_rounded,
                        'pageId': page_id
                    })

    return detailed_screenshots


def generate_video_from_screenshots(screenshots, image_dir):
    filelist_content = "\n".join(
        f"file '{os.path.abspath(os.path.join(image_dir, screenshot['sha1']))}'\n"
        f"duration {screenshot['duration']}"
        for screenshot in screenshots
    )

    filelist_path = os.path.join(image_dir, "filelist.txt")

    with open(filelist_path, 'w', encoding='utf-8') as f:
        f.write(filelist_content)
    output_buffer = BytesIO()
    try:
        # Запускаем ffmpeg с выводом в pipe
        process = subprocess.run(
            [
                "ffmpeg",
                "-threads", "0",
                "-protocol_whitelist", "file,http,https,tcp,tls",
                "-f", "concat", "-safe", "0", "-i", filelist_path,
                "-vf", "setpts=2.0*PTS,fps=30", "-c:v", "libvpx-vp9", "-crf", "30", "-b:v", "0",
                "-pix_fmt", "yuv420p", "-f", "webm", "pipe:1"
            ],
            timeout=600,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True
        )

        output_buffer.write(process.stdout)
        output_buffer.seek(0)

        return output_buffer

    except TimeoutExpired:
        logger.error("FFmpeg TimeoutExpired many 10 min")
        output_buffer.close()
        return None
    except CalledProcessError as e:
        logger.error(f"FFmpeg error: {e.stderr.decode()}")
        output_buffer.close()
        return None
    except Exception as e:
        logger.error(f"FFmpeg execution error: {str(e)}")
        output_buffer.close()
        return None


def generate_video_from_trace(db_name: str, trace_file_path: dict, run_id: str):
    try:
        temp_dir = mkdtemp(prefix=f"video_{run_id}_")
        zip_path = os.path.join(temp_dir, "trace.zip")
        minio_client = get_minio_client()

        download_from_minio(minio_client,
                            trace_file_path['bucket'],
                            trace_file_path['file'],
                            zip_path)

        extract_to_path = zip_path.replace('.zip', '')
        if not os.path.exists(extract_to_path):
            os.makedirs(extract_to_path, exist_ok=True)

        extract_zip_to_dir(zip_path, extract_to_path)
        trace_data = read_trace_file(extract_to_path)
        matching_screenshots = find_matching_screenshots(trace_data)
        resource_dir = os.path.join(extract_to_path, "resources")

        video_buffer = generate_video_from_screenshots(matching_screenshots, resource_dir)
        video_path = None
        if video_buffer:
            try:
                video_path = upload_bytes_buffer_to_minio(minio_client,
                                                          video_buffer,
                                                          run_id,
                                                          f"{run_id}.webm")
                logger.info(f"Successfully uploaded {video_path} for {run_id}")

                db_result = update_video_path(db_name, run_id, video_path)
                if not db_result:
                    logger.error(f"Failed to update video path in DB for {run_id}")
            finally:
                video_buffer.close()
        else:
            logger.error(f"Failed to generate {video_path} for {run_id}")

    except Exception as e:
        logger.error(f"Error in video generation for {run_id}: {str(e)}", exc_info=True)
    finally:
        if os.path.exists(temp_dir):
            for root, dirs, files in os.walk(temp_dir, topdown=False):
                for name in files:
                    os.remove(os.path.join(root, name))
                for name in dirs:
                    os.rmdir(os.path.join(root, name))
            os.rmdir(temp_dir)
