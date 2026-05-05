# Launching the Full Orchestration Architecture

This repository now has one launch shell for the whole implemented orchestration path plus live visualization.

## One Command

From repository root:

```bash
./orchestrator_stack/scripts/launch_orchestration.sh
```

This is the finite thesis demo mode. It runs one full pass over the configured trace plus Ray/RLlib and Optuna bootstrap work.

## Copy-Paste Live Kubernetes Launch

Use this exact block from any terminal. It includes `cd`, so it does not depend on your current directory:

```bash
cd /Users/theokim/Documents/github/kyunghee/Borg-Agent-Orchestrator

LIVE_K8S=1 \
KUBECONFIG=~/Documents/aiopslab_validation_env/kubeconfig \
./orchestrator_stack/scripts/launch_orchestration.sh
```

One-line version:

```bash
cd /Users/theokim/Documents/github/kyunghee/Borg-Agent-Orchestrator && LIVE_K8S=1 KUBECONFIG=~/Documents/aiopslab_validation_env/kubeconfig ./orchestrator_stack/scripts/launch_orchestration.sh
```

Do not write `\./orchestrator_stack/...`; the backslash must end the previous line, not touch the command path.

`LIVE_K8S=1` keeps capturing real Kubernetes snapshots, selecting Agent A/B/C/referee actions, scoring rewards, appending `live_kubernetes_trace.json`, and refreshing the dashboard until you press `Ctrl-C`.

Live mode defaults to `MODE=full`: Ray/RLlib policy bootstrap and Optuna reward tuning run before the continuous Kubernetes loop. Use the repository `.venv` Python for this full mode because it contains Ray, Optuna, XGBoost, and Torch.

Live mode also defaults to `EXERCISE_CLUSTER=1`. The launcher rotates safe synthetic Kubernetes workloads in the dedicated `borg-orchestrator-exercise` namespace so the live cluster does not stay idle. The rotation intentionally covers distinct action families: Agent B `power_state`, `dvfs`, and `memory_balloon`; Agent A `throttle`, `migrate`, and `replicate`; and Agent C `admission:queue`, `admission:deprioritize`, and `resource_cap`.

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

Detailed dashboard interpretation guides:

- English: `docs/en/DASHBOARD_GUIDE.md`
- Korean: `docs/ko/DASHBOARD_GUIDE.md`

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
- `docs/en/DASHBOARD_GUIDE.md`
- `docs/ko/DASHBOARD_GUIDE.md`

The launch shell is the canonical simple operator path. If the architecture gains a new runtime stage, expose that stage in the shell and dashboard state stream.
