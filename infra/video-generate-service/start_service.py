import os

from celery import Celery

from celeryconfig import logger
from workers.worker_generate_video import generate_video_from_trace

if os.name == 'nt':
    os.environ.setdefault('FORKED_BY_MULTIPROCESSING', '1')

app = Celery()
app.config_from_object('celeryconfig')


@app.task(name='video_generation')
def run_single_case_queue(**kwargs):
    try:
        run_id = None
        trace_file_path = None

        db_name = kwargs['db_name']
        trace_file_path = kwargs['trace_file_path']
        run_id = kwargs['run_id']
        logger.info(f"input task data: {db_name=} | {trace_file_path=} {run_id=}")

        generate_video_from_trace(db_name, trace_file_path, run_id)

    except Exception as er:
        logger.error(f"Error in task {run_id} for {trace_file_path}: {er}", exc_info=True)


# ENTRYPOINT [
#   "celery", "-A", "start_service", "worker",
#   "-l", "INFO",
#   "-n", "video-generate-service@%h",
#   "--pool=processes",           # Важно! Используем процессы, а не потоки
#   "--concurrency=10",          # Фиксированное число процессов (10 на инстанс)
#   "--max-tasks-per-child=20",  # Перезапуск каждые 20 задач (сброс памяти)
#   "--prefetch-multiplier=1",   # Честное распределение задач (1:1)
#   "--task-acks-late=True",     # Подтверждать задачи после выполнения
#   "--without-gossip",          # Убрать лишний сетевой трафик
#   "--without-mingle",          # Убрать синхронизацию воркеров
#   "-Q", "video_generation"     # Явно указать очередь (если есть)
# ]

# celery -A start_service worker --loglevel=info --autoscale=4,2 --max-tasks-per-child=50 --hostname=video_worker@%h
