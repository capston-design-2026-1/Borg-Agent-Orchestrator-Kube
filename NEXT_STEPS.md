# Session Handoff

This file is the resume point for a new Codex session in this repository.

## Resume Prompt

Use this prompt after launching Codex from the repo root:

```text
Read Agents.md, NEXT_STEPS.md, MAS_ARCHITECTURE.md, and README.md, inspect the latest commits, and continue from the next logical step.
```

## Current State

- Repo root: `/Users/theokim/Documents/github/kyunghee/Borg-Agent-Orchestrator`
- Primary branch: `main`
- Raw data location: `~/Documents/borg_data`
- Processed data location: `~/Documents/borg_processed`
- Advanced XGBoost workspace: `~/Documents/borg_xgboost_workspace`
- Advanced runtime: repo-local `.venv` is prepared and verified with `polars 1.39.3` and `xgboost 2.1.4`
- Isolated full orchestrator track: `orchestrator_stack/` (new, dedicated)
- Orchestrator Mermaid architecture is now tracked at `orchestrator_stack/ARCHITECTURE.md`
- Orchestrator CLI now supports full flow: `build-trace -> train-brains -> run -> full-process`
- Orchestrator full-process now runs with real Ray PPO + Optuna in repo `.venv` (smoke profile)
- Codex autonomy runner is now available under `codex_autonomy/` for continuous multi-session execution
- Default working clusters: `b`, `c`, `d`, `e`, `f`, `g`
- Excluded by default: `a`, `h`
- Orchestrator Layer 1 ingestion path now enforces stricter row-by-row schema validation for metrics -> trace build and trace `.json/.jsonl` load contracts, including bool-like coercion checks, non-negative queue fields, positive bucket interval checks, and missing-source detection (implemented 2026-04-15 KST in `orchestrator_stack/`).
- Orchestrator Layer 2 now normalizes AIOpsLab-style nested simulator payloads into the shared `Observation` contract for replay and feature extraction, and the fallback AIOpsLab backend now simulates stateful steps locally; direct upstream package/session validation remains open, and this worktree runtime still cannot run repo pytest because `.venv` is a self-referential symlink while system `python3` is missing `numpy` and `pytest` (2026-04-16 KST).
- Orchestrator Layer 5 now pushes sampled reward weights and PPO hyperparameters through the real policy-training path, with config support for PPO batch/epoch knobs and a dedicated unit test covering trainer invocation. Reward-only Optuna tuning is validated end-to-end in the repo `.venv`; PPO-backed policy tuning reaches RLlib but still requires a non-sandboxed shell to complete because this macOS sandbox blocks Ray process enumeration during `ray.init()` (2026-04-16 KST).
- The latest completed orchestrator tuning artifact that matches the current validated path is `reports/tuning/202604161029_optuna_orchestrator_reward_weights.md`; the older `reports/tuning/202604142305_optuna_orchestrator_policy_and_rewards.md` was generated before the 2026-04-16 PPO-backed tuning rewrite and should be treated as historical only.
- Documentation sync for the current gate state is recorded in `reports/milestones/202604171027_orchestrator_e2e_gate_doc_sync_session1.md`.
- Architecture gap closure on 2026-04-28 KST added CSV ingestion, Prometheus export, PettingZoo parallel bridge, expanded agent action spaces, XGBoost diagnostics, PPO curriculum stages, and an explicit AIOpsLab onboarding contract adapter under `orchestrator_stack/`.
- Orchestrator validation after the 2026-04-28 architecture slice passed with `42 passed`; newer validation status is listed below.


