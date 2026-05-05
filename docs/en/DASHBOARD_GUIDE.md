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

## Launch and Data Flow Summary

The live dashboard is normally launched with the full orchestration stack:

```bash
cd /Users/theokim/Documents/github/kyunghee/Borg-Agent-Orchestrator && LIVE_K8S=1 KUBECONFIG=~/Documents/aiopslab_validation_env/kubeconfig ./orchestrator_stack/scripts/launch_orchestration.sh
```

The live-mode flow is:

| Step | Layer | Runtime behavior | Dashboard location |
|---:|---|---|---|
| 1 | Layer 1 Kubernetes Source | Reads node/pod state with `kubectl`; optionally merges Prometheus CPU/memory samples. | Metrics, Kubernetes Cluster card, `cluster` events |
| 2 | Live Perturbation | Applies or deletes safe synthetic workloads in the `borg-orchestrator-exercise` namespace. | Workload Exerciser card, Intentional Kubernetes Stimulus card, `exercise` events |
| 3 | Layer 2 AIOpsLab Twin | Converts the snapshot into an `Observation` and computes twin transitions/rewards after selected actions. | AIOpsLab Twin card, Reward Stream |
| 4 | Layer 3 XGBoost Brains | Enriches risk and demand forecasts, or uses telemetry-derived values if XGBoost is unavailable. | XGBoost Brains card, Max Risk, Decision Reason |
| 5 | Layer 4 Agents | Agent A/B/C produce safety, efficiency, and admission proposals. | Agent A/B/C cards, State Vector card, proposal chips |
| 6 | Referee | Selects one final action with safety-first conflict resolution. | Current Decision, Decision Gate, Performed Action |
| 7 | Layer 6 Scoreboard | Computes per-agent raw reward and weighted total reward. | Reward Stream, Global Scoreboard, Last Reward |
| 8 | Layer 5 Optuna | Searches reward weights `alpha`, `beta`, and `gamma`. | Optuna card, objective graph, weight graph |
| 9 | Ray/RLlib | Bootstraps/trains the multi-agent PPO policy. | Ray Status, Ray/RLlib panel, Ray RLlib PPO Policy card |

## Live Kubernetes Environment

The current live orchestration target is a local Kind validation cluster, not a managed cloud Kubernetes cluster or a production multi-node deployment. The exact inspected environment is recorded in `reports/evaluations/202605051249_kubernetes_environment_snapshot.md`.

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
| `observe` | Intended observability namespace; currently no running observability pods in the inspected snapshot. |
| `test-social-network` | DeathStarBench/AIOpsLab namespace; currently no active social-network resources in the inspected snapshot. |

Important runtime caveats:

| Item | Current status | Dashboard implication |
|---|---|---|
| Metrics Server | Not available; `kubectl top nodes/pods` fails. | The dashboard cannot currently rely on Metrics API samples. |
| In-cluster Prometheus | No running Prometheus pods were observed. | Prometheus enrichment is absent unless an external `PROMETHEUS_BASE_URL` is provided. |
| `observe/prometheus-pvc` | Pending because it requests missing storage class `openebs-hostpath`. | The observability stack is not fully deployed in this Kind cluster. |
| Energy watts | Estimated by the default utilization model. | `est power ...W` is not a physical wattmeter reading. |
| Agent placement realism | Single-node cluster. | Agent C admission logic is visible, but true multi-node placement/migration behavior cannot be demonstrated here. |

The live exerciser does perform real Kubernetes mutations. For example, it creates `pause` Deployments such as `moderate-demand`, `high-risk`, and `bursty-safety` under `borg-orchestrator-exercise`. Those Deployments can create real scheduler outcomes such as `Pending` pods and `FailedScheduling: Insufficient cpu`. The dashboard therefore mixes:

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
| Layer 1 | Kubernetes Cluster | `risk ...` | Highest risk score in the current cluster snapshot; also shows nodes/tasks/SLA. |
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
| Intentional Kubernetes Stimulus | Real synthetic workload mutation applied to the cluster. | phase, namespace, operation, CPU request, memory request, rollout return code |
| Performed Action | Final Referee-selected orchestration decision. | selected agent/action, route, target, payload, proposal chips |

Stimulus operations:

| Operation | Runtime meaning |
|---|---|
| `apply` | Applies an exercise Deployment manifest with `kubectl apply -f -`. |
| `delete` | Deletes exerciser Deployments in the exercise namespace using the label selector. |
| `observe` | Fallback for older events without structured fields or no stimulus yet. |

`rollout rc` is the return code of `kubectl rollout status`: `0` means success; non-zero indicates possible rollout failure, timeout, or validation failure.

## Kubernetes Stimulus Phases

When `EXERCISE_CLUSTER=1`, the exerciser rotates safe synthetic workloads. The default is randomized mode.

