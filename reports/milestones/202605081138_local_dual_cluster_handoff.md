# Local Dual-Cluster Orchestration Handoff

Timestamp: `2026-05-08 11:38 KST`

This report records the current local orchestration/comparison state so a new Codex session can resume without relying on chat history.

## Repository State

- Repository root: `/Users/theokim/Documents/github/kyunghee/Borg-Agent-Orchestrator`
- Branch: `main`
- Git policy: strict one tracked file per commit by default, recorded in `Agents.md` and `orchestrator_stack/AGENTS.md`.
- Current local comparison is intentionally local-only. No AWS environment is used.
- Known untracked runtime artifacts that were intentionally left alone:
  - `reports/traces/202605080955_episode_trace.log`
  - `reports/tuning/202605080955_optuna_visualized_orchestrator_reward_weights.md`

## Main Runbooks And Docs

| File | Purpose |
|---|---|
| `docs/LOCAL_DUAL_CLUSTER_RUNBOOK.md` | Copy-paste startup, dashboard, Prometheus, k9s, shutdown, cleanup, and delete commands. |
| `docs/LOCAL_CLUSTER_COMPARISON.md` | Conceptual local comparison guide. |
| `docs/ORCHESTRATION_LAUNCH.md` | Main orchestration launch guide. |
| `docs/en/DASHBOARD_GUIDE.md` | English dashboard explanation. |
| `docs/ko/DASHBOARD_GUIDE.md` | Korean dashboard explanation. |
| `orchestrator_stack/NEXT_STEPS.md` | Orchestrator-specific resume point. |
| `NEXT_STEPS.md` | Repository-wide resume point. |

## Completed Processes

### 1. Strict Git Commit Discipline

- Tightened repository instructions so future work commits exactly one tracked file per commit by default.
- Added pre-commit staged-file verification rule using `git diff --cached --name-only`.
- Added post-commit shape verification rule using `git show --name-only --oneline --stat HEAD`.
- Explicitly disallowed broad staging commands such as `git add .` and directory-wide staging for normal commits.

### 2. Local Multi-Node Clusters

Implemented and validated local multi-node Kind clusters:

| Cluster | Purpose | Shape | Kubeconfig |
|---|---|---|---|
| `borg-experimental` | experimental Agent A/B/C orchestrator | 1 control-plane + 3 workers | `~/Documents/borg_orchestrator_clusters/kubeconfig-experimental` |
| `borg-baseline` | HPA + local Karpenter-style baseline | 1 control-plane + 3 workers | `~/Documents/borg_orchestrator_clusters/kubeconfig-baseline` |
| `borg-aiopslab` | older AIOpsLab validation cluster, now multi-node too | 1 control-plane + 3 workers | `~/Documents/aiopslab_validation_env/kubeconfig` |

Tracked configs/scripts:

- `orchestrator_stack/k8s/kind/experimental-multinode.yaml`
- `orchestrator_stack/k8s/kind/baseline-hpa-karpenter-multinode.yaml`
- `orchestrator_stack/k8s/kind/aiopslab-multinode.yaml`
- `orchestrator_stack/scripts/create_local_comparison_clusters.sh`
- `orchestrator_stack/scripts/setup_kind_cluster.sh`

### 3. Baseline HPA + Local Karpenter-Style Capacity

Implemented the local baseline cluster with:

- real Kubernetes `autoscaling/v2` HPA over `borg-baseline/hpa-web`
- `hpa-load-generator` to create CPU pressure
- `karpenter-surge` workload for capacity pressure
- local Kind Karpenter-style controller that activates warm workers by uncordoning and removing the warm taint

Important boundary:

- HPA is real Kubernetes HPA.
- Karpenter is not AWS Karpenter. It is a local emulation over pre-created Kind workers because upstream Karpenter needs cloud provider APIs.

Tracked files:

- `orchestrator_stack/k8s/baseline/hpa-workload.yaml`
- `orchestrator_stack/k8s/baseline/karpenter-surge-workload.yaml`
- `orchestrator_stack/scripts/local_karpenter_controller.py`
- `orchestrator_stack/scripts/apply_baseline_surge.sh`

### 4. Observability

The comparison clusters are bootstrapped with:

- Metrics Server in `kube-system`
- Prometheus in `observe`
- Node Exporter in `observe`

Relevant commands and URLs are in `docs/LOCAL_DUAL_CLUSTER_RUNBOOK.md`.

Default URLs when port-forwarded:

| Component | URL |
|---|---|
| Experimental Prometheus | `http://127.0.0.1:19090` |
| Baseline Prometheus | `http://127.0.0.1:19091` |

### 5. Experimental Orchestration Dashboard

The experimental orchestration launch command is:

```bash
./orchestrator_stack/scripts/launch_experimental_multinode_orchestration.sh
```

Default dashboard:

```text
http://127.0.0.1:8765
```

It writes state and events to:

