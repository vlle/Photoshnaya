#!/usr/bin/env bash

set -euo pipefail

: "${DEPLOY_PATH:?DEPLOY_PATH is required}"
: "${IMAGE_REPOSITORY:?IMAGE_REPOSITORY is required}"
: "${IMAGE_TAG:?IMAGE_TAG is required}"

if docker compose version >/dev/null 2>&1; then
  COMPOSE_CMD=(docker compose)
elif command -v docker-compose >/dev/null 2>&1; then
  COMPOSE_CMD=(docker-compose)
else
  echo "docker compose is not installed on the remote host" >&2
  exit 1
fi

cd "${DEPLOY_PATH}"

export IMAGE_REPOSITORY
export IMAGE_TAG

"${COMPOSE_CMD[@]}" pull web
"${COMPOSE_CMD[@]}" up -d web
"${COMPOSE_CMD[@]}" ps
