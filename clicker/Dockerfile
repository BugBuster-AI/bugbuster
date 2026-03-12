FROM mcr.microsoft.com/playwright/python:v1.49.0-jammy

ENV LANG=C.UTF-8
ENV COLUMNS=5000
ENV TERM=xterm-color
ENV PYTHONPATH=/app


COPY infra/playwright-custom /tmp/playwright-custom

RUN python -m pip uninstall -y playwright || true && \
    python -m pip install /tmp/playwright-custom

RUN apt-get -y update && apt-get -y install dos2unix && \
    dos2unix /usr/local/lib/python3.10/dist-packages/playwright/driver/package/bin/*.sh || true && \
    chmod +x /usr/local/lib/python3.10/dist-packages/playwright/driver/node && \
    chmod -R +x /usr/local/lib/python3.10/dist-packages/playwright/driver/package && \
    python -m playwright install chrome && \
    apt-get -y purge dos2unix && apt-get -y autoremove && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN apt-get -y update && apt-get -y -f install apt-utils dialog
RUN apt-get -y update && apt-get -y install git bash mc procps python3-pip libsndfile1 libsndfile1-dev libgtk-3-0 libx11-xcb1 libasound2 ffmpeg


COPY clicker/requirements.txt /app/

RUN python -m pip install --no-cache-dir --upgrade pip && \
    python -m pip install --no-cache-dir -r requirements.txt

COPY clicker/src/ /app/

CMD ["python", "./main.py"]