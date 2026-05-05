# Borg-MAS-Optimizer

Project scaffold for a Borg-inspired multi-agent scheduling and cluster optimization system.

## Bilingual Documentation

Repository-level companion documents now live under:

- `docs/en`
- `docs/ko`
- `reports/en`
- `reports/ko`

The original Markdown files remain the canonical working documents, and the language directories provide organized English/Korean companion access.

## Dashboard Guide

For a detailed explanation of every dashboard panel, graph, runtime event, Agent A/B/C operation, reward rule, Optuna trace, Ray/RLlib status, and Kubernetes stimulus field, see:

- `docs/en/DASHBOARD_GUIDE.md`

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
