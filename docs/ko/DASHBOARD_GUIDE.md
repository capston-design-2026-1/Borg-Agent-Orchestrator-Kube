# Borg Orchestrator Dashboard 설명서

이 문서는 `http://127.0.0.1:8765`에서 열리는 Live Orchestration Dashboard의 모든 주요 영역을 설명한다. 대시보드는 `orchestrator_stack/runtime/visualization/state.json`과 `orchestrator_stack/runtime/visualization/events.jsonl`을 주기적으로 읽어 현재 오케스트레이션 상태를 시각화한다.

## 유지보수 규칙

대시보드 UI, 상태 필드, 이벤트 형식, 에이전트 정책, 보상 함수, Ray/RLlib, Optuna, Kubernetes exerciser가 바뀌면 이 문서도 같은 커밋 또는 같은 작업 세션에서 갱신해야 한다.

반드시 함께 확인할 파일은 다음과 같다.

| 영역 | 구현 파일 | 문서 반영 위치 |
|---|---|---|
| 대시보드 HTML 구조 | `orchestrator_stack/dashboard/index.html` | 이 문서의 화면 영역 설명 |
| 대시보드 렌더링/그래프/이벤트 해석 | `orchestrator_stack/dashboard/app.js` | 이 문서의 카드, 그래프, 이벤트 표 |
| 대시보드 레이아웃/시각 규칙 | `orchestrator_stack/dashboard/styles.css` | 이 문서의 시각적 의미 설명 |
| 상태/이벤트 JSON 쓰기 | `orchestrator_stack/orchestrator/runtime_state.py` | 이 문서의 Runtime State, Event Log 설명 |
| 실시간 Kubernetes 루프 | `orchestrator_stack/orchestrator/visualization.py` | Live Flow, Current Decision, Stage 설명 |
| Agent A/B/C 정책 | `orchestrator_stack/orchestrator/layer4/agents.py`, `orchestrator_stack/orchestrator/layer4/policy.py` | Agent 작업/보상 표 |
| Referee 충돌 해결 | `orchestrator_stack/orchestrator/layer4/referee.py` | Decision Gate 설명 |
| Reward 계산 | `orchestrator_stack/orchestrator/layer2/simulator.py`, `orchestrator_stack/orchestrator/layer6/scoreboard.py` | Reward Stream 및 Agent 보상 표 |
| Kubernetes 의도적 부하 변화 | `orchestrator_stack/orchestrator/layer1/kubernetes_exerciser.py` | Intentional Kubernetes Stimulus 설명 |
| Kubernetes observability bootstrap | `orchestrator_stack/scripts/bootstrap_observability.sh`, `orchestrator_stack/k8s/observability/metrics-prometheus.yaml` | 실시간 Kubernetes 환경과 telemetry source 설명 |

## 실행과 데이터 흐름 요약

대시보드는 다음 명령으로 오케스트레이션과 함께 실행된다.

```bash
cd /Users/theokim/Documents/github/kyunghee/Borg-Agent-Orchestrator && LIVE_K8S=1 KUBECONFIG=~/Documents/aiopslab_validation_env/kubeconfig ./orchestrator_stack/scripts/launch_orchestration.sh
```

실시간 모드의 핵심 흐름은 다음과 같다.

| 순서 | 레이어 | 실제 동작 | 대시보드에 보이는 위치 |
|---:|---|---|---|
| 1 | Layer 1 Kubernetes Source | `kubectl`로 node/pod 상태를 읽고, live launcher가 Prometheus/Node Exporter를 기본 bootstrap한 뒤 Prometheus CPU/memory 샘플을 병합한다. | Metrics, Kubernetes Cluster 카드, Event Log의 `cluster` 이벤트 |
| 2 | Live Perturbation | `borg-orchestrator-exercise` namespace에 안전한 synthetic workload를 `apply/delete`하여 클러스터 상태를 일부러 흔든다. | Workload Exerciser 카드, Intentional Kubernetes Stimulus 카드, `exercise` 이벤트 |
| 3 | Layer 2 AIOpsLab Twin | Kubernetes snapshot을 `Observation`으로 변환하고 action에 따른 twin transition/reward를 계산한다. | AIOpsLab Twin 카드, Reward Stream |
| 4 | Layer 3 XGBoost Brains | 위험도 `p_fail_scores`와 수요 `demand_projection`을 보강하거나, XGBoost가 없으면 live telemetry 값을 그대로 쓴다. | XGBoost Brains 카드, Max Risk, Decision Reason |
| 5 | Layer 4 Agents | Agent A/B/C가 각각 safety, efficiency, admission 관점에서 proposal을 만든다. | Agent A/B/C 카드, State Vector 카드, proposal chip |
| 6 | Referee | safety-first 규칙으로 하나의 최종 action을 고른다. | Current Decision, Decision Gate, Performed Action |
| 7 | Layer 6 Scoreboard | Agent별 reward와 `alpha/beta/gamma` 가중합을 계산한다. | Reward Stream, Global Scoreboard, Last Reward |
| 8 | Layer 5 Optuna | reward weight `alpha/beta/gamma`를 trial별로 탐색한다. | Optuna 카드, Objective graph, Weight graph |
| 9 | Ray/RLlib | multi-agent PPO policy를 bootstrap/training한다. | Ray Status, Ray/RLlib panel, Ray RLlib PPO Policy 카드 |

