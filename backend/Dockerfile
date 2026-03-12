FROM python:3.11-slim-bullseye

ENV LANG=C.UTF-8
ENV COLUMNS=5000
ENV TERM=xterm-color

WORKDIR /app

RUN apt-get -y update && apt-get -y -f install apt-utils dialog
RUN apt-get -y update && apt-get -y -f install git bash mc bash procps python3-pip libsndfile1 libsndfile1-dev


COPY requirements.txt /app/
RUN pip install --upgrade pip setuptools wheel
RUN pip install -r requirements.txt

COPY . /app

ENTRYPOINT ["python", "main.py"]
