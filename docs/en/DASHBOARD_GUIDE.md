# Borg Orchestrator Dashboard Guide

This document explains every major area of the Live Orchestration Dashboard served at `http://127.0.0.1:8765`. The dashboard periodically reads `orchestrator_stack/runtime/visualization/state.json` and `orchestrator_stack/runtime/visualization/events.jsonl` and turns them into the live control-plane view.

## Maintenance Rule

Whenever the dashboard UI, state schema, event schema, agent policy, reward function, Ray/RLlib path, Optuna path, or Kubernetes exerciser changes, update this guide in the same commit or at least in the same work session.

Files that must be checked together:

| Area | Implementation file | Documentation impact |
|---|---|---|
| Dashboard HTML structure | `orchestrator_stack/dashboard/index.html` | Screen-region descriptions |
| Dashboard rendering, charts, event parsing | `orchestrator_stack/dashboard/app.js` | Cards, graphs, event tables |
| Dashboard layout and visual grammar | `orchestrator_stack/dashboard/styles.css` | Visual interpretation rules |
| Runtime state/event writer | `orchestrator_stack/orchestrator/runtime_state.py` | Runtime State and Event Log sections |
| Live Kubernetes loop | `orchestrator_stack/orchestrator/visualization.py` | Live Flow, Current Decision, Stage sections |
| Agent A/B/C policies | `orchestrator_stack/orchestrator/layer4/agents.py`, `orchestrator_stack/orchestrator/layer4/policy.py` | Agent operation and reward tables |
| Referee conflict resolution | `orchestrator_stack/orchestrator/layer4/referee.py` | Decision Gate section |
| Reward computation | `orchestrator_stack/orchestrator/layer2/simulator.py`, `orchestrator_stack/orchestrator/layer6/scoreboard.py` | Reward Stream and agent reward tables |
| Kubernetes intentional perturbation | `orchestrator_stack/orchestrator/layer1/kubernetes_exerciser.py` | Intentional Kubernetes Stimulus section |
| Kubernetes observability bootstrap | `orchestrator_stack/scripts/bootstrap_observability.sh`, `orchestrator_stack/k8s/observability/metrics-prometheus.yaml` | Live Kubernetes Environment and telemetry-source sections |

## Launch and Data Flow Summary

The live dashboard is normally launched with the full orchestration stack:

```bash
cd /Users/theokim/Documents/github/kyunghee/Borg-Agent-Orchestrator && LIVE_K8S=1 KUBECONFIG=~/Documents/aiopslab_validation_env/kubeconfig ./orchestrator_stack/scripts/launch_orchestration.sh
```

The live-mode flow is:

| Step | Layer | Runtime behavior | Dashboard location |
|---:|---|---|---|
| 1 | Layer 1 Kubernetes Source | Reads node/pod state with `kubectl`; live launch also bootstraps Prometheus/Node Exporter and merges Prometheus CPU/memory samples by default. | Metrics, Kubernetes Cluster card, `cluster` events |
| 2 | Live Perturbation | Applies or deletes safe synthetic workloads in the `borg-orchestrator-exercise` namespace. | Workload Exerciser card, Intentional Kubernetes Stimulus card, `exercise` events |
| 3 | Layer 2 AIOpsLab Twin | Converts the snapshot into an `Observation` and computes twin transitions/rewards after selected actions. | AIOpsLab Twin card, Reward Stream |
| 4 | Layer 3 XGBoost Brains | Enriches risk and demand forecasts, or uses telemetry-derived values if XGBoost is unavailable. | XGBoost Brains card, Max Risk, Decision Reason |
| 5 | Layer 4 Agents | Agent A/B/C produce safety, efficiency, and admission proposals. | Agent A/B/C cards, State Vector card, proposal chips |
| 6 | Referee | Selects one final action with safety-first conflict resolution. | Current Decision, Decision Gate, Performed Action |
| 7 | Layer 6 Scoreboard | Computes per-agent raw reward and weighted total reward. | Reward Stream, Global Scoreboard, Last Reward |
| 8 | Layer 5 Optuna | Searches reward weights `alpha`, `beta`, and `gamma`. | Optuna card, objective graph, weight graph |
| 9 | Ray/RLlib | Bootstraps/trains the multi-agent PPO policy. | Ray Status, Ray/RLlib panel, Ray RLlib PPO Policy card |

## Live Kubernetes Environment