## 실시간 Kubernetes 환경

현재 live orchestration target은 local Kind validation cluster다. managed cloud Kubernetes나 production multi-node cluster가 아니다. baseline inspection 결과는 `reports/evaluations/202605051249_kubernetes_environment_snapshot.md`에 있고, observability 수정 검증은 `reports/evaluations/202605051339_observability_bootstrap_report.md`에 기록되어 있다.

| 항목 | 현재 값 |
|---|---|
| Kubernetes context | `kind-borg-aiopslab` |
| Cluster type | Docker에서 실행되는 local Kind cluster |
| API server | `https://127.0.0.1:54392` |
| Kind node container | `borg-aiopslab-control-plane` |
| Kind node image | `kindest/node:v1.35.0` |
| Kubernetes server | `v1.35.0` |
| kubectl client | `v1.34.1` |
| Node 수 | `1` |
| Node role | 하나의 `control-plane` node가 worker 역할까지 함께 수행 |
| Node architecture | `arm64` |
| Node OS | `Debian GNU/Linux 12 (bookworm)` |
| Kernel | `6.12.76-linuxkit` |
| Container runtime | `containerd://2.2.0` |
| Node capacity | CPU core `10`, memory 약 `8Gi`, pod `110` |
| Pod CIDR | `10.244.0.0/24` |
| CNI | Kindnet |
| Default storage class | `standard`, provisioner `rancher.io/local-path` |

현재 환경에서 확인된 namespace의 의미는 다음과 같다.

| Namespace | 역할 |
|---|---|
| `borg-orchestrator-exercise` | live exerciser가 synthetic workload Deployment를 생성/삭제하는 핵심 namespace |
| `default` | 이전 AIOpsLab/DeathStarBench 검증에서 사용된 completed `wrk2` job 존재 |
| `kube-system` | CoreDNS, API server, scheduler, controller-manager, etcd, kube-proxy, kindnet 등 cluster system component |
| `local-path-storage` | local-path storage provisioner |
| `observe` | in-cluster observability namespace. live launcher가 여기에 `prometheus-server`와 `prometheus-node-exporter`를 배포한다. |
| `test-social-network` | DeathStarBench/AIOpsLab namespace이나, inspection snapshot 기준 active social-network resource는 없음 |

반드시 알고 있어야 할 runtime telemetry 상태는 다음과 같다.

| 항목 | 현재 상태 | Dashboard 해석 |
|---|---|---|
| Metrics Server | `bootstrap_observability.sh`가 설치한다. `v1beta1.metrics.k8s.io`가 Available이고 `kubectl top nodes`가 CPU/memory sample을 반환한다. | operator가 Metrics API로 cluster 상태를 직접 확인할 수 있다. |
| In-cluster Prometheus | repository manifest가 `observe/prometheus-server`를 실행한다. launcher는 기본적으로 `http://127.0.0.1:19090`으로 port-forward한다. | live trace row가 Prometheus 기반 CPU/memory enrichment를 포함할 수 있다. 정상 row에는 `telemetry_sources`에 `prometheus_node_exporter`가 들어간다. |
| Node Exporter | `observe/prometheus-node-exporter` DaemonSet이 Kind node에서 실행된다. | `node_cpu_seconds_total`, `node_memory_MemAvailable_bytes` 같은 node-exporter metric이 trace collector에 공급된다. |
| Legacy `openebs-hostpath` PVC | 예전 `observe/prometheus-pvc`는 이 Kind cluster에 없는 storage class를 요구해서 Pending이었다. bootstrap script가 이 stale Pending PVC를 삭제하고 Prometheus는 `emptyDir`를 사용한다. | thesis demo가 telemetry 수집을 위해 OpenEBS에 의존하지 않는다. Prometheus 데이터는 pod 재시작 시 사라지는 ephemeral 데이터이며 live dashboard evidence에는 충분하다. |
| Energy watts | default utilization model 기반 estimate다. | `est power ...W`는 실제 wattmeter 측정값이 아니다. |
| Agent placement realism | single-node cluster다. | Agent C admission logic은 볼 수 있지만, 진짜 multi-node placement/migration 실험은 이 환경만으로는 보여주기 어렵다. |

실시간 telemetry 정상 여부는 다음 신호로 확인한다.

