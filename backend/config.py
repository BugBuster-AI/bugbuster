import logging
import os
import sys
import redis


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s (%(filename)s:%(funcName)s:%(lineno)d) [%(levelname)s] - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)])

logger = logging.getLogger('portal-backend')
logger.setLevel(logging.INFO)
logging.getLogger("urllib3").setLevel(logging.ERROR)

DOMAIN = os.getenv("DOMAIN", "http://127.0.0.1:3000")

DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "portal")
DB_USER = os.getenv("DB_USER", "")
DB_PASS = os.getenv("DB_PASS", "")

DB_URL = f"postgresql+asyncpg://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

RABBIT_HOST = os.getenv("RABBIT_HOST", "localhost")
RABBIT_PORT = int(os.getenv("RABBIT_PORT", "5672"))
RABBIT_USER = os.getenv("RABBIT_USER", "")
RABBIT_PASSWORD = os.getenv("RABBIT_PASSWORD", "")
RABBIT_PREFIX = os.getenv("RABBIT_PREFIX", "prod")

BROKER_URL = f'amqp://{RABBIT_USER}:{RABBIT_PASSWORD}@{RABBIT_HOST}:{RABBIT_PORT}'

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "")
REDIS_PREFIX = os.getenv("REDIS_PREFIX", "prod")

REDIS_URL = f'redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/0'

redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, password=REDIS_PASSWORD)

UVICORN_PORT = int(os.getenv("UVICORN_PORT", "7665"))

# openssl rand -hex 32
SECRET_KEY = os.getenv("SECRET_KEY", "")
SECRET_KEY_API = os.getenv("SECRET_KEY_API", "")
SECRET_KEY_INVITING = os.getenv("SECRET_KEY_INVITING", "")
# do not change after initial generation and insertion into DB
TOKEN_HASH_SECRET = ""

ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "180"))

MINIO_HOST = os.environ.get("MINIO_HOST", "127.0.0.1")
MINIO_PUBLIC_URL = os.environ.get("MINIO_PUBLIC_URL", "")
MINIO_PORT = os.environ.get("MINIO_PORT", "9000")
MINIO_ACCESS_KEY = os.environ.get("MINIO_ACCESS_KEY", "")
MINIO_SECRET_KEY = os.environ.get("MINIO_SECRET_KEY", "")
MINIO_SECURE = int(os.environ.get("MINIO_SECURE", "0"))
MINIO_USE_INTERNAL_PROXY = int(os.environ.get("MINIO_USE_INTERNAL_PROXY", "1"))

CLICKER_IP = os.environ.get("CLICKER_IP", "127.0.0.1")
CLICKER_PORT = os.environ.get("CLICKER_PORT", "7660")

MAX_CONCURRENT_TASKS_DEFAULT = int(os.environ.get("MAX_CONCURRENT_TASKS_DEFAULT", "1"))

USE_TELEGRAMM = int(os.environ.get("USE_TELEGRAMM", "0"))
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
TOPIC_ID = os.getenv("TOPIC_ID", "")

SMTP_CONFIG = {
    "enabled": int(os.environ.get("SMTP_ENABLED", "0")),
    "server": os.environ.get("SMTP_SERVER", "smtp.yandex.ru"),
    "port": int(os.environ.get("SMTP_PORT") or "587"),
    "username": os.environ.get("SMTP_USERNAME", ""),
    "password": os.environ.get("SMTP_PASSWORD", "")
}

TRACE_VIEWER_HOST = os.getenv("TRACE_VIEWER_HOST", "http://localhost:3209")