- Follow-up validation on 2026-04-28 KST: PPO curriculum now runs locally after Ray fixes; PettingZoo bridge validated against the installed package; AIOpsLab install remains blocked in this Python 3.13 venv because upstream requires Python >=3.11,<3.13; telemetry reward fields are now implemented for future live SLA/energy/task metrics.
- Current orchestrator architecture status report: `reports/evaluations/202605020536_orchestrator_architecture_status.md`.
- Follow-up validation on 2026-05-02 KST: Layer 1 telemetry fields now survive metric rows into trace rows, and `export-brain-datasets` now writes reusable trace-derived risk/demand `.npz` matrices with feature metadata for calibration and diagnostics.
- Follow-up implementation on 2026-05-02 KST: `architecture-status` now regenerates the orchestrator architecture completion/gap report from a repeatable CLI.
- Follow-up implementation on 2026-05-02 KST: `diagnose-brain` now reports risk Brier score, expected/max calibration error, and named feature importances when given exported `.npz` datasets.
- Follow-up implementation on 2026-05-02 KST: `telemetry-reward-audit` now quantifies telemetry coverage and SLA/completion/energy reward deltas before PPO tuning.
- Follow-up implementation on 2026-05-02 KST: `train-policy` now reports `heuristic_baseline` and `policy_vs_heuristic` so PPO promotion has an explicit baseline gate.
- Follow-up implementation on 2026-05-02 KST: Python 3.12 and upstream AIOpsLab are installed in `~/Documents/aiopslab_validation_env`; `orchestrator_stack/scripts/setup_aiopslab_env.sh` now recreates that environment; adapter contract was aligned to upstream registration/parser/import behavior; live blocker is missing Kubernetes config (`KUBECONFIG` or `~/.kube/config`).
- Follow-up implementation on 2026-05-02 KST: `orchestrator_stack/examples/sample_telemetry_trace.json` and `reports/evaluations/202605020534_sample_telemetry_reward_audit.json` now provide a local telemetry reward audit fixture.
- Follow-up implementation on 2026-05-02 KST: Kind cluster `kind-borg-aiopslab` and kubeconfig `~/Documents/aiopslab_validation_env/kubeconfig` were created; live upstream AIOpsLab no-op detection ran on Kubernetes and produced `Detection Accuracy=Correct`.
- Follow-up implementation on 2026-05-02 KST: live Kind/AIOpsLab run now exports Kubernetes-derived trace rows from `kubectl get nodes/pods/jobs -A -o json`, and `reports/evaluations/202605021205_aiopslab_noop_kube_reward_audit.json` validates telemetry reward audit coverage against that real trace.
- Current orchestrator validation: `PYTHONPATH=orchestrator_stack .venv/bin/python -m pytest orchestrator_stack/tests -q` passes with `68 passed`.

## Pipeline Status

Advanced XGBoost track status:

- Advanced workspace root: `~/Documents/borg_xgboost_workspace`
- Advanced runtime wrappers now write timestamped stage logs under `~/Documents/borg_xgboost_workspace/runtime/logs`
- Latest successful advanced flatten log: `~/Documents/borg_xgboost_workspace/runtime/logs/20260331031358_advanced_flatten.log`
- Latest join log: `~/Documents/borg_xgboost_workspace/runtime/logs/20260331035719_advanced_join_resumable.log`
- Latest advanced feature-build log: `~/Documents/borg_xgboost_workspace/runtime/logs/20260331040043_advanced_feature_build.log`
- Latest advanced train log: `~/Documents/borg_xgboost_workspace/runtime/logs/20260331041159_advanced_train_resumable.log`
- Latest tuning report: `~/Documents/borg_xgboost_workspace/reports/202603311104_advanced_xgboost_tuning.json`
- Detailed event-repair log: `~/Documents/borg_xgboost_workspace/runtime/logs/20260331151302_advanced_event_repair_detailed.log`
- Detailed join-rerun log for repaired clusters: `~/Documents/borg_xgboost_workspace/runtime/logs/20260331152055_advanced_join_resumable_detailed.log`
- Detailed feature-rerun log for repaired clusters: `~/Documents/borg_xgboost_workspace/runtime/logs/20260331152830_advanced_feature_build_resumable_detailed.log`
- Current tuned retrain log: `~/Documents/borg_xgboost_workspace/runtime/logs/20260331153419_advanced_train_resumable_detailed.log`
- Advanced flatten currently completed for the fixed-shard advanced set after regenerating corrupt and failed usage parquet shards
- Current flattened advanced shard count: `186` non-`.DS_Store` parquet files
- Current advanced flatten config: `BORG_FLATTEN_WORKERS=8`, `BORG_FLATTEN_HEARTBEAT_SECONDS=10`
- Advanced flatten now uses `scan_ndjson(...).sink_parquet(...)` for shard processing and logs `started ...`, `done ...`, and `heartbeat completed=...`
- Join-stage schema mismatch is fixed in `scripts/make_dataset.py` by normalizing each shard lazily before concatenation, so mixed shard schemas no longer crash `scan_parquet`
- Advanced usage flattening bug is fixed in `scripts/data_flattener.py` by casting quoted numeric NDJSON fields after scan instead of relying on `schema_overrides` for string-backed IDs/timestamps
- Advanced join rerun is now complete for clusters `b` through `g`
- Advanced feature build is now complete for clusters `b` through `g`
- Advanced training is now complete for all configured horizons under the resumable target-by-target runner
- Latest joined row counts:
  - `b`: `62,116,886`
  - `c`: `66,758,768`
  - `d`: `64,764,425`
  - `e`: `58,784,525`
  - `f`: `71,298,784`
  - `g`: `61,083,781`
