# Kubernetes Environment Snapshot for the Live Orchestration Run

Snapshot time: 2026-05-05 12:49 KST  
Kubeconfig: `~/Documents/aiopslab_validation_env/kubeconfig`  
Current context: `kind-borg-aiopslab`

## Executive Summary

The orchestration architecture is currently running against a **local Kind Kubernetes validation cluster**, not a cloud-managed or production multi-node cluster.

The live target is a **single-node, control-plane-only Kubernetes v1.35.0 cluster** named `borg-aiopslab`. The orchestrator is connected through the Kubernetes API and is actively creating synthetic workload/stimulus deployments in the `borg-orchestrator-exercise` namespace. These stimuli create real Kubernetes scheduler behavior, including pending pods and `Insufficient cpu` scheduling failures, but the dashboard's energy number is currently an estimated value derived from utilization calibration rather than a physical wattmeter reading.

## Cluster Identity

| Field | Value |
|---|---|
| Kubernetes context | `kind-borg-aiopslab` |
| Cluster type | Local Kind cluster running in Docker |
| Docker node container | `borg-aiopslab-control-plane` |
| Kind node image | `kindest/node:v1.35.0` |
| API server endpoint | `https://127.0.0.1:54392` |
| Docker port mapping | `127.0.0.1:54392 -> 6443/tcp` |
| Kubernetes server version | `v1.35.0` |
| kubectl client version | `v1.34.1` |
| Kustomize version | `v5.7.1` |

## Node Inventory

| Field | Value |
|---|---|
| Node name | `borg-aiopslab-control-plane` |
| Role | `control-plane` |
| Status | `Ready` |
| Provider ID | `kind://docker/borg-aiopslab/borg-aiopslab-control-plane` |
| Internal IP | `172.19.0.2` |
| Pod CIDR | `10.244.0.0/24` |
| Architecture | `arm64` |
| OS image | `Debian GNU/Linux 12 (bookworm)` |
| Kernel | `6.12.76-linuxkit` |
| Container runtime | `containerd://2.2.0` |
| Kubelet | `v1.35.0` |
| Capacity CPU | `10` cores |
| Allocatable CPU | `10` cores |
| Capacity memory | `8024472Ki` |
| Allocatable memory | `8024472Ki` |
| Pod capacity | `110` pods |
| Ephemeral storage | `954925484Ki` |

Current node pressure conditions:

| Condition | Status | Meaning |
|---|---:|---|
| `Ready` | `True` | Kubelet is healthy and accepting work. |
| `MemoryPressure` | `False` | No memory-pressure condition reported by kubelet. |
| `DiskPressure` | `False` | No disk-pressure condition reported by kubelet. |
| `PIDPressure` | `False` | No PID-pressure condition reported by kubelet. |

## Namespaces

| Namespace | Age | Current role in this architecture |
|---|---:|---|
| `borg-orchestrator-exercise` | 11h | Active namespace used by the orchestrator's intentional Kubernetes stimulus/exerciser. |
| `default` | 3d1h | Contains a completed DeathStarBench `wrk2` job from prior validation activity. |
| `kube-node-lease` | 3d1h | Standard Kubernetes node lease namespace. |
| `kube-public` | 3d1h | Standard public cluster namespace. |
| `kube-system` | 3d1h | Core control-plane, DNS, CNI, and proxy components. |
| `local-path-storage` | 3d1h | Kind/local-path dynamic storage provisioner namespace. |
| `observe` | 3d1h | Intended observability namespace; currently no running pods. Has a pending Prometheus PVC. |
| `test-social-network` | 2d15h | DeathStarBench/AIOpsLab test namespace; currently no active resources. |

## Active Workloads at Snapshot

### Orchestrator Exercise Namespace

At the snapshot, the live workload exerciser had created this active deployment:

| Resource | Value |
|---|---|
| Namespace | `borg-orchestrator-exercise` |
| Deployment | `bursty-safety` |
| Image | `registry.k8s.io/pause:3.10` |
| Replicas | `1` desired |
| Pod status | `Pending` |
| QoS class | `Guaranteed` |
| CPU request/limit | `9595m` / `9595m` |
| Memory request/limit | `1089Mi` / `1089Mi` |
| Scheduling result | `FailedScheduling`: `0/1 nodes are available: 1 Insufficient cpu` |

This is a real Kubernetes scheduling effect. The orchestrator is intentionally generating workloads with changing requests such as `moderate-demand`, `high-risk`, and `bursty-safety` so that Agent A/B/C and the referee have non-static cluster states to evaluate.

### System Workloads

| Namespace | Resource | Status |
|---|---|---|
| `kube-system` | `coredns` deployment, 2 pods | Running |
| `kube-system` | `kindnet` daemonset | Running |
| `kube-system` | `kube-proxy` daemonset | Running |
| `kube-system` | `etcd-borg-aiopslab-control-plane` | Running |
| `kube-system` | `kube-apiserver-borg-aiopslab-control-plane` | Running |
| `kube-system` | `kube-controller-manager-borg-aiopslab-control-plane` | Running |
| `kube-system` | `kube-scheduler-borg-aiopslab-control-plane` | Running |
| `local-path-storage` | `local-path-provisioner` | Running |
| `default` | `wrk2-job` | Completed |

No active pods were present in `test-social-network` or `observe` at the snapshot time.

## Networking and Services