| Phase | Kubernetes mutation | Purpose | Fixed/random resources |
|---|---|---|---|
| `idle-efficiency` | Deletes exercise Deployments. | Creates low demand so Agent B can produce efficiency actions. | No deployment |
| `moderate-demand` | Creates a moderate-demand Deployment. | Gives Agent C/referee a non-efficiency decision opportunity. | Fixed: `8500m`, `128Mi`; random: `6500m-8800m`, `96Mi-768Mi` |
| `high-risk` | Creates a high-risk Deployment. | Pushes high requested load so Agent A's safety path activates. | Fixed: `8800m`, `3Gi`; random: `8600m-9900m`, `1536Mi-4096Mi` |
| `bursty-safety` | Creates a bursty-safety Deployment. | Produces a high CPU burst to trigger safety decisions. | Random: `9000m-10000m`, `512Mi-2048Mi` |
| `memory-pressure` | Creates a memory-pressure Deployment. | Creates memory pressure to alter demand/risk and agent selection. | Random: `4000m-7200m`, `2048Mi-5120Mi` |

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
| `migrate` | max risk `>= 0.7` and `< 0.9` | 1 | None | Moves one active task from the highest-loaded other on-node to the target; lowers source load and raises target load slightly. | `+10.0` if `p_fail > 0.75`; `-20.0` if migrating at `p_fail < 0.4`. |
| `replicate` | max risk `>= 0.9` | 2 | None | Replicates the most urgent task on the target node to the lowest-loaded other node. | `+8.0` if `p_fail > 0.85`. |

Live telemetry effects that can always affect Agent A:

| Condition | Reward change | Meaning |
|---|---:|---|
| `sla_violations > 0` | `-50.0 * sla_violations` | SLA violations are treated as safety failures. |
| Any dead task | `-100.0` | Task survival failure penalty. |

### Agent B: Efficiency Optimizer / Energy Agent

| Action | Heuristic trigger | RLlib action id | Payload | Twin transition effect | Possible reward |
|---|---|---:|---|---|---|
| `noop` | No demand projection or min demand `>= 0.45` | 0 | None | No state change. | Base `+1.0`; estimated-power telemetry bonus can still apply. |
| `dvfs` | min demand `< 0.3` | 3 | `clock_scale=0.65` | Multiplies target CPU by `clock_scale`; adjusts network by `0.9 + 0.1*clock_scale`. | Selected efficiency action gets `+5.0` when max demand `< 0.35`; `-30.0` when max demand `> 0.75`. |
| `memory_balloon` | min demand `>= 0.3` and `< 0.45` | 4 | `mem_scale=0.75` | Multiplies target memory utilization by `mem_scale`. | Same efficiency reward rule as DVFS. |
| `power_state` sleep | Not selected by heuristic; possible through RLlib policy | 1 | `state=sleep` | Sets node power state and reduces CPU/MEM utilization for sleep/off. | Same efficiency reward rule. |
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
| `admission:queue` | Not selected by heuristic; possible through RLlib policy | 1 | `decision=queue` | Increases queue length by 1. | No explicit bonus in the trace twin, but protective admission can preempt Agent B in the Referee. |
| `admission:reject` | Not selected by heuristic; possible through RLlib policy | 2 | `decision=reject` | Reduces queue length by 1. | `-20.0` when queue `< 60`. |
| `admission:deprioritize` | Not selected by heuristic; possible through RLlib policy | 3 | `decision=deprioritize` | Lowers queued task priority. | `+3.0` when queue `>= 80`. |
| `resource_cap` | queue `> 120` or overloaded nodes are at least half of all nodes | 4 | `cpu_cap=0.85`, `mem_cap=0.85` | Caps target CPU/MEM utilization at payload values. | `+4.0` when queue `>= 80`; the AIOpsLab adapter path can give `-5.0` when queue `< 80`. |

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
| Deterministic exercise cycle | `EXERCISE_RANDOMIZE=0` repeats idle/moderate/high-risk phases. |
| Randomized exercise | Default `EXERCISE_RANDOMIZE=1` randomizes phase and resource requests. |
| Live cluster saturation | A one-node/one-workload cluster can push decisions toward one agent/action. |
| Referee priority | High safety risk can repeatedly select Agent A; sustained low demand can repeatedly select Agent B. |

## Optuna Panel

Optuna is the Layer 5 meta-optimizer. The dashboard separates objective score from reward-weight parameter traces.

| UI element | Meaning |
|---|---|
| Study name | Usually `visualized_orchestrator_reward_weights`. |
| `alpha`, `beta`, `gamma` cards | Best trial's reward weights. |
| Objective score graph | The single scalar objective Optuna maximizes. It has one line because there is one objective value. |
| Weight graph | Trial-by-trial sampled `alpha`, `beta`, and `gamma` values. |

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
