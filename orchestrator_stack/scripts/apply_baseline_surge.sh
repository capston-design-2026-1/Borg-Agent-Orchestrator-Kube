#!/usr/bin/env bash
set -euo pipefail

CLUSTER_ROOT="${CLUSTER_ROOT:-$HOME/Documents/borg_orchestrator_clusters}"
KUBECONFIG_PATH="${KUBECONFIG:-$CLUSTER_ROOT/kubeconfig-baseline}"
NAMESPACE="${NAMESPACE:-borg-comparison-workload}"
REPLICAS="${REPLICAS:-8}"

kubectl --kubeconfig "$KUBECONFIG_PATH" -n "$NAMESPACE" scale deployment/karpenter-surge --replicas "$REPLICAS"
kubectl --kubeconfig "$KUBECONFIG_PATH" -n "$NAMESPACE" get pods -o wide
