FROM python:3.11-slim-bullseye

ENV LANG=C.UTF-8
ENV COLUMNS=5000
ENV TERM=xterm-color


WORKDIR /app

RUN apt-get -y update && apt-get -y -f install apt-utils dialog
RUN apt-get -y update && apt-get -y install git bash mc procps python3-pip libsndfile1 libsndfile1-dev libgtk-3-0 libx11-xcb1 libasound2 ffmpeg

COPY . /app

RUN pip install --upgrade pip && pip install -r requirements.txt

ENTRYPOINT ["celery", "-A", "start_service", "worker", "-l", "INFO", "-n", "video-generate-service@%h", "-Q", "video_generation", "--pool=processes", "--max-tasks-per-child=20", "--concurrency=10", "--prefetch-multiplier=1", "--without-gossip", "--without-mingle"]
