#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

CLUSTER_ROOT="${CLUSTER_ROOT:-$HOME/Documents/borg_orchestrator_clusters}"
EXPERIMENTAL_KUBECONFIG="${EXPERIMENTAL_KUBECONFIG:-$CLUSTER_ROOT/kubeconfig-experimental}"
BASELINE_KUBECONFIG="${BASELINE_KUBECONFIG:-$CLUSTER_ROOT/kubeconfig-baseline}"
EXPERIMENTAL_EVENT_DIR="${EXPERIMENTAL_EVENT_DIR:-orchestrator_stack/runtime/visualization-experimental}"
PORT="${PORT:-8876}"
PYTHON_BIN="${PYTHON_BIN:-$ROOT/.venv/bin/python}"
OPEN_BROWSER="${OPEN_BROWSER:-1}"
RUN_LOCAL_KARPENTER="${RUN_LOCAL_KARPENTER:-1}"
KARPENTER_STATE="${KARPENTER_STATE:-orchestrator_stack/runtime/comparison/local_karpenter_state.json}"
KARPENTER_LOG="${KARPENTER_LOG:-orchestrator_stack/runtime/comparison/local-karpenter.log}"
SERVER_LOG="${SERVER_LOG:-orchestrator_stack/runtime/comparison/server.log}"

if [[ ! -x "$PYTHON_BIN" ]]; then
  PYTHON_BIN="$(command -v python3)"
fi
mkdir -p orchestrator_stack/runtime/comparison "$EXPERIMENTAL_EVENT_DIR"

cleanup() {
  kill "${KARPENTER_PID:-}" >/dev/null 2>&1 || true
  kill "${SERVER_PID:-}" >/dev/null 2>&1 || true
}
trap cleanup EXIT

if [[ "$RUN_LOCAL_KARPENTER" == "1" ]]; then
  echo "local-karpenter: starting warm-node controller"
  : > "$KARPENTER_LOG"
  "$PYTHON_BIN" orchestrator_stack/scripts/local_karpenter_controller.py \
    --kubeconfig "$BASELINE_KUBECONFIG" \
    --state-out "$KARPENTER_STATE" \
    --namespace borg-baseline \
    > "$KARPENTER_LOG" 2>&1 &
  KARPENTER_PID=$!
fi

PYTHONPATH="orchestrator_stack${PYTHONPATH:+:$PYTHONPATH}" "$PYTHON_BIN" -m orchestrator.comparison_dashboard_server \
  --port "$PORT" \
  --experimental-kubeconfig "$EXPERIMENTAL_KUBECONFIG" \
  --baseline-kubeconfig "$BASELINE_KUBECONFIG" \
  --experimental-event-dir "$EXPERIMENTAL_EVENT_DIR" \
  --karpenter-state "$KARPENTER_STATE" \
  > "$SERVER_LOG" 2>&1 &
SERVER_PID=$!

URL="http://127.0.0.1:$PORT"
echo "comparison dashboard: $URL"
echo "experimental kubeconfig: $EXPERIMENTAL_KUBECONFIG"
echo "baseline kubeconfig: $BASELINE_KUBECONFIG"
echo "experimental event dir: $EXPERIMENTAL_EVENT_DIR"
echo "local karpenter state: $KARPENTER_STATE"

if [[ "$OPEN_BROWSER" == "1" && "$(uname -s)" == "Darwin" ]]; then
  open "$URL" >/dev/null 2>&1 || true
fi

wait "$SERVER_PID"
