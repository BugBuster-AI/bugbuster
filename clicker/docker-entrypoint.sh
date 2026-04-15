#!/bin/sh
# Браузеры ставятся в образе (Dockerfile RUN). Здесь только env и exec — без apt/playwright install при старте.
set -e
export PLAYWRIGHT_BROWSERS_PATH="${PLAYWRIGHT_BROWSERS_PATH:-/ms-playwright}"
exec "$@"
