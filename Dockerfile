# syntax=docker/dockerfile:1

FROM python:3.9
WORKDIR /mackbot

RUN apt-get update && apt-get install -y

COPY requirements.txt requirements.txt
RUN pip install --upgrade pip
RUN pip install --no-cache-dir --timeout 60 -r requirements.txt

COPY GameParamsPruned_*.json GameParamsPruned_*.json
COPY data .
COPY scripts .
COPY data/live_config.json data/
COPY mackbot.py .

CMD ["python3", "mackbot.py"]
