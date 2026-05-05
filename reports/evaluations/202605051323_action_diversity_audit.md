# Live Action Diversity Audit

Audit time: 2026-05-05 13:23 KST

## Current Event Stream Before This Change

The live dashboard event stream was inspected from `orchestrator_stack/runtime/visualization/events.jsonl` and `orchestrator_stack/runtime/visualization/state.json`.

Observed event counts:

| Event kind | Count |
|---|---:|
| `stage` | 1669 |
| `artifact` | 170 |
| `ray` | 2 |
| `optuna` | 5 |
| `exercise` | 554 |
| `cluster` | 1662 |
| `decision` | 1662 |
| `reward` | 1662 |

Observed selected decision counts:

| Selected action | Count |
|---|---:|
| `AgentB:memory_balloon` | 927 |
| `AgentA:throttle` | 480 |
| `AgentC:admission` | 186 |
| `AgentA:migrate` | 63 |
| `AgentC:resource_cap` | 6 |

Observed stimulus phases:

| Stimulus phase | Count |
|---|---:|
| `high-risk` | 159 |
| `moderate-demand` | 141 |
| `idle-efficiency` | 103 |
| `bursty-safety` | 99 |
| `memory-pressure` | 52 |

## Diagnosis

The run was active and not broken, but the action distribution was too narrow for thesis-quality visualization of the architecture.

Problems found:

| Problem | Cause | Effect |
|---|---|---|
| Agent B dominated | Demand often remained in the `0.3-0.45` band. | `memory_balloon` repeated far more than other actions. |
| No AgentB `dvfs` or `power_state` | The heuristic did not distinguish very-low-demand power-state cases from low-demand DVFS cases. | Efficiency policy looked narrower than the architecture supports. |
| No AgentA `replicate` | Live Kind requested-load risk rarely crossed the old `0.9` replication threshold. | Safety path showed throttle/migrate but not replication. |
| AgentC admission details were collapsed | Events labeled all AgentC admission decisions as `admission`. | The dashboard could hide whether AgentC queued, rejected, or deprioritized. |
| Stimulus phases were too coarse | Old phases targeted broad idle/moderate/high-risk behavior. | They did not reliably force all Agent A/B/C action families. |

## Implemented Fix

The Kubernetes exerciser now uses an action-covering phase library instead of the old coarse phase set.

| Phase | Intended selected action |
|---|---|
| `idle-power-save` | `AgentB:power_state:sleep` |
| `light-dvfs` | `AgentB:dvfs` |
| `moderate-memory` | `AgentB:memory_balloon` |
| `safety-throttle` | `AgentA:throttle` |
| `safety-migrate` | `AgentA:migrate` |
| `safety-replicate` | `AgentA:replicate` |
| `admission-queue` | `AgentC:admission:queue` |
| `admission-deprioritize` | `AgentC:admission:deprioritize` |
| `admission-cap` | `AgentC:resource_cap` |

Other changes:

| Area | Change |
|---|---|
| Agent A heuristic | Replication threshold changed from `0.9` to `0.83` so severe schedulable pressure in a single-node Kind cluster can activate replication. |
| Agent B heuristic | Split low demand into `power_state:sleep`, `dvfs`, and `memory_balloon` bands. |
| Agent C heuristic | Added queue/deprioritize/resource-cap queue bands from real pending pods. |
| Ray/RLlib default policy | Default action IDs now align with the diversified heuristic bands. |
| Referee rationale | Safety override messages now name the exact safety action, e.g. `replicate` instead of always saying migration. |
| Dashboard events | Decisions and reward labels can now show sub-actions such as `AgentC:admission:queue` and `AgentB:power_state:sleep`. |
| Dashboard stimulus card | Stimulus details now include intended action and replica count. |

## Offline Policy Smoke Result

The updated agent/referee policies were checked with representative observations for each phase. Expected selected actions were produced:

| Scenario | Selected action |
|---|---|
| `idle-power-save` | `AgentB:power_state:sleep` |
| `light-dvfs` | `AgentB:dvfs` |
| `moderate-memory` | `AgentB:memory_balloon` |
| `safety-throttle` | `AgentA:throttle` |
| `safety-migrate` | `AgentA:migrate` |
| `safety-replicate` | `AgentA:replicate` |
| `admission-queue` | `AgentC:admission:queue` |
| `admission-deprioritize` | `AgentC:admission:deprioritize` |
| `admission-cap` | `AgentC:resource_cap` |

## Verification

Commands run:

```bash
PYTHONPATH=orchestrator_stack .venv/bin/pytest -q orchestrator_stack/tests
node --check orchestrator_stack/dashboard/app.js
python3 -m py_compile orchestrator_stack/orchestrator/layer1/kubernetes_exerciser.py orchestrator_stack/orchestrator/layer4/agents.py orchestrator_stack/orchestrator/layer4/policy.py orchestrator_stack/orchestrator/layer4/referee.py orchestrator_stack/orchestrator/layer2/simulator.py orchestrator_stack/orchestrator/visualization.py orchestrator_stack/orchestrator/runtime_state.py
PYTHONPATH=orchestrator_stack .venv/bin/python - <<'PY' | KUBECONFIG=~/Documents/aiopslab_validation_env/kubeconfig kubectl apply --dry-run=client -f -
from orchestrator.layer1.kubernetes_exerciser import exercise_phases
print('\\n---\\n'.join(p.manifest for p in exercise_phases('borg-orchestrator-exercise') if p.manifest))
PY
git diff --check
```

Result: `105 passed`; all action-covering Kubernetes manifests also passed client-side dry-run validation.

## Runtime Note

The current already-running orchestration process will continue using the old Python code until it is restarted. Restart the launcher to activate the new action-diversity behavior.
