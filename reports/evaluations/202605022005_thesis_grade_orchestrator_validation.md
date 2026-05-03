# Thesis-Grade Orchestrator Validation Report

Generated: 2026-05-02 KST

## Claim Under Test

The Borg-Agent-Orchestrator architecture is no longer validated only with synthetic JSON traces. It now runs against a real Kubernetes control plane through Microsoft AIOpsLab, captures live cluster state during workload/fault execution, converts that state into the six-layer orchestrator trace contract, audits reward pressure, trains PPO policies, and compares learned policy reward against a deterministic heuristic baseline.

## Live Infrastructure

- Kubernetes backend: Kind cluster `borg-aiopslab`
- Kubeconfig: `~/Documents/aiopslab_validation_env/kubeconfig`
- AIOpsLab runtime: Python 3.12 environment at `~/Documents/aiopslab_validation_env`
- Application: AIOpsLab Hotel Reservation
- Observer stack: AIOpsLab-deployed Prometheus plus Kubernetes API snapshots
- Fault family validated: `misconfig_app_hotel_res-*`

## Engineering Changes Validated

- Real Kubernetes snapshot exporter derives orchestrator trace rows from `kubectl get nodes/pods/jobs -A -o json`.
- Trace rows now include live reward telemetry: `sla_violations`, `completed_tasks`, and `energy_watts`.
- Trace rows now include live control signals: `p_fail_scores` and `demand_projection`, derived from pod health, restart state, and node resource requests.
- AIOpsLab agent supports task-specific submissions for detection, localization, analysis, and mitigation.
- AIOpsLab mitigation can run real remediation commands before `submit()`.
- Periodic capture records intra-run state transitions instead of only one agent-turn snapshot.
- Trace twin preserves live SLA risk when applying synthetic action deltas, preventing learned/simulated actions from erasing hard evidence from the next real trace row.
- Prometheus/node-exporter enrichment now adds direct node CPU and memory utilization to live trace rows after AIOpsLab deploys the observer stack.
- PPO gate now compares policy episode return against heuristic total episode score, not per-step average.

## Live Task Coverage

| Task | Artifact | Result |
|---|---|---|
| No-op detection | `reports/evaluations/202605021205_aiopslab_noop_live_summary.json` | `Detection Accuracy=Correct` |
| Misconfig detection | `reports/evaluations/202605021230_aiopslab_misconfig_detection_live_summary.json` | `Detection Accuracy=Correct` |
| Misconfig localization | `reports/evaluations/202605021245_aiopslab_misconfig_localization_live_summary.json` | `Localization Accuracy=100.0`, `success=true` |
| Misconfig analysis | `reports/evaluations/202605021250_aiopslab_misconfig_analysis_live_summary.json` | `system_level_correct=true`, `fault_type_correct=true`, `success=true` |
| Misconfig mitigation | `reports/evaluations/202605021350_aiopslab_mitigation_enriched_live_summary.json` | `success=true` |
| Target-port misconfig detection | `reports/evaluations/202605022100_k8s_target_port_detection_live_summary.json` | `Detection Accuracy=Correct` |
| Target-port misconfig localization | `reports/evaluations/202605022105_k8s_target_port_localization_live_summary.json` | `Localization Accuracy=100.0`, `success=true` |
| Target-port misconfig analysis | `reports/evaluations/202605022110_k8s_target_port_analysis_live_summary.json` | `system_level_correct=true`, `fault_type_correct=true`, `success=true` |
| Target-port misconfig mitigation | `reports/evaluations/202605022120_k8s_target_port_mitigation_live_summary.json` | `success=true` |
| Scale-to-zero detection | `reports/evaluations/202605030120_scale_pod_zero_detection_live_summary.json` | `Detection Accuracy=Correct` |
| Scale-to-zero localization | `reports/evaluations/202605030125_scale_pod_zero_localization_live_summary.json` | `Localization Accuracy=100.0`, `success=true` |
| Scale-to-zero analysis | `reports/evaluations/202605030130_scale_pod_zero_analysis_live_summary.json` | `system_level_correct=true`, `fault_type_correct=true`, `success=true` |
| Scale-to-zero mitigation | `reports/evaluations/202605030135_scale_pod_zero_mitigation_live_summary.json` | `success=true` |

