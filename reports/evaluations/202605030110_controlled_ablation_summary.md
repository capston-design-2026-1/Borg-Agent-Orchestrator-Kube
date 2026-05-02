# Controlled Ablation Summary

Generated: 2026-05-03 KST

Method: controlled single-seed ablation on the same Prometheus mitigation trace with fixed PPO curriculum and seed `515`.

- Trace: `reports/evaluations/202605022020_aiopslab_mitigation_prometheus_kube_trace.json`
- Status: `passed`
- SLA preservation delta gain with predictor: `27.90277777777783`
- Predictor runtime delta change without SLA preservation: `-25.338888888888846`

| variant | label | delta_vs_heuristic | beats_heuristic | policy_reward | heuristic_total | artifact |
| --- | --- | ---: | --- | ---: | ---: | --- |
| no_predictor_no_sla_preservation | No predictor runtime, no SLA-risk preservation | 67.3659401947 | true | -665.910149513 | -733.276089708 | reports/evaluations/controlled_ablations/202605030105_prometheus_no_predictor_no_sla_preservation_seed_515.json |
| predictor_no_sla_preservation | Predictor runtime, no SLA-risk preservation | 42.0270513058 | true | -698.249038402 | -740.276089708 | reports/evaluations/controlled_ablations/202605030105_prometheus_predictor_no_sla_preservation_seed_515.json |
| predictor_sla_preservation | Predictor runtime plus SLA-risk preservation | 69.9298290836 | true | -670.346260624 | -740.276089708 | reports/evaluations/controlled_ablations/202605030105_prometheus_predictor_sla_preservation_seed_515.json |
