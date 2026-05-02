# Thesis Evaluation Tables

- Source directory: `reports/evaluations`

## Live AIOpsLab Tasks

| label | problem_id | final_state | success | trace_rows | capture_error_count | primary_result | artifact |
| --- | --- | --- | --- | --- | --- | --- | --- |
| aiopslab_noop_live_summary | noop_detection_hotel_reservation-1 | SubmissionStatus.VALID_SUBMISSION |  |  | 0 | Detection Accuracy=Correct | reports/evaluations/202605021141_aiopslab_noop_live_summary.json |
| aiopslab_noop_live_summary | noop_detection_hotel_reservation-1 | SubmissionStatus.VALID_SUBMISSION |  | 2 | 0 | Detection Accuracy=Correct | reports/evaluations/202605021205_aiopslab_noop_live_summary.json |
| aiopslab_misconfig_detection_live_summary | misconfig_app_hotel_res-detection-1 | SubmissionStatus.VALID_SUBMISSION |  | 2 | 0 | Detection Accuracy=Correct | reports/evaluations/202605021230_aiopslab_misconfig_detection_live_summary.json |
| aiopslab_misconfig_localization_live_summary | misconfig_app_hotel_res-localization-1 | SubmissionStatus.VALID_SUBMISSION | true | 2 | 0 | Localization Accuracy=100 | reports/evaluations/202605021245_aiopslab_misconfig_localization_live_summary.json |
| aiopslab_misconfig_analysis_live_summary | misconfig_app_hotel_res-analysis-1 | SubmissionStatus.VALID_SUBMISSION | true | 2 | 0 | system_level_correct=true | reports/evaluations/202605021250_aiopslab_misconfig_analysis_live_summary.json |
| aiopslab_misconfig_mitigation_live_summary | misconfig_app_hotel_res-mitigation-1 | SubmissionStatus.VALID_SUBMISSION | true | 3 | 0 | success=true | reports/evaluations/202605021255_aiopslab_misconfig_mitigation_live_summary.json |
| aiopslab_misconfig_mitigation_periodic_live_summary | misconfig_app_hotel_res-mitigation-1 | SubmissionStatus.VALID_SUBMISSION | true | 26 | 0 | success=true | reports/evaluations/202605021325_aiopslab_misconfig_mitigation_periodic_live_summary.json |
| aiopslab_mitigation_enriched_live_summary | misconfig_app_hotel_res-mitigation-1 | SubmissionStatus.VALID_SUBMISSION | true | 24 | 0 | success=true | reports/evaluations/202605021350_aiopslab_mitigation_enriched_live_summary.json |
| aiopslab_mitigation_prometheus_live_summary | misconfig_app_hotel_res-mitigation-1 | SubmissionStatus.VALID_SUBMISSION | true | 15 | 2 | success=true | reports/evaluations/202605022020_aiopslab_mitigation_prometheus_live_summary.json |
| k8s_target_port_detection_live_summary | k8s_target_port-misconfig-detection-1 | SubmissionStatus.VALID_SUBMISSION |  | 4 | 0 | Detection Accuracy=Correct | reports/evaluations/202605022100_k8s_target_port_detection_live_summary.json |
| k8s_target_port_localization_live_summary | k8s_target_port-misconfig-localization-1 | SubmissionStatus.VALID_SUBMISSION | true | 4 | 0 | Localization Accuracy=100 | reports/evaluations/202605022105_k8s_target_port_localization_live_summary.json |
| k8s_target_port_analysis_live_summary | k8s_target_port-misconfig-analysis-1 | SubmissionStatus.VALID_SUBMISSION | true | 4 | 0 | system_level_correct=true | reports/evaluations/202605022110_k8s_target_port_analysis_live_summary.json |
| k8s_target_port_mitigation_live_summary | k8s_target_port-misconfig-mitigation-1 | SubmissionStatus.VALID_SUBMISSION | true | 5 | 0 | success=true | reports/evaluations/202605022120_k8s_target_port_mitigation_live_summary.json |

## Telemetry Reward Audits

