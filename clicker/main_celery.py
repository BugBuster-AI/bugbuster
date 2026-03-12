import os
import sys

ROOT = os.path.dirname(__file__)
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from src.main_celery import app  # noqa: E402

if __name__ == "__main__":
    worker = app.Worker(loglevel="INFO", pool="solo", concurrency=1)
    worker.start()
