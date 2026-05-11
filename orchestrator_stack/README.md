# Full Orchestrator Stack (Isolated Workspace)

This directory implements the full 6-layer orchestrator process end-to-end:

1. Local source ingestion (`Prometheus/JSON` -> trace file)
2. AIOpsLab-style simulator backend + feature extraction
3. XGBoost safety-risk and demand predictors
4. MARL policy layer (PettingZoo-style parallel bridge, PPO-compatible RLlib env) + referee
5. Optuna trial manager for reward and policy hyperparameters
6. Scoreboard feedback loop into policy/trial evaluation

Architecture diagrams: [ARCHITECTURE.md](ARCHITECTURE.md) | [Visual (mmd)](architecture.mmd)

## Directory Layout

```text
orchestrator_stack/
├── AGENTS.md
├── ARCHITECTURE.md
├── NEXT_STEPS.md
├── README.md
├── config/
│   └── orchestrator.example.json
├── examples/
│   ├── sample_metrics.json
│   ├── sample_trace.json
│   └── generate_synthetic_assets.py
├── orchestrator/
│   ├── cli.py
│   ├── main.py
│   ├── layer1/  # collector + trace ingestion
│   ├── layer2/  # twin backend + feature extraction
│   ├── layer3/  # XGBoost training/inference
│   ├── layer4/  # policy spaces + referee + RLlib env/trainer
│   ├── layer5/  # Optuna tuners
│   └── layer6/  # scoreboard
└── run.py
```

## Open-Source Upstream Snapshot (checked on 2026-04-14)

- Ray RLlib latest release tag: `Ray-2.54.1`
- Optuna latest release tag: `v4.8.0`
- XGBoost latest release tag: `v3.2.0`
- Prometheus latest release tag: `v3.11.2`
- Microsoft AIOpsLab: active repository, no formal GitHub release tags

## Getting Started from Scratch

Follow these steps to initialize the environment and run the full orchestrator stack.

### 1. Prerequisites
- **Python 3.10 to 3.13** (Note: Ray does not yet support 3.14+)
- **Git**

### 2. Initialize Virtual Environment
From the repository root, create and activate the virtual environment. **Note:** Use Python 3.10-3.13 (e.g., `python3.13`) as Ray does not yet support 3.14.

**Important:** If you previously created a `.venv` with a different Python version, you must remove it first: `rm -rf .venv`

```bash
python3.13 -m venv .venv  # Recommended
...
python3.12 -m venv .venv
# THEN
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install --upgrade pip
pip install -r orchestrator_stack/requirements.txt
```

### 3.5 Optional: Export Metrics from Prometheus
If you have a live Prometheus endpoint, export query-range results into the same flat JSON format accepted by `build-trace`:

```bash
./.venv/bin/python orchestrator_stack/run.py scrape-prometheus \
  --base-url http://localhost:9090 \
  --queries orchestrator_stack/config/prometheus_queries.example.json \
  --start 1700000000 \
  --end 1700003600 \
  --step 60 \
  --out orchestrator_stack/runtime/prometheus_metrics.json
```

The query file must be a JSON object mapping output fields such as `cpu_util`, `mem_util`, `disk_util`, and `net_util` to PromQL expressions. The exporter merges Prometheus matrix results by timestamp and node label, then `build-trace` can convert the output into Layer 2 trace rows.

### 3.6 Optional: Convert Prepared Google Cluster Trace Frames
Prepared Google/Borg aggregate frames can now be converted into the same Layer 1 trace contract used by the simulator, XGBoost trainers, PPO training, Optuna tuning, and dashboard:

```bash
./.venv/bin/python orchestrator_stack/run.py build-google-trace \
  --frames marlops-baseline/data/processed/google_trace/trace_frames.parquet \
  --out orchestrator_stack/runtime/google_trace.json \
  --max-rows 500 \
  --max-nodes 32 \
  --max-tasks-per-row 64
```

Accepted frame formats are `.json`, `.jsonl`, `.csv`, and `.parquet`. Required aggregate fields are timestamp (`timestamp` or `ts`), observed node count, active task count, mean CPU utilization, and mean memory utilization. The adapter preserves provenance with `source_platform=google_trace` and `telemetry_sources=["google_cluster_trace"]`, then validates the generated trace before writing it.

### 4. Generate Initial Assets (Synthetic Data & Models)
Before running the orchestrator, you must generate the synthetic trace and training datasets:
```bash
# Generate metrics, traces, and datasets
./.venv/bin/python orchestrator_stack/examples/generate_synthetic_assets.py
```

Layer 1 ingestion now enforces strict contracts for `.json` and `.jsonl` trace sources:

- rejects mixed flat/grouped metrics row shapes during trace build
- rejects malformed JSON/JSONL with file/line context
- validates required trace keys (`timestamp`, `nodes`, `tasks`) before Layer 2/3 usage

See `orchestrator_stack/examples/README.md` for the concise schema contract.

Layer 2 now normalizes AIOpsLab-style nested payloads into the shared `Observation` contract before simulator replay and feature extraction. Supported adapter-friendly shapes include nested wrappers such as `snapshot/state/observation`, dict-backed `machines`/`pods`, and alternate score fields such as `risk_scores` and `demand_scores`.
Layer 3 runtime inference is now wired through a predictor-backed backend wrapper, so `run`, `train-policy`, and PPO/Optuna evaluation paths all receive live XGBoost-enriched observations on both `reset()` and `step()`, not only the manual episode loop.

### 5. Train the Predictor Models (Layer 3)
Export trace-derived NPZ datasets when you want a reusable calibration/diagnostics artifact before model training:
```bash
./.venv/bin/python orchestrator_stack/run.py export-brain-datasets \
  --trace orchestrator_stack/examples/sample_trace.json \
  --risk-out orchestrator_stack/examples/risk_train.npz \
  --demand-out orchestrator_stack/examples/demand_train.npz
```

The exported files use the same feature contract as `train-brains`: `x`, `y`, `feature_names`, and `target_name`. This lets `diagnose-brain` and external calibration runs inspect the exact matrices used for risk and demand training.

Train the XGBoost safety-risk and resource-demand models from the generated trace:
```bash
./.venv/bin/python orchestrator_stack/run.py train-brains \
  --trace orchestrator_stack/examples/sample_trace.json \
  --risk-out orchestrator_stack/examples/models/risk_model.json \
  --demand-out orchestrator_stack/examples/models/demand_model.json
```

Generate model diagnostics after training:
```bash
./.venv/bin/python orchestrator_stack/run.py diagnose-brain \
  --model orchestrator_stack/examples/models/risk_model.json \
  --dataset orchestrator_stack/examples/risk_train.npz \
  --task risk \
  --out reports/evaluations/risk_model_diagnostics.json
```
Risk diagnostics include threshold optimization, calibration bins, Brier score, expected/max calibration error, XGBoost feature importance, and contribution summaries from XGBoost `pred_contribs`. Datasets exported by `export-brain-datasets` also carry feature names, so diagnostics can report `cpu_util`/`mem_util` style names instead of raw `f0`/`f1` keys.

## Testing the Architecture

You can test the full 6-layer orchestrator stack using the provided CLI:

### 1. Build and Train Everything (Full Process)
This runs Layer 1 through Layer 6 in one go using the project virtual environment:
```bash
./.venv/bin/python orchestrator_stack/run.py full-process \
  --config orchestrator_stack/config/orchestrator.example.json \
  --trials 3
```
After completion, check `reports/` for a KST-timestamped Optuna report (e.g., `202604142115_optuna_*.md`).

### 2. Run a Manual Episode (Sim Loop)
```bash
./.venv/bin/python orchestrator_stack/run.py run --config orchestrator_stack/config/orchestrator.example.json
```

### 3. Run Optuna Tuning Only
```bash
./.venv/bin/python orchestrator_stack/run.py tune \
  --config orchestrator_stack/config/orchestrator.example.json \
  --trials 20

./.venv/bin/python orchestrator_stack/run.py tune-policy-rewards \
  --config orchestrator_stack/config/orchestrator.example.json \
  --trials 20
```

### 4. Unit Tests
```bash
./.venv/bin/pytest orchestrator_stack/tests/
```

### 5. Regenerate Architecture Status
```bash
./.venv/bin/python orchestrator_stack/run.py architecture-status \
  --out reports/evaluations/manual_orchestrator_architecture_status.md
```

If `--out` is omitted, the command writes a KST-timestamped report under `reports/evaluations/`.

### 6. Audit Telemetry Rewards
After building a trace that includes live `sla_violations`, `completed_tasks`, and `energy_watts`, replay it through the heuristic agents and report how much these telemetry fields changed rewards:
```bash
./.venv/bin/python orchestrator_stack/run.py telemetry-reward-audit \
  --trace orchestrator_stack/examples/sample_trace.json \
  --out reports/evaluations/manual_telemetry_reward_audit.json
```

Use this before PPO tuning on live traces to verify that reward pressure is coming from the intended SLA, completion, and energy signals.
For a local fixture, run the same command against `orchestrator_stack/examples/sample_telemetry_trace.json`; the latest committed audit is `reports/evaluations/202605020534_sample_telemetry_reward_audit.json`.

