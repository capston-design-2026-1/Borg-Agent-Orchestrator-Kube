# Repeated-Seed PPO Summary

Generated: 2026-05-03 KST

| evaluation_set | seeds | pass_rate | mean_delta | std_delta | min_delta | max_delta | mean_policy_reward | mean_heuristic |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| hotel_reservation_prometheus_mitigation | 3 | 1.000 | 69.3446438984 | 15.7333746109 | 51.7381624169 | 82.0270513058 | -670.93144581 | -740.276089708 |
| social_network_k8s_target_port_full_phase | 3 | 1.000 | 7.61621055467 | 4.11161219204 | 2.902668888 | 10.465168888 | -316.731348613 | -324.347559168 |

## Per-Run Details

### hotel_reservation_prometheus_mitigation

| seed | delta_vs_heuristic | beats_heuristic | policy_episode_reward_mean | heuristic_total_score | artifact |
| ---: | ---: | --- | ---: | ---: | --- |
| 101 | 51.7381624169 | true | -688.537927291 | -740.276089708 | reports/evaluations/repeated_seeds/202605030030_aiopslab_prometheus_mitigation_seed_101.json |
| 202 | 82.0270513058 | true | -658.249038402 | -740.276089708 | reports/evaluations/repeated_seeds/202605030030_aiopslab_prometheus_mitigation_seed_202.json |
| 303 | 74.2687179724 | true | -666.007371736 | -740.276089708 | reports/evaluations/repeated_seeds/202605030030_aiopslab_prometheus_mitigation_seed_303.json |

### social_network_k8s_target_port_full_phase

| seed | delta_vs_heuristic | beats_heuristic | policy_episode_reward_mean | heuristic_total_score | artifact |
| ---: | ---: | --- | ---: | ---: | --- |
| 101 | 10.465168888 | true | -313.88239028 | -324.347559168 | reports/evaluations/repeated_seeds/202605030030_k8s_target_port_full_phase_seed_101.json |
| 202 | 2.902668888 | true | -321.44489028 | -324.347559168 | reports/evaluations/repeated_seeds/202605030030_k8s_target_port_full_phase_seed_202.json |
| 303 | 9.480793888 | true | -314.86676528 | -324.347559168 | reports/evaluations/repeated_seeds/202605030030_k8s_target_port_full_phase_seed_303.json |