The current live orchestration target is a local Kind validation cluster, not a managed cloud Kubernetes cluster or a production multi-node deployment. The baseline inspected environment is recorded in `reports/evaluations/202605051249_kubernetes_environment_snapshot.md`, and the observability repair is recorded in `reports/evaluations/202605051339_observability_bootstrap_report.md`.

| Field | Current value |
|---|---|
| Kubernetes context | `kind-borg-aiopslab` |
| Cluster type | Local Kind cluster running in Docker |
| API server | `https://127.0.0.1:54392` |
| Kind node container | `borg-aiopslab-control-plane` |
| Kind node image | `kindest/node:v1.35.0` |
| Kubernetes server | `v1.35.0` |
| kubectl client | `v1.34.1` |
| Node count | `1` |
| Node role | Single `control-plane` node also used as the worker |
| Node architecture | `arm64` |
| Node OS | `Debian GNU/Linux 12 (bookworm)` |
| Kernel | `6.12.76-linuxkit` |
| Container runtime | `containerd://2.2.0` |
| Node capacity | `10` CPU cores, about `8Gi` memory, `110` pods |
| Pod CIDR | `10.244.0.0/24` |
| CNI | Kindnet |
| Default storage class | `standard`, provisioner `rancher.io/local-path` |

Active namespaces observed in this environment:

| Namespace | Role |
|---|---|
| `borg-orchestrator-exercise` | Main namespace where the live exerciser creates/deletes synthetic workload Deployments. |
| `default` | Contains a completed `wrk2` validation job from earlier AIOpsLab/DeathStarBench work. |
| `kube-system` | CoreDNS, API server, scheduler, controller-manager, etcd, kube-proxy, and kindnet. |
| `local-path-storage` | Local-path storage provisioner. |
| `observe` | In-cluster observability namespace. The live launcher deploys `prometheus-server` and `prometheus-node-exporter` here. |
| `test-social-network` | DeathStarBench/AIOpsLab namespace; currently no active social-network resources in the inspected snapshot. |

Important runtime telemetry status:

| Item | Current status | Dashboard implication |
|---|---|---|
| Metrics Server | Installed by `bootstrap_observability.sh`; `v1beta1.metrics.k8s.io` is available and `kubectl top nodes` returns CPU/memory samples. | Operator-level Kubernetes metrics are now available for direct checks and debugging. |
| In-cluster Prometheus | `observe/prometheus-server` runs from the repository manifest. The launcher port-forwards it to `http://127.0.0.1:19090` unless overridden. | Live trace rows can include Prometheus-derived CPU/memory enrichment. Healthy rows show `prometheus_node_exporter` in `telemetry_sources`. |
| Node Exporter | `observe/prometheus-node-exporter` runs as a DaemonSet on the Kind node. | Prometheus queries such as `node_cpu_seconds_total` and `node_memory_MemAvailable_bytes` feed the trace collector. |
| Legacy `openebs-hostpath` PVC | The old pending `observe/prometheus-pvc` came from a storage class this Kind cluster does not have. The bootstrap script deletes that stale pending PVC and uses `emptyDir` Prometheus storage instead. | The thesis demo no longer depends on OpenEBS just to collect telemetry. Prometheus data is ephemeral across pod restarts, which is acceptable for live dashboard evidence. |
| Energy watts | Estimated by the default utilization model. | `est power ...W` is not a physical wattmeter reading. |
| Agent placement realism | Single-node cluster. | Agent C admission logic is visible, but true multi-node placement/migration behavior cannot be demonstrated here. |

Expected live telemetry indicators:

| Check | Expected result |
|---|---|
| `kubectl get apiservice v1beta1.metrics.k8s.io` | APIService exists and condition `Available=True`. |
| `kubectl top nodes` | Returns the Kind node CPU and memory sample. |
| `kubectl -n observe get pods,svc -l app.kubernetes.io/part-of=borg-orchestrator` | Shows running Prometheus and Node Exporter pods/services. |
| `state.json` / trace rows | `telemetry_sources` includes both `kubernetes_api` and `prometheus_node_exporter` when Prometheus enrichment succeeds. |

The live exerciser does perform real Kubernetes mutations. For example, it creates `pause` Deployments such as `light-dvfs`, `safety-replicate`, and `admission-queue` under `borg-orchestrator-exercise`. Those Deployments can create real scheduler outcomes such as `Pending` pods and `FailedScheduling` events. The dashboard therefore mixes:

