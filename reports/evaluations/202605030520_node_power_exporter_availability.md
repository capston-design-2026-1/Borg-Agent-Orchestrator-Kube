# Node Power Exporter Availability

Generated: 2026-05-03 22:05 KST

- Cluster: `kind-borg-aiopslab`
- Kubeconfig: `~/Documents/aiopslab_validation_env/kubeconfig`
- Checked pod/service patterns: `kepler`, `power`, `rapl`, `ipmi`, `dcgm`, `node-exporter`, `prometheus`
- Result: no matching pod or service exposing direct node-power telemetry was present.

Conclusion: direct measured node-power telemetry is not available in the current Kind validation cluster. The orchestrator therefore keeps `energy_watts` as utilization-derived and records explicit `power_calibration` metadata beside trace rows until Kepler, RAPL, IPMI, or an equivalent measured source is installed.
