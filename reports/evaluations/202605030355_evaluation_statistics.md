# Evaluation Statistics

- Confidence level: `0.95`
- Method: Student t confidence intervals for seed-repeated deltas; n=3 intervals are descriptive and intentionally wide.
- Repeated-seed input: `reports/evaluations/202605030350_repeated_seed_ppo_summary.json`
- Controlled-ablation input: `reports/evaluations/202605030225_controlled_ablation_repeated_seed_summary.json`

## Repeated-Seed Policy Deltas

| evaluation_set | n | mean | std | ci95_low | ci95_high | ci95_half_width | pass_rate |
| --- | --- | --- | --- | --- | --- | --- | --- |
| hotel_reservation_prometheus_mitigation | 3 | 69.3446438984 | 15.7333746109 | 30.2607746944 | 108.428513102 | 39.083869204 | 1 |
| social_network_k8s_target_port_full_phase | 3 | 7.61621055467 | 4.11161219204 | -2.59760034767 | 17.830021457 | 10.2138109023 | 1 |
| social_network_scale_pod_zero_full_phase | 3 | 3.76714558933 | 2.43059206322 | -2.27077981679 | 9.80507099545 | 6.03792540612 | 1 |
| social_network_assign_nonexistent_node_full_phase | 3 | 49.5807217641 | 11.3752749594 | 21.3229722559 | 77.8384712724 | 28.2577495083 | 1 |

## Controlled Ablation Variant Deltas

| variant | n | mean | std | ci95_low | ci95_high | ci95_half_width | pass_rate |
| --- | --- | --- | --- | --- | --- | --- | --- |
| no_predictor_no_sla_preservation | 3 | 71.161310565 | 8.57060379936 | 49.8707504546 | 92.4518706755 | 21.2905601105 | 1 |
| predictor_no_sla_preservation | 3 | 65.2603846391 | 20.892138673 | 13.3614350823 | 117.159334196 | 51.8989495568 | 1 |
| predictor_sla_preservation | 3 | 75.6890883428 | 7.89458046511 | 56.077863291 | 95.3003133947 | 19.6112250518 | 1 |

## Controlled Ablation Effects

| effect | n | mean | std | ci95_low | ci95_high | ci95_half_width |
| --- | --- | --- | --- | --- | --- | --- |
| sla_preservation_delta_gain_with_predictor | 3 | 10.4287037037 | 15.1410674613 | -27.1837929731 | 48.0412003805 | 37.6124966768 |
| predictor_runtime_delta_change_without_sla_preservation | 3 | -5.90092592593 | 16.9888544467 | -48.1035799364 | 36.3017280846 | 42.2026540105 |
