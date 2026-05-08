#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

KIND_BIN="${KIND_BIN:-kind}"
RUNTIME_DIR="${RUNTIME_DIR:-orchestrator_stack/runtime/local-dual-cluster}"
DELETE_CLUSTERS="${DELETE_CLUSTERS:-1}"
KEEP_CLUSTERS="${KEEP_CLUSTERS:-0}"
DELETE_AIOPSLAB="${DELETE_AIOPSLAB:-0}"
EXPERIMENTAL_CLUSTER="${EXPERIMENTAL_CLUSTER:-borg-experimental}"
BASELINE_CLUSTER="${BASELINE_CLUSTER:-borg-baseline}"
AIOPSLAB_CLUSTER="${AIOPSLAB_CLUSTER:-borg-aiopslab}"

kill_pidfile() {
  local label="$1"
  local pidfile="$2"
  local pid
  pid="$(cat "$pidfile" 2>/dev/null || true)"
  if [[ -z "$pid" ]]; then
    rm -f "$pidfile"
    return 0
  fi
  if kill -0 "$pid" >/dev/null 2>&1; then
    echo "stop: $label pid $pid"
    kill "$pid" >/dev/null 2>&1 || true
    for _ in {1..30}; do
      kill -0 "$pid" >/dev/null 2>&1 || break
      sleep 0.2
    done
    kill -0 "$pid" >/dev/null 2>&1 && kill -9 "$pid" >/dev/null 2>&1 || true
  fi
  rm -f "$pidfile"
}

if [[ -d "$RUNTIME_DIR" ]]; then
  kill_pidfile "experimental orchestration" "$RUNTIME_DIR/experimental.pid"
  kill_pidfile "comparison dashboard" "$RUNTIME_DIR/comparison.pid"
  kill_pidfile "baseline prometheus port-forward" "$RUNTIME_DIR/baseline-prometheus.pid"
fi

pkill -f '[l]aunch_orchestration.sh' >/dev/null 2>&1 || true
pkill -f '[l]aunch_experimental_multinode_orchestration.sh' >/dev/null 2>&1 || true
pkill -f '[l]aunch_cluster_comparison.sh' >/dev/null 2>&1 || true
pkill -f '[o]rchestrator.dashboard_server' >/dev/null 2>&1 || true
pkill -f '[o]rchestrator.comparison_dashboard_server' >/dev/null 2>&1 || true
pkill -f '[o]rchestrator_stack/run.py live-kubernetes-run' >/dev/null 2>&1 || true
pkill -f '[l]ocal_karpenter_controller.py' >/dev/null 2>&1 || true
pkill -f '[k]ubectl .*port-forward svc/prometheus-server' >/dev/null 2>&1 || true

rm -rf \
  orchestrator_stack/runtime/visualization/.launch.lock \
  orchestrator_stack/runtime/visualization-experimental/.launch.lock

if [[ "$KEEP_CLUSTERS" == "1" ]]; then
  DELETE_CLUSTERS=0
fi

if [[ "$DELETE_CLUSTERS" == "1" ]]; then
  echo "kind: deleting $EXPERIMENTAL_CLUSTER and $BASELINE_CLUSTER"
  "$KIND_BIN" delete cluster --name "$EXPERIMENTAL_CLUSTER" >/dev/null 2>&1 || true
  "$KIND_BIN" delete cluster --name "$BASELINE_CLUSTER" >/dev/null 2>&1 || true
fi

if [[ "$DELETE_AIOPSLAB" == "1" ]]; then
  echo "kind: deleting $AIOPSLAB_CLUSTER"
  "$KIND_BIN" delete cluster --name "$AIOPSLAB_CLUSTER" >/dev/null 2>&1 || true
fi

echo "stopped local dual-cluster stack"
