#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

CLUSTER_ROOT="${CLUSTER_ROOT:-$HOME/Documents/borg_orchestrator_clusters}"
EXPERIMENTAL_KUBECONFIG="${EXPERIMENTAL_KUBECONFIG:-$CLUSTER_ROOT/kubeconfig-experimental}"
BASELINE_KUBECONFIG="${BASELINE_KUBECONFIG:-$CLUSTER_ROOT/kubeconfig-baseline}"
RUNTIME_DIR="${RUNTIME_DIR:-orchestrator_stack/runtime/local-dual-cluster}"
EXPERIMENTAL_DASHBOARD_PORT="${EXPERIMENTAL_DASHBOARD_PORT:-8765}"
COMPARISON_DASHBOARD_PORT="${COMPARISON_DASHBOARD_PORT:-8876}"
EXPERIMENTAL_PROMETHEUS_PORT="${EXPERIMENTAL_PROMETHEUS_PORT:-19090}"
BASELINE_PROMETHEUS_PORT="${BASELINE_PROMETHEUS_PORT:-19091}"
OPEN_BROWSER="${OPEN_BROWSER:-1}"
STOP_EXISTING_RUNTIME="${STOP_EXISTING_RUNTIME:-1}"
START_BASELINE_PROMETHEUS="${START_BASELINE_PROMETHEUS:-1}"
PYTHON_BIN="${PYTHON_BIN:-$ROOT/.venv/bin/python}"

mkdir -p "$RUNTIME_DIR"

if [[ "$STOP_EXISTING_RUNTIME" == "1" ]]; then
  KEEP_CLUSTERS=1 ./orchestrator_stack/scripts/stop_local_dual_cluster_stack.sh >/dev/null 2>&1 || true
fi

./orchestrator_stack/scripts/create_local_comparison_clusters.sh

start_process() {
  local label="$1"
  local logfile="$2"
  local pidfile="$3"
  shift 3
  : > "$logfile"
  nohup "$@" > "$logfile" 2>&1 &
  echo "$!" > "$pidfile"
  echo "$label pid: $(cat "$pidfile")"
  echo "$label log: $logfile"
}

start_process \
  "experimental orchestration" \
  "$RUNTIME_DIR/experimental.log" \
  "$RUNTIME_DIR/experimental.pid" \
  env \
    OPEN_BROWSER=0 \
    PYTHON_BIN="$PYTHON_BIN" \
    KUBECONFIG="$EXPERIMENTAL_KUBECONFIG" \
    MIRROR_EXERCISE_KUBECONFIG="$BASELINE_KUBECONFIG" \
    PORT="$EXPERIMENTAL_DASHBOARD_PORT" \
    PROMETHEUS_PORT="$EXPERIMENTAL_PROMETHEUS_PORT" \
    ./orchestrator_stack/scripts/launch_experimental_multinode_orchestration.sh

start_process \
  "comparison dashboard" \
  "$RUNTIME_DIR/comparison.log" \
  "$RUNTIME_DIR/comparison.pid" \
  env \
    OPEN_BROWSER=0 \
    PYTHON_BIN="$PYTHON_BIN" \
    EXPERIMENTAL_KUBECONFIG="$EXPERIMENTAL_KUBECONFIG" \
    BASELINE_KUBECONFIG="$BASELINE_KUBECONFIG" \
    PORT="$COMPARISON_DASHBOARD_PORT" \
    ./orchestrator_stack/scripts/launch_cluster_comparison.sh

if [[ "$START_BASELINE_PROMETHEUS" == "1" ]]; then
  start_process \
    "baseline prometheus" \
    "$RUNTIME_DIR/baseline-prometheus.log" \
    "$RUNTIME_DIR/baseline-prometheus.pid" \
    kubectl --kubeconfig "$BASELINE_KUBECONFIG" -n observe port-forward svc/prometheus-server "$BASELINE_PROMETHEUS_PORT:80"
fi

EXPERIMENTAL_URL="http://127.0.0.1:$EXPERIMENTAL_DASHBOARD_PORT"
COMPARISON_URL="http://127.0.0.1:$COMPARISON_DASHBOARD_PORT"
EXPERIMENTAL_PROM_URL="http://127.0.0.1:$EXPERIMENTAL_PROMETHEUS_PORT"
BASELINE_PROM_URL="http://127.0.0.1:$BASELINE_PROMETHEUS_PORT"

if [[ "$OPEN_BROWSER" == "1" && "$(uname -s)" == "Darwin" ]]; then
  open "$EXPERIMENTAL_URL" >/dev/null 2>&1 || true
  open "$COMPARISON_URL" >/dev/null 2>&1 || true
fi

cat <<INFO

local dual-cluster stack is starting
experimental dashboard: $EXPERIMENTAL_URL
comparison dashboard:   $COMPARISON_URL
experimental prometheus: $EXPERIMENTAL_PROM_URL
baseline prometheus:     $BASELINE_PROM_URL

k9s experimental:
  KUBECONFIG=$EXPERIMENTAL_KUBECONFIG k9s
k9s baseline:
  KUBECONFIG=$BASELINE_KUBECONFIG k9s

stop everything:
  cd $ROOT && ./orchestrator_stack/scripts/stop_local_dual_cluster_stack.sh

runtime logs:
  tail -f $RUNTIME_DIR/experimental.log
  tail -f $RUNTIME_DIR/comparison.log
  tail -f $RUNTIME_DIR/baseline-prometheus.log
INFO
