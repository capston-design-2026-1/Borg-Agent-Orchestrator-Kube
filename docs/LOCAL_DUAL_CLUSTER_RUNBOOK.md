# Local Dual-Cluster Runbook

This is the copy-paste runbook for the local comparison setup.

It starts and observes two local Kind clusters:

| Cluster | Purpose | Kubeconfig |
|---|---|---|
| `borg-experimental` | Agent A/B/C experimental orchestration cluster | `~/Documents/borg_orchestrator_clusters/kubeconfig-experimental` |
| `borg-baseline` | real Kubernetes HPA plus local Karpenter-style baseline | `~/Documents/borg_orchestrator_clusters/kubeconfig-baseline` |

No AWS environment is used. Karpenter behavior is locally emulated by activating pre-created Kind workers; HPA is real Kubernetes HPA.

## 0. Repository Root

Run all commands from the repository root:

```bash
cd /Users/theokim/Documents/github/kyunghee/Borg-Agent-Orchestrator
```

Set reusable kubeconfig variables:

```bash
export EXPERIMENTAL_KUBECONFIG=~/Documents/borg_orchestrator_clusters/kubeconfig-experimental
export BASELINE_KUBECONFIG=~/Documents/borg_orchestrator_clusters/kubeconfig-baseline
```

## 1. Create Or Reuse Both Clusters

Create or reuse both local multi-node clusters:

```bash
./orchestrator_stack/scripts/create_local_comparison_clusters.sh
```

Recreate both clusters from scratch:

```bash
RECREATE=1 ./orchestrator_stack/scripts/create_local_comparison_clusters.sh
```

Verify nodes:

```bash
kubectl --kubeconfig "$EXPERIMENTAL_KUBECONFIG" get nodes -o wide
kubectl --kubeconfig "$BASELINE_KUBECONFIG" get nodes -L borg.local/provisioning-state -o wide
```

Expected shape for each cluster:

```text
1 control-plane + 3 workers
```

## 2. Start Experimental Orchestration

Use this in Terminal 1:

```bash
./orchestrator_stack/scripts/launch_experimental_multinode_orchestration.sh
```

This starts:

| Component | URL / file |
|---|---|
| Experimental orchestration dashboard | `http://127.0.0.1:8765` |
| Experimental Prometheus port-forward | `http://127.0.0.1:19090` |
| Experimental state | `orchestrator_stack/runtime/visualization-experimental/state.json` |
| Experimental events | `orchestrator_stack/runtime/visualization-experimental/events.jsonl` |

Important behavior:

- Intentional exercise stimuli are mirrored to `borg-baseline` by default.
- Agent A/B/C and Referee actions are not mirrored.
- HPA and local Karpenter reactions are not mirrored.

## 3. Start Comparison Dashboard

Use this in Terminal 2:

```bash
./orchestrator_stack/scripts/launch_cluster_comparison.sh
```

This starts:

| Component | URL / file |
|---|---|
| Comparison dashboard | `http://127.0.0.1:8876` |
| Local Karpenter state | `orchestrator_stack/runtime/comparison/local_karpenter_state.json` |
| Shared stimulus state | `orchestrator_stack/runtime/comparison/shared_stimulus.json` |
| Comparison server log | `orchestrator_stack/runtime/comparison/server.log` |
| Local Karpenter log | `orchestrator_stack/runtime/comparison/local-karpenter.log` |

## 4. Prometheus Links

The experimental orchestration launcher normally creates this port-forward automatically:

```text
http://127.0.0.1:19090
```

If you need to start Prometheus port-forwards manually, use separate terminals.

Experimental Prometheus:

```bash
kubectl --kubeconfig "$EXPERIMENTAL_KUBECONFIG" -n observe port-forward svc/prometheus-server 19090:80
```

Baseline Prometheus:

```bash
kubectl --kubeconfig "$BASELINE_KUBECONFIG" -n observe port-forward svc/prometheus-server 19091:80
```

Prometheus URLs:

| Cluster | Prometheus URL | Health URL |
|---|---|---|
| experimental | `http://127.0.0.1:19090` | `http://127.0.0.1:19090/-/ready` |
| baseline | `http://127.0.0.1:19091` | `http://127.0.0.1:19091/-/ready` |

If port `19090` is already occupied, run the experimental orchestrator with a different Prometheus port:

```bash
PROMETHEUS_PORT=19092 ./orchestrator_stack/scripts/launch_experimental_multinode_orchestration.sh
```

## 5. k9s Commands

Experimental cluster:

```bash
KUBECONFIG=~/Documents/borg_orchestrator_clusters/kubeconfig-experimental k9s
```

Baseline cluster:

```bash
KUBECONFIG=~/Documents/borg_orchestrator_clusters/kubeconfig-baseline k9s
```

Useful namespaces to inspect in k9s:

| Namespace | Meaning |
|---|---|
| `borg-orchestrator-exercise` | mirrored intentional stimuli |
| `borg-baseline` | HPA baseline workload and surge workload |
| `observe` | Prometheus and Node Exporter |
| `kube-system` | Metrics Server and Kubernetes system pods |

