#!/usr/bin/env bash

set -euo pipefail

: "${DEPLOY_PATH:?DEPLOY_PATH is required}"
: "${IMAGE_REPOSITORY:?IMAGE_REPOSITORY is required}"
: "${IMAGE_TAG:?IMAGE_TAG is required}"
: "${GO_API_IMAGE_REPOSITORY:?GO_API_IMAGE_REPOSITORY is required}"

GO_API_IMAGE_TAG="${GO_API_IMAGE_TAG:-$IMAGE_TAG}"

if docker compose version >/dev/null 2>&1; then
  COMPOSE_CMD=(docker compose)
elif command -v docker-compose >/dev/null 2>&1; then
  COMPOSE_CMD=(docker-compose)
else
  echo "docker compose is not installed on the remote host" >&2
  exit 1
fi

wait_for_service_health() {
  local service="$1"
  local container_id=""
  local health_status=""

  for _ in $(seq 1 30); do
    container_id="$("${COMPOSE_CMD[@]}" ps -q "$service")"
    if [[ -n "$container_id" ]]; then
      health_status="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}starting{{end}}' "$container_id")"
      if [[ "$health_status" == "healthy" ]]; then
        return 0
      fi
    fi
    sleep 2
  done

  echo "service $service did not become healthy" >&2
  return 1
}

cd "${DEPLOY_PATH}"

export IMAGE_REPOSITORY
export IMAGE_TAG
export GO_API_IMAGE_REPOSITORY
export GO_API_IMAGE_TAG

"${COMPOSE_CMD[@]}" pull go-api web
"${COMPOSE_CMD[@]}" up -d go-api
wait_for_service_health go-api
"${COMPOSE_CMD[@]}" up -d web
"${COMPOSE_CMD[@]}" ps go-api web