| label | steps | telemetry_coverage | max_sla_violations | max_completed_tasks | max_energy_watts | actions | weighted_telemetry_delta | artifact |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| sample_telemetry_reward_audit | 2 | 1 | 1 | 25 | 310 | {"migrate": 1, "throttle": 1} | -94.46 | reports/evaluations/202605020534_sample_telemetry_reward_audit.json |
| aiopslab_noop_kube_reward_audit | 1 | 1 | 0 | 0 | 116.420408 | {"dvfs": 1} | 2.301477552 | reports/evaluations/202605021205_aiopslab_noop_kube_reward_audit.json |
| aiopslab_misconfig_detection_reward_audit | 1 | 1 | 1 | 0 | 116.420408 | {"dvfs": 1} | -47.698522448 | reports/evaluations/202605021230_aiopslab_misconfig_detection_reward_audit.json |
| aiopslab_combined_reward_audit | 3 | 1 | 1 | 0 | 116.420408 | {"dvfs": 3} | -43.095567344 | reports/evaluations/202605021235_aiopslab_combined_reward_audit.json |
| aiopslab_misconfig_localization_reward_audit | 1 | 1 | 1 | 0 | 116.420408 | {"dvfs": 1} | -47.698522448 | reports/evaluations/202605021245_aiopslab_misconfig_localization_reward_audit.json |
| aiopslab_misconfig_analysis_reward_audit | 1 | 1 | 1 | 0 | 116.420408 | {"dvfs": 1} | -47.698522448 | reports/evaluations/202605021250_aiopslab_misconfig_analysis_reward_audit.json |
| aiopslab_misconfig_mitigation_reward_audit | 2 | 1 | 1 | 0 | 116.420408 | {"dvfs": 2} | -95.397044896 | reports/evaluations/202605021255_aiopslab_misconfig_mitigation_reward_audit.json |
| aiopslab_full_phase_reward_audit | 10 | 1 | 1 | 0 | 116.420408 | {"dvfs": 10} | -376.98522448 | reports/evaluations/202605021300_aiopslab_full_phase_reward_audit.json |
| aiopslab_misconfig_mitigation_periodic_reward_audit | 25 | 1 | 2 | 2 | 117.620408 | {"dvfs": 25} | -1237.4086612 | reports/evaluations/202605021325_aiopslab_misconfig_mitigation_periodic_reward_audit.json |
| aiopslab_mitigation_enriched_reward_audit | 23 | 1 | 2 | 2 | 117.620408 | {"dvfs": 22, "replicate": 1} | -1142.5252163 | reports/evaluations/202605021350_aiopslab_mitigation_enriched_reward_audit.json |
| aiopslab_mitigation_enriched_reward_audit_risk_preserved | 23 | 1 | 2 | 2 | 117.620408 | {"dvfs": 2, "replicate": 21} | -1142.5252163 | reports/evaluations/202605021355_aiopslab_mitigation_enriched_reward_audit_risk_preserved.json |
| aiopslab_mitigation_prometheus_reward_audit | 14 | 1 | 1 | 2 | 128.083859 | {"dvfs": 1, "replicate": 13} | -665.876089708 | reports/evaluations/202605022020_aiopslab_mitigation_prometheus_reward_audit.json |
| k8s_target_port_detection_reward_audit | 3 | 1 | 0 | 0 | 93.620408 | {"dvfs": 3} | 7.314832656 | reports/evaluations/202605022100_k8s_target_port_detection_reward_audit.json |
| k8s_target_port_localization_reward_audit | 3 | 1 | 0 | 0 | 93.620408 | {"dvfs": 3} | 7.314832656 | reports/evaluations/202605022105_k8s_target_port_localization_reward_audit.json |
| k8s_target_port_analysis_reward_audit | 3 | 1 | 0 | 0 | 93.620408 | {"dvfs": 3} | 7.314832656 | reports/evaluations/202605022110_k8s_target_port_analysis_reward_audit.json |
| k8s_target_port_mitigation_reward_audit | 4 | 1 | 0 | 0 | 93.620408 | {"dvfs": 4} | 9.753110208 | reports/evaluations/202605022120_k8s_target_port_mitigation_reward_audit.json |
| k8s_target_port_full_phase_reward_audit | 16 | 1 | 1 | 1 | 93.620408 | {"dvfs": 13, "replicate": 3} | -260.507559168 | reports/evaluations/202605022125_k8s_target_port_full_phase_reward_audit.json |

## PPO Policy Gates

| label | status | stage_count | policy_episode_reward_mean | heuristic_total_score | delta_vs_heuristic | beats_heuristic | artifact |
| --- | --- | --- | --- | --- | --- | --- | --- |
| aiopslab_live_train_policy | trained | 2 | 3.94517092 | 8.701477552 | -4.756306632 | false | reports/evaluations/202605021218_aiopslab_live_train_policy.json |
| aiopslab_live_train_policy_stronger | trained | 3 | 6.75767092 | 8.701477552 | -1.943806632 | false | reports/evaluations/202605021222_aiopslab_live_train_policy_stronger.json |
| aiopslab_combined_train_policy | trained | 3 | -31.2994304218 | -23.895567344 | -23.3342413072 | false | reports/evaluations/202605021235_aiopslab_combined_train_policy.json |
| aiopslab_full_phase_train_policy_fixed_gate | trained | 3 | -340.600374133 | -312.98522448 | -27.6151496533 | false | reports/evaluations/202605021310_aiopslab_full_phase_train_policy_fixed_gate.json |
| aiopslab_periodic_mitigation_train_policy | trained | 3 | -1219.131102 | -1202.4086612 | -16.7224408 | false | reports/evaluations/202605021330_aiopslab_periodic_mitigation_train_policy.json |
| aiopslab_enriched_mitigation_train_policy | trained | 3 | -991.63369384 | -1118.3252163 | 126.691522464 | true | reports/evaluations/202605021400_aiopslab_enriched_mitigation_train_policy.json |
| aiopslab_prometheus_mitigation_train_policy | trained | 3 | -663.043482847 | -740.276089708 | 77.2326068613 | true | reports/evaluations/202605022025_aiopslab_prometheus_mitigation_train_policy.json |
| k8s_target_port_full_phase_train_policy | trained | 3 | -329.92926528 | -324.347559168 | -5.581706112 | false | reports/evaluations/202605022130_k8s_target_port_full_phase_train_policy.json |