```text
orchestrator_stack/runtime/visualization-experimental/state.json
orchestrator_stack/runtime/visualization-experimental/events.jsonl
```

### 6. Comparison Dashboard

The comparison dashboard launch command is:

```bash
./orchestrator_stack/scripts/launch_cluster_comparison.sh
```

Default dashboard:

```text
http://127.0.0.1:8876
```

Dashboard now includes:

- behavior scorecards
- experimental-minus-baseline difference ledger
- pending/CPU/memory pressure timeline
- live resource mix from `kubectl top`
- request-vs-capacity visualization
- pod phase distribution
- namespace distribution
- controller reaction panel
- shared intentional stimulus panel
- node inventory
- workload inventory
- HPA and local Karpenter state

Tracked files:

- `orchestrator_stack/orchestrator/comparison_dashboard_server.py`
- `orchestrator_stack/comparison_dashboard/index.html`
- `orchestrator_stack/comparison_dashboard/styles.css`
- `orchestrator_stack/comparison_dashboard/app.js`

### 7. Mirrored Intentional Stimuli

Implemented exact comparison input semantics:

Mirrored to both clusters:

- exerciser workload creation/deletion
- namespace
- deployment name
- CPU request
- memory request
- replica count
- node selector
- exercise phase identity

Not mirrored, because these are controller reactions:

- Agent A/B/C decisions
- Referee choices
- HPA replica changes
- local Karpenter active/warm node changes

Manual shared stimulus command:

```bash
PHASE_INDEX=1 ./orchestrator_stack/scripts/apply_comparison_stimulus.sh
```

Tracked files:

- `orchestrator_stack/orchestrator/layer1/kubernetes_exerciser.py`
- `orchestrator_stack/orchestrator/visualization.py`
- `orchestrator_stack/orchestrator/cli.py`
- `orchestrator_stack/scripts/apply_comparison_stimulus.sh`
- `orchestrator_stack/scripts/launch_orchestration.sh`
- `orchestrator_stack/scripts/launch_experimental_multinode_orchestration.sh`

Live smoke already performed:

- Applied `PHASE_INDEX=1`.
- Verified both clusters had `borg-orchestrator-exercise/light-dvfs` with:
  - `replicas=1`
  - `cpu=2200m`
  - `memory=256Mi`
- Comparison API reported:
  - `shared_stimulus.phase=light-dvfs`
  - `shared_stimulus.mirror_count=1`

### 8. Operational Runbook

Created:

```text
docs/LOCAL_DUAL_CLUSTER_RUNBOOK.md
```

It includes:

- creating both clusters
- recreating both clusters
- starting experimental orchestration
- starting comparison dashboard
- Prometheus port-forward links
- k9s commands for both clusters
- shared stimulus commands
- baseline HPA/Karpenter pressure commands
- stopping runtime processes
- deleting Kind clusters/Docker node containers
- quick startup sequence

### 9. Current Validation Status

Latest full test suite status after mirrored stimulus work:

```text
PYTHONPATH=orchestrator_stack ./.venv/bin/python -m pytest orchestrator_stack/tests -q
115 passed
```

Other validations run recently:

- Python compile checks on changed orchestrator modules: passed
- shell syntax checks on launch scripts: passed
- `node --check orchestrator_stack/comparison_dashboard/app.js`: passed
- comparison API smoke: passed
- live shared stimulus smoke across both clusters: passed

## Exact Startup Commands

From repository root:

```bash
cd /Users/theokim/Documents/github/kyunghee/Borg-Agent-Orchestrator
export EXPERIMENTAL_KUBECONFIG=~/Documents/borg_orchestrator_clusters/kubeconfig-experimental
export BASELINE_KUBECONFIG=~/Documents/borg_orchestrator_clusters/kubeconfig-baseline
./orchestrator_stack/scripts/create_local_comparison_clusters.sh
```

Terminal 1:

```bash
cd /Users/theokim/Documents/github/kyunghee/Borg-Agent-Orchestrator
./orchestrator_stack/scripts/launch_experimental_multinode_orchestration.sh
```

Terminal 2:

```bash
cd /Users/theokim/Documents/github/kyunghee/Borg-Agent-Orchestrator
./orchestrator_stack/scripts/launch_cluster_comparison.sh
```

Terminal 3 for baseline Prometheus:

```bash
kubectl --kubeconfig ~/Documents/borg_orchestrator_clusters/kubeconfig-baseline -n observe port-forward svc/prometheus-server 19091:80
```

Open:

| UI | URL |
|---|---|
| Experimental orchestration dashboard | `http://127.0.0.1:8765` |
| Comparison dashboard | `http://127.0.0.1:8876` |
| Experimental Prometheus | `http://127.0.0.1:19090` |
| Baseline Prometheus | `http://127.0.0.1:19091` |

## One-Liner Stop Commands

Stop host-side runtime helpers only:

