#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

CLUSTER_ROOT="${CLUSTER_ROOT:-$HOME/Documents/borg_orchestrator_clusters}"
EXPERIMENTAL_KUBECONFIG="${EXPERIMENTAL_KUBECONFIG:-$CLUSTER_ROOT/kubeconfig-experimental}"
BASELINE_KUBECONFIG="${BASELINE_KUBECONFIG:-$CLUSTER_ROOT/kubeconfig-baseline}"
EXERCISE_NAMESPACE="${EXERCISE_NAMESPACE:-borg-orchestrator-exercise}"
MIRROR_EXERCISE_NAMESPACE="${MIRROR_EXERCISE_NAMESPACE:-$EXERCISE_NAMESPACE}"
PHASE_INDEX="${PHASE_INDEX:-0}"
EXERCISE_RANDOMIZE="${EXERCISE_RANDOMIZE:-0}"
EXERCISE_SEED="${EXERCISE_SEED:-}"
SHARED_STIMULUS_OUT="${SHARED_STIMULUS_OUT:-orchestrator_stack/runtime/comparison/shared_stimulus.json}"
PYTHON_BIN="${PYTHON_BIN:-$ROOT/.venv/bin/python}"

if [[ ! -x "$PYTHON_BIN" ]]; then
  PYTHON_BIN="$(command -v python3)"
fi

PYTHONPATH="orchestrator_stack${PYTHONPATH:+:$PYTHONPATH}" \
EXPERIMENTAL_KUBECONFIG="$EXPERIMENTAL_KUBECONFIG" \
BASELINE_KUBECONFIG="$BASELINE_KUBECONFIG" \
EXERCISE_NAMESPACE="$EXERCISE_NAMESPACE" \
MIRROR_EXERCISE_NAMESPACE="$MIRROR_EXERCISE_NAMESPACE" \
PHASE_INDEX="$PHASE_INDEX" \
EXERCISE_RANDOMIZE="$EXERCISE_RANDOMIZE" \
EXERCISE_SEED="$EXERCISE_SEED" \
SHARED_STIMULUS_OUT="$SHARED_STIMULUS_OUT" \
"$PYTHON_BIN" - <<'PY'
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from orchestrator.layer1.kubernetes_exerciser import apply_exercise_phase_to_clusters

seed_text = os.environ.get("EXERCISE_SEED", "")
result = apply_exercise_phase_to_clusters(
    kubeconfig=os.environ["EXPERIMENTAL_KUBECONFIG"],
    namespace=os.environ["EXERCISE_NAMESPACE"],
    phase_index=int(os.environ.get("PHASE_INDEX", "0")),
    mirror_kubeconfigs=[os.environ["BASELINE_KUBECONFIG"]],
    mirror_namespace=os.environ["MIRROR_EXERCISE_NAMESPACE"],
    randomize=os.environ.get("EXERCISE_RANDOMIZE", "0") == "1",
    seed=int(seed_text) if seed_text else None,
)
payload = {
    "recorded_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    **result,
}
out = Path(os.environ["SHARED_STIMULUS_OUT"])
out.parent.mkdir(parents=True, exist_ok=True)
tmp = out.with_suffix(".tmp")
tmp.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
tmp.replace(out)
print(json.dumps(payload, indent=2, sort_keys=True))
PY
