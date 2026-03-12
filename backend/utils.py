import asyncio
import base64
import io
import json
import smtplib
import time
from datetime import datetime, timedelta
from email.message import EmailMessage
from html import escape as escape_html
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import aiohttp
from urllib.parse import urlencode, urlparse, urlunparse
import urllib3

from aiohttp import ClientConnectorError
from md2tgmd import escape
from minio import Minio
from PIL import Image, ImageDraw, UnidentifiedImageError

from config import (MINIO_ACCESS_KEY, MINIO_HOST, MINIO_PORT,
                    MINIO_SECRET_KEY, MINIO_SECURE, USE_TELEGRAMM,
                    RABBIT_PREFIX, SMTP_CONFIG, TELEGRAM_BOT_TOKEN,
                    TELEGRAM_CHAT_ID, TOPIC_ID, TRACE_VIEWER_HOST, logger, DOMAIN, MINIO_PUBLIC_URL, MINIO_USE_INTERNAL_PROXY)
from schemas import Lang, UserRead


def escape_html_variables(variables: dict) -> dict:
    """Экранирует HTML-символы в значениях переменных."""
    escaped = {}
    for key, value in variables.items():
        if isinstance(value, str):
            escaped[key] = escape_html(value)
        else:
            escaped[key] = value
    return escaped


EMAIL_SUBJECTS = {
    "welcome": {
        Lang.RU: "Добро пожаловать в BugBuster!",
        Lang.EN: "Welcome to ScreenMate AI!"
    },
    "fast-welcome": {
        Lang.RU: "Добро пожаловать в BugBuster!",
        Lang.EN: "Welcome to ScreenMate AI!"
    },
    "invite": {
        Lang.RU: "Вас пригласили в проект",
        Lang.EN: "You were invited to the project"
    },
    "recovery": {
        Lang.RU: "Восстановление доступа",
        Lang.EN: "Reset your ScreenMate AI password"
    },
    "blocked": {
        Lang.RU: "Аккаунт временно заблокирован",
        Lang.EN: "The account is temporarily blocked"
    },
    "payment_confirmed": {
        Lang.RU: "Платёж подтверждён",
        Lang.EN: "The payment is confirmed"
    },
    "payment_reminder": {
        Lang.RU: "Напоминание о платеже",
        Lang.EN: "Payment reminder"
    },
    "update_notification": {
        Lang.RU: "Обновили генерацию кейсов",
        Lang.EN: "Updated the generation of cases"
    },
    "automation_info": {
        Lang.RU: "Автоматизируйте без автоматизаторов",
        Lang.EN: "Automate without automaticizers"
    }
}


def load_email_templates() -> Dict[str, Dict[Lang, str]]:
    """Загружает все шаблоны писем из папки templates/emails"""
    templates = {}
    template_files = Path("templates/emails").glob("*.html")

    for file in template_files:
        # Извлекаем тип письма и язык из имени файла
        name_parts = file.stem.split("_")
        if len(name_parts) != 2:
            continue

        template_type, lang = name_parts
        try:
            lang = Lang(lang)
        except ValueError:
            continue

        with open(file, "r", encoding="utf-8") as f:
            content = f.read()

        if template_type not in templates:
            templates[template_type] = {}
        templates[template_type][lang] = content

    return templates


# Загружаем шаблоны при старте
EMAIL_TEMPLATES = load_email_templates()


def create_new_user_message(source: str, user: UserRead) -> str:
    message = (
        "Новый пользователь!\n--------------------\n"
        f"**Источник**: {source}\n"
        f"**Хост**: {user.host}\n"
        f"**Email**: {user.email}\n"
        f"**Username**: {user.username}\n--------------------\n"
        f"**User_id**: {user.user_id}\n"
        f"**Active workspace**: {user.active_workspace_id}\n"
        f"**Registred at UTC**: {user.registered_at}\n"
    )
    return message


async def send_telegramm(original_message: str) -> None:
    try:
        if USE_TELEGRAMM:
            original_message = str(f"**{RABBIT_PREFIX}**\n{original_message}")[:3900]
            original_message = escape(original_message)

            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            headers = {'Content-type': 'application/json'}

            async with aiohttp.ClientSession() as session:
                for retry_count in range(4):
                    message = original_message
                    if retry_count > 0:
                        message += f"\n\n(Повторная отправка #{retry_count} после сбоя)"
                    data = {
                        "chat_id": TELEGRAM_CHAT_ID,
                        "message_thread_id": TOPIC_ID,
                        "text": message,
                        "parse_mode": "MarkdownV2"
                    }
                    async with session.post(url, data=json.dumps(data), headers=headers) as response:
                        if response.status != 200:
                            logger.info(f"Retry send to telegramm: {response.status} | {message}")
                            await asyncio.sleep(30)
                        else:
                            logger.info(f"Send to telegramm: {response.status} | {message}")
                            break

    except Exception as e:
        logger.error(f'Error on send to telegramm, message={original_message}, error={e}', exc_info=True)


