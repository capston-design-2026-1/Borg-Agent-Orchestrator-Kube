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
NO_POLICY="${NO_POLICY:-0}"
NO_TUNE="${NO_TUNE:-0}"
KEEP_DASHBOARD="${KEEP_DASHBOARD:-1}"
LIVE_K8S="${LIVE_K8S:-0}"
KUBECONFIG_PATH="${KUBECONFIG:-$HOME/.kube/config}"
INTERVAL_SECONDS="${INTERVAL_SECONDS:-10}"
LIVE_MAX_ITERATIONS="${LIVE_MAX_ITERATIONS:-}"
NAMESPACE_PREFIXES="${NAMESPACE_PREFIXES:-test-,default}"
PROMETHEUS_BASE_URL="${PROMETHEUS_BASE_URL:-}"
POWER_CALIBRATION="${POWER_CALIBRATION:-}"
TRACE_OUT="${TRACE_OUT:-orchestrator_stack/runtime/visualization/live_kubernetes_trace.json}"

if [[ ! -x "$PYTHON_BIN" ]]; then
  PYTHON_BIN="$(command -v python3)"
fi

mkdir -p "$EVENT_DIR" orchestrator_stack/runtime/dashboard
SERVER_LOG="orchestrator_stack/runtime/dashboard/server.log"
RUN_LOG="orchestrator_stack/runtime/dashboard/run.log"

PYTHONPATH="orchestrator_stack${PYTHONPATH:+:$PYTHONPATH}" "$PYTHON_BIN" -m orchestrator.dashboard_server --port "$PORT" --event-dir "$EVENT_DIR" > "$SERVER_LOG" 2>&1 &
SERVER_PID=$!
trap 'kill "$SERVER_PID" >/dev/null 2>&1 || true' EXIT

URL="http://127.0.0.1:$PORT"
echo "dashboard: $URL"
echo "state: $EVENT_DIR/state.json"
echo "events: $EVENT_DIR/events.jsonl"

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