| 확인 항목 | 정상 결과 |
|---|---|
| `kubectl get apiservice v1beta1.metrics.k8s.io` | APIService가 존재하고 condition이 `Available=True`다. |
| `kubectl top nodes` | Kind node의 CPU/memory sample을 반환한다. |
| `kubectl -n observe get pods,svc -l app.kubernetes.io/part-of=borg-orchestrator` | Prometheus와 Node Exporter pod/service가 running으로 보인다. |
| `state.json` / trace row | Prometheus enrichment가 성공하면 `telemetry_sources`에 `kubernetes_api`와 `prometheus_node_exporter`가 함께 들어간다. |

live exerciser는 실제 Kubernetes mutation을 수행한다. 예를 들어 `borg-orchestrator-exercise` namespace에 `light-dvfs`, `safety-replicate`, `admission-queue` 같은 `pause` Deployment를 만들거나 삭제한다. 이 Deployment들은 실제 scheduler 결과를 만들 수 있으며, `Pending` pod와 `FailedScheduling` event가 발생한다. 따라서 dashboard는 다음 데이터들을 섞어서 보여준다.

| 데이터 종류 | 실제성 수준 |
|---|---|
| Node, pod, deployment, event, namespace, scheduler failure | Kind cluster의 실제 Kubernetes API 데이터 |
| Synthetic workload phase와 rollout return code | exerciser가 실행한 실제 `kubectl apply/delete/rollout status` 결과 |
| Agent A/B/C proposal, Referee choice, reward total | live cluster observation을 기반으로 twin/reward path에서 평가되는 orchestrator control-plane decision |
| Energy watts | 별도 calibration이 없으면 `idle_watts=80`, `cpu_full_scale_watts=120`, `mem_full_scale_watts=60`을 쓰는 model-derived estimate |

## 아주 중요한 해석: 실제 Kubernetes 변화와 선택된 오케스트레이션 action

대시보드에는 두 종류의 action-like 정보가 동시에 보인다.

| 이름 | 실제 Kubernetes에 직접 수행되는가 | 의미 |
|---|---:|---|
| Intentional Kubernetes Stimulus | 예 | exerciser가 `kubectl apply/delete`로 exercise namespace의 synthetic Deployment를 만들거나 삭제한다. 이 변화가 cluster risk/demand를 흔들어 Agent A/B/C가 다양한 결정을 하도록 만든다. |
| Performed Action | 현재 구현에서는 live twin/reward path에 적용 | Referee가 선택한 오케스트레이션 action이다. live dashboard는 이 action을 twin transition과 reward 계산에 적용하고 시각화한다. 별도의 executor가 연결되지 않는 한 이 selected action 자체가 곧바로 실제 cluster resource를 바꾸는 것은 아니다. |

따라서 thesis 보고서에서는 다음처럼 표현하는 것이 정확하다.

- 실제 cluster perturbation은 Workload Exerciser가 수행한다.
- Agent/Referee action은 live cluster snapshot을 보고 선택된 control decision이며, 현재 dashboard는 이 decision을 twin/reward layer에 적용해 결과를 평가한다.
- 실제 Kubernetes remediation executor를 추가하면 Performed Action 카드가 실제 cluster mutation까지 연결되는 구조로 확장될 수 있다.

## 상단 Hero와 실행 상태 카드

| UI 요소 | 의미 | 원천 상태 필드 |
|---|---|---|
| `Live Orchestration Control Plane` | 현재 화면이 전체 오케스트레이션 control plane임을 나타내는 제목이다. | 정적 HTML |
| 상태 배지 `Running`, `complete`, `failed` | 런타임 전체 상태. `running`이면 루프 또는 demo가 진행 중이고, `complete`는 bounded run 완료, `failed`는 오류 발생이다. | `state.status` |
| `updated ...` | dashboard가 마지막으로 읽은 runtime state timestamp. | `state.updated_at` |

## Metrics 카드 6개

상단 metrics는 가장 빠르게 현재 상태를 판단하기 위한 요약 영역이다.

| 카드 | 표시 예 | 의미 | 주의점 |
|---|---|---|---|
| Active Stage | `live_kubernetes_loop` | 현재 active orchestration stage. | `brains`, `ray_ppo`, `optuna`, `episode`, `live_kubernetes_loop`, `complete` 등이 가능하다. |
| Last Reward | `7.359` | 가장 최근 step의 weighted total reward. | 누적 reward가 아니라 마지막 step의 weighted value다. |
| Reward Steps | `842` | reward event가 기록된 step 수. | 화면 그래프는 최근 history window만 그릴 수 있다. |
| Optuna | `1417.159` 또는 `disabled` | Optuna best objective score. | `NO_TUNE=1`이면 disabled/skipped로 보일 수 있다. |
| Ray Status | `trained`, `disabled`, `idle` | Ray/RLlib PPO bootstrap 상태. | `NO_POLICY=1` 또는 fast mode에서는 disabled가 정상이다. |
| Max Risk | `0.590` | 현재 node 중 가장 높은 failure/risk score. | XGBoost가 없으면 Kubernetes/Prometheus utilization과 pod health 기반 telemetry risk다. |