def select_smtp_and_domain(host: str) -> Tuple[Dict[str, str], str]:

    return (SMTP_CONFIG, DOMAIN, DOMAIN)


def select_minio_host(host: str) -> str:
    return MINIO_HOST


def select_trace_viewer_host(host: str) -> str:
    return TRACE_VIEWER_HOST


def select_language(host: str) -> str:
    return Lang.RU.value


async def send_email_async(email: str,
                           template_type: str,
                           variables: dict,
                           host: Optional[str] = None,
                           lang: Optional[Lang] = None):
    try:
        if SMTP_CONFIG["enabled"]:

            if lang is None:
                lang = select_language(host)

            smtp_config, domain, static_domain = select_smtp_and_domain(host)

            # Добавляем домен в переменные
            variables_with_domain = {"domain": domain, "static_domain": static_domain, **variables}
            variables_with_domain = escape_html_variables(variables_with_domain)

            # Получаем шаблон письма
            template = EMAIL_TEMPLATES.get(template_type, {}).get(lang)
            if not template:
                raise ValueError(f"Template {template_type} for language {lang} not found")

            # Получаем тему письма
            subject = EMAIL_SUBJECTS.get(template_type, {}).get(lang, "Notification")

            # Заменяем переменные в шаблоне
            for key, value in variables_with_domain.items():
                template = template.replace(f"[{key}]", str(value))

            # Создаем и отправляем письмо
            message = EmailMessage()
            message["Subject"] = EMAIL_SUBJECTS.get(template_type, {}).get(lang, "Notification")
            message["From"] = smtp_config["username"]
            message["To"] = email

            message.set_content(template, subtype='html', charset='utf-8')

            logger.info(f"email: {variables_with_domain=}\n{host=}\n{lang=}\n{domain=}\n{subject=}\n")

            with smtplib.SMTP(smtp_config["server"], smtp_config["port"]) as server:
                server.starttls()
                server.login(smtp_config["username"], smtp_config["password"])
                server.send_message(message)

            logger.info(f"Successfully sent {template_type} email to {email}")
    except Exception as er:
        mess = f"send email error {er} to {email}"
        logger.error(mess, exc_info=True)
        await send_telegramm(mess)


async def send_simple_email_async(email: str,
                                  subject: str,
                                  body: str,
                                  host: Optional[str] = None):
    try:
        smtp_config, domain, static_domain = select_smtp_and_domain(host)

        # Создаем и отправляем письмо
        message = EmailMessage()
        message.set_content(body, charset='utf-8')
        message["Subject"] = str(subject)
        message["From"] = smtp_config["username"]
        message["To"] = email

        with smtplib.SMTP(smtp_config["server"], smtp_config["port"]) as server:
            server.starttls()
            server.login(smtp_config["username"], smtp_config["password"])
            server.send_message(message)

        logger.info(f"Successfully sent email to {email}")
    except Exception as er:
        mess = f"send email error {er} to {email}"
        logger.error(mess, exc_info=True)
        await send_telegramm(mess)


def get_file_from_minio(bucket_name, object_name):
    """Получаем файл в bytes"""
    minioClient = Minio(f"{MINIO_HOST}:{MINIO_PORT}",
                        access_key=MINIO_ACCESS_KEY,
                        secret_key=MINIO_SECRET_KEY,
                        secure=MINIO_SECURE)

    response = minioClient.get_object(bucket_name, object_name)
    file_data = response.read()
    response.close()
    response.release_conn()
    return file_data


def remove_file_from_minio(bucket_name, object_name):
    minioClient = Minio(f"{MINIO_HOST}:{MINIO_PORT}",
                        access_key=MINIO_ACCESS_KEY,
                        secret_key=MINIO_SECRET_KEY,
                        secure=MINIO_SECURE)
    minioClient.remove_object(bucket_name, object_name)


def upload_to_minio(bucket_name, file_bytes, task_id, filename, content_type='image/jpeg'):
    minioClient = Minio(f"{MINIO_HOST}:{MINIO_PORT}",
                        access_key=MINIO_ACCESS_KEY,
                        secret_key=MINIO_SECRET_KEY,
                        secure=MINIO_SECURE)

    today = datetime.utcnow().strftime("%Y-%m-%d")
    object_name = f"{today}/{filename}"
    with io.BytesIO(file_bytes) as file_data:
        minioClient.put_object(bucket_name, object_name, file_data, len(file_bytes), content_type=content_type)
    return {"bucket": bucket_name, "filename": object_name}


def draw_point_on_screenshot(image_bytes, x, y, bbox=None):
    with Image.open(io.BytesIO(image_bytes)) as img:
        draw = ImageDraw.Draw(img)

        if bbox:
            draw.rectangle([bbox[0], bbox[1], bbox[2], bbox[3]], outline='red', width=3)

        radius = 4
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill='green', outline='green')
        with io.BytesIO() as output:
            img.save(output, format="JPEG")
            return output.getvalue()


