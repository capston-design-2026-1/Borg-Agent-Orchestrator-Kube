# Orchestrator Stack Next Steps

1. Build a held-out multi-family trace corpus and require PPO to beat heuristic total score across held-out traces, not only per-family enriched slices.
2. Add repeated-seed statistical tables: confidence intervals and ablations for no risk derivation vs risk derivation vs SLA risk preservation vs Prometheus enrichment.
3. Replace model-derived energy watts with a measured or externally calibrated node-power source when available; Prometheus/node-exporter now supplies CPU and memory utilization but not hardware wattmeter readings.

## Latest Session Note (2026-05-03 KST, second-family PPO pass slice)

- Added stronger PPO curriculum for the second full-phase family:
  - config `orchestrator_stack/config/aiopslab_k8s_target_port_full_phase_stronger_kind.json`
  - output `reports/evaluations/202605030010_k8s_target_port_full_phase_train_policy_stronger.json`
- Stronger PPO gate on `k8s_target_port-misconfig-*` full-phase trace:
  - policy episode reward `-306.3355152799999`
  - heuristic total score `-324.347559168`
  - delta `+18.01204388800005`
  - `beats_heuristic=true`
- Best intermediate stage was stage 3 with reward `-303.6011402799999`; final stage still beats the gate.
- Conclusion: per-family PPO gates now pass on Prometheus-enriched mitigation and second-family full-phase traces. Next blocker is held-out multi-family generalization and repeated-seed statistics.

## Latest Session Note (2026-05-02 KST, second-family AIOpsLab validation slice)

- Ran live Kind-backed `k8s_target_port-misconfig-*` on the SocialNetwork app:
  - detection `reports/evaluations/202605022100_k8s_target_port_detection_live_summary.json`: `Detection Accuracy=Correct`
  - localization `reports/evaluations/202605022105_k8s_target_port_localization_live_summary.json`: `Localization Accuracy=100.0`, `success=true`
  - analysis `reports/evaluations/202605022110_k8s_target_port_analysis_live_summary.json`: `system_level_correct=true`, `fault_type_correct=true`, `success=true`
  - mitigation `reports/evaluations/202605022120_k8s_target_port_mitigation_live_summary.json`: `success=true`
- Built second-family full-phase trace:
  - trace `reports/evaluations/202605022125_k8s_target_port_full_phase_kube_trace.json`
  - rows `17`
  - telemetry coverage `1.0`
  - actions `dvfs=13`, `replicate=3`
- PPO gate on second-family full-phase trace:
  - config `orchestrator_stack/config/aiopslab_k8s_target_port_full_phase_kind.json`
  - output `reports/evaluations/202605022130_k8s_target_port_full_phase_train_policy.json`
  - policy episode reward `-329.9292652799999`
  - heuristic total score `-324.347559168`
  - delta `-5.581706111999949`
  - `beats_heuristic=false`
- Conclusion: external validity improved from one full-phase fault family to two; original PPO gate was close but below heuristic, superseded by the 2026-05-03 stronger PPO pass.

## Latest Session Note (2026-05-02 KST, thesis table export slice)

- Added `thesis-tables` CLI to convert raw validation JSON artifacts into thesis-ready tables.
- Recorded AIOpsLab problem catalog snapshot:
  - `reports/evaluations/202605022055_aiopslab_problem_catalog.md`
  - `89` registered problem IDs
  - `8` full-phase candidate families
  - recommended next live family: `k8s_target_port-misconfig-*`
- Generated current appendix artifacts:
  - Markdown `reports/evaluations/202605022050_thesis_evaluation_tables.md`
  - CSV directory `reports/evaluations/202605022050_thesis_tables`
- Exported tables cover:
  - live AIOpsLab task outcomes
  - telemetry reward audits
  - PPO policy-vs-heuristic gates
- Validation run status:
  - `PYTHONPATH=orchestrator_stack .venv/bin/python -m pytest orchestrator_stack/tests -q`: success (`78 passed`)

## Latest Session Note (2026-05-02 KST, Prometheus/node-exporter mitigation slice)

- Added direct Prometheus/node-exporter enrichment to live Kubernetes trace capture:
  - Prometheus service is port-forwarded after AIOpsLab deploys the observer stack.
  - node-exporter instant queries provide live CPU and memory utilization.
  - trace rows retain Kubernetes API state and add `prometheus_node_exporter` to `telemetry_sources`.
- Re-ran live Kind-backed `misconfig_app_hotel_res-mitigation-1` with Prometheus enrichment:
  - summary `reports/evaluations/202605022020_aiopslab_mitigation_prometheus_live_summary.json`
  - trace `reports/evaluations/202605022020_aiopslab_mitigation_prometheus_kube_trace.json`
  - captured `15` live rows
  - all `15` rows include `prometheus_node_exporter`
  - final state `SubmissionStatus.VALID_SUBMISSION`