## Reward And Policy Evidence

### Full-Phase Live Trace

- Trace: `reports/evaluations/202605021300_aiopslab_full_phase_kube_trace.json`
- Rows: 11
- Coverage: no-op plus misconfig detection/localization/analysis/mitigation
- PPO gate before enrichment: `beats_heuristic=false`
- Evidence: `reports/evaluations/202605021310_aiopslab_full_phase_train_policy_fixed_gate.json`

### Periodic Mitigation Trace Before Risk Preservation

- Trace: `reports/evaluations/202605021325_aiopslab_misconfig_mitigation_periodic_kube_trace.json`
- Rows: 26
- PPO delta vs heuristic: `-16.72244079999996`
- Gate: `beats_heuristic=false`
- Diagnosis: richer telemetry existed, but action path still lacked sufficient safety signal persistence.

### Enriched Mitigation Trace After Risk/Demand Derivation And SLA Risk Preservation

- Trace: `reports/evaluations/202605021350_aiopslab_mitigation_enriched_kube_trace.json`
- Reward audit after preserving risk: `reports/evaluations/202605021355_aiopslab_mitigation_enriched_reward_audit_risk_preserved.json`
- Actions selected by heuristic audit: `replicate=21`, `dvfs=2`
- PPO gate: `reports/evaluations/202605021400_aiopslab_enriched_mitigation_train_policy.json`
- Policy episode reward: `-991.63369384`
- Heuristic total score: `-1118.325216304`
- Delta: `+126.69152246399995`
- Gate: `beats_heuristic=true`

This is the first validated slice where the learned policy beats the deterministic heuristic gate on a Kubernetes-derived live trace.

### Prometheus/Node-Exporter Enriched Mitigation Trace

- Trace: `reports/evaluations/202605022020_aiopslab_mitigation_prometheus_kube_trace.json`
- Summary: `reports/evaluations/202605022020_aiopslab_mitigation_prometheus_live_summary.json`
- Reward audit: `reports/evaluations/202605022020_aiopslab_mitigation_prometheus_reward_audit.json`
- PPO gate: `reports/evaluations/202605022025_aiopslab_prometheus_mitigation_train_policy.json`
- Rows: 15
- Prometheus coverage: 15 of 15 rows include `prometheus_node_exporter`
- Actions selected by heuristic audit: `replicate=13`, `dvfs=1`
- Policy episode reward: `-663.0434828466666`
- Heuristic total score: `-740.276089708`
- Delta: `+77.23260686133335`
- Gate: `beats_heuristic=true`

This replaces the earlier CPU/memory resource-request proxy for the latest mitigation validation slice with live node-exporter utilization. Energy remains model-derived from observed utilization rather than measured from hardware power telemetry.

### Second-Family Full-Phase Trace

- Fault family: `k8s_target_port-misconfig-*`
- Application: AIOpsLab SocialNetwork
- Trace: `reports/evaluations/202605022125_k8s_target_port_full_phase_kube_trace.json`
- Reward audit: `reports/evaluations/202605022125_k8s_target_port_full_phase_reward_audit.json`
- PPO gate: `reports/evaluations/202605022130_k8s_target_port_full_phase_train_policy.json`
- Stronger PPO gate: `reports/evaluations/202605030010_k8s_target_port_full_phase_train_policy_stronger.json`
- Rows: 17
- Telemetry coverage: `1.0`
- Actions selected by heuristic audit: `dvfs=13`, `replicate=3`
- Initial policy episode reward: `-329.9292652799999`
- Heuristic total score: `-324.347559168`
- Initial delta: `-5.581706111999949`
- Initial gate: `beats_heuristic=false`
- Stronger policy episode reward: `-306.3355152799999`
- Stronger delta: `+18.01204388800005`
- Stronger gate: `beats_heuristic=true`

