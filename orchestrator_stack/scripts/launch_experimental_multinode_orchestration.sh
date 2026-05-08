#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

CLUSTER_ROOT="${CLUSTER_ROOT:-$HOME/Documents/borg_orchestrator_clusters}"
export KUBECONFIG="${KUBECONFIG:-$CLUSTER_ROOT/kubeconfig-experimental}"
export LIVE_K8S="${LIVE_K8S:-1}"
export EVENT_DIR="${EVENT_DIR:-orchestrator_stack/runtime/visualization-experimental}"
export TRACE_OUT="${TRACE_OUT:-orchestrator_stack/runtime/visualization-experimental/live_kubernetes_trace.json}"
export PORT="${PORT:-8765}"
export NAMESPACE_PREFIXES="${NAMESPACE_PREFIXES:-borg-orchestrator-exercise,default,test-}"
export EXERCISE_CLUSTER="${EXERCISE_CLUSTER:-1}"
export EXERCISE_INTERVAL_ITERATIONS="${EXERCISE_INTERVAL_ITERATIONS:-2}"
export EXERCISE_RANDOMIZE="${EXERCISE_RANDOMIZE:-1}"

./orchestrator_stack/scripts/launch_orchestration.sh
