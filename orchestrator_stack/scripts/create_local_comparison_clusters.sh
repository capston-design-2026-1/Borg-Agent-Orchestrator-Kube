#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

KIND_BIN="${KIND_BIN:-kind}"
KUBECTL="${KUBECTL:-kubectl}"
CLUSTER_ROOT="${CLUSTER_ROOT:-$HOME/Documents/borg_orchestrator_clusters}"
EXPERIMENTAL_CLUSTER="${EXPERIMENTAL_CLUSTER:-borg-experimental}"
BASELINE_CLUSTER="${BASELINE_CLUSTER:-borg-baseline}"
EXPERIMENTAL_CONFIG="${EXPERIMENTAL_CONFIG:-orchestrator_stack/k8s/kind/experimental-multinode.yaml}"
BASELINE_CONFIG="${BASELINE_CONFIG:-orchestrator_stack/k8s/kind/baseline-hpa-karpenter-multinode.yaml}"
EXPERIMENTAL_KUBECONFIG="${EXPERIMENTAL_KUBECONFIG:-$CLUSTER_ROOT/kubeconfig-experimental}"
BASELINE_KUBECONFIG="${BASELINE_KUBECONFIG:-$CLUSTER_ROOT/kubeconfig-baseline}"
SHARED_WORKLOAD_MANIFEST="${SHARED_WORKLOAD_MANIFEST:-orchestrator_stack/k8s/comparison/shared-workload.yaml}"
BASELINE_HPA_MANIFEST="${BASELINE_HPA_MANIFEST:-orchestrator_stack/k8s/baseline/hpa-workload.yaml}"
BASELINE_SURGE_MANIFEST="${BASELINE_SURGE_MANIFEST:-orchestrator_stack/k8s/baseline/karpenter-surge-workload.yaml}"
COMPARISON_WORKLOAD_NAMESPACE="${COMPARISON_WORKLOAD_NAMESPACE:-borg-comparison-workload}"
LEGACY_BASELINE_NAMESPACE="${LEGACY_BASELINE_NAMESPACE:-borg-baseline}"
OBSERVABILITY_WAIT_TIMEOUT="${OBSERVABILITY_WAIT_TIMEOUT:-240s}"
OBSERVABILITY_STRICT_TOP="${OBSERVABILITY_STRICT_TOP:-0}"
BOOTSTRAP_OBSERVABILITY="${BOOTSTRAP_OBSERVABILITY:-1}"
APPLY_SHARED_WORKLOAD="${APPLY_SHARED_WORKLOAD:-1}"
APPLY_BASELINE_WORKLOAD="${APPLY_BASELINE_WORKLOAD:-1}"
RECREATE="${RECREATE:-0}"

mkdir -p "$CLUSTER_ROOT"

cluster_exists() {
  "$KIND_BIN" get clusters 2>/dev/null | grep -Fxq "$1"
}

create_cluster() {
  local name="$1"
  local config="$2"
  local kubeconfig="$3"
  if [[ "$RECREATE" == "1" ]] && cluster_exists "$name"; then
    echo "kind: deleting existing cluster $name"
    "$KIND_BIN" delete cluster --name "$name"
  fi
  if ! cluster_exists "$name"; then
    echo "kind: creating cluster $name from $config"
    "$KIND_BIN" create cluster --name "$name" --config "$config" --kubeconfig "$kubeconfig"
  else
    echo "kind: cluster $name already exists"
    "$KIND_BIN" export kubeconfig --name "$name" --kubeconfig "$kubeconfig"
  fi
  chmod 600 "$kubeconfig"
}

label_baseline_nodes() {
  local kubeconfig="$1"
  local workers
  workers="$($KUBECTL --kubeconfig "$kubeconfig" get nodes -l '!node-role.kubernetes.io/control-plane' -o jsonpath='{range .items[*]}{.metadata.name}{"\n"}{end}')"
  local index=0
  while IFS= read -r node; do
    [[ -z "$node" ]] && continue
    index=$((index + 1))
    "$KUBECTL" --kubeconfig "$kubeconfig" label node "$node" \
      borg.local/cluster-role=baseline-worker \
      borg.local/karpenter-node=true \
      borg.local/node-index="$index" \
      --overwrite >/dev/null
    if [[ "$index" == "1" ]]; then
      "$KUBECTL" --kubeconfig "$kubeconfig" label node "$node" borg.local/provisioning-state=active --overwrite >/dev/null
      "$KUBECTL" --kubeconfig "$kubeconfig" uncordon "$node" >/dev/null || true
      "$KUBECTL" --kubeconfig "$kubeconfig" taint node "$node" borg.local/capacity- >/dev/null 2>&1 || true
    else
      "$KUBECTL" --kubeconfig "$kubeconfig" label node "$node" borg.local/provisioning-state=warm --overwrite >/dev/null
      "$KUBECTL" --kubeconfig "$kubeconfig" cordon "$node" >/dev/null || true
      "$KUBECTL" --kubeconfig "$kubeconfig" taint node "$node" borg.local/capacity=warm:NoSchedule --overwrite >/dev/null
    fi
  done <<< "$workers"
}

