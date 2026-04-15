# Версия совпадает с clicker/src/codegen/node_runner (playwright 1.58.x): один набор браузеров для VLM и MCP/Code.
FROM mcr.microsoft.com/playwright/python:v1.58.0-jammy

ENV LANG=C.UTF-8
ENV COLUMNS=5000
ENV TERM=xterm-color
ENV PYTHONPATH=/app
# Единый каталог для Python и Node Playwright; заполняется при docker build (не при старте контейнера).
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

# В MCR /usr/bin/python3 часто без пакета playwright; ставим 1.58.x как в node_runner, затем браузеры и chmod драйвера.
RUN apt-get -y update && apt-get -y install dos2unix python3-pip && \
    python3 -m pip install --no-cache-dir --upgrade pip && \
    python3 -m pip install --no-cache-dir "playwright==1.58.0" && \
    mkdir -p /ms-playwright && python3 -m playwright install chrome firefox && \
    python3 -c "import pathlib, playwright, subprocess; r=pathlib.Path(playwright.__file__).resolve().parent; [subprocess.run(['dos2unix', str(f)], check=True) for f in (r / 'driver/package/bin').glob('*.sh')]; subprocess.run(['chmod', '+x', str(r / 'driver/node')], check=True); [subprocess.run(['chmod', '+x', str(f)], check=True) for f in (r / 'driver/package/bin').iterdir()]" && \
    apt-get -y purge dos2unix && apt-get -y autoremove -y && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN apt-get -y update && apt-get -y -f install apt-utils dialog
RUN apt-get -y update && apt-get -y install git bash mc procps python3-pip libsndfile1 libsndfile1-dev libgtk-3-0 libx11-xcb1 libasound2 ffmpeg

COPY clicker/requirements.txt /app/

RUN python3 -m pip install --no-cache-dir --upgrade pip && \
    python3 -m pip install --no-cache-dir -r requirements.txt

# Node 20 via NodeSource APT repo (pinned keyring, no pipe-to-bash).
RUN apt-get update && apt-get install -y ca-certificates curl gnupg && \
    mkdir -p /etc/apt/keyrings && \
    curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg && \
    echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_20.x nodistro main" > /etc/apt/sources.list.d/nodesource.list && \
    apt-get update && apt-get install -y nodejs && \
    apt-get purge -y curl gnupg && apt-get autoremove -y && rm -rf /var/lib/apt/lists/*

COPY clicker/src/codegen/node_runner/package.json clicker/src/codegen/node_runner/package-lock.json /app/codegen/node_runner/
# postinstall (patch browser_run_code: expect в VM) — скрипт нужен до npm ci.
COPY clicker/src/codegen/node_runner/scripts/patch-mcp-runexpect.cjs /app/codegen/node_runner/scripts/patch-mcp-runexpect.cjs

# Тот же PLAYWRIGHT_BROWSERS_PATH и та же версия Playwright (1.58), что у python — отдельный npx install не нужен.
RUN cd /app/codegen/node_runner && npm ci && \
    node -e "require('fs').accessSync(require('playwright').firefox.executablePath())"

COPY clicker/src/ /app/

COPY clicker/docker-entrypoint.sh /docker-entrypoint.sh
# Windows CRLF ломает shebang в Linux (exec: no such file or directory).
RUN sed -i 's/\r$//' /docker-entrypoint.sh && chmod +x /docker-entrypoint.sh

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["python3", "./main.py"]