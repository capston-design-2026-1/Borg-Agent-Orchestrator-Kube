# Controlled Repeated-Seed Ablation Summary

Generated: 2026-05-03 KST

Method: controlled repeated-seed ablation on the same Prometheus mitigation trace with fixed PPO curriculum and seeds `515`, `616`, and `717`.

- Trace: `reports/evaluations/202605022020_aiopslab_mitigation_prometheus_kube_trace.json`
- Status: `passed`
- Mean SLA preservation delta gain with predictor: `10.428703703703718`
- Mean predictor runtime delta change without SLA preservation: `-5.90092592592589`

## Variant Summary

| variant | seeds | pass_rate | mean_delta | std_delta | min_delta | max_delta | mean_policy_reward |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| no_predictor_no_sla_preservation | 3 | 1.000 | 71.161310565 | 8.57060379936 | 65.1437179724 | 80.974273528 | -662.114779143 |
| predictor_no_sla_preservation | 3 | 1.000 | 65.2603846391 | 20.892138673 | 42.0270513058 | 82.5020513058 | -675.015705069 |
| predictor_sla_preservation | 3 | 1.000 | 75.6890883428 | 7.89458046511 | 69.9298290836 | 84.6881624169 | -664.587001365 |

## Effects By Seed

| seed | SLA preservation gain with predictor | predictor runtime change without SLA preservation |
| ---: | ---: | ---: |
| 515 | 27.9027777778 | -25.3388888889 |
| 616 | 1.19722222222 | 6.10833333333 |
| 717 | 2.18611111111 | 1.52777777778 |

## Per-Run Details

| seed | variant | delta_vs_heuristic | beats_heuristic | policy_reward | heuristic_total | artifact |
| ---: | --- | ---: | --- | ---: | ---: | --- |
| 515 | no_predictor_no_sla_preservation | 67.3659401947 | true | -665.910149513 | -733.276089708 | reports/evaluations/controlled_ablations/202605030105_prometheus_no_predictor_no_sla_preservation_seed_515.json |
| 515 | predictor_no_sla_preservation | 42.0270513058 | true | -698.249038402 | -740.276089708 | reports/evaluations/controlled_ablations/202605030105_prometheus_predictor_no_sla_preservation_seed_515.json |
| 515 | predictor_sla_preservation | 69.9298290836 | true | -670.346260624 | -740.276089708 | reports/evaluations/controlled_ablations/202605030105_prometheus_predictor_sla_preservation_seed_515.json |
| 616 | no_predictor_no_sla_preservation | 65.1437179724 | true | -668.132371736 | -733.276089708 | reports/evaluations/controlled_ablations/202605030220_prometheus_no_predictor_no_sla_preservation_seed_616.json |
| 616 | predictor_no_sla_preservation | 71.2520513058 | true | -669.024038402 | -740.276089708 | reports/evaluations/controlled_ablations/202605030220_prometheus_predictor_no_sla_preservation_seed_616.json |
| 616 | predictor_sla_preservation | 72.449273528 | true | -667.82681618 | -740.276089708 | reports/evaluations/controlled_ablations/202605030220_prometheus_predictor_sla_preservation_seed_616.json |
| 717 | no_predictor_no_sla_preservation | 80.974273528 | true | -652.30181618 | -733.276089708 | reports/evaluations/controlled_ablations/202605030220_prometheus_no_predictor_no_sla_preservation_seed_717.json |
| 717 | predictor_no_sla_preservation | 82.5020513058 | true | -657.774038402 | -740.276089708 | reports/evaluations/controlled_ablations/202605030220_prometheus_predictor_no_sla_preservation_seed_717.json |
| 717 | predictor_sla_preservation | 84.6881624169 | true | -655.587927291 | -740.276089708 | reports/evaluations/controlled_ablations/202605030220_prometheus_predictor_sla_preservation_seed_717.json |