- Prometheus trace audit:
  - output `reports/evaluations/202605022020_aiopslab_mitigation_prometheus_reward_audit.json`
  - telemetry coverage `1.0`
  - actions: `replicate=13`, `dvfs=1`
  - max energy watts `128.083859`
- PPO gate on Prometheus-enriched trace:
  - config `orchestrator_stack/config/aiopslab_prometheus_mitigation_kind.json`
  - output `reports/evaluations/202605022025_aiopslab_prometheus_mitigation_train_policy.json`
  - policy episode reward `-663.0434828466666`
  - heuristic total score `-740.276089708`
  - delta `+77.23260686133335`
  - `beats_heuristic=true`
- Validation run status:
  - superseded by thesis table export slice (`78 passed`)

## Latest Session Note (2026-05-02 KST, thesis-grade action-diversity slice)

- Added live Kubernetes control signals to trace rows:
  - `p_fail_scores` from unhealthy pod phases/readiness/restarts plus node utilization
  - `demand_projection` from node resource requests
- Preserved live SLA risk inside the trace twin so synthetic action deltas cannot erase hard evidence from baseline trace rows.
- Re-ran enriched periodic mitigation on Kind:
  - output `reports/evaluations/202605021350_aiopslab_mitigation_enriched_live_summary.json`
  - `success=true`
  - captured `24` live Kubernetes rows
- Action audit changed from mostly `dvfs` to safety-dominant behavior:
  - `replicate=21`
  - `dvfs=2`
- PPO gate now passes on the enriched live mitigation trace:
  - config `orchestrator_stack/config/aiopslab_enriched_mitigation_kind.json`
  - output `reports/evaluations/202605021400_aiopslab_enriched_mitigation_train_policy.json`
  - policy episode reward `-991.63369384`
  - heuristic total score `-1118.325216304`
  - delta `+126.69152246399995`
  - `beats_heuristic=true`
- Added thesis-grade validation report:
  - `reports/evaluations/202605022005_thesis_grade_orchestrator_validation.md`
- Validation run status:
  - superseded by Prometheus slice (`76 passed`)

## Latest Session Note (2026-05-02 KST, periodic mitigation capture slice)

- Added optional background Kubernetes capture to `orchestrator_stack/scripts/run_aiopslab_noop_smoke.py` with `--capture-interval-seconds`.
- `write_kubernetes_trace()` now sorts rows by `timestamp`, preventing thread interleaving from writing out-of-order trace files.
- Re-ran live Kind-backed `misconfig_app_hotel_res-mitigation-1` with periodic capture every `2` seconds:
  - output `reports/evaluations/202605021325_aiopslab_misconfig_mitigation_periodic_live_summary.json`
  - `success=true`
  - captured `26` Kubernetes trace rows
  - no capture errors
- Periodic trace audit:
  - output `reports/evaluations/202605021325_aiopslab_misconfig_mitigation_periodic_reward_audit.json`
  - telemetry coverage `1.0`
  - max SLA violations `2`
  - max completed tasks `2`
  - max energy watts `117.620408`
  - weighted telemetry reward delta `-1237.4086612000003`
- Periodic PPO gate:
  - config `orchestrator_stack/config/aiopslab_periodic_mitigation_kind.json`
  - output `reports/evaluations/202605021330_aiopslab_periodic_mitigation_train_policy.json`
  - policy episode reward `-1219.131102`
  - heuristic total score `-1202.4086612`
  - delta `-16.72244079999996`
  - `beats_heuristic=false`
- Validation run status:
  - `PYTHONPATH=orchestrator_stack .venv/bin/python -m pytest orchestrator_stack/tests/test_kubernetes_trace.py -q`: success (`3 passed`)
  - `PYTHONPATH=orchestrator_stack .venv/bin/python -m pytest orchestrator_stack/tests -q`: success (`72 passed`)

## Latest Session Note (2026-05-02 KST, full-phase live AIOpsLab slice)

- Added task-specific AIOpsLab submissions:
  - `--submission-code` supports detection/localization/analysis/mitigation final calls such as `submit(["geo"])`, `submit({...})`, and `submit()`.
  - repeatable `--pre-submit-command` runs remediation commands before final mitigation submit.
- Ran live Kind-backed `misconfig_app_hotel_res-localization-1`:
  - `Localization Accuracy=100.0`
  - `success=true`
  - captured `2` Kubernetes trace rows
- Ran live Kind-backed `misconfig_app_hotel_res-analysis-1`:
  - `system_level_correct=true`
  - `fault_type_correct=true`
  - `success=true`
  - captured `2` Kubernetes trace rows
- Ran live Kind-backed `misconfig_app_hotel_res-mitigation-1`:
  - remediation command set `deployment/geo` back to `yinfangchen/hotelreservation:latest` and waited for rollout
  - `success=true`
  - captured `3` Kubernetes trace rows