| Data type | Reality level |
|---|---|
| Nodes, pods, deployments, events, namespaces, scheduler failures | Real Kubernetes API data from the Kind cluster |
| Synthetic workload phases and rollout return codes | Real `kubectl apply/delete/rollout status` results generated by the exerciser |
| Agent A/B/C proposals, referee choice, reward totals | Orchestrator control-plane decisions evaluated through the twin/reward path |
| Energy watts | Model-derived estimate using `idle_watts=80`, `cpu_full_scale_watts=120`, `mem_full_scale_watts=60` unless calibrated otherwise |

## Critical Interpretation: Real Kubernetes Stimulus vs Selected Orchestration Action

The dashboard shows two action-like streams, and they should not be confused.

| Name | Directly mutates Kubernetes now? | Meaning |
|---|---:|---|
| Intentional Kubernetes Stimulus | Yes | The exerciser runs `kubectl apply/delete` in the exercise namespace to create controlled cluster fluctuation. This is what makes risk/demand change and gives Agent A/B/C decision opportunities. |
| Performed Action | Applied to the live twin/reward path in the current implementation | The Referee-selected orchestration decision. The dashboard applies it to the twin transition and reward calculation. Unless a separate executor is added, this selected decision does not itself directly mutate Kubernetes resources. |

For thesis wording, the precise interpretation is:

- The real cluster perturbation is performed by the Workload Exerciser.
- Agent/Referee actions are control decisions selected from live cluster observations and evaluated through the twin/reward layer.
- If a Kubernetes remediation executor is added later, the Performed Action card can represent direct cluster mutation as well.

## Hero and Runtime Status

| UI element | Meaning | Source field |
|---|---|---|
| `Live Orchestration Control Plane` | The page title for the orchestration control-plane dashboard. | Static HTML |
| Status badge: `Running`, `complete`, `failed` | Overall runtime state. `running` means the loop/demo is active, `complete` means a bounded run finished, and `failed` means an error occurred. | `state.status` |
| `updated ...` | Last runtime state timestamp read by the dashboard. | `state.updated_at` |

## Six Metrics Cards

| Card | Example | Meaning | Caveat |
|---|---|---|---|
| Active Stage | `live_kubernetes_loop` | Current active orchestration stage. | Common values include `brains`, `ray_ppo`, `optuna`, `episode`, `live_kubernetes_loop`, and `complete`. |
| Last Reward | `7.359` | Latest step's weighted total reward. | This is not cumulative reward. |
| Reward Steps | `842` | Number of reward events recorded. | The line chart can show a recent history window. |
| Optuna | `1417.159` or `disabled` | Best Optuna objective score. | `NO_TUNE=1` can make disabled/skipped normal. |
| Ray Status | `trained`, `disabled`, `idle` | Ray/RLlib PPO bootstrap status. | `NO_POLICY=1` or fast mode can make disabled normal. |
| Max Risk | `0.590` | Highest current node failure/risk score. | Without XGBoost, this is telemetry-derived from Kubernetes/Prometheus utilization and pod health. |

## Current Decision Panel

| Field | Meaning |
|---|---|
| Recommendation | Selected agent and action kind, such as `AgentB:memory_balloon`. |
| Target | Target node or cluster target, such as `borg-aiopslab-control-plane`. |
| Reason | Short explanation of why the selected agent/action was chosen. |
| Timestamp | Time the decision was recorded, in KST ISO format. |

Reason formats:

| Agent | Reason format | Meaning |
|---|---|---|
| AgentA | `risk=0.590129 on node; sla=0` | Safety decision based on highest risk node and SLA violations. |
| AgentB | `low demand=0.30928 on node; est_power=93.620W` | Efficiency decision based on low demand and estimated power. |
| AgentC | `queue=...; avg_cpu=...; avg_mem=...` | Admission/resource decision based on queue pressure and utilization. |

## Architecture Stages Panel

| Stage | Meaning | Normal states |
|---|---|---|
| `brains` | XGBoost risk/demand predictor preparation. | `complete`, or `skipped` when XGBoost is unavailable |
| `ray_ppo` | Ray/RLlib PPO bootstrap/training. | `complete`, `trained`, or `disabled` in fast mode |
| `optuna` | Reward-weight tuning. | `complete`, `running`, `disabled`, `skipped` |
| `episode` | Finite trace replay in visualized-run mode. | Used in finite demo mode |
| `live_kubernetes_loop` | Continuous live Kubernetes snapshot, decision, and reward loop. | `running` in live mode |
| `complete` | Bounded run completion. | Dashboard server can remain alive when `KEEP_DASHBOARD=1`. |

