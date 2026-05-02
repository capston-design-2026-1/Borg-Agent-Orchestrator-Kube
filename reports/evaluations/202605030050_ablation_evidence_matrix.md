# Ablation Evidence Matrix

Generated: 2026-05-03 KST

Method note: sequential evidence from committed live-validation artifacts. This is not yet a fully controlled causal ablation; controlled reruns should keep fault family, trace length, and PPO budget fixed.

| label | factor | rows | telemetry_coverage | actions | delta_vs_heuristic | beats_heuristic | policy_artifact |
| --- | --- | ---: | ---: | --- | ---: | --- | --- |
| full_phase_before_enrichment | Live full-phase trace before enriched mitigation reward design | 11 | 1.0 | {"dvfs": 10} | -27.6151496533 | false | reports/evaluations/202605021310_aiopslab_full_phase_train_policy_fixed_gate.json |
| periodic_mitigation_before_risk_preservation | Periodic mitigation capture before SLA-risk preservation | 26 | 1.0 | {"dvfs": 25} | -16.7224408 | false | reports/evaluations/202605021330_aiopslab_periodic_mitigation_train_policy.json |
| risk_demand_plus_sla_preservation | Risk/demand derivation plus SLA-risk preservation | 24 | 1.0 | {"dvfs": 2, "replicate": 21} | 126.691522464 | true | reports/evaluations/202605021400_aiopslab_enriched_mitigation_train_policy.json |
| prometheus_node_exporter_enrichment | Prometheus/node-exporter CPU and memory enrichment | 15 | 1.0 | {"dvfs": 1, "replicate": 13} | 77.2326068613 | true | reports/evaluations/202605022025_aiopslab_prometheus_mitigation_train_policy.json |
| second_family_stronger_curriculum | Second full-phase family plus stronger PPO curriculum | 17 | 1.0 | {"dvfs": 13, "replicate": 3} | 18.012043888 | true | reports/evaluations/202605030010_k8s_target_port_full_phase_train_policy_stronger.json |