- Fixed PPO gate comparison: policy episode return is now compared against heuristic episode total score, not heuristic average score.
- Built full-phase live trace:
  - `reports/evaluations/202605021300_aiopslab_full_phase_kube_trace.json`
  - includes no-op detection plus misconfig detection/localization/analysis/mitigation
  - `11` real Kubernetes-derived rows
- Full-phase telemetry audit:
  - telemetry coverage `1.0`
  - max SLA violations `1`
  - weighted telemetry reward delta `-376.98522448`
- Full-phase PPO gate:
  - config `orchestrator_stack/config/aiopslab_full_phase_kind.json`
  - output `reports/evaluations/202605021310_aiopslab_full_phase_train_policy_fixed_gate.json`
  - policy episode reward `-340.60037413333333`
  - heuristic total score `-312.98522448`
  - `beats_heuristic=false`
- Exported full-phase live brain datasets and retrained predictors:
  - `reports/evaluations/brain_live_full_phase/risk_dataset.npz`
  - `reports/evaluations/brain_live_full_phase/demand_dataset.npz`
  - `orchestrator_stack/examples/models/live_full_phase/risk_model.json`
  - `orchestrator_stack/examples/models/live_full_phase/demand_model.json`
- Brain diagnostics:
  - risk rows `11`, Brier score `0.14887345848485453`, expected calibration error `0.010636160319501708`
  - demand rows `11`, active feature importance on `cpu_util` and `task_pressure`
- Validation run status:
  - `PYTHONPATH=orchestrator_stack .venv/bin/python -m pytest orchestrator_stack/tests/test_aiopslab_contract.py -q`: success (`7 passed`)
  - `PYTHONPATH=orchestrator_stack .venv/bin/python -m pytest orchestrator_stack/tests/test_ppo_curriculum.py -q`: success (`4 passed`)
  - `PYTHONPATH=orchestrator_stack .venv/bin/python -m pytest orchestrator_stack/tests -q`: success (`71 passed`)

## Latest Session Note (2026-05-02 KST, live trace PPO gate slice)

- Added `orchestrator_stack/config/aiopslab_live_kind.json` for policy training against the live Kubernetes-derived AIOpsLab trace.
- Ran smoke curriculum PPO against `reports/evaluations/202605021205_aiopslab_noop_kube_trace.json`:
  - output `reports/evaluations/202605021218_aiopslab_live_train_policy.json`
  - status `trained`
  - policy reward `3.945170919999999`
  - heuristic average `8.701477552`
  - `beats_heuristic=false`
- Ran stronger 3-stage PPO curriculum against the same live trace:
  - output `reports/evaluations/202605021222_aiopslab_live_train_policy_stronger.json`
  - status `trained`
  - best final policy reward `6.757670919999999`
  - heuristic average `8.701477552`
  - `beats_heuristic=false`
- Conclusion: PPO gate remains closed because the no-op live trace has only two duplicate healthy-state rows. Next useful job is richer AIOpsLab multi-problem trace capture, not more tuning on this trace.

## Latest Session Note (2026-05-02 KST, live fault trace slice)

- Parameterized `AIOpsLabPolicyAgent` with `detection_answer`, preserving no-op `No` by default and allowing fault detection runs to submit `Yes`.
- Ran real Kind-backed AIOpsLab fault detection:
  - problem `misconfig_app_hotel_res-detection-1`
  - fault service `geo`
  - final state `SubmissionStatus.VALID_SUBMISSION`
  - result `Detection Accuracy=Correct`
  - captured `2` Kubernetes-derived trace rows
  - captured `20` target pods
  - max SLA violations `1`
- Ran telemetry reward audit on the fault trace:
  - telemetry coverage `1.0`
  - max SLA violations `1`
  - weighted telemetry reward delta `-47.698522448`
- Combined no-op and misconfig traces into `reports/evaluations/202605021235_aiopslab_combined_kube_trace.json`.
- Combined trace audit:
  - telemetry coverage `1.0`
  - max SLA violations `1`
  - score average `-8.965189114666666`
- Combined trace PPO gate:
  - config `orchestrator_stack/config/aiopslab_combined_kind.json`
  - output `reports/evaluations/202605021235_aiopslab_combined_train_policy.json`
  - policy reward `-31.29943042181818`
  - heuristic average `-7.965189114666667`
  - `beats_heuristic=false`
- Recorded artifacts:
  - `reports/evaluations/202605021230_aiopslab_misconfig_detection_live_summary.json`
  - `reports/evaluations/202605021230_aiopslab_misconfig_detection_kube_trace.json`
  - `reports/evaluations/202605021230_aiopslab_misconfig_detection_reward_audit.json`
  - `reports/evaluations/202605021235_aiopslab_combined_kube_trace.json`
  - `reports/evaluations/202605021235_aiopslab_combined_reward_audit.json`
  - `reports/evaluations/202605021235_aiopslab_combined_train_policy.json`
