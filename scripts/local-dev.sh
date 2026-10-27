#!/bin/sh
# Explicit project prevents accidentally restarting a different checkout/DB.
set -eu
repo_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$repo_dir"

compose_legacy=false
if docker compose version >/dev/null 2>&1; then
  :
elif command -v docker-compose >/dev/null 2>&1; then
  compose_legacy=true
else
  echo "Instale Docker Compose para iniciar o ambiente local." >&2
  exit 1
fi

compose() {
  if [ "$compose_legacy" = true ]; then
    docker-compose -p verify-reviewed-local -f "$repo_dir/docker-compose.local.yml" "$@"
  else
    docker compose -p verify-reviewed-local -f "$repo_dir/docker-compose.local.yml" "$@"
  fi
}

action=${1:-status}
if [ "$#" -gt 0 ]; then shift; fi
case "$action" in
  up)
    if [ ! -f backend/.env ]; then
      echo "Crie backend/.env nesta cópia revisada; consulte docs/GEMINI-LOCAL-2026-10-27.md." >&2
      exit 1
    fi
    if [ "$compose_legacy" = true ]; then
      # Compose v1 recreation crashes on current Docker Engine (ContainerConfig).
      # Remove only this project's two runtime containers; both data/dependencies
      # use named volumes. Never remove volumes, the old project or its DB.
      compose stop backend frontend
      compose rm -f backend frontend
      compose up -d "$@"
    else
      compose up -d --force-recreate "$@"
    fi
    echo "Aplicação local: http://127.0.0.1:5176 — backend: http://127.0.0.1:8016/health"
    ;;
  status) compose ps "$@" ;;
  down)
    if [ "$#" -ne 0 ]; then
      echo "Use down sem opções. O banco local será preservado." >&2
      exit 1
    fi
    compose down
    ;;
  *)
    echo "Uso: sh scripts/local-dev.sh up [--build | --no-build] | status | down" >&2
    exit 1
    ;;
esac
