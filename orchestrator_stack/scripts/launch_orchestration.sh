#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

CONFIG="${CONFIG:-orchestrator_stack/config/orchestrator.example.json}"
TRIALS="${TRIALS:-3}"
PORT="${PORT:-8765}"
EVENT_DIR="${EVENT_DIR:-orchestrator_stack/runtime/visualization}"
PYTHON_BIN="${PYTHON_BIN:-$ROOT/.venv/bin/python}"
OPEN_BROWSER="${OPEN_BROWSER:-1}"
KEEP_DASHBOARD="${KEEP_DASHBOARD:-1}"
LIVE_K8S="${LIVE_K8S:-0}"
MODE="${MODE:-full}"
if [[ "$LIVE_K8S" == "1" && "$MODE" == "fast" ]]; then
  NO_POLICY="${NO_POLICY:-1}"
  NO_TUNE="${NO_TUNE:-1}"
else
  NO_POLICY="${NO_POLICY:-0}"
  NO_TUNE="${NO_TUNE:-0}"
fi
KUBECONFIG_PATH="${KUBECONFIG:-$HOME/.kube/config}"
INTERVAL_SECONDS="${INTERVAL_SECONDS:-10}"
LIVE_MAX_ITERATIONS="${LIVE_MAX_ITERATIONS:-}"
NAMESPACE_PREFIXES="${NAMESPACE_PREFIXES:-test-,default}"
PROMETHEUS_BASE_URL="${PROMETHEUS_BASE_URL:-}"
if [[ "$LIVE_K8S" == "1" ]]; then
  OBSERVABILITY_STACK="${OBSERVABILITY_STACK:-1}"
  PROMETHEUS_PORT_FORWARD="${PROMETHEUS_PORT_FORWARD:-1}"
else
  OBSERVABILITY_STACK="${OBSERVABILITY_STACK:-0}"
  PROMETHEUS_PORT_FORWARD="${PROMETHEUS_PORT_FORWARD:-0}"
fi
PROMETHEUS_PORT="${PROMETHEUS_PORT:-19090}"
OBSERVABILITY_WAIT_TIMEOUT="${OBSERVABILITY_WAIT_TIMEOUT:-180s}"
POWER_CALIBRATION="${POWER_CALIBRATION:-}"
TRACE_OUT="${TRACE_OUT:-orchestrator_stack/runtime/visualization/live_kubernetes_trace.json}"
if [[ "$LIVE_K8S" == "1" ]]; then
  EXERCISE_CLUSTER="${EXERCISE_CLUSTER:-1}"
else
  EXERCISE_CLUSTER="${EXERCISE_CLUSTER:-0}"
fi
EXERCISE_NAMESPACE="${EXERCISE_NAMESPACE:-borg-orchestrator-exercise}"
EXERCISE_INTERVAL_ITERATIONS="${EXERCISE_INTERVAL_ITERATIONS:-3}"
EXERCISE_RANDOMIZE="${EXERCISE_RANDOMIZE:-1}"
EXERCISE_SEED="${EXERCISE_SEED:-}"

if [[ ! -x "$PYTHON_BIN" ]]; then
  PYTHON_BIN="$(command -v python3)"
fi

mkdir -p "$EVENT_DIR" orchestrator_stack/runtime/dashboard
SERVER_LOG="orchestrator_stack/runtime/dashboard/server.log"
RUN_LOG="orchestrator_stack/runtime/dashboard/run.log"
PROMETHEUS_FORWARD_LOG="orchestrator_stack/runtime/dashboard/prometheus-port-forward.log"
RUN_ID="$(date +%Y%m%d%H%M%S)"
GIT_REV="$(git rev-parse --short HEAD 2>/dev/null || echo unknown)"