| Component | Value |
|---|---|
| CNI | Kindnet (`kindnet` daemonset) |
| Pod network | `10.244.0.0/24` on the single node |
| Cluster DNS service | `kube-system/kube-dns`, ClusterIP `10.96.0.10` |
| Kubernetes API service | `default/kubernetes`, ClusterIP `10.96.0.1` |
| External service exposure | None observed beyond the local Kind API port mapping |

Only the default Kubernetes service and CoreDNS service were present at snapshot time.

## Storage and Observability

| Item | Status | Interpretation |
|---|---|---|
| Default storage class | `standard`, provisioner `rancher.io/local-path` | Local-path storage is available. |
| `observe/prometheus-pvc` | `Pending` | The PVC requests `openebs-hostpath`, but that storage class does not exist. |
| Existing PV | `pvc-ec186114-ccc3-40f1-bae5-5e3511573547`, `Released` | Old/released OpenEBS-hostpath PV remains from prior observability setup. |
| Metrics API | Unavailable | `kubectl top nodes` and `kubectl top pods` fail because Metrics Server is not installed or not active. |
| In-cluster Prometheus | No running pods observed | The cluster currently does not have an active in-cluster Prometheus workload. |

## Orchestrator Runtime Interpretation

The current dashboard state says:

| Field | Value |
|---|---|
| Active stage | `live_kubernetes_loop` |
| Telemetry source | `kubernetes_api` |
| Ray status | `trained`, `train_iters=1` |
| Optuna status | `complete`, study `visualized_orchestrator_reward_weights`, 3 recent trials shown |
| Live trace rows | 1617 rows at inspection time |
| Latest cluster node count | `1` |
| Latest task count | `0` |
| Latest SLA violations | `0` |
| Latest completed tasks | `1` |
| Latest max risk | `0.065202` |
| Latest estimated power | `93.620408W` |

Important distinction:

- The **node, pods, deployments, namespaces, scheduling failures, and Kubernetes events** are real data from the Kind Kubernetes API.
- The **energy watt value** is not a direct physical power-meter reading in this run. It is produced by the default utilization power model: `idle_watts=80`, `cpu_full_scale_watts=120`, `mem_full_scale_watts=60`, `source=default_utilization_model`.
- Since Metrics API and active Prometheus are unavailable, the orchestrator cannot currently use `kubectl top` or in-cluster Prometheus metrics for this snapshot.

## What This Means for the Architecture

This environment is suitable for validating the orchestration control loop, dashboard flow, Kubernetes API integration, scheduler pressure, and intentional perturbation behavior. It is not yet equivalent to a realistic multi-node production or cloud K8s environment.

The current architecture is effectively:

1. Local Kind cluster provides the live Kubernetes API target.
2. The orchestrator reads live cluster objects and events through `kubernetes_api` telemetry.
3. The exerciser mutates real Kubernetes deployments in `borg-orchestrator-exercise`.
4. Scheduler results, pending pods, and resource-request pressure become part of the live trace.
5. The AIOpsLab twin, predictor layer, Agent A/B/C proposals, referee, Ray policy, Optuna tuning, and reward feedback run in the orchestrator process around that live K8s stream.
6. The dashboard visualizes the merged real-Kubernetes plus orchestrator-derived state.

## Current Limitations

| Limitation | Why it matters |
|---|---|
| Single node only | Agent C admission/node-placement behavior cannot demonstrate true multi-node placement or migration. |
| Control-plane node is also the worker | Scheduling pressure is real, but not representative of a separated production control-plane/worker topology. |
| Metrics API unavailable | CPU/memory telemetry is limited to Kubernetes API-derived/request-derived signals unless Prometheus or Metrics Server is restored. |
| Prometheus PVC pending | The observability namespace is not fully deployed because `openebs-hostpath` is missing. |
| No active DeathStarBench service graph | `test-social-network` exists, but no active social-network microservices were running at snapshot time. |
| Energy is estimated | Dashboard power values are model-derived, not physical measurements. |

## Concrete Kubernetes Commands Used

```bash
KUBECONFIG=~/Documents/aiopslab_validation_env/kubeconfig kubectl config current-context
KUBECONFIG=~/Documents/aiopslab_validation_env/kubeconfig kubectl cluster-info
KUBECONFIG=~/Documents/aiopslab_validation_env/kubeconfig kubectl version
KUBECONFIG=~/Documents/aiopslab_validation_env/kubeconfig kubectl get nodes -o wide
KUBECONFIG=~/Documents/aiopslab_validation_env/kubeconfig kubectl get ns --show-labels
KUBECONFIG=~/Documents/aiopslab_validation_env/kubeconfig kubectl get pods -A -o wide
KUBECONFIG=~/Documents/aiopslab_validation_env/kubeconfig kubectl get deploy,ds,sts,job,svc,pvc,pv,storageclass -A -o wide
KUBECONFIG=~/Documents/aiopslab_validation_env/kubeconfig kubectl get deployment -n borg-orchestrator-exercise -o json
KUBECONFIG=~/Documents/aiopslab_validation_env/kubeconfig kubectl describe pod -n borg-orchestrator-exercise bursty-safety-6c65d5dbf9-zl2pl
KUBECONFIG=~/Documents/aiopslab_validation_env/kubeconfig kubectl get events -A --sort-by=.lastTimestamp
KUBECONFIG=~/Documents/aiopslab_validation_env/kubeconfig kubectl top nodes
KUBECONFIG=~/Documents/aiopslab_validation_env/kubeconfig kubectl top pods -A
docker ps --filter 'name=borg-aiopslab'
```
