# Launching the Full Orchestration Architecture

This repository now has one launch shell for the whole implemented orchestration path plus live visualization.

## Top One-Liners

Start the full local dual-cluster orchestration and comparison stack:

```bash
cd /Users/theokim/Documents/github/kyunghee/Borg-Agent-Orchestrator && ./orchestrator_stack/scripts/start_local_dual_cluster_stack.sh
```

Stop the full local dual-cluster stack, including the Kind Docker node containers:

```bash
cd /Users/theokim/Documents/github/kyunghee/Borg-Agent-Orchestrator && ./orchestrator_stack/scripts/stop_local_dual_cluster_stack.sh
```

Open k9s for the experimental cluster:

```bash
KUBECONFIG=~/Documents/borg_orchestrator_clusters/kubeconfig-experimental k9s
```

Open k9s for the HPA/local-Karpenter baseline cluster:

```bash
KUBECONFIG=~/Documents/borg_orchestrator_clusters/kubeconfig-baseline k9s
```

## One Command

From repository root:

```bash
./orchestrator_stack/scripts/launch_orchestration.sh
```

This is the finite thesis demo mode. It runs one full pass over the configured trace plus Ray/RLlib and Optuna bootstrap work.

## Copy-Paste Live Kubernetes Launch

Use this exact block from any terminal. It includes `cd`, so it does not depend on your current directory. This is the preferred multi-node local launch path:

```bash
cd /Users/theokim/Documents/github/kyunghee/Borg-Agent-Orchestrator

./orchestrator_stack/scripts/create_local_comparison_clusters.sh
./orchestrator_stack/scripts/launch_experimental_multinode_orchestration.sh
```

One-line version:

```bash
cd /Users/theokim/Documents/github/kyunghee/Borg-Agent-Orchestrator && ./orchestrator_stack/scripts/create_local_comparison_clusters.sh && ./orchestrator_stack/scripts/launch_experimental_multinode_orchestration.sh
```

Do not write `\./orchestrator_stack/...`; the backslash must end the previous line, not touch the command path.

The launcher uses `~/Documents/borg_orchestrator_clusters/kubeconfig-experimental`, which is a local Kind cluster with one control-plane and three workers. `LIVE_K8S=1` keeps capturing real Kubernetes snapshots, selecting Agent A/B/C/referee actions, scoring rewards, appending `live_kubernetes_trace.json`, and refreshing the dashboard until you press `Ctrl-C`.

For exact local comparison, `launch_experimental_multinode_orchestration.sh` also mirrors each intentional exercise phase to `~/Documents/borg_orchestrator_clusters/kubeconfig-baseline`. Only the external stimulus is mirrored. Controller reactions are intentionally not mirrored:

- mirrored: exerciser workload create/delete operations, CPU/memory request, replica count, node selector, and namespace
- not mirrored: Agent A/B/C actions, Referee decisions, HPA scaling, and local Karpenter warm-node activation/consolidation

Manual shared stimulus command:

```bash
PHASE_INDEX=3 ./orchestrator_stack/scripts/apply_comparison_stimulus.sh
```

If you specifically need the older AIOpsLab validation kubeconfig, recreate it as multi-node before use:

```bash
RECREATE=1 ./orchestrator_stack/scripts/setup_kind_cluster.sh
```

That writes `~/Documents/aiopslab_validation_env/kubeconfig` for a local Kind cluster with one control-plane and three workers.

By default, live mode also bootstraps in-cluster observability before the control loop starts:

- Metrics Server in `kube-system`, including `v1beta1.metrics.k8s.io`
- Prometheus in the `observe` namespace
- Node Exporter as a DaemonSet on the Kind node
- a local Prometheus port-forward at `http://127.0.0.1:19090`

The launcher passes that Prometheus URL into `live-kubernetes-run`, so live trace rows should include `prometheus_node_exporter` in `telemetry_sources` when the stack is healthy.

Live mode defaults to `MODE=full`: Ray/RLlib policy bootstrap and Optuna reward tuning run before the continuous Kubernetes loop. Use the repository `.venv` Python for this full mode because it contains Ray, Optuna, XGBoost, and Torch.

Live mode also defaults to `EXERCISE_CLUSTER=1`. The launcher rotates safe synthetic Kubernetes workloads in the dedicated `borg-orchestrator-exercise` namespace so the live cluster does not stay idle. The rotation intentionally covers distinct action families: Agent B `power_state`, `dvfs`, and `memory_balloon`; Agent A `throttle`, `migrate`, and `replicate`; and Agent C `admission:queue`, `admission:deprioritize`, and `resource_cap`.

What it does:

1. Applies `orchestrator_stack/k8s/observability/metrics-prometheus.yaml` when `LIVE_K8S=1` and `OBSERVABILITY_STACK=1`.
2. Waits for Metrics Server, `kubectl top nodes`, Prometheus, and Node Exporter.
3. Starts a local Prometheus port-forward unless `PROMETHEUS_BASE_URL` is already provided.
4. Starts the local visualization dashboard at `http://127.0.0.1:8765`.
5. Opens the dashboard automatically on macOS.
6. Loads or builds the Layer 1 trace from `orchestrator_stack/config/orchestrator.example.json`.
7. Trains the Layer 3 XGBoost risk and demand models.
8. Runs the Layer 4 multi-agent heuristic/referee episode and streams per-step rewards.
9. Runs Ray/RLlib PPO training and streams Ray status plus final checkpoint/reward metadata.
10. Runs Optuna reward tuning and streams trial scores/parameters.
11. Writes runtime state and summary files under `orchestrator_stack/runtime/visualization/`.

After the orchestration run finishes, the dashboard stays open. Press `Ctrl-C` in the shell to stop the dashboard server.

## Dashboard

Default URL:

```text
http://127.0.0.1:8765
```

Detailed dashboard interpretation guides:

- English: `docs/en/DASHBOARD_GUIDE.md`
- Korean: `docs/ko/DASHBOARD_GUIDE.md`

The dashboard shows:

- current orchestration stage
- per-step reward stream for Agent A, Agent B, Agent C, and weighted total score
- learning-progress view with Optuna best-so-far lift, new-best events, trial timeline, and PPO reward mean
- Optuna study name, full completed persistent-trial history, latest trial, best score, and best parameters
- Ray/RLlib PPO trainer status, checkpoint path, train iterations, and reward mean
- generated artifacts, including trace/model/report/summary paths
- live event log from the runtime JSONL stream

## Local Multi-Node Comparison Mode

For local thesis comparison without AWS, use the dedicated local comparison stack:

```bash
./orchestrator_stack/scripts/create_local_comparison_clusters.sh
./orchestrator_stack/scripts/launch_experimental_multinode_orchestration.sh
./orchestrator_stack/scripts/launch_cluster_comparison.sh
```

This creates two separate multi-node Kind clusters:

- `borg-experimental`: the experimental orchestrator cluster.
- `borg-baseline`: a baseline cluster with real Kubernetes HPA and a local Karpenter-style warm-node controller.

The comparison dashboard runs at:

```text
http://127.0.0.1:8876
```

Full guide: `docs/LOCAL_CLUSTER_COMPARISON.md`.

Runtime files:

```text
orchestrator_stack/runtime/visualization/state.json
orchestrator_stack/runtime/visualization/events.jsonl
orchestrator_stack/runtime/visualization/summary.json
orchestrator_stack/runtime/dashboard/server.log
orchestrator_stack/runtime/dashboard/run.log
orchestrator_stack/runtime/dashboard/prometheus-port-forward.log
```

## Common Options

Use a different config:

```bash
CONFIG=orchestrator_stack/config/aiopslab_prometheus_mitigation_kind.json \
./orchestrator_stack/scripts/launch_orchestration.sh
```

Use more Optuna trials:

```bash
TRIALS=10 ./orchestrator_stack/scripts/launch_orchestration.sh
```

Enable Ray/RLlib bootstrap in live Kubernetes mode:

```bash
LIVE_K8S=1 NO_POLICY=0 ./orchestrator_stack/scripts/launch_orchestration.sh
```

Enable Optuna bootstrap in live Kubernetes mode:

```bash
LIVE_K8S=1 NO_TUNE=0 ./orchestrator_stack/scripts/launch_orchestration.sh
```

Fast live Kubernetes mode without Ray/RLlib or Optuna:

```bash
MODE=fast LIVE_K8S=1 ./orchestrator_stack/scripts/launch_orchestration.sh
```

Disable synthetic cluster exercise and only observe existing workloads:

```bash
LIVE_K8S=1 EXERCISE_CLUSTER=0 ./orchestrator_stack/scripts/launch_orchestration.sh
```

Change exercise cadence:

```bash
LIVE_K8S=1 EXERCISE_INTERVAL_ITERATIONS=2 ./orchestrator_stack/scripts/launch_orchestration.sh
```

Use deterministic action-coverage exercise phases for debugging:

```bash
LIVE_K8S=1 EXERCISE_RANDOMIZE=0 ./orchestrator_stack/scripts/launch_orchestration.sh
```

Use reproducible randomized exercise phases:

```bash
LIVE_K8S=1 EXERCISE_SEED=42 ./orchestrator_stack/scripts/launch_orchestration.sh
```

Use another port:

```bash
PORT=8899 ./orchestrator_stack/scripts/launch_orchestration.sh
```

Run live Kubernetes loop every 5 seconds:

```bash
LIVE_K8S=1 INTERVAL_SECONDS=5 ./orchestrator_stack/scripts/launch_orchestration.sh
```

