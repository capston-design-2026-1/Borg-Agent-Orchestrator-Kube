# Launching the Full Orchestration Architecture

This repository now has one launch shell for the whole implemented orchestration path plus live visualization.

## One Command

From repository root:

```bash
./orchestrator_stack/scripts/launch_orchestration.sh
```

This is the finite thesis demo mode. It runs one full pass over the configured trace plus Ray/RLlib and Optuna bootstrap work.

For the intended continuously running Kubernetes control-loop visualization, use:

```bash
LIVE_K8S=1 \
KUBECONFIG=~/Documents/aiopslab_validation_env/kubeconfig \
PYTHON_BIN=~/Documents/aiopslab_validation_env/bin/python \
./orchestrator_stack/scripts/launch_orchestration.sh
```

`LIVE_K8S=1` keeps capturing real Kubernetes snapshots, selecting Agent A/B/C/referee actions, scoring rewards, appending `live_kubernetes_trace.json`, and refreshing the dashboard until you press `Ctrl-C`.

What it does:

1. Starts the local visualization dashboard at `http://127.0.0.1:8765`.
2. Opens the dashboard automatically on macOS.
3. Loads or builds the Layer 1 trace from `orchestrator_stack/config/orchestrator.example.json`.
4. Trains the Layer 3 XGBoost risk and demand models.
5. Runs the Layer 4 multi-agent heuristic/referee episode and streams per-step rewards.
6. Runs Ray/RLlib PPO training and streams Ray status plus final checkpoint/reward metadata.
7. Runs Optuna reward tuning and streams trial scores/parameters.
8. Writes runtime state and summary files under `orchestrator_stack/runtime/visualization/`.

After the orchestration run finishes, the dashboard stays open. Press `Ctrl-C` in the shell to stop the dashboard server.

## Dashboard

Default URL:

```text
http://127.0.0.1:8765
```

The dashboard shows:

- current orchestration stage
- per-step reward stream for Agent A, Agent B, Agent C, and weighted total score
- Optuna study name, latest trial, best score, and best parameters
- Ray/RLlib PPO trainer status, checkpoint path, train iterations, and reward mean
- generated artifacts, including trace/model/report/summary paths
- live event log from the runtime JSONL stream

Runtime files:

```text
orchestrator_stack/runtime/visualization/state.json
orchestrator_stack/runtime/visualization/events.jsonl
orchestrator_stack/runtime/visualization/summary.json
orchestrator_stack/runtime/dashboard/server.log
orchestrator_stack/runtime/dashboard/run.log
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

Use Prometheus enrichment in live Kubernetes loop:

```bash
LIVE_K8S=1 PROMETHEUS_BASE_URL=http://127.0.0.1:19090 ./orchestrator_stack/scripts/launch_orchestration.sh
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

## Live Kubernetes / AIOpsLab Mode

For live cluster evidence mode, point `CONFIG` to a config backed by traces collected from the Kind/AIOpsLab run and use your kube context for preflight/collection commands. Add `LIVE_K8S=1` when you want the dashboard to keep evaluating the live cluster instead of ending after one finite demo pass:

```bash
LIVE_K8S=1 \
KUBECONFIG=~/Documents/aiopslab_validation_env/kubeconfig \
CONFIG=orchestrator_stack/config/aiopslab_prometheus_mitigation_kind.json \
PYTHON_BIN=~/Documents/aiopslab_validation_env/bin/python \
./orchestrator_stack/scripts/launch_orchestration.sh
```

Important: upstream AIOpsLab problem sessions are bounded tasks, so the infinite part is the repository control loop over the live Kubernetes cluster state. The loop continuously observes Kubernetes/AIOpsLab-deployed workloads, chooses orchestration actions, computes rewards, and updates the dashboard. Fault injection and individual AIOpsLab task sessions remain finite unless a separate scenario runner restarts them.

Before live mode, verify the cluster once:

```bash
orchestrator_stack/scripts/setup_kind_cluster.sh
orchestrator_stack/scripts/setup_aiopslab_env.sh

KUBECONFIG=~/Documents/aiopslab_validation_env/kubeconfig \
PYTHONPATH=orchestrator_stack ~/Documents/aiopslab_validation_env/bin/python \
  orchestrator_stack/run.py aiopslab-preflight \
  --kube-config ~/Documents/aiopslab_validation_env/kubeconfig
```

## Architecture Update Rule

When `docs/repository_architecture.mmd` or any real orchestration layer changes, keep these files synchronized in the same work session:

- `orchestrator_stack/scripts/launch_orchestration.sh`
- `docs/ORCHESTRATION_LAUNCH.md`
- `orchestrator_stack/dashboard/index.html`
- `orchestrator_stack/dashboard/app.js`
- `orchestrator_stack/dashboard/styles.css`

The launch shell is the canonical simple operator path. If the architecture gains a new runtime stage, expose that stage in the shell and dashboard state stream.
