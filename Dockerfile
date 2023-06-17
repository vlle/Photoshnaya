# syntax=docker/dockerfile:1
FROM python:3.11-buster
WORKDIR /code
COPY ./requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir --upgrade  -r requirements.txt
COPY ./app /code/app
CMD ["python", "app/bot.py"]
