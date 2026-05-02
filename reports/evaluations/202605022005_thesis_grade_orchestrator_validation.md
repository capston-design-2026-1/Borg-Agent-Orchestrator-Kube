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
- Rows: 17
- Telemetry coverage: `1.0`
- Actions selected by heuristic audit: `dvfs=13`, `replicate=3`
- Policy episode reward: `-329.9292652799999`
- Heuristic total score: `-324.347559168`
- Delta: `-5.581706111999949`
- Gate: `beats_heuristic=false`

This expands live external validity to a second full-phase fault family. The remaining policy gap is now robustness across families, because the learned policy does not yet beat the heuristic on this second-family trace.

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

- Current latest mitigation CPU and memory signals come from Prometheus/node-exporter, but energy watts are still model-derived rather than measured by hardware power telemetry.
- Current validated full-phase fault families are Hotel Reservation application misconfiguration and SocialNetwork Kubernetes target-port misconfiguration; external validity still requires held-out multi-family testing.
- Kind is a local control plane; production cluster behavior may differ in scheduling, resource pressure, and exporter availability.
- PPO pass is validated on enriched mitigation traces, including one Prometheus/node-exporter slice, but not yet on the second full-phase family or a broad multi-family trace corpus.
- Prometheus enrichment currently uses node-exporter CPU and memory utilization; additional PromQL mappings are still needed for service-level latency, queue pressure, and direct power signals if those exporters are available.

## Next Thesis-Grade Work

1. Improve PPO robustness on the second full-phase family and then on held-out multi-family traces.
2. Build a multi-family trace corpus and require PPO to beat heuristic total score across held-out traces.
3. Add statistical reporting: repeated seeds, confidence intervals, and ablation table for `no risk derivation`, `risk derivation only`, `risk preservation`, and `Prometheus enrichment`.
4. Add direct power or calibrated energy telemetry if a node-power exporter is available.
5. Keep thesis-ready tables synchronized with raw JSON artifacts for reproducible evaluation appendices.

## Validation Commands

```bash
PYTHONPATH=orchestrator_stack .venv/bin/python -m pytest orchestrator_stack/tests -q
```

Latest result: `76 passed`.