- Validation run status:
  - `PYTHONPATH=orchestrator_stack .venv/bin/python -m pytest orchestrator_stack/tests/test_aiopslab_contract.py -q`: success (`5 passed`)
  - `PYTHONPATH=orchestrator_stack .venv/bin/python -m pytest orchestrator_stack/tests -q`: success (`69 passed`)

## Latest Session Note (2026-05-02 KST, live Kubernetes telemetry audit slice)

- Added `orchestrator.layer1.kubernetes_trace` to export real Kubernetes API snapshots into orchestrator trace rows from `kubectl get nodes/pods/jobs -A -o json`.
- Added `--trace-out` to `orchestrator_stack/scripts/run_aiopslab_noop_smoke.py`, so the AIOpsLab agent captures live Kind cluster state while the Hotel Reservation app and workload are still running and before upstream cleanup removes namespaces.
- Re-ran live AIOpsLab no-op detection on Kind with trace capture:
  - problem `noop_detection_hotel_reservation-1`
  - final state `SubmissionStatus.VALID_SUBMISSION`
  - result `Detection Accuracy=Correct`
  - captured `2` Kubernetes-derived trace rows
  - captured `20` live target pods
  - max SLA violations `0`
  - max energy watts `116.420408`
- Ran `telemetry-reward-audit` against the live Kubernetes trace:
  - telemetry coverage `1.0`
  - selected action `dvfs=1`
  - weighted telemetry reward delta `2.3014775519999997`
- Recorded artifacts:
  - `reports/evaluations/202605021205_aiopslab_noop_live_summary.json`
  - `reports/evaluations/202605021205_aiopslab_noop_kube_trace.json`
  - `reports/evaluations/202605021205_aiopslab_noop_kube_reward_audit.json`
- Validation run status:
  - `PYTHONPATH=orchestrator_stack .venv/bin/python -m pytest orchestrator_stack/tests/test_kubernetes_trace.py -q`: success (`2 passed`)
  - `PYTHONPATH=orchestrator_stack .venv/bin/python -m pytest orchestrator_stack/tests/test_kubernetes_trace.py orchestrator_stack/tests/test_aiopslab_contract.py -q`: success (`6 passed`)
  - `PYTHONPATH=orchestrator_stack .venv/bin/python -m pytest orchestrator_stack/tests -q`: success (`68 passed`)

## Latest Session Note (2026-05-02 KST, live AIOpsLab Kind validation slice)

- Installed Kind and Helm, created a real local Kubernetes cluster `kind-borg-aiopslab`, and wrote kubeconfig at `~/Documents/aiopslab_validation_env/kubeconfig`.
- Patched the AIOpsLab validation environment for local Kind usage:
  - `k8s_host: localhost` in upstream `config.yml`
  - observer `kubernetes_path` points to the generated kubeconfig
  - upstream `aiopslab-applications` is linked from `~/Documents/AIOpsLab/aiopslab-applications`
- Added `orchestrator_stack/scripts/setup_kind_cluster.sh` and `orchestrator_stack/scripts/run_aiopslab_noop_smoke.py` for repeatable cluster + live AIOpsLab validation.
- Fixed `AIOpsLabPolicyAgent` for real AIOpsLab turn semantics:
  - accepts natural-language action prompts, not only JSON state
  - performs one parser-compliant observation action
  - submits `No` on the no-op detection smoke path
- Live AIOpsLab smoke result:
  - problem `noop_detection_hotel_reservation-1`
  - Hotel Reservation app deployed on Kind
  - Prometheus and workload job ran
  - agent/env loop executed
  - final state `SubmissionStatus.VALID_SUBMISSION`
  - result `Detection Accuracy=Correct`
- Recorded artifacts:
  - `reports/evaluations/202605021140_aiopslab_noop_live_session.json`
  - `reports/evaluations/202605021141_aiopslab_noop_live_summary.json`
  - `reports/evaluations/202605021141_aiopslab_preflight_ready.json`
- Validation run status:
  - `PYTHONPATH=orchestrator_stack .venv/bin/python -m pytest orchestrator_stack/tests/test_aiopslab_contract.py -q`: success (`4 passed`)
  - `PYTHONPATH=orchestrator_stack .venv/bin/python -m pytest orchestrator_stack/tests -q`: success (`66 passed`)
  - `KUBECONFIG=~/Documents/aiopslab_validation_env/kubeconfig PYTHONPATH=orchestrator_stack ~/Documents/aiopslab_validation_env/bin/python orchestrator_stack/run.py aiopslab-preflight --kube-config ~/Documents/aiopslab_validation_env/kubeconfig`: success (`status=ready`)

## Latest Session Note (2026-05-02 KST, AIOpsLab preflight slice)