This expands live external validity to a second full-phase fault family and closes the per-family PPO gate after a stronger curriculum. The remaining policy gap is held-out multi-family robustness rather than single-family validation.

### Multi-Family Policy Gate Suite

- Manifest: `orchestrator_stack/config/aiopslab_multi_family_gate_suite.json`
- Report: `reports/evaluations/202605030020_aiopslab_multi_family_policy_gate_suite.json`
- Latest report: `reports/evaluations/202605030445_aiopslab_multi_family_policy_gate_suite.json`
- Suite status: `passed`
- Held-out entries: 5
- Held-out passes: 5
- Hotel Reservation Prometheus mitigation delta: `+77.23260686133335`
- SocialNetwork target-port full-phase delta: `+18.01204388800005`
- SocialNetwork scale-to-zero full-phase delta: `+20.700478922666548`
- SocialNetwork assign-to-nonexistent-node full-phase delta: `+25.097637718564556`
- Hotel Reservation wrong-binary full-phase delta: `+295.0030654248894`

This is the first machine-checkable multi-family policy gate. It does not replace repeated-seed statistics, but it prevents thesis reporting from relying on unstructured manual inspection of policy JSON artifacts.

### Repeated-Seed PPO Statistics

- Summary JSON: `reports/evaluations/202605030505_repeated_seed_ppo_summary.json`
- Summary table: `reports/evaluations/202605030505_repeated_seed_ppo_summary.md`
- Seeds: `101`, `202`, `303`
- Hotel Reservation Prometheus mitigation pass rate: `3/3`
- Hotel Reservation Prometheus mitigation mean delta: `+69.34464389837028`
- Hotel Reservation Prometheus mitigation delta standard deviation: `15.733374610873856`
- SocialNetwork target-port full-phase pass rate: `3/3`
- SocialNetwork target-port full-phase mean delta: `+7.616210554666718`
- SocialNetwork target-port full-phase delta standard deviation: `4.111612192037126`
- SocialNetwork scale-to-zero full-phase pass rate: `3/3`
- SocialNetwork scale-to-zero full-phase mean delta: `+3.767145589333192`
- SocialNetwork scale-to-zero full-phase delta standard deviation: `2.430592063223214`
- SocialNetwork assign-to-nonexistent-node full-phase pass rate: `3/3`
- SocialNetwork assign-to-nonexistent-node full-phase mean delta: `+49.58072176414854`
- SocialNetwork assign-to-nonexistent-node full-phase delta standard deviation: `11.375274959397744`
- Hotel Reservation wrong-binary full-phase pass rate: `3/3`
- Hotel Reservation wrong-binary full-phase mean delta: `+254.84565801748158`
- Hotel Reservation wrong-binary full-phase delta standard deviation: `51.6215124022043`

This strengthens the PPO evidence from one-off gate passes to seed-repeated gate passes on all five reported live fault families.

### Ablation Evidence Matrix

- Matrix JSON: `reports/evaluations/202605030050_ablation_evidence_matrix.json`
- Matrix table: `reports/evaluations/202605030050_ablation_evidence_matrix.md`
- Full-phase before enrichment delta: `-27.615149653333333`
- Periodic mitigation before SLA-risk preservation delta: `-16.72244079999996`
- Risk/demand plus SLA-risk preservation delta: `+126.69152246399995`
- Prometheus/node-exporter enrichment delta: `+77.23260686133335`
- Second-family stronger curriculum delta: `+18.01204388800005`

This matrix is sequential evidence across committed validation artifacts, not a fully controlled causal ablation. The repeated-seed controlled ablation below reruns variants while holding fault family, trace length, PPO budget, and trace source fixed.

### Controlled Repeated-Seed Ablation

