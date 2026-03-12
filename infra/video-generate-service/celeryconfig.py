import logging
import os
import sys

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
DB_NAME = os.getenv("DB_NAME", "")
DB_USER = os.getenv("DB_USER", "")
DB_PASS = os.getenv("DB_PASS", "")

MINIO_HOST = os.environ.get("MINIO_HOST", "minio")
MINIO_PORT = os.environ.get("MINIO_PORT", "9000")
MINIO_ACCESS_KEY = os.environ.get("MINIO_ACCESS_KEY", "")
MINIO_SECRET_KEY = os.environ.get("MINIO_SECRET_KEY", "")
MINIO_SECURE = int(os.environ.get("MINIO_SECURE", "1"))

RABBIT_HOST = os.getenv("RABBIT_HOST", "localhost")
RABBIT_PORT = int(os.getenv("RABBIT_PORT", "5672"))
RABBIT_USER = os.getenv("RABBIT_USER", "")
RABBIT_PASSWORD = os.getenv("RABBIT_PASSWORD", "")


broker_url = f'amqp://{RABBIT_USER}:{RABBIT_PASSWORD}@{RABBIT_HOST}:{RABBIT_PORT}'


task_serializer = 'json'
result_serializer = 'json'
accept_content = ['application/json', 'application/data']
result_accept_content = ['application/json', 'application/data']
timezone = 'UTC'
enable_utc = True


task_queues = (
    Queue('video_generation',
          Exchange('video-generate-service'),
          routing_key='video_generation'),
)