- Added `aiopslab-preflight` CLI to make live AIOpsLab readiness machine-checkable.
- Installed Homebrew Python 3.12 and created `~/Documents/aiopslab_validation_env` for upstream AIOpsLab validation.
- Installed upstream AIOpsLab from GitHub into that environment.
- Added `orchestrator_stack/scripts/setup_aiopslab_env.sh` to recreate the Python 3.12 AIOpsLab validation environment and copy upstream `config.yml.example` to `config.yml` when needed.
- Fixed `initialize_aiopslab_problem()` registration order after verifying upstream `Orchestrator.init_problem()` requires `agent_name` to exist first.
- Updated `AIOpsLabPolicyAgent.get_action()` to return one parser-compliant fenced AIOpsLab API call instead of raw JSON.
- Updated `AIOpsLabBackend` to import `aiopslab.orchestrator.orchestrator.Orchestrator` directly because the upstream top-level package exposes no `orchestrator` attribute.
- Strengthened preflight to perform real imports for `aiopslab.paths` and `aiopslab.orchestrator.orchestrator`.
- Preflight now reports `kube_config_available` and the exact Kubernetes config paths checked before live AIOpsLab runs.
- `aiopslab-preflight --kube-config <path>` can validate a non-default kubeconfig without modifying environment variables.
- Current external preflight report: `reports/evaluations/202605020527_aiopslab_preflight.json`.
- Remaining live blocker: no `KUBECONFIG` or `~/.kube/config`; upstream orchestrator import reaches Kubernetes initialization and fails with `Invalid kube-config file. No configuration found.`
- Validation run status:
  - `PYTHONPATH=orchestrator_stack .venv/bin/python -m pytest orchestrator_stack/tests/test_simulator.py orchestrator_stack/tests/test_aiopslab_contract.py -q`: success (`9 passed`)
  - `PYTHONPATH=orchestrator_stack .venv/bin/python -m pytest orchestrator_stack/tests/test_cli_aiopslab_preflight.py orchestrator_stack/tests/test_aiopslab_preflight.py -q`: success (`5 passed`)
  - `PYTHONPATH=orchestrator_stack .venv/bin/python -m pytest orchestrator_stack/tests -q`: success (`64 passed`)
  - `orchestrator_stack/scripts/setup_aiopslab_env.sh`: success
  - `PYTHONPATH=orchestrator_stack ~/Documents/aiopslab_validation_env/bin/python orchestrator_stack/run.py aiopslab-preflight`: success; reported `status=blocked`, `kube_config_available=false`, and checked `/Users/theokim/.kube/config`.

## Latest Session Note (2026-05-02 KST, telemetry example slice)

- Added `orchestrator_stack/examples/sample_telemetry_trace.json` as a small grouped trace with live reward telemetry fields.
- Recorded `reports/evaluations/202605020534_sample_telemetry_reward_audit.json` from that trace.
- Audit result: telemetry coverage `1.0`, max SLA violations `1`, max completed tasks `25`, max energy watts `310.0`, selected actions `migrate=1` and `throttle=1`.
- Use this fixture as the local regression sample before replacing it with real Prometheus/AIOpsLab telemetry traces.

## Latest Session Note (2026-05-02 KST, PPO comparison slice)

- `train-policy` now attaches `heuristic_baseline` and `policy_vs_heuristic` to PPO/curriculum training output.
- `policy_vs_heuristic` reports PPO reward mean, heuristic average score, delta, and `beats_heuristic`, so policy quality is an explicit gate.
- Validation run status:
  - `PYTHONPATH=orchestrator_stack .venv/bin/python -m pytest orchestrator_stack/tests/test_ppo_curriculum.py orchestrator_stack/tests/test_optuna_meta_tuning.py -q`: success (`6 passed`)
  - `PYTHONPATH=orchestrator_stack .venv/bin/python -m pytest orchestrator_stack/tests -q`: success (`58 passed`)
  - `PYTHONPATH=orchestrator_stack .venv/bin/python orchestrator_stack/run.py train-policy --config orchestrator_stack/config/orchestrator.example.json --output-dir /private/tmp/.../rllib`: success; output included `heuristic_baseline`, `policy_vs_heuristic`, and `delta_vs_heuristic`.

## Latest Session Note (2026-05-02 KST, telemetry reward audit slice)

- Added `telemetry-reward-audit` CLI to replay trace rows through heuristic agents/referee and quantify telemetry reward pressure.
- Audit reports include telemetry coverage, max SLA/completion/energy values, selected action counts, weighted score summary, and per-agent reward deltas from `sla_violations`, `completed_tasks`, and `energy_watts`.
- Validation run status:
  - `PYTHONPATH=orchestrator_stack .venv/bin/python -m pytest orchestrator_stack/tests/test_telemetry_audit.py orchestrator_stack/tests/test_simulator.py -q`: success (`9 passed`)
  - `PYTHONPATH=orchestrator_stack .venv/bin/python -m pytest orchestrator_stack/tests -q`: success (`56 passed`)
  - `PYTHONPATH=orchestrator_stack .venv/bin/python orchestrator_stack/run.py telemetry-reward-audit --trace <temp-live-shape-trace> --out <temp-audit.json>`: success