```bash
pkill -f '[l]aunch_orchestration.sh|[l]aunch_experimental_multinode_orchestration.sh|[l]aunch_cluster_comparison.sh|[o]rchestrator.dashboard_server|[o]rchestrator.comparison_dashboard_server|[o]rchestrator_stack/run.py live-kubernetes-run|[l]ocal_karpenter_controller.py|[k]ubectl .*port-forward svc/prometheus-server' || true
```

Stop helpers and delete the two comparison clusters:

```bash
pkill -f '[l]aunch_orchestration.sh|[l]aunch_experimental_multinode_orchestration.sh|[l]aunch_cluster_comparison.sh|[o]rchestrator.dashboard_server|[o]rchestrator.comparison_dashboard_server|[o]rchestrator_stack/run.py live-kubernetes-run|[l]ocal_karpenter_controller.py|[k]ubectl .*port-forward svc/prometheus-server' || true; kind delete cluster --name borg-experimental; kind delete cluster --name borg-baseline
```

Stop helpers and delete all three local Kind clusters:

```bash
pkill -f '[l]aunch_orchestration.sh|[l]aunch_experimental_multinode_orchestration.sh|[l]aunch_cluster_comparison.sh|[o]rchestrator.dashboard_server|[o]rchestrator.comparison_dashboard_server|[o]rchestrator_stack/run.py live-kubernetes-run|[l]ocal_karpenter_controller.py|[k]ubectl .*port-forward svc/prometheus-server' || true; kind delete cluster --name borg-experimental; kind delete cluster --name borg-baseline; kind delete cluster --name borg-aiopslab
```

## Next Jobs

### Immediate Engineering Jobs

1. Add an experiment-runner script that runs a fixed sequence of mirrored stimuli against both clusters, records per-stimulus windows, and exports a timestamped comparison artifact.
2. Persist comparison dashboard time-series history to JSON/CSV so evidence survives browser refresh and can be cited in the thesis.
3. Add a baseline Prometheus port-forward helper to `launch_cluster_comparison.sh` or a companion script, so both Prometheus links are automatic.
4. Add dashboard export buttons or CLI exports for comparison metrics: pending pods, HPA desired/current replicas, active/warm nodes, CPU/memory usage, pod phases, namespace distribution, and Agent A/B/C action counts.
5. Add tests for `shared_stimulus.json` fallback precedence in `comparison_dashboard_server.py`.
6. Clean or intentionally track the two old untracked runtime artifacts if the user wants a pristine `git status`.

### Thesis/Evaluation Jobs

1. Run repeated shared-stimulus comparison trials with fixed seeds and report mean/std/CI for experimental vs baseline behavior.
2. Define objective comparison metrics:
   - time to clear pending pods
   - max pending pods
   - SLA/risk proxy area-under-curve
   - CPU/memory request pressure
   - CPU/memory actual usage
   - replica churn
   - node activation count
   - recovery latency after stimulus removal
3. Produce a controlled comparison report under `reports/evaluations/` for the local dual-cluster experiment.
4. Add ablation variants:
   - experimental without Agent A
   - experimental without Agent B
   - experimental without Agent C
   - baseline HPA only without local Karpenter-style capacity
   - baseline local Karpenter only without HPA load scaling
5. Add stronger visualization of behavior differences over time, including event-aligned vertical markers for each shared stimulus.

### System Fidelity Jobs

1. Replace estimated `energy_watts` with measured power if a local exporter such as Kepler/RAPL becomes available.
2. Improve local Karpenter emulation fidelity by recording activation latency, consolidation latency, and pending-pod trigger reasons.
3. Add a clearer local-Karpenter caveat directly inside the comparison dashboard so thesis viewers do not confuse it with AWS Karpenter.
4. Validate that the mirrored stimuli produce sufficiently diverse Agent A/B/C actions over long runs; tune exerciser phases if one agent dominates.
5. Add a cluster reset command that clears workloads, resets baseline HPA/surge replicas, rewarm-taints baseline workers, and clears runtime state without deleting clusters.

### Documentation Jobs

1. Keep `docs/LOCAL_DUAL_CLUSTER_RUNBOOK.md` synchronized whenever launch ports, paths, or shutdown behavior changes.
2. Keep `docs/en/DASHBOARD_GUIDE.md` and `docs/ko/DASHBOARD_GUIDE.md` synchronized whenever dashboard sections or field semantics change.
3. Add screenshots or rendered dashboard captures to a thesis appendix once the comparison dashboard UI stabilizes.
4. Add a short `README` quick link near the top for the local dual-cluster runbook.

## Recommended Resume Prompt

```text
Read Agents.md, NEXT_STEPS.md, orchestrator_stack/NEXT_STEPS.md, docs/LOCAL_DUAL_CLUSTER_RUNBOOK.md, and reports/milestones/202605081138_local_dual_cluster_handoff.md. Continue from the next local dual-cluster comparison job. Preserve one-file-per-commit discipline.
```