## Current Decision 패널

Current Decision은 현재 iteration에서 Referee가 최종 선택한 action을 보여준다.

| 필드 | 의미 |
|---|---|
| Recommendation | `AgentB:memory_balloon`처럼 선택된 agent와 action kind를 표시한다. |
| Target | action이 겨냥하는 node 또는 cluster target. 예: `borg-aiopslab-control-plane`. |
| Reason | 왜 선택되었는지에 대한 요약. Agent A는 risk/SLA, Agent B는 demand/estimated power, Agent C는 queue/cpu/memory를 중심으로 설명한다. |
| timestamp | 이 decision이 기록된 시간. KST ISO timestamp다. |

Reason의 해석 예시는 다음과 같다.

| Agent | Reason 형식 | 의미 |
|---|---|---|
| AgentA | `risk=0.590129 on node; sla=0` | 가장 위험한 node의 risk와 SLA violation 수를 근거로 safety action을 선택했다. |
| AgentB | `low demand=0.30928 on node; est_power=93.620W` | 가장 낮은 demand node와 estimated power를 근거로 efficiency action을 선택했다. |
| AgentC | `queue=...; avg_cpu=...; avg_mem=...` | queue pressure와 평균 utilization을 근거로 admission/resource action을 선택했다. |

## Architecture Stages 패널

Architecture Stages는 전체 6-layer pipeline의 stage 상태를 보여준다.

| Stage | 의미 | 정상 상태 예 |
|---|---|---|
| `brains` | XGBoost risk/demand predictor 준비 단계. | `complete`, 또는 `xgboost missing`이면 `skipped` |
| `ray_ppo` | Ray/RLlib PPO policy bootstrap/training 단계. | `complete`, `trained`, 또는 fast mode에서 `disabled` |
| `optuna` | reward weight tuning 단계. | `complete`, `running`, `disabled`, `skipped` |
| `episode` | finite visualized-run에서 trace episode를 replay하는 단계. | finite demo 모드에서 사용 |
| `live_kubernetes_loop` | live Kubernetes snapshot을 계속 수집하고 decision/reward를 기록하는 단계. | live mode에서 계속 `running` |
| `complete` | bounded run 완료. | `KEEP_DASHBOARD=1`이면 완료 후 dashboard server는 남아 있을 수 있다. |

## Live Orchestration Flow: 전체 구조

이 영역은 대시보드의 핵심이다. 위쪽 큰 canvas는 architecture map이고, 아래쪽 operations deck은 실제 runtime 세부 정보를 보여준다.

### Legend 색상/선 의미

| Legend | 색상/선 | 의미 |
|---|---|---|
| Telemetry | 회색 점선 | Kubernetes/exerciser에서 digital twin으로 들어오는 관측 흐름 |
| Inference | 파란 점선 | twin/feature state가 predictor와 policy로 이동하는 흐름 |
| Policy | 주황 계열 | policy와 agent proposal, selected action의 흐름 |
| Reward/Meta Loop | 초록 계열 | reward feedback, scoreboard, Optuna meta feedback 흐름 |

### Architecture map의 lane과 node

| Lane | Node | 표시 값 | 의미 |
|---|---|---|---|
| Layer 1 | Kubernetes Cluster | `risk ...` | 현재 cluster snapshot의 가장 큰 risk score. `nodes/tasks/sla`와 함께 해당 row가 `kubectl only`인지 `kubectl + prometheus`인지도 표시한다. |
| Layer 1 | Workload Exerciser | `active` 또는 `idle` | synthetic workload perturbation이 활성화되어 있는지 보여준다. |
| Layer 2 | AIOpsLab Twin | `cpu ...` | live snapshot을 twin observation으로 변환한 평균 CPU. detail에는 memory와 estimated power가 표시된다. |
| Layer 3 | XGBoost Brains | `risk ... / demand ...` | risk forecast와 resource demand projection. XGBoost runtime이 disabled이면 telemetry-derived value를 사용한다. |
| Layer 3 | State Vector | `3 proposals` | Agent A/B/C proposal 수. 일반적으로 세 agent가 하나씩 proposal한다. |
| Layer 4 | Ray RLlib PPO Policy | `trained`, `disabled`, `idle` | PPO policy bootstrap 상태. 현재 heuristic/referee path와 공존한다. |
| Layer 4 | Agent A | `candidate`, `throttle`, `migrate`, `replicate` | safety/risk 관점 proposal 또는 selected action. |
| Layer 4 | Agent B | `candidate`, `dvfs`, `memory balloon`, `power state` | efficiency/energy 관점 proposal 또는 selected action. |
| Layer 4 | Agent C | `candidate`, `admission`, `resource cap` | admission/queue 관점 proposal 또는 selected action. |
| Referee | Decision Gate | `score ...` | final selected action의 score와 reason. |
| Layer 6 | Global Scoreboard | weighted total | 최신 reward event의 weighted total과 Agent별 raw reward. |
| Layer 5 | Optuna Trial Manager | best score | reward weights tuning의 best objective score와 study name. |