## Latest Session Note (2026-05-02 KST, calibration diagnostics slice)

- Enhanced `diagnose-brain` risk reports with `calibration_summary`: Brier score, expected calibration error, and max calibration error.
- Diagnostics now read `feature_names` from exported `.npz` datasets and map XGBoost `f0`/`f1` keys to stable Layer 2 feature names when available.
- Validation run status:
  - `PYTHONPATH=orchestrator_stack .venv/bin/python -m pytest orchestrator_stack/tests/test_diagnostics.py orchestrator_stack/tests/test_brain_dataset_export.py -q`: success (`6 passed`)
  - `PYTHONPATH=orchestrator_stack .venv/bin/python -m pytest orchestrator_stack/tests -q`: success (`53 passed`)
  - `export-brain-datasets` plus `diagnose-brain` smoke against `sample_trace.json` and the example risk model: success; report included `calibration_summary` and named feature importances.

## Latest Session Note (2026-05-02 KST, repeatable architecture status slice)

- Added `architecture-status` CLI to regenerate the orchestrator architecture completion/gap report instead of hand-writing one-off markdown.
- Default output is `reports/evaluations/YYYYMMDDHHMM_orchestrator_architecture_status.md`; `--out` can target a specific path for smoke tests or manual reports.
- Validation run status:
  - `PYTHONPATH=orchestrator_stack .venv/bin/python -m pytest orchestrator_stack/tests/test_architecture_report.py -q`: success (`2 passed`)
  - `PYTHONPATH=orchestrator_stack .venv/bin/python orchestrator_stack/run.py architecture-status --out /private/tmp/orchestrator_arch_status.md`: success
  - `PYTHONPATH=orchestrator_stack .venv/bin/python -m pytest orchestrator_stack/tests -q`: success (`51 passed`)

## Latest Session Note (2026-05-02 KST, trace-derived brain dataset slice)

- Added `export-brain-datasets` CLI so trace rows can be materialized into reusable risk/demand `.npz` datasets before XGBoost training or diagnostics.
- Added stable `FEATURE_NAMES` metadata beside the existing Layer 2 feature count so exported matrices carry column meaning.
- Exported risk/demand datasets contain `x`, `y`, `feature_names`, and `target_name`, matching the existing `train-brains` feature contract.
- Validation run status:
  - `PYTHONPATH=orchestrator_stack .venv/bin/python -m pytest orchestrator_stack/tests/test_brain_dataset_export.py orchestrator_stack/tests/test_feature_extractor.py orchestrator_stack/tests/test_predictor_runtime.py -q`: success (`7 passed`)
  - `PYTHONPATH=orchestrator_stack .venv/bin/python -m pytest orchestrator_stack/tests -q`: success (`49 passed`)
  - `PYTHONPATH=orchestrator_stack .venv/bin/python orchestrator_stack/run.py export-brain-datasets --trace orchestrator_stack/examples/sample_trace.json --risk-out /private/tmp/.../risk_train.npz --demand-out /private/tmp/.../demand_train.npz`: success

## Latest Session Note (2026-04-28 KST, architecture gap closure slice)

- Repaired the existing test baseline:
  - feature extractor risk labels now use current and next risk/death/overload signals
  - demand labels now fall back to a deterministic resource-pressure heuristic
  - Optuna meta-tuning unit test now mocks the predictor-backed backend seam instead of loading real boosters
- Added Layer 1 architecture inputs:
  - CSV metric files are accepted by `build-trace`
  - `scrape-prometheus` exports Prometheus `query_range` results into flat metric JSON rows
- Added the Layer 2.5 PettingZoo-style bridge:
  - `OrchestratorParallelEnv` wraps the existing RLlib-compatible multi-agent environment and exposes PettingZoo parallel reset/step behavior
- Expanded Layer 4 action semantics to match the PDF more closely:
  - Agent A: migrate, replicate, throttle
  - Agent B: sleep/wake, DVFS, memory balloon
  - Agent C: admit, queue, reject, deprioritize, resource cap
  - Referee now treats secondary safety actions as top-priority and protective admission/resource-cap actions as higher priority than efficiency actions
- Added Layer 3 diagnostics:
  - `diagnose-brain` CLI
  - threshold optimization and calibration bins for risk models
  - XGBoost feature importance and contribution summaries
- Added PPO curriculum training:
  - `ppo_curriculum` config stages
  - staged runtime directories under `train-policy`