`train-policy` results include `heuristic_baseline` and `policy_vs_heuristic` fields. Treat PPO as not promoted until `policy_vs_heuristic.beats_heuristic` is true on representative telemetry-backed traces.

To enforce a held-out multi-family gate from generated policy artifacts:
```bash
./.venv/bin/python orchestrator_stack/run.py policy-gate-suite \
  --manifest orchestrator_stack/config/aiopslab_multi_family_gate_suite.json \
  --out reports/evaluations/manual_aiopslab_multi_family_policy_gate_suite.json
```

### 6.5 Export Thesis Evaluation Tables
After live validation and policy training, convert raw JSON evidence into thesis-ready Markdown and CSV tables:
```bash
./.venv/bin/python orchestrator_stack/run.py thesis-tables \
  --evaluation-dir reports/evaluations \
  --out-md reports/evaluations/manual_thesis_evaluation_tables.md \
  --out-csv-dir reports/evaluations/manual_thesis_tables
```

Latest committed table export:
- Markdown: `reports/evaluations/202605022050_thesis_evaluation_tables.md`
- CSV directory: `reports/evaluations/202605022050_thesis_tables`

### 7. Check AIOpsLab Readiness
```bash
./.venv/bin/python orchestrator_stack/run.py aiopslab-preflight \
  --out reports/evaluations/manual_aiopslab_preflight.json
```

The repo `.venv` uses Python `3.13.12`, so use the separate Python 3.12 validation environment for upstream checks:
```bash
orchestrator_stack/scripts/setup_aiopslab_env.sh

PYTHONPATH=orchestrator_stack ~/Documents/aiopslab_validation_env/bin/python \
  orchestrator_stack/run.py aiopslab-preflight \
  --kube-config ~/.kube/config
```

Current status: Python 3.12, the upstream `aiopslab` package, Kind, and the local kubeconfig are installed for live validation. The active local kubeconfig used by validation is `~/Documents/aiopslab_validation_env/kubeconfig`.

For local live validation, create a Kind cluster and run the no-op AIOpsLab smoke:
```bash
orchestrator_stack/scripts/setup_kind_cluster.sh
orchestrator_stack/scripts/setup_aiopslab_env.sh

KUBECONFIG=~/Documents/aiopslab_validation_env/kubeconfig \
PYTHONPATH=orchestrator_stack ~/Documents/aiopslab_validation_env/bin/python \
  orchestrator_stack/scripts/run_aiopslab_noop_smoke.py \
  --out reports/evaluations/manual_aiopslab_noop_live_summary.json \
  --trace-out reports/evaluations/manual_aiopslab_noop_kube_trace.json
```

