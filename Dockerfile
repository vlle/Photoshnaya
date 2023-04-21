# syntax=docker/dockerfile:1
FROM python:3.11-buster
COPY . .
RUN pip install --no-cache-dir -r requirements.txt
CMD ["python", "bot.py"]