- Summary JSON: `reports/evaluations/202605030225_controlled_ablation_repeated_seed_summary.json`
- Summary table: `reports/evaluations/202605030225_controlled_ablation_repeated_seed_summary.md`
- Trace: `reports/evaluations/202605022020_aiopslab_mitigation_prometheus_kube_trace.json`
- Seeds: `515`, `616`, `717`
- No predictor and no SLA preservation mean delta: `+71.16131056503795`
- Predictor and no SLA preservation mean delta: `+65.26038463911178`
- Predictor and SLA preservation mean delta: `+75.6890883428155`
- Mean SLA preservation gain with predictor: `+10.428703703703718`
- Mean predictor runtime delta change without SLA preservation: `-5.90092592592589`

This shows SLA-risk preservation keeps a positive mean gain across repeated seeds, while the predictor-only effect is seed-sensitive and should be reported as mixed rather than uniformly beneficial.

### Statistical Reporting

- Statistics JSON: `reports/evaluations/202605030510_evaluation_statistics.json`
- Statistics table: `reports/evaluations/202605030510_evaluation_statistics.md`
- Method: descriptive 95% Student-t confidence intervals for seed-repeated deltas.
- Caveat: `n=3` intervals are intentionally wide; use them to report uncertainty, not as definitive significance proof.

## Brain Model Evidence

- Live full-phase risk dataset: `reports/evaluations/brain_live_full_phase/risk_dataset.npz`
- Live full-phase demand dataset: `reports/evaluations/brain_live_full_phase/demand_dataset.npz`
- Risk model: `orchestrator_stack/examples/models/live_full_phase/risk_model.json`
- Demand model: `orchestrator_stack/examples/models/live_full_phase/demand_model.json`
- Risk diagnostics: `reports/evaluations/202605021315_aiopslab_full_phase_risk_diagnostics.json`
- Demand diagnostics: `reports/evaluations/202605021315_aiopslab_full_phase_demand_diagnostics.json`

Key diagnostics:

- Risk rows: 11
- Risk Brier score: `0.14887345848485453`
- Risk expected calibration error: `0.010636160319501708`
- Demand model active features: `cpu_util`, `task_pressure`

## Current Scientific Limitations

- Current latest mitigation CPU and memory signals come from Prometheus/node-exporter. Energy watts now carry explicit calibration metadata, but are still utilization-derived rather than measured by hardware power telemetry.
- Current validated full-phase fault families are Hotel Reservation application misconfiguration, SocialNetwork Kubernetes target-port misconfiguration, SocialNetwork scale-to-zero operation error, SocialNetwork assign-to-nonexistent-node dependency fault, and Hotel Reservation wrong-binary usage; external validity still requires broader held-out multi-family testing.
- Kind is a local control plane; production cluster behavior may differ in scheduling, resource pressure, and exporter availability.
- PPO pass is validated on enriched mitigation traces, including one Prometheus/node-exporter slice, on three SocialNetwork full-phase families, on two Hotel Reservation full-phase families, on the current five-entry multi-family gate suite, and across three seeds for all five reported families. Broader external coverage remains open.
- Prometheus enrichment currently uses node-exporter CPU and memory utilization; additional PromQL mappings are still needed for service-level latency, queue pressure, and direct power signals if those exporters are available.

## Next Thesis-Grade Work

1. Expand the multi-family gate suite with another full-phase family from the AIOpsLab catalog when available.
2. Increase seed count beyond `n=3` if significance testing is required rather than descriptive confidence intervals.
3. Add ablation table coverage for `Prometheus enrichment` and any future direct measured power telemetry source.
4. Add direct power or calibrated energy telemetry if a node-power exporter is available.
5. Keep thesis-ready tables synchronized with raw JSON artifacts for reproducible evaluation appendices.

## Validation Commands

```bash
PYTHONPATH=orchestrator_stack .venv/bin/python -m pytest orchestrator_stack/tests -q
```

Latest result: `76 passed`.
