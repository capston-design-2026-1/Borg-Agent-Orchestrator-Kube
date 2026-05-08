# Borg-MAS-Optimizer

Project scaffold for a Borg-inspired multi-agent scheduling and cluster optimization system.

## Bilingual Documentation

Repository-level companion documents now live under:

- `docs/en`
- `docs/ko`
- `reports/en`
- `reports/ko`

The original Markdown files remain the canonical working documents, and the language directories provide organized English/Korean companion access.

## New Isolated Track: Full Orchestrator

An independent end-to-end orchestrator workspace now exists at `orchestrator_stack/`.

- Includes a 6-layer implementation matching the architecture (source -> twin -> XGBoost -> MARL/referee -> Optuna -> scoreboard)
- Keeps this work isolated from the existing baseline and advanced XGBoost tracks
- Has dedicated handoff files: `orchestrator_stack/README.md`, `orchestrator_stack/AGENTS.md`, `orchestrator_stack/NEXT_STEPS.md`
- Mermaid architecture source is tracked at `orchestrator_stack/ARCHITECTURE.md`
- Repository-wide Mermaid architecture source is tracked at `docs/repository_architecture.mmd`
- One-command orchestration launch and live visualization instructions are tracked at `docs/ORCHESTRATION_LAUNCH.md`
- Detailed dashboard interpretation guides are tracked at `docs/en/DASHBOARD_GUIDE.md` and `docs/ko/DASHBOARD_GUIDE.md`
- Repo `.venv` has verified orchestrator smoke support for reward-weight Optuna runs, Layer 4 referee/RLlib environment smoke checks, and sample predictor training
- Layer 5 policy tuning now forwards real PPO hyperparameters into RLlib-backed trials instead of scoring a placeholder learning-rate proxy; in restricted sandboxes it returns a structured skip when Ray process permissions are blocked
- Layer 1 ingestion/trace contracts are strict by default (row-indexed schema checks, `.json/.jsonl` contract validation, bool-like and non-negative queue guardrails)
- Layer 2 now normalizes AIOpsLab-style nested state payloads into the shared `Observation`/feature contract used by simulator replay, live adapters, and XGBoost feature extraction
- Layer 3 predictor inference is now attached at the backend seam so manual episodes, heuristic evaluation, RLlib training, and PPO-backed Optuna trials all consume the same XGBoost-enriched observations
- `orchestrator_stack/examples/generate_synthetic_assets.py` now derives sample matrix width from Layer 2 `FEATURE_COUNT`, so synthetic assets stay aligned with simulator/feature changes
- The latest completed reward-only Optuna artifact is `reports/tuning/202604161029_optuna_orchestrator_reward_weights.md`; the older `reports/tuning/202604142305_optuna_orchestrator_policy_and_rewards.md` predates the PPO-backed tuning rewrite and should not be treated as current validation for `tune-policy-rewards`

### Launch Orchestration + Live Visualization

Run the whole orchestration path and the dashboard together from the repository root:

```bash
./orchestrator_stack/scripts/launch_orchestration.sh
```

This starts the dashboard at `http://127.0.0.1:8765`, opens it on macOS, runs trace loading, XGBoost brains, multi-agent/referee rewards, Ray/RLlib PPO, and Optuna reward tuning, then streams state to `orchestrator_stack/runtime/visualization/`.

For the continuous Kubernetes/AIOpsLab-style control loop, use the multi-node local cluster path:

```bash
cd /Users/theokim/Documents/github/kyunghee/Borg-Agent-Orchestrator

./orchestrator_stack/scripts/create_local_comparison_clusters.sh
./orchestrator_stack/scripts/launch_experimental_multinode_orchestration.sh
```

One-line copy-paste version:

```bash
cd /Users/theokim/Documents/github/kyunghee/Borg-Agent-Orchestrator && ./orchestrator_stack/scripts/create_local_comparison_clusters.sh && ./orchestrator_stack/scripts/launch_experimental_multinode_orchestration.sh
```