## Live Orchestration Flow

This is the heart of the dashboard. The upper canvas is the architecture map. The lower operations deck shows live details without covering the map.

### Legend

| Legend | Color/line | Meaning |
|---|---|---|
| Telemetry | Gray dashed | Observation flow from Kubernetes/exerciser into the digital twin. |
| Inference | Blue dashed | Feature/state movement into predictors and policy. |
| Policy | Amber | Policy, agent proposal, and selected action flow. |
| Reward/Meta Loop | Green | Reward feedback, scoreboard, and Optuna meta feedback. |

### Architecture Map Lanes and Nodes

| Lane | Node | Display value | Meaning |
|---|---|---|---|
| Layer 1 | Kubernetes Cluster | `risk ...` | Highest risk score in the current cluster snapshot; also shows nodes/tasks/SLA and whether the row is `kubectl only` or `kubectl + prometheus`. |
| Layer 1 | Workload Exerciser | `active` or `idle` | Whether synthetic workload perturbation is active. |
| Layer 2 | AIOpsLab Twin | `cpu ...` | Average CPU after live snapshot normalization; detail shows memory and estimated power. |
| Layer 3 | XGBoost Brains | `risk ... / demand ...` | Risk forecast and resource demand projection. |
| Layer 3 | State Vector | `3 proposals` | Number of Agent A/B/C proposals. Usually one per agent. |
| Layer 4 | Ray RLlib PPO Policy | `trained`, `disabled`, `idle` | PPO policy bootstrap/training status. |
| Layer 4 | Agent A | `candidate`, `throttle`, `migrate`, `replicate` | Safety/risk proposal or selected action. |
| Layer 4 | Agent B | `candidate`, `dvfs`, `memory balloon`, `power state` | Efficiency/energy proposal or selected action. |
| Layer 4 | Agent C | `candidate`, `admission`, `resource cap` | Admission/queue proposal or selected action. |
| Referee | Decision Gate | `score ...` | Selected proposal score and reason. |
| Layer 6 | Global Scoreboard | Weighted total | Latest weighted reward and raw Agent A/B/C rewards. |
| Layer 5 | Optuna Trial Manager | Best score | Best reward-weight objective score and study name. |

### Operations Deck

| Card | Meaning | Key fields |
|---|---|---|
| Intentional Kubernetes Stimulus | Real synthetic workload mutation applied to the cluster. | phase, intended action, namespace, operation, replicas, CPU request, memory request, rollout return code |
| Performed Action | Final Referee-selected orchestration decision. | selected agent/action, route, target, payload, proposal chips |

Stimulus operations:

| Operation | Runtime meaning |
|---|---|
| `apply` | Applies an exercise Deployment manifest with `kubectl apply -f -`. |
| `delete` | Deletes exerciser Deployments in the exercise namespace using the label selector. |
| `observe` | Fallback for older events without structured fields or no stimulus yet. |

`rollout rc` is the return code of `kubectl rollout status`: `0` means success; non-zero indicates possible rollout failure, timeout, or validation failure.

## Kubernetes Stimulus Phases

When `EXERCISE_CLUSTER=1`, the exerciser rotates safe synthetic workloads. The default is randomized mode. Randomized mode samples from the same action-covering phase library below and jitters request sizes so the run is less periodic.

| Phase | Kubernetes mutation | Intended action coverage | Fixed/random resources |
|---|---|---|---|
| `idle-power-save` | Deletes exercise Deployments. | AgentB `power_state:sleep` under very low demand. | No deployment |
| `light-dvfs` | Creates a light schedulable Deployment. | AgentB `dvfs` under low-but-not-empty demand. | Fixed: `2200m`, `256Mi`; random: `1600m-2800m`, `128Mi-512Mi` |
| `moderate-memory` | Creates a moderate schedulable Deployment. | AgentB `memory_balloon` under moderate demand. | Fixed: `6200m`, `768Mi`; random: `5200m-6800m`, `512Mi-1280Mi` |
| `safety-throttle` | Creates a moderate-high schedulable Deployment. | AgentA `throttle`. | Fixed: `8600m`, `1Gi`; random: `8200m-8800m`, `768Mi-1536Mi` |
| `safety-migrate` | Creates a high schedulable Deployment. | AgentA `migrate`. | Fixed: `9200m`, `5Gi`; random: `9000m-9300m`, `4096Mi-5632Mi` |
| `safety-replicate` | Creates a severe-but-schedulable Deployment. | AgentA `replicate`. | Fixed: `9400m`, `7Gi`; random: `9300m-9450m`, `6656Mi-7424Mi` |
| `admission-queue` | Creates 12 unschedulable pods using an intentionally unmatched node selector. | AgentC `admission:queue`. | `12` replicas, random `80m-200m`, `48Mi-128Mi` |
| `admission-deprioritize` | Creates 90 unschedulable pods using an intentionally unmatched node selector. | AgentC `admission:deprioritize`. | `90` replicas, random `80m-200m`, `48Mi-128Mi` |
| `admission-cap` | Creates 130 unschedulable pods using an intentionally unmatched node selector. | AgentC `resource_cap`. | `130` replicas, random `80m-200m`, `48Mi-128Mi` |