- Added explicit AIOpsLab onboarding contract support:
  - `AIOpsLabPolicyAgent`
  - `initialize_aiopslab_problem()`
  - aligns with the documented AIOpsLab flow: `init_problem`, agent context initialization, `register_agent`, and async `get_action`
- Validation run status:
  - `PYTHONPATH=orchestrator_stack .venv/bin/python -m pytest orchestrator_stack/tests -q`: success (`42 passed`)
- Remaining validation gap:
  - Live AIOpsLab package/session execution and long PPO curriculum runs still need a non-sandboxed local shell with the target infrastructure running.

## Latest Session Note (2026-04-17 KST, XGBoost observation integration slice)

- Layer 3 predictor inference is now attached at the backend seam via `PredictorBackedBackend` rather than only inside `run_episode()`.
- `run_episode()`, `run_policy_training()`, heuristic evaluation, and PPO-backed Optuna policy tuning now all consume predictor-enriched observations from both `reset()` and `step()`.
- Added `orchestrator_stack/tests/test_predictor_runtime.py` to verify reset/step enrichment without requiring live XGBoost model files.
- Validation run status:
  - `python3 -m compileall orchestrator_stack/orchestrator/layer3 orchestrator_stack/orchestrator/main.py orchestrator_stack/tests/test_predictor_runtime.py`: success
  - `PYTHONPATH=orchestrator_stack python3 -m unittest orchestrator_stack.tests.test_predictor_runtime`: success
- Residual validation gap:
  - End-to-end execution with real XGBoost boosters still requires a dependency-complete interpreter; this worktree shell does not currently include `numpy` or `xgboost`.

## Latest Session Note (2026-04-17 KST, targeted fixups slice)

- Hardened `orchestrator_stack/orchestrator/cli.py` so parser/help flows and Layer 1-only commands no longer import `numpy`, XGBoost, or RL runtime modules eagerly.
- Verified `python3 orchestrator_stack/run.py --help` now succeeds in the degraded system interpreter and `build-trace` still runs against `orchestrator_stack/examples/sample_metrics.json`.
- Dataset-backed and RL-backed commands now fail closed with explicit missing-dependency messages such as `missing dependency 'numpy' ... install orchestrator_stack/requirements.txt` instead of raw `ModuleNotFoundError` tracebacks.
- Validation gap remains unchanged: full Layer 3/4/5 execution still requires a repaired repo `.venv` or another interpreter with orchestrator dependencies installed.

## Latest Session Note (2026-04-17 KST, doc sync slice)

- Synced orchestrator-facing docs to the latest tested behavior from the 2026-04-16 validation sessions so README and handoff files now distinguish:
  - completed reward-weight tuning validation (`reports/tuning/202604161029_optuna_orchestrator_reward_weights.md`)
  - PPO-backed `tune-policy-rewards` reaching RLlib but returning structured `"status": "skipped"` in this sandbox when `ray.init()` is blocked
  - focused Layer 4 smoke validation succeeding while `pytest` remained unavailable in the repo virtualenv
- Marked `reports/tuning/202604142305_optuna_orchestrator_policy_and_rewards.md` as a historical pre-rewrite artifact rather than current evidence for the post-2026-04-16 PPO-backed tuning path.
- Added `reports/milestones/202604171027_orchestrator_e2e_gate_doc_sync_session1.md` as the documentation checkpoint for this synchronization pass.

## Latest Session Note (2026-04-16 KST, RLlib/referee slice)

- Layer 4 referee resolution is now explicit and deterministic instead of a simple priority sort:
  - `resolve_with_context()` records the chosen action, rationale, and overridden proposals while keeping `resolve()` as the single-action backend adapter.
  - Agent A migration now preempts other actions, Agent C protective admission (`queue`/`reject`) now preempts efficiency actions, and idle/noop fallback stays deterministic.
- `OrchestratorMultiAgentEnv` now includes RLlib-facing referee metadata in per-agent `infos`:
  - each agent sees its decoded proposal, whether it was overridden, the override reason, the resolved backend action, and the current weighted global score.
- Added focused Layer 4 tests in `orchestrator_stack/tests/test_referee.py` and `orchestrator_stack/tests/test_rllib_env.py`.
- Validation run status:
  - `PYTHONPATH=orchestrator_stack .venv/bin/python -m compileall orchestrator_stack/orchestrator/layer4 orchestrator_stack/tests/test_referee.py orchestrator_stack/tests/test_rllib_env.py`: success
  - `PYTHONPATH=orchestrator_stack .venv/bin/python` smoke invoking `test_policy_decode`, `test_referee`, and `test_rllib_env`: success (`layer4-smoke-ok`)
  - `.venv/bin/python -m pytest ...`: failed because `pytest` is not installed in the repo virtualenv

## Previous Session Note (2026-04-16 KST, Layer 2 slice)