EXISTING_WRITERS="$(
  pgrep -f "orchestrator_stack/run.py .*--event-dir $EVENT_DIR" 2>/dev/null | while read -r pid; do
    [[ "$pid" != "$$" ]] && echo "$pid"
  done || true
)"
if [[ -n "$EXISTING_WRITERS" ]]; then
  echo "error: another orchestration writer is already using $EVENT_DIR" >&2
  echo "pids: $EXISTING_WRITERS" >&2
  echo "stop the old process first, or set EVENT_DIR to a separate runtime directory" >&2
  exit 2
fi

LOCK_DIR="$EVENT_DIR/.launch.lock"
if ! mkdir "$LOCK_DIR" 2>/dev/null; then
  LOCK_PID="$(cat "$LOCK_DIR/pid" 2>/dev/null || true)"
  if [[ -n "$LOCK_PID" ]] && kill -0 "$LOCK_PID" 2>/dev/null; then
    echo "error: launcher lock is active for $EVENT_DIR by pid $LOCK_PID" >&2
    exit 2
  fi
  rmdir "$LOCK_DIR" 2>/dev/null || true
  mkdir "$LOCK_DIR"
fi
echo "$$" > "$LOCK_DIR/pid"

cleanup() {
  kill "${SERVER_PID:-}" >/dev/null 2>&1 || true
  kill "${PROMETHEUS_PF_PID:-}" >/dev/null 2>&1 || true
  rm -f "$LOCK_DIR/pid" >/dev/null 2>&1 || true
  rmdir "$LOCK_DIR" >/dev/null 2>&1 || true
}
trap cleanup EXIT

wait_for_local_http() {
  local url="$1"
  local timeout_seconds="$2"
  local watched_pid="${3:-}"
  local deadline=$((SECONDS + timeout_seconds))
  while (( SECONDS < deadline )); do
    if [[ -n "$watched_pid" ]] && ! kill -0 "$watched_pid" >/dev/null 2>&1; then
      return 2
    fi
    if "$PYTHON_BIN" -c 'import sys; from urllib.request import urlopen; urlopen(sys.argv[1], timeout=2).read()' "$url" >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
  done
  return 1
}

if [[ "$LIVE_K8S" == "1" && "$OBSERVABILITY_STACK" == "1" ]]; then
  echo "observability: bootstrapping in-cluster Metrics Server, Prometheus, and Node Exporter"
  KUBECONFIG="$KUBECONFIG_PATH" \
  OBSERVABILITY_WAIT_TIMEOUT="$OBSERVABILITY_WAIT_TIMEOUT" \
    ./orchestrator_stack/scripts/bootstrap_observability.sh
fi

if [[ "$LIVE_K8S" == "1" && -z "$PROMETHEUS_BASE_URL" && "$PROMETHEUS_PORT_FORWARD" == "1" ]]; then
  echo "observability: starting Prometheus port-forward on 127.0.0.1:$PROMETHEUS_PORT"
  : > "$PROMETHEUS_FORWARD_LOG"
  kubectl --kubeconfig "$KUBECONFIG_PATH" -n observe port-forward svc/prometheus-server "$PROMETHEUS_PORT:80" > "$PROMETHEUS_FORWARD_LOG" 2>&1 &
  PROMETHEUS_PF_PID=$!
  if ! wait_for_local_http "http://127.0.0.1:$PROMETHEUS_PORT/-/ready" 45 "$PROMETHEUS_PF_PID"; then
    echo "error: Prometheus port-forward did not become ready" >&2
    sed 's/^/prometheus-port-forward: /' "$PROMETHEUS_FORWARD_LOG" >&2 || true
    exit 1
  fi
  PROMETHEUS_BASE_URL="http://127.0.0.1:$PROMETHEUS_PORT"
  echo "observability: Prometheus ready at $PROMETHEUS_BASE_URL"
fi

