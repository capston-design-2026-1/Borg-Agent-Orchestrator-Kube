# Repeated-Seed PPO Summary

Generated: 2026-05-03 KST

| evaluation_set | seeds | pass_rate | mean_delta | std_delta | min_delta | max_delta | mean_policy_reward | mean_heuristic |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| hotel_reservation_prometheus_mitigation | 3 | 1.000 | 69.3446438984 | 15.7333746109 | 51.7381624169 | 82.0270513058 | -670.93144581 | -740.276089708 |
| social_network_k8s_target_port_full_phase | 3 | 1.000 | 7.61621055467 | 4.11161219204 | 2.902668888 | 10.465168888 | -316.731348613 | -324.347559168 |
| social_network_scale_pod_zero_full_phase | 3 | 1.000 | 3.76714558933 | 2.43059206322 | 1.50047892267 | 6.333812256 | -562.582136027 | -566.349281616 |
| social_network_assign_nonexistent_node_full_phase | 3 | 1.000 | 49.5807217641 | 11.3752749594 | 36.4603513938 | 56.6783001117 | -1744.29541781 | -1793.87613958 |

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

### social_network_scale_pod_zero_full_phase

| seed | delta_vs_heuristic | beats_heuristic | policy_episode_reward_mean | heuristic_total_score | artifact |
| ---: | ---: | --- | ---: | ---: | --- |
| 101 | 1.50047892267 | true | -564.848802693 | -566.349281616 | reports/evaluations/repeated_seeds/202605030200_scale_pod_zero_full_phase_seed_101.json |
| 202 | 3.46714558933 | true | -562.882136027 | -566.349281616 | reports/evaluations/repeated_seeds/202605030200_scale_pod_zero_full_phase_seed_202.json |
| 303 | 6.333812256 | true | -560.01546936 | -566.349281616 | reports/evaluations/repeated_seeds/202605030200_scale_pod_zero_full_phase_seed_303.json |

### social_network_assign_nonexistent_node_full_phase

| seed | delta_vs_heuristic | beats_heuristic | policy_episode_reward_mean | heuristic_total_score | artifact |
| ---: | ---: | --- | ---: | ---: | --- |
| 101 | 55.6035137869 | true | -1738.27262579 | -1793.87613958 | reports/evaluations/repeated_seeds/202605030345_assign_nonexistent_full_phase_stronger_seed_101.json |
| 202 | 36.4603513938 | true | -1757.41578818 | -1793.87613958 | reports/evaluations/repeated_seeds/202605030345_assign_nonexistent_full_phase_stronger_seed_202.json |
| 303 | 56.6783001117 | true | -1737.19783946 | -1793.87613958 | reports/evaluations/repeated_seeds/202605030345_assign_nonexistent_full_phase_stronger_seed_303.json |
