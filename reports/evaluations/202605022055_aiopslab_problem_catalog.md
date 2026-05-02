# AIOpsLab Problem Catalog Snapshot

Generated: 2026-05-02 KST

- Total problem IDs: `89`
- Source: `aiopslab.orchestrator.problems.registry.ProblemRegistry` in `~/Documents/aiopslab_validation_env`
- Purpose: choose the next live validation family beyond Hotel Reservation misconfiguration.

## Full-Phase Candidates

Families with detection, localization, analysis, and mitigation entries are best next thesis targets.

| family | detection | localization | analysis | mitigation |
| --- | --- | --- | --- | --- |
| assign_to_non_existent_node_social_net | assign_to_non_existent_node_social_net-detection-1 | assign_to_non_existent_node_social_net-localization-1 | assign_to_non_existent_node_social_net-analysis-1 | assign_to_non_existent_node_social_net-mitigation-1 |
| auth_miss_mongodb | auth_miss_mongodb-detection-1 | auth_miss_mongodb-localization-1 | auth_miss_mongodb-analysis-1 | auth_miss_mongodb-mitigation-1 |
| k8s_target_port-misconfig | k8s_target_port-misconfig-detection-1, k8s_target_port-misconfig-detection-2, k8s_target_port-misconfig-detection-3 | k8s_target_port-misconfig-localization-1, k8s_target_port-misconfig-localization-2, k8s_target_port-misconfig-localization-3 | k8s_target_port-misconfig-analysis-1, k8s_target_port-misconfig-analysis-2, k8s_target_port-misconfig-analysis-3 | k8s_target_port-misconfig-mitigation-1, k8s_target_port-misconfig-mitigation-2, k8s_target_port-misconfig-mitigation-3 |
| misconfig_app_hotel_res | misconfig_app_hotel_res-detection-1 | misconfig_app_hotel_res-localization-1 | misconfig_app_hotel_res-analysis-1 | misconfig_app_hotel_res-mitigation-1 |
| revoke_auth_mongodb | revoke_auth_mongodb-detection-1, revoke_auth_mongodb-detection-2 | revoke_auth_mongodb-localization-1, revoke_auth_mongodb-localization-2 | revoke_auth_mongodb-analysis-1, revoke_auth_mongodb-analysis-2 | revoke_auth_mongodb-mitigation-1, revoke_auth_mongodb-mitigation-2 |
| scale_pod_zero_social_net | scale_pod_zero_social_net-detection-1 | scale_pod_zero_social_net-localization-1 | scale_pod_zero_social_net-analysis-1 | scale_pod_zero_social_net-mitigation-1 |
| user_unregistered_mongodb | user_unregistered_mongodb-detection-1, user_unregistered_mongodb-detection-2 | user_unregistered_mongodb-localization-1, user_unregistered_mongodb-localization-2 | user_unregistered_mongodb-analysis-1, user_unregistered_mongodb-analysis-2 | user_unregistered_mongodb-mitigation-1, user_unregistered_mongodb-mitigation-2 |
| wrong_bin_usage | wrong_bin_usage-detection-1 | wrong_bin_usage-localization-1 | wrong_bin_usage-analysis-1 | wrong_bin_usage-mitigation-1 |

## Detection/Localization-Only Candidates

| family | detection | localization |
| --- | --- | --- |
| astronomy_shop_ad_service_failure | astronomy_shop_ad_service_failure-detection-1 | astronomy_shop_ad_service_failure-localization-1 |
| astronomy_shop_ad_service_high_cpu | astronomy_shop_ad_service_high_cpu-detection-1 | astronomy_shop_ad_service_high_cpu-localization-1 |
| astronomy_shop_ad_service_manual_gc | astronomy_shop_ad_service_manual_gc-detection-1 | astronomy_shop_ad_service_manual_gc-localization-1 |
| astronomy_shop_cart_service_failure | astronomy_shop_cart_service_failure-detection-1 | astronomy_shop_cart_service_failure-localization-1 |
| astronomy_shop_image_slow_load | astronomy_shop_image_slow_load-detection-1 | astronomy_shop_image_slow_load-localization-1 |
| astronomy_shop_kafka_queue_problems | astronomy_shop_kafka_queue_problems-detection-1 | astronomy_shop_kafka_queue_problems-localization-1 |
| astronomy_shop_loadgenerator_flood_homepage | astronomy_shop_loadgenerator_flood_homepage-detection-1 | astronomy_shop_loadgenerator_flood_homepage-localization-1 |
| astronomy_shop_payment_service_failure | astronomy_shop_payment_service_failure-detection-1 | astronomy_shop_payment_service_failure-localization-1 |
| astronomy_shop_payment_service_unreachable | astronomy_shop_payment_service_unreachable-detection-1 | astronomy_shop_payment_service_unreachable-localization-1 |
| astronomy_shop_product_catalog_service_failure | astronomy_shop_product_catalog_service_failure-detection-1 | astronomy_shop_product_catalog_service_failure-localization-1 |
| astronomy_shop_recommendation_service_cache_failure | astronomy_shop_recommendation_service_cache_failure-detection-1 | astronomy_shop_recommendation_service_cache_failure-localization-1 |
| network_delay_hotel_res | network_delay_hotel_res-detection-1 | network_delay_hotel_res-localization-1 |
| network_loss_hotel_res | network_loss_hotel_res-detection-1 | network_loss_hotel_res-localization-1 |
| pod_failure_hotel_res | pod_failure_hotel_res-detection-1 | pod_failure_hotel_res-localization-1 |
| pod_kill_hotel_res | pod_kill_hotel_res-detection-1 | pod_kill_hotel_res-localization-1 |

## Recommended Next Target

`k8s_target_port-misconfig-*` is the closest next full-phase target because it has all four stages and remains Kubernetes-service specific, while being distinct from application-image misconfiguration.
