# Observability Bootstrap Report

Timestamp: `2026-05-05 13:39 KST`

## Question

Why were in-cluster Prometheus and Metrics Server not running, and what changed so the live orchestration loop receives real cluster metrics/traces?

## Root Cause

| Component | Previous state | Cause |
|---|---|---|
| Metrics Server | Missing. `v1beta1.metrics.k8s.io` did not exist and `kubectl top nodes` failed. | The live launcher never installed Metrics Server. |
| Prometheus | No running Prometheus pod in `observe`. | A stale/older Prometheus setup expected a PVC using storage class `openebs-hostpath`. This Kind cluster uses `standard` local-path storage and does not have `openebs-hostpath`, so the PVC stayed Pending. |
| Node Exporter | Missing. | No repository-owned in-cluster telemetry manifest existed for the live launcher. |
| Orchestrator Prometheus path | Optional only. | `launch_orchestration.sh` passed `--prometheus-base-url` only when the user manually provided `PROMETHEUS_BASE_URL`; it did not create or port-forward Prometheus automatically. |

## Fix

Added repository-owned observability assets:

| File | Purpose |
|---|---|
| `orchestrator_stack/k8s/observability/metrics-prometheus.yaml` | Installs Metrics Server, Prometheus, and Node Exporter for the local Kind validation cluster. Prometheus uses `emptyDir`, not the missing `openebs-hostpath` storage class. |
| `orchestrator_stack/scripts/bootstrap_observability.sh` | Applies the manifest, removes the stale Pending `observe/prometheus-pvc` when it references `openebs-hostpath`, waits for rollout readiness, and verifies `kubectl top nodes`. |
| `orchestrator_stack/scripts/launch_orchestration.sh` | In `LIVE_K8S=1`, bootstraps observability by default, starts a Prometheus port-forward, and passes `--prometheus-base-url` into `live-kubernetes-run`. |

## Live Validation

Cluster context:

```text
kind-borg-aiopslab
```

Metrics API:

```text
v1beta1.metrics.k8s.io Available=True
```

Metrics Server sample:

```text
NAME                          CPU(cores)   CPU(%)   MEMORY(bytes)   MEMORY(%)
borg-aiopslab-control-plane   169m         1%       3383Mi          43%
```

Observability pods and services:

```text
pod/prometheus-node-exporter-6tvqf       1/1 Running
pod/prometheus-server-7989876d8d-rgcds   1/1 Running
service/prometheus-node-exporter         9100/TCP
service/prometheus-server                80/TCP
```

Prometheus enrichment functional check:

```json
{
  "sample_fields": ["cpu_util", "mem_util"],
  "cpu_sample_count": 1,
  "mem_sample_count": 1,
  "telemetry_sources": ["kubernetes_api", "prometheus_node_exporter"],
  "prometheus_error": null
}
```

One-iteration launcher smoke:

```text
LIVE_K8S=1 ... PROMETHEUS_PORT=19092 ... ./orchestrator_stack/scripts/launch_orchestration.sh
```

Smoke result:

```json
{
  "mode": "live_kubernetes",
  "iterations": 1,
  "telemetry_sources": ["kubernetes_api", "prometheus_node_exporter"],
  "prometheus_error": null
}
```

## Operational Meaning

The live dashboard now has three telemetry levels:

| Source | Runtime role |
|---|---|
| Kubernetes API | Nodes, pods, jobs, queue length, SLA/pending/failure state, scheduler effects from the exerciser. |
| Metrics Server | Direct operator checks through `kubectl top`, proving in-cluster resource metrics are being served. |
| Prometheus + Node Exporter | CPU/memory samples used by the trace collector to enrich `cpu_util`, `mem_util`, `demand_projection`, risk, and estimated power. |

Energy watts remain model-derived estimates unless a power calibration file is provided. Prometheus supplies utilization inputs; it does not turn the estimate into a physical wattmeter measurement.
