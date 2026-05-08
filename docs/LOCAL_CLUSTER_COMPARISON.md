# Local Multi-Node Cluster Comparison

For copy-paste startup, Prometheus links, dashboard links, k9s commands, and shutdown commands, use `docs/LOCAL_DUAL_CLUSTER_RUNBOOK.md`.

## Top One-Liners

Start the complete local comparison stack from one terminal:

```bash
cd /Users/theokim/Documents/github/kyunghee/Borg-Agent-Orchestrator && ./orchestrator_stack/scripts/start_local_dual_cluster_stack.sh
```

Stop the complete local comparison stack, including both Kind clusters:

```bash
cd /Users/theokim/Documents/github/kyunghee/Borg-Agent-Orchestrator && ./orchestrator_stack/scripts/stop_local_dual_cluster_stack.sh
```

Open k9s for the experimental Agent A/B/C cluster:

```bash
KUBECONFIG=~/Documents/borg_orchestrator_clusters/kubeconfig-experimental k9s
```

Open k9s for the HPA/local-Karpenter baseline cluster:

```bash
KUBECONFIG=~/Documents/borg_orchestrator_clusters/kubeconfig-baseline k9s
```

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
- identical shared `borg-comparison-workload/comparison-web` workload, Service, and load generator in both clusters
- baseline-only HPA object targeting `borg-comparison-workload/comparison-web`
- baseline-only `borg-comparison-workload/karpenter-surge` Deployment for triggering local Karpenter-style capacity activation

Fairness boundary:

- Shared environment: same namespace, application Deployment, Service, load generator, mirrored intentional exerciser phases, CPU/memory requests, and replica baselines.
- Baseline-only controller layer: HPA object, HPA-driven replica changes, local Karpenter warm-node activation, and the optional `karpenter-surge` pressure target.
- Experimental-only controller layer: Agent A/B/C decisions, Referee choices, Ray/Optuna metadata, and orchestration reward state.

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
| Pressure timeline | pending pods, CPU percent, memory percent, and HPA current/desired replicas over retained server-side samples | shows whether one system is accumulating backlog or absorbing load over a longer run, and keeps HPA scale history visible after it reaches a stable state |
| Live resource mix | `kubectl top` CPU/memory plus requested CPU/memory for each cluster | separates actual usage from declared requests without mixing incompatible units in one chart |
| Capacity matrix | separate CPU request, memory request, and live CPU usage rows with experimental/baseline gauges and percentage-point deltas | separates scheduler demand from actual usage so capacity pressure is readable instead of compressed into one chart |
| Pod phase mix | Running, Pending, Succeeded, Failed, and Unknown pod distribution | exposes admission and scheduling outcomes |
| Namespace distribution | where pods are concentrated in each cluster | confirms whether pressure comes from experiment workloads, baseline HPA workloads, or system components |
| Controller reactions | latest Agent A/B/C decision, proposals, Ray/Optuna status, HPA replica movement, and local Karpenter active/warm nodes | explains what each control plane is doing rather than only displaying cluster state |
| Node inventory | per-node readiness, schedulability, active/warm state, allocatable resources, and live usage | verifies that the comparison is truly multi-node and shows where work lands |
| Workload inventory | Deployments, DaemonSets, StatefulSets, and Jobs discovered in both clusters | confirms which workload controllers are driving the observed behavior |

The API behind the dashboard is `GET /api/comparison`. It reads both kubeconfigs live with `kubectl`, uses Metrics Server through `kubectl top`, and joins that with the experimental orchestration state file:

```text
orchestrator_stack/runtime/visualization-experimental/state.json
```

The comparison API also retains up to `7200` samples in server memory while the dashboard server is running. At the default polling cadence this gives several hours of pressure timeline context instead of only the latest short browser window.

If the HPA display says `stable at N replicas`, that does not mean HPA did nothing. It means `currentReplicas == desiredReplicas` at the latest sample. Use the HPA current/desired lines in the pressure timeline and the `Baseline Autoscalers` table to see earlier scale movement, CPU target, replica headroom, and last scale time.

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

The local Karpenter-style controller watches pending pods in `borg-comparison-workload` and activates warm worker nodes by:

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