- Layer 5 Optuna tuning now executes a PPO-backed policy objective instead of the previous learning-rate-only heuristic stub:
  - `tune-policy-rewards` now samples `learning_rate`, `train_batch_size`, `minibatch_size`, `num_epochs`, and a batch-compatible `rollout_fragment_length`.
  - `run_policy_training()` and the example config now expose the PPO batch/epoch knobs directly.
  - Layer 4 PPO training now pins Ray trial artifacts under the requested runtime output directory and returns the actual training reward metric plus the resolved PPO hyperparameters.
  - Added `orchestrator_stack/tests/test_optuna_meta_tuning.py` to verify that Layer 5 forwards sampled RL hyperparameters into `train_multiagent_ppo()` rather than scoring a placeholder objective.
- Validation run status:
  - `python3 -m compileall orchestrator_stack/run.py orchestrator_stack/orchestrator/config.py orchestrator_stack/orchestrator/main.py orchestrator_stack/orchestrator/layer4/ppo_trainer.py orchestrator_stack/orchestrator/layer5/optuna_tuner.py orchestrator_stack/tests/test_optuna_meta_tuning.py`: success
  - `PYTHONPATH=orchestrator_stack ./.venv/bin/python -m unittest orchestrator_stack.tests.test_optuna_meta_tuning`: success
  - `PYTHONPATH=orchestrator_stack ./.venv/bin/python orchestrator_stack/run.py tune --config <temp-config> --trials 1`: success, wrote `reports/tuning/202604161029_optuna_orchestrator_reward_weights.md`
  - `PYTHONPATH=orchestrator_stack ./.venv/bin/python orchestrator_stack/run.py tune-policy-rewards --config <temp-config> --trials 1`: reached the PPO-backed trial path, but Ray initialization is blocked in this sandbox by macOS process-enumeration permissions (`PermissionError` from `psutil`/`sysctl`), so the command now returns a structured `"status": "skipped"` result instead of crashing
- Remaining validation gap:
  - Re-run `tune-policy-rewards` in a non-sandboxed local shell where `ray.init()` is allowed to enumerate processes, then confirm a completed Optuna study report for `orchestrator_policy_and_rewards`.

- Layer 2 simulator + feature extraction were expanded to use a shared AIOpsLab-style normalization path:
  - `state_to_observation()` now accepts nested state wrappers, dict-backed node/task collections, queued-task placement, and common alternate field names (`machines`, `pods`, `risk_scores`, `demand_scores`, etc.).
  - `AIOpsLabBackend` now falls back to a stateful local twin-style simulation instead of returning an empty mock observation on every step, so Layer 4/5 loops can exercise Layer 2 behavior without the upstream package.
  - `TraceDrivenTwinBackend` and Layer 2 feature extraction now both depend on the same normalized observation contract instead of separate raw-dict parsing.
- Layer 2 features are now pinned at `FEATURE_COUNT=8`; synthetic asset generation now derives its matrix width from that shared constant.
- Added simulator normalization and adapter tests in `orchestrator_stack/tests/test_simulator.py`.
- Extended feature tests in `orchestrator_stack/tests/test_feature_extractor.py` to cover per-node task pressure/power-state signals and flat Prometheus-style metric-row ingestion.
- Validation run status:
  - `python3 -m compileall orchestrator_stack/orchestrator/layer2 orchestrator_stack/tests orchestrator_stack/examples/generate_synthetic_assets.py`: success
  - `PYTHONPATH=orchestrator_stack python3` Layer 2 smoke for `state_to_observation()`, fallback `AIOpsLabBackend`, and feature extraction over grouped + flat metric rows: success (`layer2-smoke-ok`)
  - `pytest` could not be executed because this worktree `.venv` is a self-referential symlink and the fallback `python3` runtime is missing `numpy` and `pytest`

- Previous session (2026-04-15 KST): Layer 1 ingestion and trace loading contracts were hardened:
  - Collector now validates all rows (not only the first row), detects mixed flat/grouped shapes, and reports row-indexed schema errors.
  - Collector now enforces non-negative queue fields, bool-like parsing for `alive/task_death`, and positive `interval_seconds`.
  - Trace ingestor now validates required trace keys and node/task minimum schema for both `.json` and `.jsonl`.
  - Trace ingestor now validates optional task fields (`urgency`, `queue_priority`, `alive`), enforces non-negative `queue_length`, and fails fast on missing trace files.
  - JSONL decode errors now include exact line number.
- Added contract tests in `orchestrator_stack/tests/test_collector.py` and `orchestrator_stack/tests/test_trace_ingestor.py`.
- Added artifact/schema notes for Layer 1 and trace logs in `orchestrator_stack/examples/README.md` and `reports/traces/README.md`.
- Validation gap: this worktree runtime does not currently have `pytest` installed, so only smoke + compile checks were executed in-session.