## Agent A/B/C Operations and Rewards

Each step starts with raw reward `1.0` for each agent. Action-specific and live telemetry rewards are then added or subtracted.

Weighted total reward:

```text
total = alpha * AgentA_reward + beta * AgentB_reward + gamma * AgentC_reward
```

Default config weights are `alpha=1.0`, `beta=0.6`, and `gamma=0.8`; Optuna searches these weights.

### Agent A: Risk Mitigator / Safety Agent

| Action | Heuristic trigger | RLlib action id | Payload | Twin transition effect | Possible reward |
|---|---|---:|---|---|---|
| `noop` | No `p_fail_scores` or max risk `< 0.5` | 0 | None | No state change. | Base `+1.0`; live telemetry penalties can still apply. |
| `throttle` | max risk `>= 0.5` and `< 0.7` | 3 | None | Multiplies target node CPU and network utilization by `0.85`. | If selected and `p_fail >= 0.5`, AgentA gets `+3.0`. |
| `migrate` | max risk `>= 0.7` and `< 0.83` | 1 | None | Moves one active task from the highest-loaded other on-node to the target; lowers source load and raises target load slightly. | `+10.0` if `p_fail > 0.75`; `-20.0` if migrating at `p_fail < 0.4`. |
| `replicate` | max risk `>= 0.83` | 2 | None | Replicates the most urgent task on the target node to the lowest-loaded other node. | `+8.0` if `p_fail >= 0.83`. |

Live telemetry effects that can always affect Agent A:

| Condition | Reward change | Meaning |
|---|---:|---|
| `sla_violations > 0` | bounded log-scaled pressure: `-min(180, 35 + 25*log1p(sla_violations))` | SLA violations are treated as safety pressure, but intentional backlog phases no longer create thousands of negative reward points. |
| Any dead task | `-100.0` | Task survival failure penalty. |

This scaling is important in live fault-injection mode. Agent C phases such as `admission-cap` intentionally create many unschedulable pods to test admission control. Those pods should create visible safety pressure, but they should not make Agent A show values like `-6499` just because `130` controlled pending pods were injected.

### Agent B: Efficiency Optimizer / Energy Agent

| Action | Heuristic trigger | RLlib action id | Payload | Twin transition effect | Possible reward |
|---|---|---:|---|---|---|
| `noop` | No demand projection or min demand `>= 0.45` | 0 | None | No state change. | Base `+1.0`; estimated-power telemetry bonus can still apply. |
| `power_state` sleep | min demand `< 0.12` | 1 | `state=sleep` | Sets node power state and reduces CPU/MEM utilization for sleep/off. | Same efficiency reward rule as DVFS. |
| `dvfs` | min demand `>= 0.12` and `< 0.3` | 3 | `clock_scale=0.65` | Multiplies target CPU by `clock_scale`; adjusts network by `0.9 + 0.1*clock_scale`. | Selected efficiency action gets `+5.0` when max demand `< 0.35`; `-30.0` when max demand `> 0.75`. |
| `memory_balloon` | min demand `>= 0.3` and `< 0.45` | 4 | `mem_scale=0.75` | Multiplies target memory utilization by `mem_scale`. | Same efficiency reward rule as DVFS. |
| `power_state` on | Not selected by heuristic; possible through RLlib policy | 2 | `state=on` | Wakes/keeps node on and slightly raises CPU/MEM utilization. | Uses the common efficiency reward rule. |

Live telemetry effect for Agent B:

| Condition | Reward change | Meaning |
|---|---:|---|
| Live metrics exist and `energy_watts` is present | `max(0, (500 - energy_watts) / 100)` | Lower estimated power gives higher AgentB bonus. Example: `93.620W` gives about `+4.064`. |

