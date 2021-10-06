# syntax=docker/dockerfile:1

FROM python:3.8-slim
WORKDIR /mackbot

COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY GameParamsPruned_0.json GameParamsPruned_0.json
COPY GameParamsPruned_1.json GameParamsPruned_1.json
COPY command_list.json command_list.json
COPY config.json config.json
COPY help_command_strings.json help_command_strings.json
COPY mackbot.py mackbot.py
COPY ship_name_dict.json ship_name_dict.json
COPY skill_list.json skill_list.json

CMD ["python3", "mackbot.py"]
