import logging
import os
import sys

import redis
from dotenv import load_dotenv
from kombu import Exchange, Queue

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s (%(filename)s:%(funcName)s:%(lineno)d) [%(levelname)s] - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)])

logger = logging.getLogger('clicker')
logger.setLevel(logging.INFO)
logging.getLogger("urllib3").setLevel(logging.ERROR)

DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "portal")
DB_USER = os.getenv("DB_USER", "")
DB_PASS = os.getenv("DB_PASS", "")

MINIO_HOST = os.environ.get("MINIO_HOST", "127.0.0.1")
MINIO_PORT = os.environ.get("MINIO_PORT", "9000")
MINIO_ACCESS_KEY = os.environ.get("MINIO_ACCESS_KEY", "")
MINIO_SECRET_KEY = os.environ.get("MINIO_SECRET_KEY", "")
MINIO_SECURE = int(os.environ.get("MINIO_SECURE", "0"))

RABBIT_HOST = os.getenv("RABBIT_HOST", "localhost")
RABBIT_PORT = int(os.getenv("RABBIT_PORT", "5672"))
RABBIT_USER = os.getenv("RABBIT_USER", "")
RABBIT_PASSWORD = os.getenv("RABBIT_PASSWORD", "")
RABBIT_PREFIX = os.getenv("RABBIT_PREFIX", "prod")

broker_url = f'amqp://{RABBIT_USER}:{RABBIT_PASSWORD}@{RABBIT_HOST}:{RABBIT_PORT}'

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "")

redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, password=REDIS_PASSWORD)
# result_backend = f'redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/0'
server_ident = os.getenv('SERVER_IDENT', 'default_id')


task_serializer = 'json'
result_serializer = 'json'
accept_content = ['application/json', 'application/data']
result_accept_content = ['application/json', 'application/data']
timezone = 'UTC'
enable_utc = True

MAX_USER_LIMIT_CONCURRENT_TASKS_DEFAULT = 1

task_queues = (
    Queue(f'{RABBIT_PREFIX}_celery.portal-clicker.run_single_case_queue',
          Exchange(f'{RABBIT_PREFIX}_portal-clicker'),
          routing_key=f'{RABBIT_PREFIX}_celery.portal-clicker.run_single_case_queue'),
)

LANGFUSE_HOST = os.getenv("LANGFUSE_HOST", "http://dlserver:3300")
LANGFUSE_PUBLIC_KEY = os.getenv("LANGFUSE_PUBLIC_KEY", "")
LANGFUSE_SECRET_KEY = os.getenv("LANGFUSE_SECRET_KEY", "")
