#!/usr/bin/env bash
set -euo pipefail

CLUSTER_NAME="${AIOPSLAB_CLUSTER_NAME:-borg-aiopslab}"
KUBECONFIG_PATH="${AIOPSLAB_KUBECONFIG:-$HOME/Documents/aiopslab_validation_env/kubeconfig}"

if ! command -v docker >/dev/null 2>&1; then
  echo "docker not found; install/start Docker Desktop first" >&2
  exit 1
fi
if ! docker info >/dev/null 2>&1; then
  echo "docker daemon not reachable; start Docker Desktop first" >&2
  exit 1
fi
if ! command -v kind >/dev/null 2>&1; then
  if command -v brew >/dev/null 2>&1; then
    brew install kind
  else
    echo "kind not found and brew unavailable" >&2
    exit 1
  fi
fi

mkdir -p "$(dirname "$KUBECONFIG_PATH")"
if ! kind get clusters | grep -qx "$CLUSTER_NAME"; then
  kind create cluster --name "$CLUSTER_NAME" --kubeconfig "$KUBECONFIG_PATH"
else
  kind export kubeconfig --name "$CLUSTER_NAME" --kubeconfig "$KUBECONFIG_PATH"
fi
kubectl --kubeconfig "$KUBECONFIG_PATH" wait --for=condition=Ready "node/$CLUSTER_NAME-control-plane" --timeout=180s
kubectl --kubeconfig "$KUBECONFIG_PATH" get nodes
