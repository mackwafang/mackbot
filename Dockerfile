# syntax=docker/dockerfile:1

FROM python:3.8
WORKDIR /mackbot

RUN apt-get update && apt-get install -y
COPY requirements.txt requirements.txt
RUN pip install --upgrade pip
RUN pip install --no-cache-dir --timeout 60 -r requirements.txt

COPY GameParamsPruned_0.json GameParamsPruned_0.json
COPY GameParamsPruned_1.json GameParamsPruned_1.json
COPY GameParamsPruned_2.json GameParamsPruned_2.json
COPY command_list.json command_list.json
COPY config.json config.json
COPY help_command_strings.json help_command_strings.json
COPY mackbot.py mackbot.py
COPY ship_name_dict.json ship_name_dict.json
COPY skill_list.json skill_list.json

CMD ["python3", "mackbot.py"]