Do not type `\./orchestrator_stack/...`; the `\` is only a line-continuation marker and must be separated from the next command path by a newline.

This keeps observing Kubernetes through `kubectl`, selecting Agent A/B/C/referee actions, computing rewards, appending a live trace, and refreshing the dashboard until stopped.

The older AIOpsLab validation kubeconfig can also be made multi-node locally. Recreate it with:

```bash
RECREATE=1 ./orchestrator_stack/scripts/setup_kind_cluster.sh
```

That produces one control-plane plus three Kind worker nodes under `~/Documents/aiopslab_validation_env/kubeconfig`.

In `LIVE_K8S=1` mode, the launcher now bootstraps the in-cluster observability path by default: Metrics Server in `kube-system`, Prometheus in `observe`, Node Exporter on the Kind node, and a local Prometheus port-forward at `http://127.0.0.1:19090`. The live trace collector receives this Prometheus URL automatically, so rows should include `prometheus_node_exporter` in `telemetry_sources` when the stack is healthy.

In `LIVE_K8S=1` mode, the default is `MODE=full`: Ray/RLlib and Optuna bootstrap run before the continuous Kubernetes loop. Use `MODE=fast LIVE_K8S=1` only for quick debugging without Ray/Optuna.

`LIVE_K8S=1` also enables `EXERCISE_CLUSTER=1` and `EXERCISE_RANDOMIZE=1` by default. This creates randomized safe workloads in `borg-orchestrator-exercise` so the cluster state fluctuates across explicit action-covering phases: Agent B `power_state`, `dvfs`, and `memory_balloon`; Agent A `throttle`, `migrate`, and `replicate`; and Agent C `admission:queue`, `admission:deprioritize`, and `resource_cap`. Set `EXERCISE_CLUSTER=0` to observe without synthetic workload changes, `EXERCISE_RANDOMIZE=0` to debug the deterministic coverage cycle, or `EXERCISE_SEED=<number>` for reproducible randomized phases.

Set `OBSERVABILITY_STACK=0` only if you have already installed a compatible telemetry stack. Set `PROMETHEUS_PORT=<port>` if local port `19090` is already in use, or provide `PROMETHEUS_BASE_URL=<url>` to use an existing Prometheus endpoint.

Dashboard field-by-field documentation:

- English: `docs/en/DASHBOARD_GUIDE.md`
- Korean: `docs/ko/DASHBOARD_GUIDE.md`

### Local Multi-Node HPA/Karpenter Comparison

Create two local multi-node Kind clusters for side-by-side evaluation:

```bash
./orchestrator_stack/scripts/create_local_comparison_clusters.sh
```

This creates:

- `borg-experimental`: the experimental multi-agent orchestrator cluster
- `borg-baseline`: a baseline cluster with real Kubernetes HPA plus local Karpenter-style warm-node provisioning/consolidation over pre-created Kind workers

Launch the experimental live orchestrator:

```bash
./orchestrator_stack/scripts/launch_experimental_multinode_orchestration.sh
```

Launch the comparison dashboard:

```bash
./orchestrator_stack/scripts/launch_cluster_comparison.sh
```

Default comparison dashboard URL:

```text
http://127.0.0.1:8876
```

Detailed local comparison guide: `docs/LOCAL_CLUSTER_COMPARISON.md`.

## New Isolated Track: Codex Autonomy Runner

An independent local agentic supervisor now exists at `codex_autonomy/`.

- Endless manager loop for Codex session orchestration
- YAML task queue + archive tracking
- Parallel task execution via isolated git worktrees
- Session rollover for context-budget continuation
- SQLite state/event tracking and status inspection

## Structure

```text
.
├── AGENTS.md
├── MAS_ARCHITECTURE.md
├── scripts/
│   ├── download_shards.sh
│   ├── data_flattener.py
│   ├── make_dataset.py
│   ├── make_forecaster_dataset.py
│   └── train_forecaster_baseline.py
├── src/
│   ├── agents/
│   └── environment/
├── .gitignore
└── README.md
```

Note: on this filesystem, `AGENTS.md` is stored via the existing tracked [`Agents.md`](/Users/theokim/Documents/github/kyunghee/Borg-Agent-Orchestrator/Agents.md) path because filenames are case-insensitive.

## Data Layout

Raw Borg data should stay outside the repository by default.

- Default raw data path: `~/Documents/borg_data`
- Default processed data path: `~/Documents/borg_processed`
- Advanced XGBoost workspace root: `~/Documents/borg_xgboost_workspace`

