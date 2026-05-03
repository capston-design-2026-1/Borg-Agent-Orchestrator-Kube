# Launching the Full Orchestration Architecture

This repository now has one launch shell for the whole implemented orchestration path plus live visualization.

## One Command

From repository root:

```bash
./orchestrator_stack/scripts/launch_orchestration.sh
```

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

For live cluster evidence mode, point `CONFIG` to a config backed by traces collected from the Kind/AIOpsLab run and use your kube context for preflight/collection commands. The launch shell itself stays the same:

```bash
KUBECONFIG=~/Documents/aiopslab_validation_env/kubeconfig \
CONFIG=orchestrator_stack/config/aiopslab_prometheus_mitigation_kind.json \
PYTHON_BIN=~/Documents/aiopslab_validation_env/bin/python \
./orchestrator_stack/scripts/launch_orchestration.sh
```

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
