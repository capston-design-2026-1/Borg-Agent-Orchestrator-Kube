#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

KUBECTL="${KUBECTL:-kubectl}"
KUBECONFIG_PATH="${KUBECONFIG:-$HOME/.kube/config}"
OBSERVABILITY_NAMESPACE="${OBSERVABILITY_NAMESPACE:-observe}"
OBSERVABILITY_MANIFEST="${OBSERVABILITY_MANIFEST:-orchestrator_stack/k8s/observability/metrics-prometheus.yaml}"
OBSERVABILITY_WAIT_TIMEOUT="${OBSERVABILITY_WAIT_TIMEOUT:-180s}"
OBSERVABILITY_TOP_TIMEOUT_SECONDS="${OBSERVABILITY_TOP_TIMEOUT_SECONDS:-120}"
OBSERVABILITY_STRICT_TOP="${OBSERVABILITY_STRICT_TOP:-1}"
TOP_OUT="$(mktemp -t borg-orchestrator-kubectl-top.XXXXXX)"
TOP_ERR="$(mktemp -t borg-orchestrator-kubectl-top.XXXXXX)"

kubectl_live=("$KUBECTL" "--kubeconfig" "$KUBECONFIG_PATH")
cleanup_tmp() {
  rm -f "$TOP_OUT" "$TOP_ERR" >/dev/null 2>&1 || true
}
trap cleanup_tmp EXIT

if [[ ! -f "$OBSERVABILITY_MANIFEST" ]]; then
  echo "error: observability manifest not found: $OBSERVABILITY_MANIFEST" >&2
  exit 2
fi

echo "observability: kubeconfig=$KUBECONFIG_PATH"
echo "observability: manifest=$OBSERVABILITY_MANIFEST"

if "${kubectl_live[@]}" -n "$OBSERVABILITY_NAMESPACE" get pvc prometheus-pvc >/dev/null 2>&1; then
  pvc_state="$("${kubectl_live[@]}" -n "$OBSERVABILITY_NAMESPACE" get pvc prometheus-pvc -o jsonpath='{.status.phase} {.spec.storageClassName}' 2>/dev/null || true)"
  if [[ "$pvc_state" == "Pending openebs-hostpath" ]]; then
    echo "observability: deleting stale Pending PVC observe/prometheus-pvc that references missing openebs-hostpath"
    "${kubectl_live[@]}" -n "$OBSERVABILITY_NAMESPACE" delete pvc prometheus-pvc --ignore-not-found
  fi
fi

"${kubectl_live[@]}" apply -f "$OBSERVABILITY_MANIFEST"

echo "observability: waiting for Metrics Server"
"${kubectl_live[@]}" -n kube-system rollout status deployment/metrics-server --timeout="$OBSERVABILITY_WAIT_TIMEOUT"
"${kubectl_live[@]}" wait --for=condition=Available apiservice/v1beta1.metrics.k8s.io --timeout="$OBSERVABILITY_WAIT_TIMEOUT"

echo "observability: waiting for Prometheus"
"${kubectl_live[@]}" -n "$OBSERVABILITY_NAMESPACE" rollout status deployment/prometheus-server --timeout="$OBSERVABILITY_WAIT_TIMEOUT"

echo "observability: waiting for Node Exporter"
"${kubectl_live[@]}" -n "$OBSERVABILITY_NAMESPACE" rollout status daemonset/prometheus-node-exporter --timeout="$OBSERVABILITY_WAIT_TIMEOUT"

top_deadline=$((SECONDS + OBSERVABILITY_TOP_TIMEOUT_SECONDS))
top_status=1
while (( SECONDS < top_deadline )); do
  if "${kubectl_live[@]}" top nodes >"$TOP_OUT" 2>"$TOP_ERR"; then
    top_status=0
    break
  fi
  sleep 5
done

if [[ "$top_status" == "0" ]]; then
  echo "observability: metrics.k8s.io is serving node metrics"
  sed 's/^/observability: top: /' "$TOP_OUT"
elif [[ "$OBSERVABILITY_STRICT_TOP" == "1" ]]; then
  echo "error: metrics.k8s.io APIService became available, but kubectl top nodes did not return samples" >&2
  sed 's/^/observability: top error: /' "$TOP_ERR" >&2 || true
  exit 1
else
  echo "warning: metrics.k8s.io APIService is available, but kubectl top nodes did not return samples yet" >&2
  sed 's/^/observability: top error: /' "$TOP_ERR" >&2 || true
fi

"${kubectl_live[@]}" -n "$OBSERVABILITY_NAMESPACE" get pods,svc -l app.kubernetes.io/part-of=borg-orchestrator -o wide

echo "observability: ready"
echo "observability: prometheus service=${OBSERVABILITY_NAMESPACE}/prometheus-server"