## 6. Apply Same Intentional Stimulus To Both Clusters

Apply one deterministic shared stimulus:

```bash
PHASE_INDEX=1 ./orchestrator_stack/scripts/apply_comparison_stimulus.sh
```

Apply one reproducible randomized shared stimulus:

```bash
PHASE_INDEX=3 EXERCISE_RANDOMIZE=1 EXERCISE_SEED=17 ./orchestrator_stack/scripts/apply_comparison_stimulus.sh
```

Verify the same deployment exists in both clusters:

```bash
kubectl --kubeconfig "$EXPERIMENTAL_KUBECONFIG" -n borg-orchestrator-exercise get deploy,pods -o wide
kubectl --kubeconfig "$BASELINE_KUBECONFIG" -n borg-orchestrator-exercise get deploy,pods -o wide
```

## 7. Trigger Baseline Capacity Pressure

Scale the baseline surge workload:

```bash
REPLICAS=24 ./orchestrator_stack/scripts/apply_baseline_surge.sh
```

Scale it back down:

```bash
KUBECONFIG="$BASELINE_KUBECONFIG" REPLICAS=0 ./orchestrator_stack/scripts/apply_baseline_surge.sh
```

Inspect HPA:

```bash
kubectl --kubeconfig "$BASELINE_KUBECONFIG" -n borg-baseline get hpa,pods -o wide
```

## 8. Stop Runtime Processes

Preferred stop method:

```text
Press Ctrl-C in the terminals running the launch scripts or port-forwards.
```

If processes were orphaned, inspect them first:

```bash
pgrep -fl 'orchestrator.dashboard_server|orchestrator.comparison_dashboard_server|local_karpenter_controller.py|port-forward svc/prometheus-server' || true
```

Then stop only the local orchestration runtime helpers:

```bash
pkill -f 'orchestrator.dashboard_server' || true
pkill -f 'orchestrator.comparison_dashboard_server' || true
pkill -f 'local_karpenter_controller.py' || true
pkill -f 'port-forward svc/prometheus-server' || true
```

## 9. Clear Workloads But Keep Clusters

Delete mirrored exercise workloads from both clusters:

```bash
kubectl --kubeconfig "$EXPERIMENTAL_KUBECONFIG" -n borg-orchestrator-exercise delete deployment -l app.kubernetes.io/part-of=borg-orchestrator-exerciser --ignore-not-found
kubectl --kubeconfig "$BASELINE_KUBECONFIG" -n borg-orchestrator-exercise delete deployment -l app.kubernetes.io/part-of=borg-orchestrator-exerciser --ignore-not-found
```

Scale baseline surge down:

```bash
kubectl --kubeconfig "$BASELINE_KUBECONFIG" -n borg-baseline scale deployment/karpenter-surge --replicas=0
```

Optionally delete the exercise namespaces:

```bash
kubectl --kubeconfig "$EXPERIMENTAL_KUBECONFIG" delete namespace borg-orchestrator-exercise --ignore-not-found
kubectl --kubeconfig "$BASELINE_KUBECONFIG" delete namespace borg-orchestrator-exercise --ignore-not-found
```

## 10. Delete Both Clusters

Delete only the two comparison clusters:

```bash
kind delete cluster --name borg-experimental
kind delete cluster --name borg-baseline
```

Optional: delete the older AIOpsLab validation cluster too:

```bash
kind delete cluster --name borg-aiopslab
```

## 11. Quick Full Startup Sequence

Use this exact sequence when starting from a clean terminal:

```bash
cd /Users/theokim/Documents/github/kyunghee/Borg-Agent-Orchestrator
export EXPERIMENTAL_KUBECONFIG=~/Documents/borg_orchestrator_clusters/kubeconfig-experimental
export BASELINE_KUBECONFIG=~/Documents/borg_orchestrator_clusters/kubeconfig-baseline
./orchestrator_stack/scripts/create_local_comparison_clusters.sh
```

Then start these in separate terminals:

```bash
cd /Users/theokim/Documents/github/kyunghee/Borg-Agent-Orchestrator
./orchestrator_stack/scripts/launch_experimental_multinode_orchestration.sh
```

```bash
cd /Users/theokim/Documents/github/kyunghee/Borg-Agent-Orchestrator
./orchestrator_stack/scripts/launch_cluster_comparison.sh
```

```bash
kubectl --kubeconfig ~/Documents/borg_orchestrator_clusters/kubeconfig-baseline -n observe port-forward svc/prometheus-server 19091:80
```

Open:

| UI | URL |
|---|---|
| Experimental orchestration dashboard | `http://127.0.0.1:8765` |
| Comparison dashboard | `http://127.0.0.1:8876` |
| Experimental Prometheus | `http://127.0.0.1:19090` |
| Baseline Prometheus | `http://127.0.0.1:19091` |