### Operations deck

Flow map 아래의 operations deck은 architecture canvas와 분리되어 있어 node/arrow를 가리지 않는다.

| 카드 | 의미 | 주요 필드 |
|---|---|---|
| Intentional Kubernetes Stimulus | 실제 cluster에 가한 synthetic workload 변화. | phase, intended action, namespace, operation, replicas, cpu request, memory request, rollout return code |
| Performed Action | Referee가 선택한 최종 orchestration decision. | selected agent/action, route, target, payload, proposal chips |

Intentional Kubernetes Stimulus의 `operation`은 보통 다음 중 하나다.

| operation | 실제 명령 의미 |
|---|---|
| `apply` | exercise Deployment manifest를 `kubectl apply -f -`로 적용한다. |
| `delete` | exercise namespace의 exerciser Deployment를 label selector로 삭제한다. |
| `observe` | 새 structured field가 없는 오래된 event를 fallback으로 해석하거나 아직 stimulus가 없는 상태다. |

`rollout rc`는 `kubectl rollout status`의 return code다. `0`이면 rollout 성공, non-zero면 rollout 실패/timeout/검증 실패 가능성을 의미한다.

## Kubernetes Stimulus phase

Live mode에서 `EXERCISE_CLUSTER=1`이면 exerciser가 safe synthetic workloads를 반복적으로 적용한다. 기본은 randomized mode다. randomized mode는 아래 action-covering phase library에서 phase를 샘플링하고 request size를 흔들어 reward/action pattern이 너무 주기적으로 보이지 않게 만든다.

| Phase | 실제 Kubernetes 변화 | 의도한 action coverage | 기본/랜덤 리소스 |
|---|---|---|---|
| `idle-power-save` | exercise Deployment 삭제 | AgentB `power_state:sleep` | deployment 없음 |
| `light-dvfs` | 낮은 schedulable Deployment 생성 | AgentB `dvfs` | 고정: `2200m`, `256Mi`; 랜덤: `1600m-2800m`, `128Mi-512Mi` |
| `moderate-memory` | 중간 수준 schedulable Deployment 생성 | AgentB `memory_balloon` | 고정: `6200m`, `768Mi`; 랜덤: `5200m-6800m`, `512Mi-1280Mi` |
| `safety-throttle` | 중간-높은 schedulable Deployment 생성 | AgentA `throttle` | 고정: `8600m`, `1Gi`; 랜덤: `8200m-8800m`, `768Mi-1536Mi` |
| `safety-migrate` | 높은 schedulable Deployment 생성 | AgentA `migrate` | 고정: `9200m`, `5Gi`; 랜덤: `9000m-9300m`, `4096Mi-5632Mi` |
| `safety-replicate` | severe-but-schedulable Deployment 생성 | AgentA `replicate` | 고정: `9400m`, `7Gi`; 랜덤: `9300m-9450m`, `6656Mi-7424Mi` |
| `admission-queue` | intentionally unmatched node selector를 가진 unschedulable pod 12개 생성 | AgentC `admission:queue` | `12` replicas, 랜덤 `80m-200m`, `48Mi-128Mi` |
| `admission-deprioritize` | intentionally unmatched node selector를 가진 unschedulable pod 90개 생성 | AgentC `admission:deprioritize` | `90` replicas, 랜덤 `80m-200m`, `48Mi-128Mi` |
| `admission-cap` | intentionally unmatched node selector를 가진 unschedulable pod 130개 생성 | AgentC `resource_cap` | `130` replicas, 랜덤 `80m-200m`, `48Mi-128Mi` |

## Agent A/B/C: action과 reward 상세

모든 step의 기본 raw reward는 Agent별로 `1.0`에서 시작한다. 이후 선택된 action과 live telemetry에 따라 reward가 더해지거나 차감된다.

Weighted total은 다음 공식으로 계산된다.

```text
total = alpha * AgentA_reward + beta * AgentB_reward + gamma * AgentC_reward
```

기본 config 값은 `alpha=1.0`, `beta=0.6`, `gamma=0.8`이며, Optuna가 이 weight를 탐색한다.

### Agent A: Risk Mitigator / Safety Agent

Agent A는 node failure risk와 task survival을 담당한다.

