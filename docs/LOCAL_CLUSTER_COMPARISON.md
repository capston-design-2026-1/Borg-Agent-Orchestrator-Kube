# Local Multi-Node Cluster Comparison

This repository supports a fully local comparison between:

1. `borg-experimental`: a multi-node Kind cluster used by the experimental Borg orchestration architecture.
2. `borg-baseline`: a second multi-node Kind cluster running real Kubernetes HPA plus a local Karpenter-style warm-node controller.

The baseline is intentionally local-only. Upstream AWS Karpenter requires AWS/EKS APIs to create EC2 capacity, so the local baseline emulates the Karpenter provisioning/consolidation loop over pre-created Kind worker nodes. HPA itself is real Kubernetes HPA using Metrics Server.

## Create Both Clusters

```bash
./orchestrator_stack/scripts/create_local_comparison_clusters.sh
```

This writes kubeconfigs under:

```text
~/Documents/borg_orchestrator_clusters/kubeconfig-experimental
~/Documents/borg_orchestrator_clusters/kubeconfig-baseline
```

The script creates:

- one control-plane and three workers for the experimental cluster
- one control-plane and three workers for the baseline cluster
- Metrics Server, Prometheus, and Node Exporter in both clusters
- baseline `borg-baseline/hpa-web` Deployment, Service, and HPA
- baseline `borg-baseline/karpenter-surge` Deployment for triggering local Karpenter-style capacity activation

Recreate both clusters from scratch:

```bash
RECREATE=1 ./orchestrator_stack/scripts/create_local_comparison_clusters.sh
```

## Launch Experimental Orchestrator

```bash
./orchestrator_stack/scripts/launch_experimental_multinode_orchestration.sh
```

This runs the live Kubernetes orchestration loop against the experimental multi-node cluster and writes state to:

```text
orchestrator_stack/runtime/visualization-experimental/state.json
orchestrator_stack/runtime/visualization-experimental/events.jsonl
```

By default, this launcher mirrors every intentional exercise phase to the baseline cluster through:

```text
MIRROR_EXERCISE_KUBECONFIG=~/Documents/borg_orchestrator_clusters/kubeconfig-baseline
MIRROR_EXERCISE_NAMESPACE=borg-orchestrator-exercise
```

That means the input stimulus is shared, while the reactions remain independent:

- mirrored: intentional exerciser workload creation/deletion, request size, replica count, node selector, and namespace
- not mirrored: Agent A/B/C decisions, Referee choices, HPA replica changes, and local Karpenter active/warm node changes

Apply one shared stimulus manually:

```bash
PHASE_INDEX=3 ./orchestrator_stack/scripts/apply_comparison_stimulus.sh
```

Randomized but reproducible shared stimulus:

```bash
PHASE_INDEX=3 EXERCISE_RANDOMIZE=1 EXERCISE_SEED=17 ./orchestrator_stack/scripts/apply_comparison_stimulus.sh
```

## Launch Comparison Dashboard

```bash
./orchestrator_stack/scripts/launch_cluster_comparison.sh
```

Default URL:

```text
http://127.0.0.1:8876
```

The dashboard compares:

| Signal | Experimental cluster | Baseline cluster |
|---|---|---|
| nodes | ready/schedulable nodes | ready/schedulable nodes |
| pods | total and pending pods | total and pending pods |
| orchestration | active stage, reward, risk, decision | HPA desired replicas and local Karpenter state |
| capacity | all Kind workers are available | workers start as active/warm to emulate Karpenter provisioning |

## Dashboard Interpretation

The comparison dashboard is designed to show behavioral differences, not just whether both clusters are alive.

| Area | What it shows | Why it matters |
|---|---|---|
| Behavior scorecards | queue pressure, CPU utilization, replica reaction, capacity reaction | summarizes the immediate control behavior of both systems |
| Difference ledger | experimental value, baseline value, and experimental-minus-baseline delta | makes the comparison auditable instead of visual-only |
| Pressure timeline | pending pods, CPU percent, memory percent, and schedulable workers over recent samples | shows whether one system is accumulating backlog or absorbing load |
| Live resource mix | `kubectl top` CPU and memory for each cluster | separates actual usage from declared requests |
| Capacity and demand | pod CPU/memory requests versus allocatable cluster capacity | shows scheduling pressure before pods become pending |
| Pod phase mix | Running, Pending, Succeeded, Failed, and Unknown pod distribution | exposes admission and scheduling outcomes |
| Namespace distribution | where pods are concentrated in each cluster | confirms whether pressure comes from experiment workloads, baseline HPA workloads, or system components |
| Controller reactions | latest Agent A/B/C decision, proposals, Ray/Optuna status, HPA replica movement, and local Karpenter active/warm nodes | explains what each control plane is doing rather than only displaying cluster state |
| Node inventory | per-node readiness, schedulability, active/warm state, allocatable resources, and live usage | verifies that the comparison is truly multi-node and shows where work lands |
| Workload inventory | Deployments, DaemonSets, StatefulSets, and Jobs discovered in both clusters | confirms which workload controllers are driving the observed behavior |

The API behind the dashboard is `GET /api/comparison`. It reads both kubeconfigs live with `kubectl`, uses Metrics Server through `kubectl top`, and joins that with the experimental orchestration state file:

```text
orchestrator_stack/runtime/visualization-experimental/state.json
```

If Metrics Server is unhealthy, the dashboard still renders Kubernetes object state, but the live CPU/memory sections show warnings in the `Interpretation Boundary` panel.

## Trigger Baseline Karpenter-Style Provisioning

```bash
./orchestrator_stack/scripts/apply_baseline_surge.sh
```

Default surge replicas: `8`.

Custom surge:

```bash
REPLICAS=14 ./orchestrator_stack/scripts/apply_baseline_surge.sh
```

The local Karpenter-style controller watches pending pods in `borg-baseline` and activates warm worker nodes by:

- removing the `borg.local/capacity=warm:NoSchedule` taint
- uncordoning the node
- changing `borg.local/provisioning-state` from `warm` to `active`

When extra nodes remain idle for a configured period, the controller can cordon and taint them again to emulate consolidation.

## Observe With k9s

Experimental cluster:

```bash
KUBECONFIG=~/Documents/borg_orchestrator_clusters/kubeconfig-experimental k9s
```

Baseline cluster:

```bash
KUBECONFIG=~/Documents/borg_orchestrator_clusters/kubeconfig-baseline k9s
```

## Important Boundary

This is not real AWS Karpenter. It is a local, reproducible Karpenter-style baseline that preserves the comparison idea without requiring AWS. For a production claim, the same experiment should later be repeated on EKS with real Karpenter NodePools and EC2NodeClasses.