cat > "$EVENT_DIR/run_manifest.json" <<EOF
{
  "run_id": "$RUN_ID",
  "git_rev": "$GIT_REV",
  "live_k8s": "$LIVE_K8S",
  "mode": "$MODE",
  "config": "$CONFIG",
  "event_dir": "$EVENT_DIR",
  "python": "$PYTHON_BIN",
  "observability_stack": "$OBSERVABILITY_STACK",
  "prometheus_base_url": "$PROMETHEUS_BASE_URL",
  "prometheus_port_forward": "$PROMETHEUS_PORT_FORWARD",
  "prometheus_port": "$PROMETHEUS_PORT"
}
EOF

PYTHONPATH="orchestrator_stack${PYTHONPATH:+:$PYTHONPATH}" "$PYTHON_BIN" -m orchestrator.dashboard_server --port "$PORT" --event-dir "$EVENT_DIR" > "$SERVER_LOG" 2>&1 &
SERVER_PID=$!

URL="http://127.0.0.1:$PORT"
echo "dashboard: $URL"
echo "state: $EVENT_DIR/state.json"
echo "events: $EVENT_DIR/events.jsonl"
echo "run id: $RUN_ID"
echo "git rev: $GIT_REV"
echo "live k8s: $LIVE_K8S"
echo "mode: $MODE"
echo "observability stack: $OBSERVABILITY_STACK"
if [[ -n "$PROMETHEUS_BASE_URL" ]]; then
  echo "prometheus: $PROMETHEUS_BASE_URL"
fi

if [[ "$OPEN_BROWSER" == "1" && "$(uname -s)" == "Darwin" ]]; then
  open "$URL" >/dev/null 2>&1 || true
fi

if [[ "$LIVE_K8S" == "1" ]]; then
  ARGS=(
    orchestrator_stack/run.py live-kubernetes-run
    --config "$CONFIG"
    --event-dir "$EVENT_DIR"
    --kubeconfig "$KUBECONFIG_PATH"
    --interval-seconds "$INTERVAL_SECONDS"
    --namespace-prefixes "$NAMESPACE_PREFIXES"
    --trace-out "$TRACE_OUT"
    --trials "$TRIALS"
  )
  if [[ -n "$LIVE_MAX_ITERATIONS" ]]; then ARGS+=(--max-iterations "$LIVE_MAX_ITERATIONS"); fi
  if [[ -n "$PROMETHEUS_BASE_URL" ]]; then ARGS+=(--prometheus-base-url "$PROMETHEUS_BASE_URL"); fi
  if [[ -n "$POWER_CALIBRATION" ]]; then ARGS+=(--power-calibration "$POWER_CALIBRATION"); fi
  if [[ "$EXERCISE_CLUSTER" == "1" ]]; then
    ARGS+=(--exercise-cluster --exercise-namespace "$EXERCISE_NAMESPACE" --exercise-interval-iterations "$EXERCISE_INTERVAL_ITERATIONS")
    if [[ "$EXERCISE_RANDOMIZE" == "1" ]]; then ARGS+=(--exercise-randomize); fi
    if [[ -n "$EXERCISE_SEED" ]]; then ARGS+=(--exercise-seed "$EXERCISE_SEED"); fi
  fi
else
  ARGS=(orchestrator_stack/run.py visualized-run --config "$CONFIG" --trials "$TRIALS" --event-dir "$EVENT_DIR")
fi
if [[ "$NO_POLICY" == "1" ]]; then ARGS+=(--no-policy); fi
if [[ "$NO_TUNE" == "1" ]]; then ARGS+=(--no-tune); fi

PYTHONPATH="orchestrator_stack${PYTHONPATH:+:$PYTHONPATH}" "$PYTHON_BIN" "${ARGS[@]}" 2>&1 | tee "$RUN_LOG"

echo "complete: $URL"
echo "run log: $RUN_LOG"
echo "server log: $SERVER_LOG"
if [[ "$KEEP_DASHBOARD" == "1" ]]; then
  echo "dashboard still running; press Ctrl-C to stop"
  wait "$SERVER_PID"
fi