label_experimental_nodes() {
  local kubeconfig="$1"
  local workers
  workers="$($KUBECTL --kubeconfig "$kubeconfig" get nodes -l '!node-role.kubernetes.io/control-plane' -o jsonpath='{range .items[*]}{.metadata.name}{"\n"}{end}')"
  local index=0
  while IFS= read -r node; do
    [[ -z "$node" ]] && continue
    index=$((index + 1))
    "$KUBECTL" --kubeconfig "$kubeconfig" label node "$node" \
      borg.local/cluster-role=experimental-worker \
      borg.local/node-index="$index" \
      borg.local/experiment-node=true \
      --overwrite >/dev/null
    "$KUBECTL" --kubeconfig "$kubeconfig" uncordon "$node" >/dev/null || true
  done <<< "$workers"
}

bootstrap_observability() {
  local kubeconfig="$1"
  local name="$2"
  if [[ "$BOOTSTRAP_OBSERVABILITY" != "1" ]]; then
    return 0
  fi
  echo "observability: bootstrapping $name"
  KUBECONFIG="$kubeconfig" \
  OBSERVABILITY_WAIT_TIMEOUT="$OBSERVABILITY_WAIT_TIMEOUT" \
  OBSERVABILITY_STRICT_TOP="$OBSERVABILITY_STRICT_TOP" \
    ./orchestrator_stack/scripts/bootstrap_observability.sh
}

create_cluster "$EXPERIMENTAL_CLUSTER" "$EXPERIMENTAL_CONFIG" "$EXPERIMENTAL_KUBECONFIG"
create_cluster "$BASELINE_CLUSTER" "$BASELINE_CONFIG" "$BASELINE_KUBECONFIG"
label_experimental_nodes "$EXPERIMENTAL_KUBECONFIG"
label_baseline_nodes "$BASELINE_KUBECONFIG"
bootstrap_observability "$EXPERIMENTAL_KUBECONFIG" "$EXPERIMENTAL_CLUSTER"
bootstrap_observability "$BASELINE_KUBECONFIG" "$BASELINE_CLUSTER"

if [[ "$APPLY_SHARED_WORKLOAD" == "1" ]]; then
  echo "shared workload: applying identical comparison workload to both clusters"
  "$KUBECTL" --kubeconfig "$EXPERIMENTAL_KUBECONFIG" apply -f "$SHARED_WORKLOAD_MANIFEST"
  "$KUBECTL" --kubeconfig "$BASELINE_KUBECONFIG" apply -f "$SHARED_WORKLOAD_MANIFEST"
fi

if [[ "$APPLY_BASELINE_WORKLOAD" == "1" ]]; then
  echo "baseline: applying HPA controller and local Karpenter surge target"
  "$KUBECTL" --kubeconfig "$BASELINE_KUBECONFIG" apply -f "$BASELINE_HPA_MANIFEST"
  "$KUBECTL" --kubeconfig "$BASELINE_KUBECONFIG" apply -f "$BASELINE_SURGE_MANIFEST"
  "$KUBECTL" --kubeconfig "$BASELINE_KUBECONFIG" delete namespace "$LEGACY_BASELINE_NAMESPACE" --ignore-not-found --wait=false >/dev/null
fi

cat <<INFO

local comparison clusters are ready
experimental kubeconfig: $EXPERIMENTAL_KUBECONFIG
baseline kubeconfig:     $BASELINE_KUBECONFIG
shared workload ns:      $COMPARISON_WORKLOAD_NAMESPACE

experimental nodes:
$($KUBECTL --kubeconfig "$EXPERIMENTAL_KUBECONFIG" get nodes -o wide)

baseline nodes:
$($KUBECTL --kubeconfig "$BASELINE_KUBECONFIG" get nodes -L borg.local/provisioning-state -o wide)

next commands:
  EXPERIMENTAL_KUBECONFIG=$EXPERIMENTAL_KUBECONFIG BASELINE_KUBECONFIG=$BASELINE_KUBECONFIG ./orchestrator_stack/scripts/launch_cluster_comparison.sh
  KUBECONFIG=$EXPERIMENTAL_KUBECONFIG LIVE_K8S=1 ./orchestrator_stack/scripts/launch_orchestration.sh
INFO
