#!/usr/bin/env bash
set -euo pipefail

CLUSTER_ROOT="${CLUSTER_ROOT:-$HOME/Documents/borg_orchestrator_clusters}"
KUBECONFIG_PATH="${KUBECONFIG:-$CLUSTER_ROOT/kubeconfig-baseline}"
REPLICAS="${REPLICAS:-8}"

kubectl --kubeconfig "$KUBECONFIG_PATH" -n borg-baseline scale deployment/karpenter-surge --replicas "$REPLICAS"
kubectl --kubeconfig "$KUBECONFIG_PATH" -n borg-baseline get pods -o wide