Latest live Kind result: `reports/evaluations/202605021205_aiopslab_noop_live_summary.json` with `Detection Accuracy=Correct`.
Latest live Kubernetes-derived trace: `reports/evaluations/202605021205_aiopslab_noop_kube_trace.json`.
Latest live telemetry audit: `reports/evaluations/202605021205_aiopslab_noop_kube_reward_audit.json` with telemetry coverage `1.0`.
Live trace PPO config: `orchestrator_stack/config/aiopslab_live_kind.json`. Current PPO gate remains closed on this two-row no-op trace; `reports/evaluations/202605021222_aiopslab_live_train_policy_stronger.json` records `beats_heuristic=false`.
Fault detection validation: `reports/evaluations/202605021230_aiopslab_misconfig_detection_live_summary.json` records `Detection Accuracy=Correct` for `misconfig_app_hotel_res-detection-1` on Kind. Combined no-op+fault trace config is `orchestrator_stack/config/aiopslab_combined_kind.json`; current PPO gate remains closed there too, with `reports/evaluations/202605021235_aiopslab_combined_train_policy.json` recording `beats_heuristic=false`.
Full-phase validation now covers misconfig localization, analysis, and mitigation on Kind. `reports/evaluations/202605021300_aiopslab_full_phase_kube_trace.json` has 11 Kubernetes-derived rows across no-op plus misconfig detection/localization/analysis/mitigation. `reports/evaluations/202605021310_aiopslab_full_phase_train_policy_fixed_gate.json` uses corrected total-score comparison and still records `beats_heuristic=false`. Live trace-derived predictors are under `orchestrator_stack/examples/models/live_full_phase/`; diagnostics are `reports/evaluations/202605021315_aiopslab_full_phase_risk_diagnostics.json` and `reports/evaluations/202605021315_aiopslab_full_phase_demand_diagnostics.json`.
Periodic mitigation capture: run `orchestrator_stack/scripts/run_aiopslab_noop_smoke.py` with `--capture-interval-seconds 2` to collect intra-run Kubernetes transitions. Latest periodic trace is `reports/evaluations/202605021325_aiopslab_misconfig_mitigation_periodic_kube_trace.json`; PPO gate output is `reports/evaluations/202605021330_aiopslab_periodic_mitigation_train_policy.json` and remains `beats_heuristic=false` by `-16.72244079999996` total score.
Thesis-grade validation: `reports/evaluations/202605022005_thesis_grade_orchestrator_validation.md` summarizes the live Kubernetes/AIOpsLab evidence, limitations, and next research gates. Latest enriched mitigation PPO result is `reports/evaluations/202605021400_aiopslab_enriched_mitigation_train_policy.json`, with `beats_heuristic=true` and delta `+126.69152246399995` after deriving Kubernetes risk/demand signals and preserving live SLA risk.
Prometheus/node-exporter validation: `reports/evaluations/202605022020_aiopslab_mitigation_prometheus_kube_trace.json` records `15` live mitigation rows with `prometheus_node_exporter` in every row. `reports/evaluations/202605022025_aiopslab_prometheus_mitigation_train_policy.json` records `beats_heuristic=true` with delta `+77.23260686133335` on that Prometheus-enriched trace.
Second-family validation: `k8s_target_port-misconfig-*` now runs detection/localization/analysis/mitigation on the SocialNetwork app. Full-phase trace `reports/evaluations/202605022125_k8s_target_port_full_phase_kube_trace.json` has `17` Kubernetes rows. Initial PPO output `reports/evaluations/202605022130_k8s_target_port_full_phase_train_policy.json` was close but below heuristic; stronger PPO output `reports/evaluations/202605030010_k8s_target_port_full_phase_train_policy_stronger.json` now records `beats_heuristic=true` with delta `+18.01204388800005`.
Third-family validation: `scale_pod_zero_social_net-*` now runs detection/localization/analysis/mitigation on the SocialNetwork app. Full-phase trace `reports/evaluations/202605030140_scale_pod_zero_full_phase_kube_trace.json` has `18` Kubernetes rows. PPO output `reports/evaluations/202605030145_scale_pod_zero_full_phase_train_policy.json` records `beats_heuristic=true` with delta `+20.700478922666548`.
Multi-family gate suite: `reports/evaluations/202605030445_aiopslab_multi_family_policy_gate_suite.json` records `status=passed` with `5/5` held-out entries passing across Hotel Reservation Prometheus mitigation, SocialNetwork target-port full-phase validation, SocialNetwork scale-to-zero full-phase validation, SocialNetwork assign-to-nonexistent-node full-phase validation, and Hotel Reservation wrong-binary full-phase validation.
Repeated-seed PPO statistics: `reports/evaluations/202605030505_repeated_seed_ppo_summary.md` records `3/3` passing seeds for Hotel Reservation Prometheus mitigation, SocialNetwork target-port full-phase validation, SocialNetwork scale-to-zero full-phase validation, SocialNetwork assign-to-nonexistent-node full-phase validation, and Hotel Reservation wrong-binary full-phase validation.
Ablation evidence matrix: `reports/evaluations/202605030050_ablation_evidence_matrix.md` compares sequential validation stages and explicitly marks the result as preliminary, not a fully controlled causal ablation.
Controlled ablation summary: `reports/evaluations/202605030225_controlled_ablation_repeated_seed_summary.md` compares fixed-trace Prometheus mitigation variants across seeds `515`, `616`, and `717`. SLA-risk preservation has mean predictor-runtime delta gain `+10.428703703703718`; the effect is positive but seed-sensitive.
Evaluation statistics: `reports/evaluations/202605030510_evaluation_statistics.md` records descriptive 95% Student-t confidence intervals for repeated-seed PPO deltas and controlled-ablation effects. With `n=3`, these intervals are intentionally wide and should be treated as descriptive, not definitive significance proof.

## Current Validation Status

Latest checked behavior in this worktree is based on the 2026-05-02 KST validation slices:

- Layer 1 contracts, Layer 2 normalization, Layer 4 referee/RLlib env behavior, and Layer 5 reward-weight tuning all passed compile and targeted smoke or unit validation in-session.
- Layer 3 predictor observations are now injected at the backend seam, so manual episodes, heuristic evaluation, RLlib training, and PPO-backed Optuna trials share the same non-placeholder risk/demand observation path.
- `export-brain-datasets` writes trace-derived risk/demand `.npz` matrices with feature metadata for calibration and diagnostics.
- `architecture-status` regenerates the architecture completion/gap report as a repeatable CLI artifact.
- `telemetry-reward-audit` replays traces and reports telemetry coverage plus weighted SLA/completion/energy reward deltas.
- `train-policy` now reports PPO-vs-heuristic comparison fields so policy quality is explicit instead of inferred from raw training reward.
- `aiopslab-preflight` now checks real upstream imports, not just package presence.
- `AIOpsLabBackend` now loads the real upstream `Orchestrator` class by module path and registers the policy agent before `init_problem()`.
- Live AIOpsLab no-op validation now runs on a real Kind Kubernetes cluster and records a correct detection result.
- Full orchestrator test suite currently passes with `82 passed`.
- `tune` completed successfully after the PPO-tuning rewrite and emitted `reports/tuning/202604161029_optuna_orchestrator_reward_weights.md`.
- `tune-policy-rewards` now reaches the PPO-backed RLlib trial path and fails closed with a structured `"status": "skipped"` result when macOS sandbox process-enumeration blocks `ray.init()`.
- The older `reports/tuning/202604142305_optuna_orchestrator_policy_and_rewards.md` artifact predates the 2026-04-16 PPO-backed tuning rewrite and should be treated as historical, not as the current validation artifact for `tune-policy-rewards`.

## Viewing Logs and Decision Traces

The orchestrator now provides verbose step-by-step logging of agent decisions. When running the `run` or `full-process` commands, look for the following output in your terminal:

- **Proposals:** The raw actions suggested by the Risk, Efficiency, and Admission agents.
- **Referee:** The final action chosen after conflict resolution.
- **Rewards:** The score impact for each agent (e.g., `AgentA:+11.0` indicates a successful preemptive migration).

To see more training logs from Ray RLlib, increase the `"rllib_train_iters"` value in your `.json` config.
The example config now also exposes PPO knobs used by both `train-policy` and `tune-policy-rewards`: `ppo_learning_rate`, `ppo_train_batch_size`, `ppo_minibatch_size`, `ppo_num_epochs`, and `ppo_rollout_fragment_length`.
Set `random_seed` for repeatable PPO runs. If `ppo_curriculum` is present, `train-policy` runs each stage in order with its own PPO batch and iteration settings under separate runtime subdirectories; stage seeds derive from `random_seed` unless a stage-specific `seed` is provided.
For controlled ablations, set `use_predictor_runtime=false` to bypass Layer 3 prediction enrichment and set `preserve_live_sla_risk=false` to disable hard preservation of live SLA-risk evidence in the trace twin.

For energy telemetry, live Kubernetes capture writes `power_calibration` metadata next to `energy_watts`. Pass `--power-calibration orchestrator_stack/config/kind_power_calibration.example.json` to `scripts/run_aiopslab_noop_smoke.py` to make the utilization-to-watts calibration explicit; replace the example coefficients with measured node calibration when a wattmeter, IPMI, RAPL, or equivalent exporter is available.
Current node-power exporter availability is recorded in `reports/evaluations/202605030520_node_power_exporter_availability.md`; the current Kind validation cluster has no direct measured node-power source, so `energy_watts` remains calibrated/utilization-derived.

## Notes

- The default config uses `rllib_train_iters=1` for fast local smoke tests.
- Optuna studies are persisted at `orchestrator_stack/runtime/optuna/orchestrator.db`.
- PPO checkpoints are written under `orchestrator_stack/runtime/rllib`.
- `tune-policy-rewards` now scores each Optuna trial with a real PPO training run plus a small heuristic stability term; it is no longer a learning-rate-only placeholder objective.
- In restricted macOS sandboxes, Ray may fail during `ray.init()` with a `PermissionError` from process enumeration. The command now returns a structured `"status": "skipped"` result in that case instead of crashing.
- Direct validation against the live upstream AIOpsLab package/session API is now proven on Kind no-op, Hotel Reservation misconfig detection/localization/analysis/mitigation, Prometheus/node-exporter enriched mitigation, SocialNetwork target-port misconfig detection/localization/analysis/mitigation, SocialNetwork scale-to-zero detection/localization/analysis/mitigation, SocialNetwork assign-to-nonexistent-node detection/localization/analysis/mitigation, and Hotel Reservation wrong-binary detection/localization/analysis/mitigation paths. Per-family PPO gates pass on all five reported live families; the current five-entry held-out multi-family gate suite also passes.
- AIOpsLab agent onboarding now has an explicit contract adapter for the documented flow: `init_problem(problem_id)`, agent `init_context(...)`, `register_agent(agent)`, and async agent `get_action(state)`.