| Action | 발생 조건: heuristic policy | RLlib policy action id | payload | Twin transition 효과 | Reward 가능성 |
|---|---|---:|---|---|---|
| `noop` | `p_fail_scores`가 없거나 max risk `< 0.5` | 0 | 없음 | 상태 변경 없음 | 기본 `+1.0`; live telemetry penalty는 별도 적용 가능 |
| `throttle` | max risk `>= 0.5` and `< 0.7` | 3 | 없음 | target node의 `cpu_util`과 `net_util`을 각각 `*0.85`로 낮춘다. | 선택된 action이고 `p_fail >= 0.5`이면 AgentA `+3.0` |
| `migrate` | max risk `>= 0.7` and `< 0.83` | 1 | 없음 | 가장 부하가 큰 다른 on node에서 task 하나를 target으로 이동시키고 source load를 낮추며 target load를 소폭 올린다. | `p_fail > 0.75`이면 `+10.0`; `p_fail < 0.4`인데 migrate하면 `-20.0` |
| `replicate` | max risk `>= 0.83` | 2 | 없음 | target node의 가장 urgent한 task를 낮은 부하 node에 replica로 추가한다. | `p_fail >= 0.83`이면 `+8.0` |

Agent A에 항상 영향을 줄 수 있는 live telemetry reward/penalty는 다음과 같다.

| 조건 | Reward 변화 | 의미 |
|---|---:|---|
| `sla_violations > 0` | `-50.0 * sla_violations` | SLA violation은 safety 실패로 강하게 벌점 처리된다. |
| 죽은 task가 하나라도 있음 | `-100.0` | task survival failure penalty. |

### Agent B: Efficiency Optimizer / Energy Agent

Agent B는 낮은 수요 node를 찾아 DVFS, memory balloon, power state 같은 efficiency action을 제안한다.

| Action | 발생 조건: heuristic policy | RLlib policy action id | payload | Twin transition 효과 | Reward 가능성 |
|---|---|---:|---|---|---|
| `noop` | demand projection이 없거나 min demand `>= 0.45` | 0 | 없음 | 상태 변경 없음 | 기본 `+1.0`; estimated power bonus는 live telemetry가 있으면 별도 적용 가능 |
| `power_state` sleep | min demand `< 0.12` | 1 | `state=sleep` | target node power state를 sleep/off/on 중 하나로 바꾸며 sleep/off는 CPU/MEM utilization을 낮춘다. | selected efficiency action이고 max demand `< 0.35`이면 `+5.0`; max demand `> 0.75`이면 `-30.0` |
| `dvfs` | min demand `>= 0.12` and `< 0.3` | 3 | `clock_scale=0.65` | target node의 `cpu_util *= clock_scale`, `net_util *= 0.9 + 0.1*clock_scale` | selected efficiency action이고 max demand `< 0.35`이면 `+5.0`; max demand `> 0.75`이면 `-30.0` |
| `memory_balloon` | min demand `>= 0.3` and `< 0.45` | 4 | `mem_scale=0.75` | target node의 `mem_util *= mem_scale` | selected efficiency action이고 max demand `< 0.35`이면 `+5.0`; max demand `> 0.75`이면 `-30.0` |
| `power_state` on | heuristic은 직접 선택하지 않음; RLlib policy에서 가능 | 2 | `state=on` | node를 on 상태로 두고 CPU/MEM utilization을 소폭 올린다. | high demand node wake-up policy로 사용될 수 있으나 reward rule은 efficiency action 공통 규칙을 따른다. |

Agent B에 항상 영향을 줄 수 있는 live telemetry reward는 다음과 같다.

| 조건 | Reward 변화 | 의미 |
|---|---:|---|
| `energy_watts > 0` 또는 다른 live metric 존재 | `max(0, (500 - energy_watts) / 100)` | estimated power가 낮을수록 AgentB bonus가 커진다. 예: `93.620W`이면 약 `+4.064` |

주의: dashboard의 `est power ...W`는 실제 wattmeter 측정값이 아니라 calibrated utilization-derived estimate다. 기본 공식은 `80 + 120*cpu_util + 60*mem_util`이다.

### Agent C: Gatekeeper / Admission Agent

Agent C는 queue pressure와 overloaded node를 보고 admission 또는 resource cap 결정을 담당한다.

