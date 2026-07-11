#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

readonly PROJECT_ROOT="/home/dstroud/Projects/sovereign-colony"
readonly STATE_ROOT="/home/dstroud/.local/state/sovereign-colony"
readonly DB_CONTAINER="/state/experiment-001.db"
readonly MODEL="qwen2.5:1.5b"
readonly PYTHON_IMAGE="python:3.13-slim"
readonly LOCK_FILE="${STATE_ROOT}/hourly-turn.lock"

mkdir -p "${STATE_ROOT}/batches"
for required_command in basename curl docker flock jq logger mktemp realpath; do
  if ! command -v "${required_command}" >/dev/null 2>&1; then
    printf 'Missing required command: %s\n' "${required_command}" >&2
    exit 127
  fi
done
exec 9>"${LOCK_FILE}"
if ! flock -n 9; then
  printf '%s\n' 'Sovereign Colony turn already running; skipped.'
  exit 0
fi

readonly HOST_UID="$(id -u)"
readonly HOST_GID="$(id -g)"
readonly -a DOCKER_BASE=(
  docker run --rm
  --network none
  --read-only
  --cap-drop ALL
  --security-opt no-new-privileges
  --pids-limit 64
  --memory 256m
  --cpus 0.5
  --user "${HOST_UID}:${HOST_GID}"
  --tmpfs /tmp:rw,noexec,nosuid,size=64m
  -e PYTHONDONTWRITEBYTECODE=1
  -v "${PROJECT_ROOT}:/workspace:ro"
  -v "${STATE_ROOT}:/state:rw"
  -w /workspace
  "${PYTHON_IMAGE}"
  python -m sovereign_colony.cli
)

run_colony() {
  "${DOCKER_BASE[@]}" "$@"
}

if ! curl -fsS --max-time 5 http://127.0.0.1:11434/api/tags \
  | jq -e --arg model "${MODEL}" 'any(.models[]; .name == $model)' >/dev/null; then
  printf 'Local Ollama model unavailable: %s\n' "${MODEL}" >&2
  exit 1
fi

status_json="$(run_colony status --db "${DB_CONTAINER}")"
if [[ "$(jq -r '.paused' <<<"${status_json}")" == "true" ]]; then
  printf '%s\n' 'Sovereign Colony is paused; no turn advanced.'
  exit 0
fi

current_day="$(jq -r '.colony_day' <<<"${status_json}")"
target_day="$((current_day + 1))"
printf -v day_label '%03d' "${target_day}"
readonly batch_host="${STATE_ROOT}/batches/day-${day_label}"
readonly batch_container="/state/batches/day-${day_label}"

run_colony prepare \
  --db "${DB_CONTAINER}" \
  --batch-root /state/batches \
  --model "${MODEL}" >/dev/null

if [[ -L "${batch_host}/responses" ]]; then
  printf '%s\n' 'Unsafe symlinked response directory rejected.' >&2
  exit 1
fi
mkdir -p "${batch_host}/responses"
readonly response_root="$(realpath "${batch_host}/responses")"
if [[ "${response_root}" != "${batch_host}/responses" ]]; then
  printf '%s\n' 'Response directory escaped its batch boundary.' >&2
  exit 1
fi
citizen_index=0
while IFS= read -r citizen_id; do
  citizen_index="$((citizen_index + 1))"
  prompt_file="${batch_host}/requests/${citizen_id}.txt"
  response_file="${batch_host}/responses/${citizen_id}.json"
  temporary_file="$(mktemp --tmpdir="${response_root}" ".${citizen_id}.tmp.XXXXXX")"
  temporary_container="${batch_container}/responses/$(basename "${temporary_file}")"
  validated=false

  for attempt in 1 2 3; do
    inference_seed="$((20260711 + target_day * 1000 + citizen_index * 10 + attempt))"
    if jq -n \
      --arg model "${MODEL}" \
      --rawfile prompt "${prompt_file}" \
      --slurpfile format "${PROJECT_ROOT}/schemas/citizen-decision.schema.json" \
      --argjson seed "${inference_seed}" \
      '{model:$model,prompt:$prompt,stream:false,format:$format[0],options:{temperature:0.8,seed:$seed,num_predict:384}}' \
      | curl -fsS --max-time 240 \
          http://127.0.0.1:11434/api/generate \
          -H 'Content-Type: application/json' \
          --data-binary @- \
      | jq -er '.response' >"${temporary_file}"; then
      if run_colony validate-response \
        --file "${temporary_container}" >/dev/null 2>&1; then
        chmod 600 "${temporary_file}"
        mv -f "${temporary_file}" "${response_file}"
        validated=true
        break
      fi
    fi
    printf 'Invalid model response for %s (attempt %s/3).\n' "${citizen_id}" "${attempt}" >&2
  done

  if [[ "${validated}" != "true" ]]; then
    rm -f "${temporary_file}"
    printf 'Failed closed: no state mutation; citizen %s never produced a valid decision.\n' "${citizen_id}" >&2
    exit 1
  fi
done < <(jq -r '.citizens[]' "${batch_host}/manifest.json")

report="$(run_colony apply --db "${DB_CONTAINER}" --batch-dir "${batch_container}")"
printf '%s\n' "${report}"
logger --tag sovereign-colony "advanced to colony day ${target_day}; state_digest=$(jq -r '.state_digest' <<<"${report}")"