Note: `est power ...W` is not a direct wattmeter value. It is calibrated utilization-derived power, with the default formula `80 + 120*cpu_util + 60*mem_util`.

### Agent C: Gatekeeper / Admission Agent

| Action | Heuristic trigger | RLlib action id | Payload | Twin transition effect | Possible reward |
|---|---|---:|---|---|---|
| `admission:admit` | queue `< 20` and no overloaded nodes gives score `1.0`; otherwise normal state gives score `0.5` | 0 | `decision=admit` | Reduces queue length by up to 2. | `+5.0` when queue `< 80`; `-50.0` when queue `> 120`. |
| `admission:queue` | queue `>= 8` and `< 80` | 1 | `decision=queue` | Increases queue length by 1. | No explicit bonus in the trace twin, but protective admission can preempt Agent B in the Referee. |
| `admission:reject` | `sla_violations > 0` and queue `> 0` but below the queue band | 2 | `decision=reject` | Reduces queue length by 1. | `-20.0` when queue `< 60`. |
| `admission:deprioritize` | queue `>= 80` and `< 120` | 3 | `decision=deprioritize` | Lowers queued task priority. | `+3.0` when queue `>= 80`. |
| `resource_cap` | queue `>= 120` or overloaded nodes are at least half of all nodes | 4 | `cpu_cap=0.85`, `mem_cap=0.85` | Caps target CPU/MEM utilization at payload values. | `+4.0` when queue `>= 80`; the AIOpsLab adapter path can give `-5.0` when queue `< 80`. |

Live telemetry effect for Agent C:

| Condition | Reward change | Meaning |
|---|---:|---|
| `completed_tasks > 0` | `min(10.0, completed_tasks / 10.0)` | More completed tasks reward admission/throughput management, capped at `+10.0`. |

## Referee / Decision Gate Rules

Agent A/B/C each produce proposals, but the Referee selects exactly one final action.

| Priority | Rule | Explanation |
|---:|---|---|
| 1 | Agent A safety action first | `migrate`, `replicate`, or `throttle` preempts lower-priority actions. |
| 2 | Agent C protective admission second | `queue`, `reject`, `deprioritize`, and `resource_cap` override non-safety efficiency actions. |
| 3 | Agent B efficiency action by score | Selects the highest-scoring `power_state`, `dvfs`, or `memory_balloon`. |
| 4 | Deterministic priority fallback | Chooses by `AgentA -> AgentC -> AgentB` precedence and score. |
| 5 | All noop | If all proposals are noop, the fallback noop is selected by priority/score. |

The Decision Gate `score` is the selected proposal score, not the weighted reward total.

## Reward Stream Graph

| Element | Meaning |
|---|---|
| `steps` | Number of reward steps computed. |
| `avg total` | Running average of weighted total reward across all reward steps. |
| `last AgentA/B/C` | Latest raw per-agent reward, not weighted. |
| Canvas x-axis | Orchestration step. |
| Canvas y-axis | Reward value. |
| `total` line | Weighted reward: `alpha*A + beta*B + gamma*C`. |
| AgentA/B/C lines | Raw rewards for each agent. |

Why the graph may look patterned:

| Cause | Explanation |
|---|---|
| Deterministic exercise cycle | `EXERCISE_RANDOMIZE=0` repeats the action-covering stimulus phases in a fixed order. |
| Randomized exercise | Default `EXERCISE_RANDOMIZE=1` randomizes phase and resource requests. |
| Live cluster saturation | A one-node/one-workload cluster can push decisions toward one agent/action. |
| Referee priority | High safety risk can repeatedly select Agent A; sustained low demand can repeatedly select Agent B. |

## Learning Progress Panel

The Learning Progress panel is the fastest place to check whether the architecture is learning better configurations over time. It does not treat every raw trial as improvement, because Optuna must explore weak and strong parameter samples. Instead, it separates exploration from confirmed improvement.