- Current feature-build label totals:
  - `b`: non-zero positives for all configured horizons
  - `c`: non-zero positives for all configured horizons
  - `d`: non-zero positives for all configured horizons
  - `e`: `5m=129,553`, `15m=175,699`, `30m=200,677`, `45m=220,331`, `60m=233,409`
  - `f`: `5m=48,677`, `15m=93,644`, `30m=148,814`, `45m=194,633`, `60m=240,144`
  - `g`: `5m=39,509`, `15m=60,618`, `30m=81,189`, `45m=97,625`, `60m=111,570`
- Final training summary:
  - `target_failure_5m`: average precision `0.9810528429`, precision@1% `0.9940523790`, recall@1% `0.3911846272`
  - `target_failure_15m`: average precision `0.9726464046`, precision@1% `0.9951022040`, recall@1% `0.3226700374`
  - `target_failure_30m`: average precision `0.9720370948`, precision@1% `0.9954522739`, recall@1% `0.2821028481`
  - `target_failure_45m`: average precision `0.9659209812`, precision@1% `0.9960021988`, recall@1% `0.2523550266`
  - `target_failure_60m`: average precision `0.9595348583`, precision@1% `0.9960519740`, recall@1% `0.2326268120`
- Tuning status:
  - Pilot sweep winner: `regularized_balanced`
  - Winner parameters: `max_depth=6`, `learning_rate=0.03`, `n_estimators=1600`, `subsample=0.9`, `colsample_bytree=0.7`, `min_child_weight=8`, `reg_alpha=0.2`, `reg_lambda=2.0`, `early_stopping_rounds=80`
  - The earlier `xgboost_failure_risk_tuned_v1` run is obsolete because it started before the `e/f/g` event-key repair and does not reflect repaired labels
  - The current repaired-label tuned retrain is running under model name `xgboost_failure_risk_tuned_v2_repaired_labels`
  - The current live process is `./scripts/run_advanced_train_resumable_detailed.sh` plus `scripts/train_advanced_xgboost.py`
  - The detailed training wrapper now preserves explicit CLI hyperparameter overrides and echoes them at the start of each target
  - The detailed training log currently starts on `target_failure_5m` and should emit XGBoost verbose-eval lines during fit once preprocessing completes

Completed stages:

1. Raw Borg shard download script
2. Raw trace flattening into per-cluster parquet
3. Joined usage/events/machine dataset builder
4. Forecaster label dataset builder
5. First Polars-only forecaster baseline trainer
6. Forecaster inspection artifact export
7. Forecaster temporal feature generation and profile evaluation
8. Canonical forecaster schema export for non-Borg adapters

Implemented scripts:

- `scripts/download_shards.sh`
- `scripts/data_flattener.py`
- `scripts/make_dataset.py`
- `scripts/make_forecaster_dataset.py`
- `scripts/export_common_forecaster_dataset.py`
- `scripts/build_local_common_forecaster_dataset.py`
- `scripts/train_forecaster_baseline.py`

Supporting docs:

- `Agents.md` for repository workflow instructions
- `MAS_ARCHITECTURE.md` for the MAS design
- `AGENT_REWARD_SYSTEM.md` for a non-ML explanation of post-training agents, actions, and rewards
- `README.md` for the user-facing workflow
- `reports/202603191933_milestone.md` for the latest milestone checkpoint
- `reports/202604011550_milestone.md` for the latest capstone-architecture milestone

## Latest Verified Outputs

Joined datasets:

- Built successfully for clusters `b` through `g`
- Location: `~/Documents/borg_processed/datasets`

Forecaster datasets:

- Built successfully for clusters `b` through `g`
- Location: `~/Documents/borg_processed/datasets/forecaster`

Canonical forecaster datasets:

- Built successfully for clusters `b` through `g`
- Location: `~/Documents/borg_processed/datasets/forecaster/common_forecaster`
- Purpose: stable workload/node/time-window schema for future local-cloud adapters

Local-cloud adapter status:

- Generic adapter script added for parquet/CSV telemetry with JSON column mapping
- Example mapping file: `config/local_common_forecaster.example.json`
- Verified with a synthetic local telemetry sample and wrote canonical parquet successfully

Local parquet documentation status:

- Schema and artifact explanation files were added beside the generated parquet and artifact directories under `~/Documents/borg_processed`
- Future parquet-producing work should continue this convention

Baseline artifacts:

- Location: `~/Documents/borg_processed/datasets/forecaster/baseline`
- Files:
  - `metrics.json`
  - `weights.json`
  - `cluster_metrics.json`
  - `feature_ranking.json`
  - `validation_predictions.parquet`
  - `top_risk_alerts.parquet`

