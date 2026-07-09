#!/usr/bin/env bash
set -euo pipefail

if ! command -v docker >/dev/null 2>&1; then
  echo "Tika check skipped: docker is not installed" >&2
  exit 0
fi

image="${TIKA_DOCKER_IMAGE:-apache/tika:3.1.0.0-full}"
container="resume-builder-tika-$$"
port_file="$(mktemp)"

cleanup() {
  docker rm -f "$container" >/dev/null 2>&1 || true
  rm -f "$port_file"
}
trap cleanup EXIT

docker run --rm -d --name "$container" -p 127.0.0.1::9998 "$image" >/dev/null
docker port "$container" 9998/tcp | sed 's/.*://' > "$port_file"
port="$(cat "$port_file")"

mise exec -- uv run python scripts/check_tika.py --server-url "http://127.0.0.1:${port}"