| UI element | Meaning |
|---|---|
| Status badge | `improving`, `exploring`, `plateau watch`, or `waiting`, derived from Optuna best-so-far progress. |
| Completed trials | Number of completed Optuna trials currently loaded from the persistent study. |
| Best-so-far lift | Difference between the current best objective and the first visible objective, with percent lift when computable. |
| New-best events | Count of trials that beat every previous objective score. |
| Best trial | Persisted trial ID, such as `T15`, that currently owns the best objective score. |
| PPO reward mean | Latest Ray/RLlib PPO trainer reward mean, if available. |
| Orange objective line | Raw Optuna objective value per trial. It may go down because exploration is expected. |
| Green stepped line | Best-so-far objective. This is the clearest dashboard signal that learning/meta-optimization is improving. It only rises when a trial beats the previous best. |
| Trial rail | Compact timeline of recent trials. Green-highlighted cells mark new-best events; the strongest outlined cell is the current best. |

Interpretation:

| Pattern | Meaning |
|---|---|
| Green stepped line rises repeatedly | Optuna is finding better reward weights. |
| Orange line fluctuates while green line stays flat | Optuna is exploring, but has not found a new best recently. |
| `plateau watch` | The best trial is no longer recent; more trials or wider search may be needed. |
| PPO reward mean appears | Ray/RLlib produced a policy-training signal; compare it with Optuna progress rather than treating it as the same metric. |

## Optuna Panel

Optuna is the Layer 5 meta-optimizer. The dashboard separates objective score from reward-weight parameter traces.

| UI element | Meaning |
|---|---|
| Study name | Usually `visualized_orchestrator_reward_weights`. |
| `alpha`, `beta`, `gamma` cards | Best trial's reward weights. |
| Objective score graph | The single scalar objective Optuna maximizes. It has one line because there is one objective value. |
| Weight graph | Trial-by-trial sampled `alpha`, `beta`, and `gamma` values, drawn with points and end labels so each sampled parameter remains readable. |
| Optuna graph x-axis | Persisted Optuna study trial ID, such as `T0`, `T1`, and `T20`. |
| Optuna window note | Reports how many completed persisted trials are currently loaded and the visible `Tfirst` to `Tlast` range. |

The persisted Optuna study keeps counting across launches because `load_if_exists=True` reuses `orchestrator_stack/runtime/optuna/orchestrator.db`. The dashboard now exports and plots all completed trials in that persistent study, not only the latest three-trial bootstrap callback window. Therefore, if the study already contains trials `T0` through `T20`, both the objective graph and the weight graph should show the full `T0` to `T20` history after the launcher is restarted with this version of the runtime.

Search ranges:

| Parameter | Range | Meaning |
|---|---:|---|
| `alpha` | `0.5` to `2.5` | Agent A reward weight; controls safety emphasis. |
| `beta` | `0.1` to `2.0` | Agent B reward weight; controls efficiency emphasis. |
| `gamma` | `0.1` to `2.0` | Agent C reward weight; controls admission/throughput emphasis. |

If Optuna is `disabled`, `NO_TUNE=1` or fast mode may be active; this can be normal.

## Ray/RLlib Panel

| Field | Meaning |
|---|---|
| `status` | Can be `initializing`, `trained`, `disabled`, or `skipped`. |
| `train_iters` | PPO training iterations. |
| `reward_mean` | Episode reward mean from the PPO training summary, or `n/a`. |
| `checkpoint` | Training checkpoint path. |

The live dashboard primarily displays the heuristic Agent A/B/C plus Referee path. Ray/RLlib shows the PPO policy layer and training readiness; the policy action spaces are still defined per Agent A, Agent B, and Agent C.

## Artifacts Panel

| Artifact example | Meaning |
|---|---|
| `risk_model` | XGBoost risk model path. |
| `demand_model` | XGBoost demand model path. |
| `Optuna reward report` | Markdown report for the Optuna study. |
| `live Kubernetes trace` | Continuously appended live trace JSON. |
| `live launch summary` | Runtime summary JSON. |

Large generated traces/reports are not automatically committed to git.

## Event Log and Event Rail

| Event kind | Producer | Meaning |
|---|---|---|
| `stage` | `VisualizationState.stage` | Stage status transition. |
| `cluster` | `cluster_snapshot` | Node/task/SLA/risk snapshot. |
| `exercise` | live Kubernetes loop | Real exerciser-applied/deleted Kubernetes stimulus. |
| `decision` | `VisualizationState.decision` | Referee-selected action. |
| `reward` | `VisualizationState.reward` | Step reward and weighted total. |
| `optuna` | `optuna_trial`/`optuna_update` | Trial value, params, best score, status. |
| `ray` | `ray_update` | Ray/RLlib PPO status. |
| `artifact` | `artifact` | Generated artifact path. |
| `error` | `error` | Runtime failure. |