| Action | 발생 조건: heuristic policy | RLlib policy action id | payload | Twin transition 효과 | Reward 가능성 |
|---|---|---:|---|---|---|
| `admission:admit` | queue `< 20` and overloaded node `0`이면 score `1.0`; 그 외 일반 상태에서는 score `0.5` | 0 | `decision=admit` | queue length를 최대 2 줄인다. | queue `< 80`이면 `+5.0`; queue `> 120`에서 admit하면 `-50.0` |
| `admission:queue` | queue `>= 8` and `< 80` | 1 | `decision=queue` | queue length를 1 늘린다. | explicit reward bonus는 없지만 protective admission으로 Referee에서 Agent B보다 우선될 수 있다. |
| `admission:reject` | `sla_violations > 0`이고 queue `> 0`이지만 queue band 미만 | 2 | `decision=reject` | queue length를 1 줄인다. | queue `< 60`에서 reject하면 `-20.0` |
| `admission:deprioritize` | queue `>= 80` and `< 120` | 3 | `decision=deprioritize` | queued task priority를 낮춘다. | queue `>= 80`이면 `+3.0` |
| `resource_cap` | queue `>= 120` 또는 overloaded node가 node 수의 절반 이상 | 4 | `cpu_cap=0.85`, `mem_cap=0.85` | target node CPU/MEM utilization을 cap 이하로 제한한다. | queue `>= 80`이면 `+4.0`; AIOpsLab adapter path에서는 queue `< 80`이면 `-5.0` |

Agent C에 항상 영향을 줄 수 있는 live telemetry reward는 다음과 같다.

| 조건 | Reward 변화 | 의미 |
|---|---:|---|
| `completed_tasks > 0` | `min(10.0, completed_tasks / 10.0)` | 완료 task가 많을수록 admission policy가 보상받는다. 최대 `+10.0` |

## Referee / Decision Gate 규칙

Agent A/B/C는 각자 proposal을 만들지만, 실제 selected action은 Referee가 하나만 고른다.

| 우선순위 | 규칙 | 설명 |
|---:|---|---|
| 1 | Agent A safety action 우선 | `migrate`, `replicate`, `throttle`이 있으면 safety-first로 Agent A action이 lower-priority action을 preempt한다. |
| 2 | Agent C protective admission 우선 | `queue`, `reject`, `deprioritize`, `resource_cap`은 non-safety efficiency action보다 우선한다. |
| 3 | Agent B efficiency action score 선택 | `power_state`, `dvfs`, `memory_balloon` 중 score가 높은 action을 고른다. |
| 4 | deterministic priority fallback | meaningful action이 남아 있으면 `AgentA -> AgentC -> AgentB` 우선순위와 score로 선택한다. |
| 5 | all noop | 모두 noop이면 우선순위와 score 기준 fallback noop을 고른다. |

Decision Gate의 `score`는 selected action proposal의 score다. Reward total과 다르다.

## Reward Stream 그래프

Reward Stream panel은 최근 reward history를 보여준다.

| 요소 | 의미 |
|---|---|
| `steps` | 지금까지 reward가 계산된 step 수. |
| `avg total` | 전체 reward step에 대한 running average total. |
| `last AgentA/B/C` | 마지막 step의 raw reward. weighted가 아니다. |
| Canvas x축 | orchestration step. |
| Canvas y축 | reward value. |
| `total` line | `alpha*A + beta*B + gamma*C`의 weighted reward. |
| AgentA/B/C line | Agent별 raw reward. |

그래프가 특정 패턴을 보일 수 있는 이유는 다음과 같다.

| 원인 | 설명 |
|---|---|
| deterministic exercise cycle | `EXERCISE_RANDOMIZE=0`이면 action-covering stimulus phase가 고정 순서로 반복되어 reward도 반복 패턴을 보일 수 있다. |
| randomized exercise | 기본 `EXERCISE_RANDOMIZE=1`에서는 phase와 resource request가 무작위로 변해 더 불규칙한 reward stream이 된다. |
| live cluster saturation | 실제 cluster가 한 node/한 workload 중심이면 decision이 한 agent/action에 몰릴 수 있다. |
| Referee priority | safety risk가 높으면 Agent A가 반복적으로 preempt할 수 있고, low demand가 지속되면 Agent B가 반복될 수 있다. |

## Optuna 패널

Optuna는 reward weight와 일부 policy tuning을 위한 meta-optimization layer다. Dashboard의 Optuna panel은 두 종류의 그래프를 분리해서 보여준다.

| UI 요소 | 의미 |
|---|---|
| Study name | 보통 `visualized_orchestrator_reward_weights`. |
| `alpha`, `beta`, `gamma` 카드 | 현재 best trial의 reward weights. |
| Objective score graph | Optuna가 maximize하는 objective value. 선이 하나인 이유는 objective가 하나이기 때문이다. |
| Weight graph | trial마다 sample된 `alpha`, `beta`, `gamma` 세 weight의 변화. |
| Optuna graph x-axis | local array position이 아니라 `T15`, `T16`, `T17` 같은 실제 Optuna trial ID를 표시한다. |

Optuna runtime state는 최근 visible history window만 저장할 수 있다. 따라서 chart에 `T15`, `T16`, `T17` 세 점이 보이면 이것은 실제 Optuna trial 15-17을 의미한다. 새로 시작한 local sequence `0,1,2`로 해석하면 안 된다.

Optuna search range는 다음과 같다.