def draw_point_on_screenshot_base64(image_base64_string: str,
                                    x: int,
                                    y: int,
                                    bbox: tuple = None,
                                    output_format: str = "JPEG") -> str:
    image_bytes = base64.b64decode(image_base64_string)

    with Image.open(io.BytesIO(image_bytes)) as img:
        draw = ImageDraw.Draw(img)

        if bbox:
            draw.rectangle(bbox, outline='red', width=3)

        radius = 5
        draw.ellipse(
            (x - radius, y - radius, x + radius, y + radius),
            fill="green",
            outline="black"
        )

        with io.BytesIO() as output:
            img.save(output, format=output_format)
            output_bytes = output.getvalue()

    return base64.b64encode(output_bytes).decode('utf-8')


def draw_bbox_on_image(image_bytes: bytes,
                       bbox: tuple[int, int, int, int],
                       color: str) -> bytes:
    with Image.open(io.BytesIO(image_bytes)) as img:
        if img.format not in ("JPEG", "PNG"):
            raise ValueError("Unsupported image format. Only JPEG and PNG are supported")
        output_format = img.format

        draw = ImageDraw.Draw(img)
        draw.rectangle(bbox, outline=color, width=3)

        with io.BytesIO() as output:
            img.save(output, format=output_format)
            return output.getvalue()


async def download_file_from_url(url: str) -> Optional[bytes]:
    """Загружает файл по URL и возвращает его содержимое как bytes"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    return await response.read()
                return None
    except Exception as e:
        logger.error(f"Error downloading file from URL: {str(e)}")
        return None


def generate_presigned_url(bucket_name, object_name, host: str = None, minio: Minio = None):

    if not minio:
        current_minio_host = select_minio_host(host)

        if MINIO_USE_INTERNAL_PROXY:
            proxy = urllib3.ProxyManager(
                proxy_url=f"http://{current_minio_host}:{MINIO_PORT}",
                timeout=urllib3.Timeout(connect=5, read=60),
                cert_reqs="CERT_NONE",
            )
        http_client = proxy if MINIO_USE_INTERNAL_PROXY else None

        minioClient = Minio(
            endpoint=urlparse(MINIO_PUBLIC_URL).netloc or f"{current_minio_host}:{MINIO_PORT}",
            access_key=MINIO_ACCESS_KEY,
            secret_key=MINIO_SECRET_KEY,
            secure=MINIO_SECURE,
            http_client=http_client
        )
    else:
        minioClient = minio

    presigned_url = minioClient.presigned_get_object(bucket_name, object_name, expires=timedelta(days=1))
    return presigned_url


def save_image_to_minio(minioClient: Minio, image_data, bucket_name, object_name):
    img_data = base64.b64decode(correct_base64_padding(image_data))
    minioClient.put_object(
        bucket_name, object_name, io.BytesIO(img_data),
        length=len(img_data),
        content_type='image/png'
    )


def process_image(image_file):
    try:
        with Image.open(image_file) as img:
            if img.format not in ["JPEG", "PNG"]:
                raise ValueError("Unsupported image format. Only JPEG and PNG are supported")

            if img.format == "PNG":
                img = img.convert("RGB")

            if img.width > 1920:
                aspect_ratio = img.height / img.width
                new_height = int(1920 * aspect_ratio)
                img = img.resize((1920, new_height), Image.LANCZOS)

            output = io.BytesIO()
            img.save(output, format="JPEG")
            return output.getvalue()
    except UnidentifiedImageError:
        raise ValueError("Invalid image format")
    except Exception as e:
        raise ValueError(f"Error processing image: {e}")


def correct_base64_padding(data):
    data = data.replace("data:image/png;base64,", "")
    missing_padding = len(data) % 4
    if missing_padding != 0:
        data += '=' * (4 - missing_padding)
    return data


async def async_request(url: str, params: dict = None,
                        method: str = 'get', timeout: int = 30, to=None):
    tm = aiohttp.ClientTimeout(total=timeout)
    async with aiohttp.ClientSession(timeout=tm) as client:
        try:
            if method == 'post':
                to = 'json' if to is None else to
                async with client.post(url, json=params) as resp:
                    response = await resp.json() if to == 'json' else await resp.text()

            else:
                to = 'text' if to is None else to
                async with client.get(url, params=params) as resp:
                    response = await resp.json() if to == 'json' else await resp.text()
            return resp.status, response

        except aiohttp.ClientConnectorError as er:
            logger.error(er, exc_info=True)
            return None, None
        except aiohttp.ClientError as er:
            logger.error(er, exc_info=True)
            return None, None
        except Exception as er:
            logger.error(er, exc_info=True)
            return None, None


async def download_img(url: str):
    async with aiohttp.ClientSession() as client:
        try:
            async with client.get(url) as resp:
                response = await resp.read()
            return resp.status, response

        except aiohttp.ClientConnectorError:
            return None, None
        except aiohttp.ClientError:
            return None, None
        except Exception:
            return None, None