Both scripts can be overridden with environment variables:

```bash
export BORG_RAW_DIR=~/Documents/borg_data
export BORG_PROCESSED_DIR=~/Documents/borg_processed
python scripts/data_flattener.py
```

For the advanced-model track, create and use a fully separate workspace:

```bash
./scripts/setup_advanced_runtime.sh
./scripts/setup_advanced_xgboost_workspace.sh
./scripts/run_advanced_download.sh
```

That workspace keeps the second ML task isolated from the first baseline task:

- Raw downloads go to `~/Documents/borg_xgboost_workspace/raw`
- Flattened and derived parquet go to `~/Documents/borg_xgboost_workspace/processed`
- XGBoost models go to `~/Documents/borg_xgboost_workspace/models/xgboost`
- Experiment reports go to `~/Documents/borg_xgboost_workspace/reports`
- Advanced source code lives under `src/advanced_xgboost/` and dedicated entry scripts such as `scripts/build_advanced_xgboost_dataset.py` and `scripts/train_advanced_xgboost.py`

By default, the project processes clusters `b` through `g`.
Clusters `a` and `h` are excluded because their flattened usage schemas differ from the main dataset group.

To download the original single-shard sample into the default external location:

```bash
./scripts/download_shards.sh
```

To expand the raw starting set toward a bounded target size such as `100 GB`, use the byte-target mode:

```bash
BORG_DOWNLOAD_MODE=target_bytes \
BORG_TARGET_RAW_BYTES=100000000000 \
BORG_TARGET_TOLERANCE_BYTES=50000000000 \
./scripts/download_shards.sh
```

If you are running the advanced track, source the advanced env file first so this download lands in `~/Documents/borg_xgboost_workspace/raw` instead of the baseline sample directories.

If you want a one-command advanced download, just run:

```bash
./scripts/run_advanced_download.sh
```

That wrapper creates the advanced workspace if needed, creates `~/Documents/borg_xgboost_workspace/config/advanced_xgboost.env` if missing, loads it, and then starts the coherent target-based download.

For the current advanced setup, the default is now a fixed matched-shard plan rather than a byte target:

- clusters: `b` through `g`
- machine shards: `000000000000`
- event shards: first `15` per cluster
- usage shards: first `15` per cluster
- existing files are skipped automatically

This is intended to approximate the static `90 GB` plan you asked for:

- `0.5 GB` events + `0.5 GB` usage per shard index
- `15` shard indices
- `6` clusters
- about `90 GB` total, ignoring machine size

To build the separated advanced feature set and train the XGBoost failure-risk model, run:

```bash
./scripts/run_advanced_xgboost_pipeline.sh
```

That pipeline is intentionally separate from the baseline forecaster flow:

- It reads joined datasets from the advanced workspace
- It writes advanced feature parquet under `~/Documents/borg_xgboost_workspace/processed/feature_store`
- It writes XGBoost models and metrics under `~/Documents/borg_xgboost_workspace/models/xgboost`
- It keeps the same high-level target family: risk scoring for failures/errors within the configured prediction horizon
- It keeps label-valid rows with missing features, adds explicit `*_is_missing` indicators for key features, and lets XGBoost consume numeric nulls as missing values instead of dropping whole joined rows
- It now supports multiple forecast horizons from the same joined dataset and feature parquet, with default labels for `5`, `15`, `30`, `45`, and `60` minutes

You can also run the advanced stages separately:

```bash
./scripts/run_advanced_flatten.sh
./scripts/run_advanced_join.sh
./scripts/run_advanced_join_resumable.sh
./scripts/run_advanced_feature_build.sh
./scripts/run_advanced_feature_build_resumable.sh
./scripts/run_advanced_train.sh
./scripts/run_advanced_train_resumable.sh
```

For long unattended runs on the advanced track, prefer the resumable wrappers:

- `run_advanced_join_resumable.sh` skips clusters whose joined parquet already exists
- `run_advanced_feature_build_resumable.sh` skips clusters whose feature parquet already exists
- `run_advanced_train_resumable.sh` skips target horizons whose model and metrics artifacts already exist

The advanced trainer now uses bounded deterministic negative sampling so it can train on the full multi-cluster feature store within a laptop memory budget while still keeping all positive examples in each train/validation split. Default caps are:

- `BORG_XGB_MAX_TRAIN_ROWS=8000000`
- `BORG_XGB_MAX_VALID_ROWS=2000000`

Before running those stages for the first time, install the repo-local Python runtime once:

```bash
./scripts/setup_advanced_runtime.sh
```

Download behavior notes:

- Default clusters are `b` through `g`
- `sample` mode downloads shard `000000000000` for each of `events`, `usage`, and `machines`
- `target_bytes` mode builds coherent cluster slices: all machine shards for a cluster, then all event shards for that cluster, then usage shards for that same cluster
- `target_bytes` stops only after finishing a usage shard once the raw-data directory is between `target` and `target + tolerance`
- `fixed_shards` mode downloads one machine shard plus the first `N` event shards and first `N` usage shards per cluster, where `N=BORG_DOWNLOAD_SHARD_COUNT`
- `all` mode downloads every matching raw shard for the selected clusters
- New multi-shard files are stored as `cluster_type-<shard>.json.gz`, for example `b_usage-000000000170.json.gz`
- A practical `50–150 GB` band can be expressed as `BORG_TARGET_RAW_BYTES=100000000000` and `BORG_TARGET_TOLERANCE_BYTES=50000000000`

To build joined per-window datasets for clusters `b` through `g`:

```bash
python scripts/make_dataset.py
```

When multi-shard raw downloads are present, the flattener now writes shard parquet files under `~/Documents/borg_processed/flat_shards/<kind>/<cluster>/`, and the dataset builder reads those shard directories directly.

In the advanced workspace, the equivalent path is `~/Documents/borg_xgboost_workspace/processed/flat_shards/<kind>/<cluster>/`.

To build forecaster training datasets from the joined datasets:

```bash
python scripts/make_forecaster_dataset.py
```

The forecaster builder labels a row as positive when the task's final terminal event is in the default failure set `2,3,6` and occurs within the next 15 minutes after the usage window ends.
It also writes task-history temporal features such as one-step lags, one-step deltas, and 3-window rolling means for CPU and memory usage/utilization.

To export those datasets into a platform-agnostic canonical schema that a local-cloud adapter can also target:

```bash
python scripts/export_common_forecaster_dataset.py
```

That exporter writes cluster parquet files under `~/Documents/borg_processed/datasets/forecaster/common_forecaster` by default.
The canonical schema keeps stable fields such as workload ID, node ID, window timing, observed/requested CPU and memory, temporal features, and failure labels without depending on Borg-specific column names.

To build the same canonical schema from local-cloud telemetry, prepare a parquet or CSV file plus a column-mapping JSON file and run:

```bash
python scripts/build_local_common_forecaster_dataset.py \
  --input ~/Documents/local_cloud/telemetry.parquet \
  --output ~/Documents/local_cloud/common_forecaster.parquet \
  --mapping config/local_common_forecaster.example.json \
  --source-platform local_cloud
```

The example mapping file at [`config/local_common_forecaster.example.json`](/Users/theokim/Documents/github/kyunghee/Borg-Agent-Orchestrator/config/local_common_forecaster.example.json) shows the expected `canonical_name -> raw_column` structure.

To train and evaluate the first Polars-only forecasting baseline:

```bash
python scripts/train_forecaster_baseline.py
```

The trainer supports named feature profiles through `BORG_BASELINE_PROFILE`:

- `base` keeps the strongest average-precision baseline and is the default.
- `base_plus_roll` adds rolling-mean temporal features and improves the top-risk alert slice.
- `temporal_full` adds lag, delta, and rolling temporal features for broader experimentation.

Example:

```bash
BORG_BASELINE_PROFILE=base_plus_roll \
BORG_BASELINE_DIR=~/Documents/borg_processed/datasets/forecaster/baseline_base_plus_roll \
python scripts/train_forecaster_baseline.py
```

The baseline trainer writes:

- `metrics.json`
- `weights.json`
- `cluster_metrics.json`
- `feature_ranking.json`
- `validation_predictions.parquet`
- `top_risk_alerts.parquet`

under `~/Documents/borg_processed/datasets/forecaster/baseline` by default.

## Python Environment

Use a project-local virtual environment in PyCharm and install dependencies from the repo metadata:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```