| Parameter | 범위 | 의미 |
|---|---:|---|
| `alpha` | `0.5` to `2.5` | Agent A reward weight. safety 중심성 조절. |
| `beta` | `0.1` to `2.0` | Agent B reward weight. efficiency 중심성 조절. |
| `gamma` | `0.1` to `2.0` | Agent C reward weight. admission/throughput 중심성 조절. |

Optuna가 `disabled`이면 `NO_TUNE=1` 또는 fast mode일 수 있다. 이것은 오류가 아니라 launch option에 따른 정상 동작일 수 있다.

## Ray/RLlib 패널

Ray/RLlib은 Layer 4 multi-agent PPO training status를 보여준다.

| 필드 | 의미 |
|---|---|
| `status` | `initializing`, `trained`, `disabled`, `skipped` 등이 가능하다. |
| `train_iters` | PPO training iteration 수. |
| `reward_mean` | PPO training summary의 episode reward mean. 없으면 `n/a`. |
| `checkpoint` | 학습 checkpoint path. |

주의: Dashboard의 live loop decision은 현재 heuristic Agent A/B/C + Referee path를 중심으로 표시된다. Ray/RLlib은 PPO policy bootstrap/training 상태와 policy capability를 보여주는 layer이며, policy action space는 `AgentA`, `AgentB`, `AgentC` 각각에 대해 정의되어 있다.

## Artifacts 패널

Artifacts는 runtime 중 생성된 파일 경로를 보여준다.

| Artifact 예 | 의미 |
|---|---|
| `risk_model` | XGBoost risk model path. |
| `demand_model` | XGBoost demand model path. |
| `Optuna reward report` | Optuna study report Markdown. |
| `live Kubernetes trace` | live loop가 계속 append하는 Kubernetes trace JSON. |
| `live launch summary` | launch/runtime summary JSON. |

Generated trace/report가 크거나 runtime 성격이면 git에 자동으로 commit하지 않는다.

## Event Log와 Event Rail

Event Log는 `events.jsonl`의 최근 event를 표시한다. Flow diagram 아래 event rail은 최근 5개 event를 카드 형태로 요약한다.

| Event kind | 생성 주체 | 의미 |
|---|---|---|
| `stage` | `VisualizationState.stage` | stage 상태 변화. |
| `cluster` | `cluster_snapshot` | node/task/SLA/risk snapshot. |
| `exercise` | live Kubernetes loop | 실제 exerciser가 적용/삭제한 Kubernetes stimulus. |
| `decision` | `VisualizationState.decision` | Referee selected action. |
| `reward` | `VisualizationState.reward` | step reward와 weighted total. |
| `optuna` | `optuna_trial`/`optuna_update` | trial value, params, best score, status. |
| `ray` | `ray_update` | Ray/RLlib PPO status. |
| `artifact` | `artifact` | 생성 파일 path. |
| `error` | `error` | runtime failure. |

## Runtime JSON 파일

| 파일 | 설명 |
|---|---|
| `orchestrator_stack/runtime/visualization/state.json` | Dashboard가 주기적으로 읽는 현재 상태 snapshot. |
| `orchestrator_stack/runtime/visualization/events.jsonl` | append-only event stream. dashboard event log의 원천이다. |
| `orchestrator_stack/runtime/visualization/summary.json` | live launch/run summary. |
| `orchestrator_stack/runtime/dashboard/server.log` | dashboard HTTP server log. |
| `orchestrator_stack/runtime/dashboard/run.log` | launcher/orchestrator process log. |

## 자주 헷갈리는 표시

| 표시 | 정확한 해석 |
|---|---|
| `est power ...W` | 실제 wattmeter 값이 아니라 CPU/MEM utilization 기반 calibrated estimate다. |
| `Optuna Best` | 현재 best objective score이지 alpha/beta/gamma 자체가 아니다. |
| `Ray Status: trained` | PPO bootstrap/training이 끝났다는 뜻이며, 현재 live loop에서 heuristic/referee decision과 함께 해석해야 한다. |
| `AgentB dominates` | cluster가 low demand 상태이거나 Agent A safety/Agent C protective condition이 약하면 Agent B efficiency action이 자주 선택될 수 있다. |
| `negative total reward` | SLA violation, dead task, wrong admission, high-demand efficiency action 등이 weighted total을 음수로 만들 수 있다. |

## Dashboard 변경 시 체크리스트

1. `node --check orchestrator_stack/dashboard/app.js`를 실행한다.
2. `PYTHONPATH=orchestrator_stack .venv/bin/pytest orchestrator_stack/tests/test_visualization_runtime.py -q`를 실행한다.
3. 가능하면 Chrome headless screenshot 또는 browser smoke로 desktop-width layout을 확인한다.
4. 이 문서와 `docs/en/DASHBOARD_GUIDE.md`를 같이 갱신한다.
5. launch behavior가 바뀌면 `docs/ORCHESTRATION_LAUNCH.md`와 `README.md`도 갱신한다.
