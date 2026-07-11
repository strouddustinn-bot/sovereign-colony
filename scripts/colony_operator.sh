#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

readonly PROJECT_ROOT="/home/dstroud/Projects/sovereign-colony"
readonly STATE_ROOT="/home/dstroud/.local/state/sovereign-colony"
readonly DB_CONTAINER="/state/experiment-001.db"
readonly PYTHON_IMAGE="python:3.13-slim"

mkdir -p "${STATE_ROOT}"

readonly -a RUNNER=(
  docker run --rm
  --network none
  --read-only
  --cap-drop ALL
  --security-opt no-new-privileges
  --pids-limit 64
  --memory 256m
  --cpus 0.5
  --user "$(id -u):$(id -g)"
  --tmpfs /tmp:rw,noexec,nosuid,size=64m
  -e PYTHONDONTWRITEBYTECODE=1
  -v "${PROJECT_ROOT}:/workspace:ro"
  -v "${STATE_ROOT}:/state:rw"
  -w /workspace
  "${PYTHON_IMAGE}"
  python -m sovereign_colony.cli
)

command="${1:-status}"
case "${command}" in
  init)
    "${RUNNER[@]}" init --db "${DB_CONTAINER}" --seed 20260711
    ;;
  status|pause|resume)
    "${RUNNER[@]}" "${command}" --db "${DB_CONTAINER}"
    ;;
  emergency-pause)
    reason="${2:-}"
    if [[ -z "${reason}" ]]; then
      printf '%s\n' 'Usage: colony_operator.sh emergency-pause "reason"' >&2
      exit 2
    fi
    "${RUNNER[@]}" emergency-pause --db "${DB_CONTAINER}" --reason "${reason}"
    ;;
  *)
    printf 'Unknown command: %s\n' "${command}" >&2
    exit 2
    ;;
esac