## Runtime JSON Files

| File | Description |
|---|---|
| `orchestrator_stack/runtime/visualization/state.json` | Current state snapshot read by the dashboard. |
| `orchestrator_stack/runtime/visualization/events.jsonl` | Append-only event stream used by the event log. |
| `orchestrator_stack/runtime/visualization/summary.json` | Live launch/run summary. |
| `orchestrator_stack/runtime/dashboard/server.log` | Dashboard HTTP server log. |
| `orchestrator_stack/runtime/dashboard/run.log` | Launcher/orchestrator process log. |

## Comparison Dashboard

The separate local comparison dashboard is launched with:

```bash
./orchestrator_stack/scripts/launch_cluster_comparison.sh
```

Default URL:

```text
http://127.0.0.1:8876
```

It compares `borg-experimental` against `borg-baseline` through `GET /api/comparison`.

Both clusters now receive the same shared `borg-comparison-workload` application, Service, and load generator. Differences in that namespace should come from controller behavior: baseline HPA replica movement/local Karpenter activation versus experimental Agent A/B/C orchestration. The old baseline-only `borg-baseline` workload namespace is removed by the comparison setup script on rerun.

| Section | Meaning |
|---|---|
| Behavior scorecards | Queue pressure, CPU utilization, replica reaction, and capacity reaction as paired experimental/baseline summaries. |
| Behavior difference ledger | Experimental value, baseline value, and experimental-minus-baseline delta for ready workers, pending pods, restarts, live resource usage, and requested resources. |
| Pressure timeline | Rolling five-minute view split into three synchronized lanes: pending pods, CPU/memory utilization percent, and baseline HPA current/desired/max replicas. The server retains longer history, but the visible chart stays focused on the current operating window. |
| Live resource mix | Metrics Server-backed CPU/memory usage and requested CPU/memory for each cluster, rendered as separate bars so CPU millicores and memory MiB are not blended into one misleading donut. |
| Capacity matrix | CPU request pressure, memory request pressure, and live CPU usage are sharded into separate experimental/baseline gauge rows with percentage-point deltas. This avoids mixing scheduler demand and actual usage in one compressed chart. |
| Pod phase and namespace charts | Scheduling/admission outcomes and where workload pressure is concentrated. |
| Controller reactions | Latest Agent A/B/C decision/proposals plus Ray/Optuna status versus HPA replica movement and local Karpenter active/warm nodes. |
| Node and workload inventory | Per-node readiness/schedulability/resources and the Kubernetes workload controllers discovered in both clusters. |

The `Controller reactions` panel also shows `shared intentional stimulus`. This is the latest external exerciser operation applied to both clusters. It is the comparison input, not a controller output. Agent A/B/C decisions, Referee decisions, HPA scale changes, and local Karpenter node activation are separate reactions and are not mirrored.

If HPA reads `stable at N replicas`, HPA is not broken. It means the latest `currentReplicas` and `desiredReplicas` match after HPA has already reacted. Use the dedicated HPA replica lane plus the `Baseline Autoscalers` table to see earlier scale movement, CPU target, replica headroom, and last scale time.

This dashboard is local-only. HPA is real Kubernetes HPA; Karpenter behavior is represented by the local Kind warm-node controller because upstream AWS Karpenter requires cloud provider APIs.

## Common Misreadings

| Display | Correct interpretation |
|---|---|
| `est power ...W` | Calibrated utilization-derived estimate, not direct wattmeter power. |
| `Optuna Best` | Best objective score, not the alpha/beta/gamma values themselves. |
| `Ray Status: trained` | PPO bootstrap/training completed; live decisions still need to be interpreted with the heuristic/referee path unless a PPO executor is explicitly used. |
| `AgentB dominates` | Low demand or weak safety/admission conditions can make Agent B's efficiency actions win repeatedly. |
| Negative total reward | SLA violations, dead tasks, wrong admission, or efficiency action under high demand can make weighted reward negative. |

## Dashboard Change Checklist

1. Run `node --check orchestrator_stack/dashboard/app.js`.
2. Run `PYTHONPATH=orchestrator_stack .venv/bin/pytest orchestrator_stack/tests/test_visualization_runtime.py -q`.
3. When possible, run a desktop-width Chrome headless screenshot or browser smoke test.
4. Update this document and `docs/ko/DASHBOARD_GUIDE.md` together.
5. If launch behavior changes, update `docs/ORCHESTRATION_LAUNCH.md` and `README.md`.