Run only 20 live Kubernetes iterations:

```bash
LIVE_K8S=1 LIVE_MAX_ITERATIONS=20 ./orchestrator_stack/scripts/launch_orchestration.sh
```

Use a different local Prometheus port-forward port:

```bash
LIVE_K8S=1 PROMETHEUS_PORT=19091 ./orchestrator_stack/scripts/launch_orchestration.sh
```

Use an existing Prometheus endpoint instead of the launcher's local port-forward:

```bash
LIVE_K8S=1 PROMETHEUS_BASE_URL=http://127.0.0.1:19090 ./orchestrator_stack/scripts/launch_orchestration.sh
```

Skip observability bootstrap only when Metrics Server, Prometheus, and Node Exporter are already installed:

```bash
LIVE_K8S=1 OBSERVABILITY_STACK=0 ./orchestrator_stack/scripts/launch_orchestration.sh
```

Start the observability stack manually:

```bash
KUBECONFIG=~/Documents/aiopslab_validation_env/kubeconfig ./orchestrator_stack/scripts/bootstrap_observability.sh
```

Do not open browser automatically:

```bash
OPEN_BROWSER=0 ./orchestrator_stack/scripts/launch_orchestration.sh
```

Exit immediately after the run instead of keeping the dashboard server alive:

```bash
KEEP_DASHBOARD=0 ./orchestrator_stack/scripts/launch_orchestration.sh
```

Fast dashboard smoke without Ray/RLlib or Optuna:

```bash
NO_POLICY=1 NO_TUNE=1 KEEP_DASHBOARD=0 ./orchestrator_stack/scripts/launch_orchestration.sh
```

Use a specific Python binary:

```bash
PYTHON_BIN=~/Documents/aiopslab_validation_env/bin/python \
./orchestrator_stack/scripts/launch_orchestration.sh
```

Only use the AIOpsLab validation Python when you specifically need upstream AIOpsLab package imports. For the full repository architecture with Ray/Optuna/XGBoost, prefer the default `./.venv/bin/python`.

## Live Kubernetes / AIOpsLab Mode

For live cluster evidence mode, point `CONFIG` to a config backed by traces collected from the Kind/AIOpsLab run and use your kube context for preflight/collection commands. Add `LIVE_K8S=1` when you want the dashboard to keep evaluating the live cluster instead of ending after one finite demo pass:

```bash
LIVE_K8S=1 \
KUBECONFIG=~/Documents/aiopslab_validation_env/kubeconfig \
CONFIG=orchestrator_stack/config/aiopslab_prometheus_mitigation_kind.json \
./orchestrator_stack/scripts/launch_orchestration.sh
```

Important: upstream AIOpsLab problem sessions are bounded tasks, so the infinite part is the repository control loop over the live Kubernetes cluster state. The loop continuously observes Kubernetes/AIOpsLab-deployed workloads, chooses orchestration actions, computes rewards, and updates the dashboard. Fault injection and individual AIOpsLab task sessions remain finite unless a separate scenario runner restarts them.

Before live mode, verify the cluster once:

```bash
RECREATE=1 orchestrator_stack/scripts/setup_kind_cluster.sh
orchestrator_stack/scripts/setup_aiopslab_env.sh

KUBECONFIG=~/Documents/aiopslab_validation_env/kubeconfig \
PYTHONPATH=orchestrator_stack ~/Documents/aiopslab_validation_env/bin/python \
  orchestrator_stack/run.py aiopslab-preflight \
  --kube-config ~/Documents/aiopslab_validation_env/kubeconfig
```

To verify the live telemetry stack directly:

```bash
KUBECONFIG=~/Documents/aiopslab_validation_env/kubeconfig kubectl get apiservice v1beta1.metrics.k8s.io
KUBECONFIG=~/Documents/aiopslab_validation_env/kubeconfig kubectl top nodes
KUBECONFIG=~/Documents/aiopslab_validation_env/kubeconfig kubectl -n observe get pods,svc -l app.kubernetes.io/part-of=borg-orchestrator
```

## Architecture Update Rule

When `docs/repository_architecture.mmd` or any real orchestration layer changes, keep these files synchronized in the same work session:

- `orchestrator_stack/scripts/launch_orchestration.sh`
- `orchestrator_stack/scripts/bootstrap_observability.sh`
- `orchestrator_stack/k8s/observability/metrics-prometheus.yaml`
- `docs/ORCHESTRATION_LAUNCH.md`
- `orchestrator_stack/dashboard/index.html`
- `orchestrator_stack/dashboard/app.js`
- `orchestrator_stack/dashboard/styles.css`
- `docs/en/DASHBOARD_GUIDE.md`
- `docs/ko/DASHBOARD_GUIDE.md`

The launch shell is the canonical simple operator path. If the architecture gains a new runtime stage, expose that stage in the shell and dashboard state stream.
