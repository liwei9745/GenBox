#!/usr/bin/env bash
set -euo pipefail

: "${RELEASE_IMAGE_ID:?RELEASE_IMAGE_ID is required}"
: "${GITHUB_RUN_ID:?GITHUB_RUN_ID is required}"
: "${GITHUB_RUN_ATTEMPT:?GITHUB_RUN_ATTEMPT is required}"

smoke_timeout_seconds="${GENBOX_SMOKE_TIMEOUT_SECONDS:-90}"
max_delay_seconds="${GENBOX_SMOKE_MAX_DELAY_SECONDS:-5}"
if [[ ! "$smoke_timeout_seconds" =~ ^[1-9][0-9]*$ ]]; then
  echo "GENBOX_SMOKE_TIMEOUT_SECONDS must be a positive integer" >&2
  exit 2
fi
if [[ ! "$max_delay_seconds" =~ ^[1-9][0-9]*$ ]]; then
  echo "GENBOX_SMOKE_MAX_DELAY_SECONDS must be a positive integer" >&2
  exit 2
fi

owner_label_key="com.genbox.release-smoke-owner"
nonce="$(openssl rand -hex 8)"
owner_label_value="${GITHUB_RUN_ID}:${GITHUB_RUN_ATTEMPT}:${nonce}"
container_name="genbox-release-smoke-${GITHUB_RUN_ID}-${GITHUB_RUN_ATTEMPT}-${nonce}"
container_id=""
container_created=0

cleanup() {
  local status=$?
  local current_id=""
  local current_owner=""
  trap - EXIT

  if [[ "$container_created" == "1" && -n "$container_id" ]]; then
    current_id="$(docker inspect --format '{{.Id}}' "$container_id" 2>/dev/null || true)"
    current_owner="$(docker inspect --format '{{ index .Config.Labels "com.genbox.release-smoke-owner" }}' "$container_id" 2>/dev/null || true)"
    if [[ "$current_id" == "$container_id" && "$current_owner" == "$owner_label_value" ]]; then
      if docker rm -f "$container_id" >/dev/null 2>&1; then
        echo "removed owned smoke container id=$container_id"
      else
        echo "failed to remove owned smoke container id=$container_id" >&2
        status=1
      fi
    else
      echo "refusing to remove smoke container: ownership verification failed" >&2
      status=1
    fi
  fi

  return "$status"
}
trap cleanup EXIT

admin_key="$(openssl rand -hex 32)"
echo "::add-mask::$admin_key"
container_id="$(docker run --detach --name "$container_name" \
  --label "${owner_label_key}=${owner_label_value}" \
  --env APP_MODE=prod \
  --env GENBOX_PORT=8891 \
  --env ADMIN_KEY="$admin_key" \
  --publish 127.0.0.1::8891 \
  "$RELEASE_IMAGE_ID")"
container_created=1

test -n "$container_id"
test "$(docker inspect --format '{{.Id}}' "$container_id")" = "$container_id"
test "$(docker inspect --format '{{.Image}}' "$container_id")" = "$RELEASE_IMAGE_ID"
test "$(docker inspect --format '{{ index .Config.Labels "com.genbox.release-smoke-owner" }}' "$container_id")" = "$owner_label_value"
host_port="$(docker port "$container_id" 8891/tcp | sed -n 's/^127\.0\.0\.1:\([0-9][0-9]*\)$/\1/p' | head -n 1)"
test -n "$host_port"

deadline=$(( $(date +%s) + smoke_timeout_seconds ))
attempt=0
ready=0
while (( $(date +%s) < deadline )); do
  attempt=$((attempt + 1))
  state="$(docker inspect --format '{{.State.Status}}' "$container_id" 2>/dev/null || echo missing)"
  running="$(docker inspect --format '{{.State.Running}}' "$container_id" 2>/dev/null || echo false)"
  health="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "$container_id" 2>/dev/null || echo missing)"
  echo "readiness attempt=$attempt state=$state running=$running health=$health"
  if [[ "$running" != "true" || "$health" == "unhealthy" ]]; then
    break
  fi
  if response="$(curl --fail --silent --show-error \
      --connect-timeout 2 --max-time 5 \
      "http://127.0.0.1:${host_port}/api/setup/status" 2>/dev/null)" && \
     printf '%s' "$response" | python -c \
      "import json, sys; data = json.load(sys.stdin); assert data.get('app_mode') == 'prod'; assert data.get('auth_required') is True"; then
    ready=1
    break
  fi
  delay=$((attempt < max_delay_seconds ? attempt : max_delay_seconds))
  sleep "$delay"
done

if [[ "$ready" != "1" ]]; then
  state="$(docker inspect --format '{{.State.Status}}' "$container_id" 2>/dev/null || echo missing)"
  running="$(docker inspect --format '{{.State.Running}}' "$container_id" 2>/dev/null || echo false)"
  exit_code="$(docker inspect --format '{{.State.ExitCode}}' "$container_id" 2>/dev/null || echo missing)"
  health="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "$container_id" 2>/dev/null || echo missing)"
  echo "HTTP smoke failed after $attempt attempts: state=$state running=$running exit_code=$exit_code health=$health"
  echo "Last 200 credential-redacted container log lines:"
  (docker logs --tail 200 "$container_id" 2>&1 || true) | sed -E \
    -e "s/${admin_key}/[REDACTED]/g" \
    -e 's/(Bearer )[A-Za-z0-9._~+\/=:-]+/\1[REDACTED]/g' \
    -e 's#(https?://)[^/@[:space:]]+:[^/@[:space:]]+@#\1[REDACTED]@#g' \
    -e 's/([?&](api[_-]?key|key|token|access[_-]?token|password|signature|sig)=)[^&[:space:]]+/\1[REDACTED]/Ig' \
    -e "s/([\"']?(admin[_-]?key|genbox[_-]?admin[_-]?key|api[_-]?key|access[_-]?token|refresh[_-]?token|token|password|secret|management[_-]?key|push[_-]?key)[\"']?[=:][[:space:]]*[\"']?)[^\"',}&[:space:]]+/\1[REDACTED]/Ig" \
    -e 's/(sk|rk|pk)-[A-Za-z0-9._-]{8,}/[REDACTED]/g'
  exit 1
fi

echo "HTTP smoke passed after $attempt attempts for image $RELEASE_IMAGE_ID"
