# syntax=docker/dockerfile:1
FROM python:3.11-buster
COPY . .
CMD ["bash", "docker_script.sh"]