Latest full baseline run summary:

- Total rows: `24,052,784`
- Validation rows: `4,810,777`
- Validation positives: `1,448`
- Validation positive rate: `0.0301%`
- Average precision: `0.0074076`
- Precision@0.1%: `0.0122661`
- Recall@0.1%: `0.0407459`
- Precision@1%: `0.0070676`
- Recall@1%: `0.2348066`

Alternate rolling-profile run summary:

- Profile: `base_plus_roll`
- Artifact location: `~/Documents/borg_processed/datasets/forecaster/baseline_base_plus_roll`
- Average precision: `0.0071694`
- Precision@0.1%: `0.0222453`
- Recall@0.1%: `0.0738950`
- Precision@1%: `0.0069013`
- Recall@1%: `0.2292818`

## Important Decisions

- Always make small, separate, logical commits and push them.
- Split commits aggressively by concern and file class; do not bundle code, docs, handoff, config, and policy changes together when they can be committed separately.
- Do not ask for permission before git commits and pushes.
- Keep large data outside the repository.
- Keep the first baseline ML task under `~/Documents/borg_data` and `~/Documents/borg_processed`, but keep the new advanced/XGBoost task fully isolated under `~/Documents/borg_xgboost_workspace`.
- Keep `a` and `h` excluded by default because their usage schemas differ from the main group.
- Prefer continuing to the next implementation step without waiting for explicit user prompts.
- Use KST timestamp-prefixed filenames in `reports/` with format `YYYYMMDDHHMM_*`.
- If the user types `milestone`, update the repository memory files for the completed work before ending the session.
- When a new parquet type or artifact directory is created under `~/Documents/borg_processed`, place a schema or artifact explanation file in that same directory.
- Multi-shard raw Borg downloads should be processed through `~/Documents/borg_processed/flat_shards` rather than merged eagerly into one raw parquet file per cluster.

## Repository Memory

These files should be kept current so a new Codex session behaves consistently:

- `Agents.md` for durable workflow rules and trigger terms such as `milestone`
- `NEXT_STEPS.md` for current state, next steps, and continuity notes
- `README.md` for user-facing workflow and usage changes
- `reports/` for timestamped evaluation, schema, and milestone-style session records when relevant

Latest milestone checkpoint:

- `reports/202604011550_milestone.md`
- Use it together with `Agents.md` and this file when resuming in a new Codex context
- Latest advanced handoff snapshot: `reports/202603310315_advanced_pipeline_handoff.md`

## Immediate Next Steps

The immediate next engineering work is now to let the advanced flatten run complete or tune it further if completions remain too slow, then continue the isolated advanced XGBoost pipeline end to end.

Parallel immediate track:

1. Continue `orchestrator_stack/` from `orchestrator_stack/NEXT_STEPS.md` by validating the live AIOpsLab adapter against the actual upstream package/session API and then replacing the current AIOpsLab-style fallback assumptions with a confirmed contract.
2. Replace the remaining heuristic post-training proxy in `orchestrator_stack/orchestrator/main.py` with evaluation of learned PPO policies/checkpoints.
3. Re-run `orchestrator_stack/run.py tune-policy-rewards` in a non-sandboxed shell and capture a completed post-rewrite `orchestrator_policy_and_rewards` Optuna report under `reports/`, replacing the stale 2026-04-14 artifact as the current validation reference.

Recommended next sequence:

1. Use `AGENT_REWARD_SYSTEM.md` as the shared reference for explaining the post-training agent layer to non-ML teammates and reviewers.
2. Refine the capstone top-line structure into a concrete predictor -> action -> reward architecture with a small explicit action space.
3. Define one primary object clearly, such as preventing near-term workload failure while minimizing intervention cost.
4. Translate the reward explanation into measurable replay or simulation metrics using existing Borg features and failure labels.
5. Then continue the advanced XGBoost comparison work: compare repaired-label tuned metrics against the baseline production model horizon by horizon.
6. Add explicit ROC-AUC beside average precision / PR-AUC in the trainer outputs and refresh the English/Korean reports so the metrics are labeled consistently for non-ML readers.

Current raw-data expansion note:

- The downloader supports `sample`, `target_bytes`, and `all` modes.
- `target_bytes` now builds coherent cluster slices by completing machine and event context for a cluster before adding that cluster's usage shards.
- The advanced env now defaults to `fixed_shards` with `BORG_DOWNLOAD_SHARD_COUNT=15`, which means the first `15` event and usage shards per cluster for `b` through `g`.
- A `100 GB` raw target can be reached from the current `6.91 GB` baseline by downloading additional upstream shards.
- For cluster `b` alone, upstream contains `49` `instance_events` shards and `1,463` `instance_usage` shards.
- The acceptable stopping window can be widened with `BORG_TARGET_TOLERANCE_BYTES`, for example `100 GB` target plus `50 GB` tolerance for a practical `50–150 GB` outcome band.
- The advanced-track directory root is now `~/Documents/borg_xgboost_workspace`, and the XGBoost/raw-expansion work should use that root rather than the original baseline directories.
- `scripts/run_advanced_download.sh` now provides a one-command entrypoint that auto-loads the advanced env file and runs the coherent downloader into the isolated advanced workspace.
- The advanced-model source tree is now separated under `src/advanced_xgboost` with dedicated scripts `scripts/build_advanced_xgboost_dataset.py`, `scripts/train_advanced_xgboost.py`, and `scripts/run_advanced_xgboost_pipeline.sh`.
- The advanced XGBoost missing-data policy is now: keep label-valid rows, preserve numeric nulls into XGBoost, and add explicit missingness indicator features rather than dropping whole joined rows.
- Step wrappers now exist for the isolated advanced pipeline: `scripts/run_advanced_flatten.sh`, `scripts/run_advanced_join.sh`, `scripts/run_advanced_feature_build.sh`, `scripts/run_advanced_train.sh`, and the full-chain `scripts/run_advanced_xgboost_pipeline.sh`.
- The advanced feature parquet now carries multiple target columns for default horizons `5m`, `15m`, `30m`, `45m`, and `60m`, and the trainer fits one XGBoost model per target column without requiring separate joined datasets.
- `scripts/setup_advanced_runtime.sh` now prepares a repo-local `.venv`, and the advanced wrappers use that interpreter plus `PYTHONPATH` so the isolated pipeline can run immediately after downloads finish.
- The advanced runtime dependency issue on macOS is resolved by installing `libomp`, and `xgboost` now imports successfully from the repo-local `.venv`.
- Mixed-schema advanced parquet shards are now normalized in the joiner per file before concatenation, which avoids `polars.exceptions.SchemaError` when earlier shards were written with string-typed IDs/timestamps.
- Advanced NDJSON flattening now casts quoted numeric scalar fields after scan, because `scan_ndjson(..., schema_overrides=Int64)` was nulling usage IDs/timestamps for the fixed-shard advanced set.
- The advanced joiner now has a resumable cluster-at-a-time wrapper `scripts/run_advanced_join_resumable.sh`, and removing the global pre-group sorts from event/machine aggregation reduced join wall time enough for the full advanced join to complete successfully.
- The advanced feature and training stages now also have resumable wrappers: `scripts/run_advanced_feature_build_resumable.sh` and `scripts/run_advanced_train_resumable.sh`.
- The advanced trainer no longer concatenates the entire feature store eagerly in memory; it now scans parquet lazily, keeps all positives, and deterministically downsamples negatives to bounded train/validation row caps so multi-cluster training fits on the local machine.
- New additive stage wrappers now exist for detailed reruns without replacing earlier scripts: `scripts/data_flattener_detailed.py`, `scripts/run_advanced_event_repair_detailed.sh`, `scripts/run_advanced_join_resumable_detailed.sh`, `scripts/run_advanced_feature_build_resumable_detailed.sh`, and `scripts/run_advanced_train_resumable_detailed.sh`.
- The detailed wrappers are intended for long-running repair and retrain work because they emit per-cluster audit lines, preserve explicit runtime overrides, and write dedicated timestamped logs beside the earlier baseline wrappers.

## Suggested Commit Shards For Next Session

If continuing the forecaster improvements, split work into commits like:

1. Add the next forecaster model implementation
2. Replace the local-cloud example mapping with a real platform mapping
3. Persist model comparison artifacts
4. Compare cluster-level calibration and ranking behavior
5. Document the winning forecaster profile/model
6. Start scheduler dataset construction

## Recent Commit Landmarks

- `e8f06d6` Record parquet schema-note rule in handoff
- `f599a15` Require local parquet schema notes
- `7e426f2` Refresh milestone handoff state
- `fd9e0cf` Add milestone checkpoint report
- `7a70556` Update handoff continuity notes
- `e25f5e8` Record milestone persistence workflow
- `be8a3e8` Prefix report filenames with KST timestamp

## Launch Command

Recommended resume command:

```bash
cd /Users/theokim/Documents/github/kyunghee/Borg-Agent-Orchestrator
codex -a never --sandbox danger-full-access --network-access enabled
```
