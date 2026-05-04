from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Protocol

from orchestrator.layer1.collector import prometheus_rows_to_trace
from orchestrator.types import ActionKind, AgentAction, NodeState, Observation, StepResult, TaskState


class SimulatorBackend(Protocol):
    def reset(self) -> Observation: ...

    def step(self, action: AgentAction) -> StepResult: ...


def _state_value(payload: Any, *keys: str, default: Any = None) -> Any:
    if payload is None:
        return default
    if isinstance(payload, dict):
        for key in keys:
            if key in payload:
                return payload[key]
        return default
    for key in keys:
        if hasattr(payload, key):
            return getattr(payload, key)
    return default


def _coerce_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _coerce_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _coerce_bool(value: Any, default: bool = True) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes", "y", "on"}:
            return True
        if lowered in {"0", "false", "no", "n", "off"}:
            return False
    if value is None:
        return default
    return bool(value)


def _normalize_ratio(value: Any, default: float = 0.0) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return default
    if 1.0 < numeric <= 10.0:
        return 1.0
    if numeric > 10.0:
        numeric /= 100.0
    return max(0.0, min(1.0, numeric))


def _normalize_state_payload(state: Any) -> Any:
    if isinstance(state, (bytes, bytearray)):
        state = state.decode("utf-8")
    if isinstance(state, str):
        state = json.loads(state)

    while True:
        for key in ("observation", "state", "cluster", "snapshot", "telemetry", "payload", "data", "current_state"):
            nested = _state_value(state, key)
            if nested is not None and nested is not state:
                state = nested
                break
        else:
            break
    return state


def _iter_state_items(collection: Any) -> list[tuple[str | None, Any]]:
    if collection is None:
        return []
    if isinstance(collection, dict):
        return [(str(key), value) for key, value in collection.items()]
    if isinstance(collection, list):
        return [(None, value) for value in collection]
    return []


def _as_mapping(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    return {}


def _node_metric(node: Any, *keys: str, default: float = 0.0) -> float:
    direct = _state_value(node, *keys)
    if direct is not None:
        if isinstance(direct, dict):
            nested_direct = _state_value(direct, "utilization", "usage", "used_ratio", "ratio", "percent", "value")
            if nested_direct is not None:
                return _normalize_ratio(nested_direct, default)
        return _normalize_ratio(direct, default)

    for container_key in ("resources", "resource_usage", "usage", "utilization", "metrics", "stats"):
        container = _as_mapping(_state_value(node, container_key))
        for key in keys:
            candidates = (
                key,
                key.replace("_util", ""),
                key.replace("_util", "_usage"),
                key.replace("_util", "_ratio"),
            )
            nested = _state_value(container, *candidates)
            if nested is not None:
                if isinstance(nested, dict):
                    nested_value = _state_value(nested, "utilization", "usage", "used_ratio", "ratio", "percent", "value")
                    if nested_value is not None:
                        return _normalize_ratio(nested_value, default)
                return _normalize_ratio(nested, default)
            sub_mapping = _as_mapping(_state_value(container, key.replace("_util", "")))
            sub_value = _state_value(sub_mapping, "utilization", "usage", "used_ratio", "ratio", "percent", "value")
            if sub_value is not None:
                return _normalize_ratio(sub_value, default)

    for key in keys:
        base_mapping = _as_mapping(_state_value(node, key.replace("_util", "")))
        base_value = _state_value(base_mapping, "utilization", "usage", "used_ratio", "ratio", "percent", "value")
        if base_value is not None:
            return _normalize_ratio(base_value, default)

    return default


def _task_node_id(task: Any) -> str:
    placement = _as_mapping(_state_value(task, "placement", "assignment", "bindings"))
    metadata = _as_mapping(_state_value(task, "metadata", "labels"))
    return str(
        _state_value(
            task,
            "node_id",
            "assigned_node",
            "host_id",
            default=_state_value(
                placement,
                "node",
                "node_id",
                "host",
                default=_state_value(metadata, "node_id", default=""),
            ),
        )
    )


def _task_alive(task: Any, default: bool = True) -> bool:
    status = _as_mapping(_state_value(task, "status"))
    return _coerce_bool(
        _state_value(task, "alive", "running", "healthy", default=_state_value(status, "alive", "running", "healthy")),
        default,
    )


def _task_urgency(task: Any) -> float:
    metadata = _as_mapping(_state_value(task, "metadata", "labels"))
    return _normalize_ratio(
        _state_value(task, "urgency", "priority_score", default=_state_value(metadata, "urgency", default=0.5)),
        0.5,
    )


def _task_queue_priority(task: Any) -> int:
    metadata = _as_mapping(_state_value(task, "metadata", "labels"))
    return max(
        0,
        _coerce_int(
            _state_value(
                task,
                "queue_priority",
                "priority",
                default=_state_value(metadata, "queue_priority", "priority", default=1),
            ),
            1,
        ),
    )


def _normalize_score_map(raw_scores: Any) -> dict[str, float]:
    if isinstance(raw_scores, dict):
        return {str(k): max(0.0, min(1.0, _coerce_float(v, 0.0))) for k, v in raw_scores.items()}

    scores: dict[str, float] = {}
    for mapping_key, value in _iter_state_items(raw_scores):
        if not isinstance(value, dict):
            continue
        node_id = str(
            _state_value(value, "node_id", "id", "machine_id", "name", default=mapping_key or "unknown-node")
        )
        score = _state_value(value, "score", "value", "risk", "probability")
        scores[node_id] = max(0.0, min(1.0, _coerce_float(score, 0.0)))
    return scores


def trace_row_to_observation(row: dict[str, Any], *, fallback_timestamp: int = 0) -> Observation:
    return state_to_observation(row, fallback_timestamp=fallback_timestamp)


def _clone_observation(obs: Observation) -> Observation:
    return Observation(
        timestamp=obs.timestamp,
        nodes=[
            NodeState(
                node_id=node.node_id,
                cpu_util=node.cpu_util,
                mem_util=node.mem_util,
                disk_util=node.disk_util,
                net_util=node.net_util,
                power_state=node.power_state,
            )
            for node in obs.nodes
        ],
        tasks=[
            TaskState(
                task_id=task.task_id,
                node_id=task.node_id,
                urgency=task.urgency,
                queue_priority=task.queue_priority,
                alive=task.alive,
            )
            for task in obs.tasks
        ],
        p_fail_scores=dict(obs.p_fail_scores),
        demand_projection=dict(obs.demand_projection),
        queue_length=obs.queue_length,
        energy_price=obs.energy_price,
        sla_violations=obs.sla_violations,
        completed_tasks=obs.completed_tasks,
        energy_watts=obs.energy_watts,
    )


def _apply_action_deltas(
    current_obs: Observation,
    simulated_obs: Observation,
    baseline_obs: Observation,
    *,
    preserve_live_sla_risk: bool = True,
) -> Observation:
    merged = _clone_observation(baseline_obs)
    current_nodes = {node.node_id: node for node in current_obs.nodes}
    merged_nodes = {node.node_id: node for node in merged.nodes}

    for simulated_node in simulated_obs.nodes:
        current_node = current_nodes.get(simulated_node.node_id)
        merged_node = merged_nodes.get(simulated_node.node_id)
        if merged_node is None:
            merged_node = NodeState(
                node_id=simulated_node.node_id,
                cpu_util=simulated_node.cpu_util,
                mem_util=simulated_node.mem_util,
                disk_util=simulated_node.disk_util,
                net_util=simulated_node.net_util,
                power_state=simulated_node.power_state,
            )
            merged.nodes.append(merged_node)
            merged_nodes[simulated_node.node_id] = merged_node
            continue

        if current_node is None:
            merged_node.cpu_util = simulated_node.cpu_util
            merged_node.mem_util = simulated_node.mem_util
            merged_node.disk_util = simulated_node.disk_util
            merged_node.net_util = simulated_node.net_util
        else:
            merged_node.cpu_util = max(0.0, min(1.0, merged_node.cpu_util + (simulated_node.cpu_util - current_node.cpu_util)))
            merged_node.mem_util = max(0.0, min(1.0, merged_node.mem_util + (simulated_node.mem_util - current_node.mem_util)))
            merged_node.disk_util = max(0.0, min(1.0, merged_node.disk_util + (simulated_node.disk_util - current_node.disk_util)))
            merged_node.net_util = max(0.0, min(1.0, merged_node.net_util + (simulated_node.net_util - current_node.net_util)))
        merged_node.power_state = simulated_node.power_state

    merged_tasks = {task.task_id: task for task in merged.tasks}
    for simulated_task in simulated_obs.tasks:
        merged_task = merged_tasks.get(simulated_task.task_id)
        if merged_task is None:
            merged.tasks.append(
                TaskState(
                    task_id=simulated_task.task_id,
                    node_id=simulated_task.node_id,
                    urgency=simulated_task.urgency,
                    queue_priority=simulated_task.queue_priority,
                    alive=simulated_task.alive,
                )
            )
            continue
        merged_task.node_id = simulated_task.node_id
        merged_task.urgency = simulated_task.urgency
        merged_task.queue_priority = simulated_task.queue_priority
        merged_task.alive = simulated_task.alive

    merged.queue_length = simulated_obs.queue_length
    merged.energy_price = max(0.0, (baseline_obs.energy_price + simulated_obs.energy_price) / 2.0)
    merged.sla_violations = max(simulated_obs.sla_violations, baseline_obs.sla_violations)
    merged.completed_tasks = max(simulated_obs.completed_tasks, baseline_obs.completed_tasks)
    merged.energy_watts = max(simulated_obs.energy_watts, baseline_obs.energy_watts)
    merged.p_fail_scores = {}
    for node in merged.nodes:
        simulated_risk = simulated_obs.p_fail_scores.get(node.node_id, 0.0)
        baseline_risk = baseline_obs.p_fail_scores.get(node.node_id, simulated_risk)
        blended_risk = (0.6 * simulated_risk) + (0.4 * baseline_risk)
        # Live SLA violations are hard evidence; do not let synthetic action deltas erase them.
        if preserve_live_sla_risk and baseline_obs.sla_violations > 0:
            blended_risk = max(blended_risk, baseline_risk)
        merged.p_fail_scores[node.node_id] = max(0.0, min(1.0, blended_risk))
    merged.demand_projection = {
        node.node_id: max(
            0.0,
            min(
                1.0,
                0.6 * simulated_obs.demand_projection.get(node.node_id, 0.0)
                + 0.4 * baseline_obs.demand_projection.get(node.node_id, simulated_obs.demand_projection.get(node.node_id, 0.0)),
            ),
        )
        for node in merged.nodes
    }
    merged.timestamp = max(simulated_obs.timestamp, baseline_obs.timestamp)
    return merged


def _simulate_observation_transition(obs: Observation, action: AgentAction) -> Observation:
    next_timestamp = obs.timestamp + 1
    queue_length = obs.queue_length
    nodes = [
        NodeState(
            node_id=node.node_id,
            cpu_util=node.cpu_util,
            mem_util=node.mem_util,
            disk_util=node.disk_util,
            net_util=node.net_util,
            power_state=node.power_state,
        )
        for node in obs.nodes
    ]
    tasks = [
        TaskState(
            task_id=task.task_id,
            node_id=task.node_id,
            urgency=task.urgency,
            queue_priority=task.queue_priority,
            alive=task.alive,
        )
        for task in obs.tasks
    ]

    node_by_id = {node.node_id: node for node in nodes}
    active_tasks = [task for task in tasks if task.node_id in node_by_id and task.alive]

    if action.kind == ActionKind.MIGRATE and action.target in node_by_id and active_tasks:
        src_candidates = [node for node in nodes if node.node_id != action.target and node.power_state == "on"]
        src = max(src_candidates, key=lambda item: item.cpu_util + item.mem_util, default=None)
        if src is not None:
            task = next((item for item in active_tasks if item.node_id == src.node_id), None)
            if task is not None:
                task.node_id = action.target
                src.cpu_util = max(0.0, src.cpu_util - 0.12)
                src.mem_util = max(0.0, src.mem_util - 0.1)
                target = node_by_id[action.target]
                target.cpu_util = min(1.0, target.cpu_util + 0.08)
                target.mem_util = min(1.0, target.mem_util + 0.07)

    if action.kind == ActionKind.REPLICATE and action.target in node_by_id and active_tasks:
        source_task = max((task for task in active_tasks if task.node_id == action.target), key=lambda task: task.urgency, default=None)
        replica_target = min((node for node in nodes if node.node_id != action.target), key=lambda node: node.cpu_util + node.mem_util, default=None)
        if source_task is not None and replica_target is not None:
            tasks.append(
                TaskState(
                    task_id=f"{source_task.task_id}-replica-{next_timestamp}",
                    node_id=replica_target.node_id,
                    urgency=source_task.urgency,
                    queue_priority=source_task.queue_priority,
                    alive=True,
                )
            )
            replica_target.cpu_util = min(1.0, replica_target.cpu_util + 0.05)
            replica_target.mem_util = min(1.0, replica_target.mem_util + 0.05)

    if action.kind == ActionKind.THROTTLE and action.target in node_by_id:
        target = node_by_id[action.target]
        target.cpu_util = max(0.0, target.cpu_util * 0.85)
        target.net_util = max(0.0, target.net_util * 0.85)

    if action.kind == ActionKind.POWER_STATE and action.target in node_by_id:
        target = node_by_id[action.target]
        state = str(action.payload.get("state", target.power_state))
        target.power_state = state
        if state in {"sleep", "off"}:
            target.cpu_util = max(0.0, target.cpu_util * 0.35)
            target.mem_util = max(0.0, target.mem_util * 0.5)
        elif state == "on":
            target.cpu_util = min(1.0, target.cpu_util + 0.1)
            target.mem_util = min(1.0, target.mem_util + 0.08)

    if action.kind == ActionKind.DVFS and action.target in node_by_id:
        target = node_by_id[action.target]
        clock_scale = max(0.3, min(1.0, float(action.payload.get("clock_scale", 0.75))))
        target.cpu_util = max(0.0, target.cpu_util * clock_scale)
        target.net_util = max(0.0, target.net_util * (0.9 + (0.1 * clock_scale)))

    if action.kind == ActionKind.MEMORY_BALLOON and action.target in node_by_id:
        target = node_by_id[action.target]
        mem_scale = max(0.4, min(1.0, float(action.payload.get("mem_scale", 0.8))))
        target.mem_util = max(0.0, target.mem_util * mem_scale)

    if action.kind == ActionKind.ADMISSION:
        decision = str(action.payload.get("decision", "admit"))
        if decision == "queue":
            queue_length += 1
        elif decision == "reject":
            queue_length = max(0, queue_length - 1)
        elif decision == "deprioritize":
            queue_length = max(0, queue_length)
            for task in tasks:
                if task.node_id == "queue":
                    task.queue_priority = max(0, task.queue_priority - 1)
        else:
            queue_length = max(0, queue_length - 2)

    if action.kind == ActionKind.RESOURCE_CAP and action.target in node_by_id:
        target = node_by_id[action.target]
        target.cpu_util = min(target.cpu_util, float(action.payload.get("cpu_cap", 0.85)))
        target.mem_util = min(target.mem_util, float(action.payload.get("mem_cap", 0.85)))

    avg_cpu = sum(node.cpu_util for node in nodes) / max(1, len(nodes))
    next_energy_price = max(0.05, min(0.2, obs.energy_price + ((avg_cpu - 0.5) * 0.015)))
    p_fail_scores = {
        node.node_id: max(0.0, min(1.0, 0.55 * node.cpu_util + 0.35 * node.mem_util + 0.1 * (queue_length / 100.0)))
        for node in nodes
    }
    demand_projection = {
        node.node_id: max(
            0.0,
            min(1.0, 0.45 * node.cpu_util + 0.35 * node.mem_util + 0.1 * node.net_util + 0.1 * avg_cpu),
        )
        for node in nodes
    }

    return Observation(
        timestamp=next_timestamp,
        nodes=nodes,
        tasks=tasks,
        p_fail_scores=p_fail_scores,
        demand_projection=demand_projection,
        queue_length=queue_length,
        energy_price=next_energy_price,
        sla_violations=obs.sla_violations,
        completed_tasks=obs.completed_tasks,
        energy_watts=sum(node.cpu_util for node in nodes) * 100.0,
    )


def state_to_observation(state: Any, *, fallback_timestamp: int = 0, default_energy_price: float = 0.1) -> Observation:
    payload = _normalize_state_payload(state)
    if isinstance(payload, Observation):
        return payload
    if isinstance(payload, list):
        trace_rows = prometheus_rows_to_trace(payload)
        if not trace_rows:
            raise ValueError("Simulator state list did not produce any trace rows.")
        return state_to_observation(
            trace_rows[-1],
            fallback_timestamp=fallback_timestamp,
            default_energy_price=default_energy_price,
        )
    if not isinstance(payload, dict):
        raise TypeError(f"Unsupported simulator state payload: {type(payload).__name__}.")

    if "rows" in payload and isinstance(payload["rows"], list):
        return state_to_observation(payload["rows"], fallback_timestamp=fallback_timestamp, default_energy_price=default_energy_price)
    if "records" in payload and isinstance(payload["records"], list):
        return state_to_observation(
            payload["records"],
            fallback_timestamp=fallback_timestamp,
            default_energy_price=default_energy_price,
        )

    raw_nodes = _iter_state_items(
        _state_value(payload, "nodes")
        or _state_value(payload, "node_pool")
        or _state_value(payload, "machines")
        or _state_value(payload, "hosts")
        or _state_value(payload, "servers")
    )
    raw_tasks = _iter_state_items(
        _state_value(payload, "tasks")
        or _state_value(payload, "instances")
        or _state_value(payload, "pods")
        or _state_value(payload, "jobs")
        or _state_value(payload, "workloads")
    )
    metrics = _state_value(payload, "metrics", default={}) or {}
    power_by_node = _state_value(payload, "power_by_node", default={}) or {}

    if not raw_nodes and ("node_id" in payload or "cpu_util" in payload or "cpu" in payload):
        raw_nodes = [(None, payload)]
    if not raw_tasks and ("task_id" in payload or "instance_id" in payload):
        raw_tasks = [(None, payload)]

    nodes = []
    for idx, (mapping_key, node) in enumerate(raw_nodes):
        node_id = str(
            _state_value(node, "node_id", "id", "name", "hostname", default=mapping_key or f"node-{idx + 1}")
        )
        cpu_util = _node_metric(node, "cpu_util", "cpu", "cpu_load", "cpu_usage")
        mem_util = _node_metric(node, "mem_util", "memory_util", "mem", "memory_usage", "memory")
        disk_util = _node_metric(node, "disk_util", "disk", "disk_usage")
        net_util = _node_metric(node, "net_util", "network_util", "network", "network_usage")
        power_state = str(
            _state_value(node, "power_state", "power", "state", default=power_by_node.get(node_id, "on"))
        )
        nodes.append(
            NodeState(
                node_id=node_id,
                cpu_util=max(0.0, min(1.0, cpu_util)),
                mem_util=max(0.0, min(1.0, mem_util)),
                disk_util=max(0.0, min(1.0, disk_util)),
                net_util=max(0.0, min(1.0, net_util)),
                power_state=power_state,
            )
        )

    node_ids = {node.node_id for node in nodes}
    tasks = []
    queued_tasks = 0
    for idx, (mapping_key, task) in enumerate(raw_tasks):
        node_id = _task_node_id(task)
        queued = _coerce_bool(_state_value(task, "queued", "pending"), False)
        alive = _task_alive(task, default=not queued)
        if not node_id or node_id not in node_ids:
            queued_tasks += 1
            node_id = "queue"
            alive = False if queued else alive
        tasks.append(
            TaskState(
                task_id=str(
                    _state_value(task, "task_id", "instance_id", "job_id", "pod_id", "id", "name", default=mapping_key or f"task-{idx + 1}")
                ),
                node_id=node_id,
                urgency=_task_urgency(task),
                queue_priority=_task_queue_priority(task),
                alive=alive,
            )
        )

    queue_length = _coerce_int(
        _state_value(
            payload,
            "queue_length",
            "pending_queue_length",
            "queueSize",
            "pending",
            default=_state_value(metrics, "queue_length", "pending_queue_length", "queueSize", "pending", default=queued_tasks),
        ),
        queued_tasks,
    )
    energy_price = _coerce_float(
        _state_value(
            payload,
            "energy_price",
            "energyPrice",
            "power_price",
            default=_state_value(metrics, "energy_price", "energyPrice", "power_price", default=default_energy_price),
        ),
        default_energy_price,
    )
    sla_violations = _coerce_int(
        _state_value(payload, "sla_violations", "slaViolationCount", default=_state_value(metrics, "sla_violations", "slaViolationCount", default=0)),
        0,
    )
    completed_tasks = _coerce_int(
        _state_value(payload, "completed_tasks", "completedJobs", default=_state_value(metrics, "completed_tasks", "completedJobs", default=0)),
        0,
    )
    energy_watts = _coerce_float(
        _state_value(payload, "energy_watts", "power_watts", default=_state_value(metrics, "energy_watts", "power_watts", default=0.0)),
        0.0,
    )
    timestamp = _coerce_int(_state_value(payload, "timestamp", "ts", "time"), fallback_timestamp)

    raw_p_fail = (
        _state_value(payload, "p_fail_scores", "risk_scores", "failure_risk", "p_fail")
        or _state_value(metrics, "p_fail_scores", "risk_scores", "failure_risk")
        or {}
    )
    raw_demand = (
        _state_value(payload, "demand_projection", "demand_scores", "resource_projection", "resource_demand")
        or _state_value(metrics, "demand_projection", "demand_scores", "resource_projection")
        or {}
    )
    p_fail_scores = _normalize_score_map(raw_p_fail)
    demand_projection = _normalize_score_map(raw_demand)
    for mapping_key, node in raw_nodes:
        node_id = str(_state_value(node, "node_id", "id", "machine_id", "name", default=mapping_key or "unknown-node"))
        if node_id not in p_fail_scores:
            raw_node_risk = _state_value(node, "p_fail_score", "risk_score", "failure_risk", "risk")
            p_fail_scores[node_id] = _normalize_ratio(raw_node_risk, 0.0)
        if node_id not in demand_projection:
            raw_node_demand = _state_value(node, "demand_projection", "demand_score", "resource_demand", "projection")
            demand_projection[node_id] = _normalize_ratio(raw_node_demand, 0.0)

    return Observation(
        timestamp=timestamp,
        nodes=nodes,
        tasks=tasks,
        p_fail_scores=p_fail_scores,
        demand_projection=demand_projection,
        queue_length=max(0, queue_length),
        energy_price=max(0.0, energy_price),
        sla_violations=max(0, sla_violations),
        completed_tasks=max(0, completed_tasks),
        energy_watts=max(0.0, energy_watts),
    )


@dataclass(slots=True)
class TraceDrivenTwinBackend:
    rows: list[dict]
    preserve_live_sla_risk: bool = True
    index: int = 0

    def reset(self) -> Observation:
        self.index = 0
        return self._to_observation(self.rows[self.index])

    def step(self, action: AgentAction) -> StepResult:
        current = self.rows[self.index]
        current_obs = self._to_observation(current)
        applied = self._apply_action(current, action)
        rewards = self._reward_from_action(current_obs, action, applied)

        next_index = min(self.index + 1, len(self.rows) - 1)
        simulated_next = _simulate_observation_transition(current_obs, action)
        if next_index == self.index:
            next_obs = simulated_next
        else:
            baseline_next = self._to_observation(self.rows[next_index])
            next_obs = _apply_action_deltas(
                current_obs,
                simulated_next,
                baseline_next,
                preserve_live_sla_risk=self.preserve_live_sla_risk,
            )

        self.index = next_index
        done = self.index >= len(self.rows) - 1

        info = {
            "applied": action.kind.value,
            "agent": action.agent_name,
            "target": action.target,
            "task_map": {t.task_id: t.node_id for t in next_obs.tasks},
            "cluster_cpu_avg": sum(n.cpu_util for n in next_obs.nodes) / max(1, len(next_obs.nodes)),
            "cluster_mem_avg": sum(n.mem_util for n in next_obs.nodes) / max(1, len(next_obs.nodes)),
            "queue_length": next_obs.queue_length,
        }
        return StepResult(next_observation=next_obs, reward_by_agent=rewards, done=done, info=info)

    def _to_observation(self, row: dict) -> Observation:
        return state_to_observation(row)

    def _apply_action(self, row: dict, action: AgentAction) -> dict[str, bool]:
        applied = {
            "migrated": False,
            "replicated": False,
            "throttled": False,
            "powered": False,
            "dvfs": False,
            "memory_ballooned": False,
            "queued": False,
            "rejected": False,
            "deprioritized": False,
            "admitted": False,
            "resource_capped": False,
        }

        if action.kind == ActionKind.MIGRATE:
            applied["migrated"] = action.target is not None
        elif action.kind == ActionKind.REPLICATE:
            applied["replicated"] = action.target is not None
        elif action.kind == ActionKind.THROTTLE:
            applied["throttled"] = action.target is not None
        elif action.kind == ActionKind.POWER_STATE:
            applied["powered"] = action.payload.get("state") in {"sleep", "off", "on"}
        elif action.kind == ActionKind.DVFS:
            applied["dvfs"] = action.target is not None
        elif action.kind == ActionKind.MEMORY_BALLOON:
            applied["memory_ballooned"] = action.target is not None
        elif action.kind == ActionKind.ADMISSION:
            decision = action.payload.get("decision", "admit")
            if decision == "queue":
                applied["queued"] = True
            elif decision == "reject":
                applied["rejected"] = True
            elif decision == "deprioritize":
                applied["deprioritized"] = True
            else:
                applied["admitted"] = True
        elif action.kind == ActionKind.RESOURCE_CAP:
            applied["resource_capped"] = action.target is not None
        return applied

    def _reward_from_action(self, obs: Observation, action: AgentAction, applied: dict[str, bool]) -> dict[str, float]:
        rewards = {"AgentA": 1.0, "AgentB": 1.0, "AgentC": 1.0}
        p_fail = max(obs.p_fail_scores.values(), default=0.0)
        demand = max(obs.demand_projection.values(), default=0.0)
        has_live_metrics = obs.sla_violations > 0 or obs.completed_tasks > 0 or obs.energy_watts > 0.0

        if action.agent_name == "AgentA":
            if applied["migrated"] and p_fail > 0.75:
                rewards["AgentA"] += 10.0
            if applied["replicated"] and p_fail > 0.85:
                rewards["AgentA"] += 8.0
            if applied["throttled"] and p_fail >= 0.5:
                rewards["AgentA"] += 3.0
            if applied["migrated"] and p_fail < 0.4:
                rewards["AgentA"] -= 20.0
        if action.agent_name == "AgentB":
            if (applied["powered"] or applied["dvfs"] or applied["memory_ballooned"]) and demand < 0.35:
                rewards["AgentB"] += 5.0
            if (applied["powered"] or applied["dvfs"] or applied["memory_ballooned"]) and demand > 0.75:
                rewards["AgentB"] -= 30.0
        if action.agent_name == "AgentC":
            qlen = int(obs.queue_length)
            if applied["admitted"] and qlen < 80:
                rewards["AgentC"] += 5.0
            if applied["deprioritized"] and qlen >= 80:
                rewards["AgentC"] += 3.0
            if applied["resource_capped"] and qlen >= 80:
                rewards["AgentC"] += 4.0
            if applied["rejected"] and qlen < 60:
                rewards["AgentC"] -= 20.0
            if applied["admitted"] and qlen > 120:
                rewards["AgentC"] -= 50.0

        if has_live_metrics:
            rewards["AgentA"] -= 50.0 * obs.sla_violations
            rewards["AgentB"] += max(0.0, (500.0 - obs.energy_watts) / 100.0)
            rewards["AgentC"] += min(10.0, obs.completed_tasks / 10.0)

        if any(not task.alive for task in obs.tasks):
            rewards["AgentA"] -= 100.0
        return rewards


import logging
import importlib

logger = logging.getLogger(__name__)

try:
    import aiopslab
    HAS_AIOPSLAB = True
except ImportError:
    HAS_AIOPSLAB = False


def _load_aiopslab_orchestrator_class() -> Any | None:
    try:
        module = importlib.import_module("aiopslab.orchestrator.orchestrator")
    except Exception as exc:  # pragma: no cover
        logger.warning("aiopslab Orchestrator import failed: %s", exc)
        return None
    return getattr(module, "Orchestrator", None)


class AIOpsLabBackend(SimulatorBackend):
    """
    AIOpsLab adapter surface.

    Connects the 6-layer orchestrator to a live Microsoft AIOpsLab environment.
    """

    def __init__(self, problem_id: str, max_steps: int = 50, orchestrator: Any | None = None):
        self.problem_id = problem_id
        self.max_steps = max_steps
        self.current_step = 0
        self._orch = orchestrator
        self._session = None
        self._obs = self._mock_observation()

    def reset(self) -> Observation:
        if self._orch is None and not HAS_AIOPSLAB:
            logger.warning("aiopslab package not found. Falling back to local AIOpsLab-style simulation.")
            self.current_step = 0
            self._obs = self._mock_observation()
            return self._obs

        self.current_step = 0
        if self._orch is None:
            self._orch = self._build_orchestrator()

        state = self._invoke_orchestrator_reset()
        if state is None:
            self._obs = self._mock_observation()
            return self._obs

        self._obs = self._to_observation(state)
        return self._obs

    def step(self, action: AgentAction) -> StepResult:
        self.current_step += 1
        done = self.current_step >= self.max_steps

        if self._orch is None and not HAS_AIOPSLAB:
            previous = self._obs
            rewards = self._reward_from_observation(previous, action)
            self._obs = self._simulate_transition(previous, action)
            return StepResult(
                next_observation=self._obs,
                reward_by_agent=rewards,
                done=done,
                info={
                    "status": "mocked",
                    "reason": "no_aiopslab_pkg",
                    "applied": action.kind.value,
                    "target": action.target,
                },
            )

        if self._orch is None:
            self._orch = self._build_orchestrator()
        if self._orch is None:
            previous = self._obs
            rewards = self._reward_from_observation(previous, action)
            self._obs = self._simulate_transition(previous, action)
            return StepResult(
                next_observation=self._obs,
                reward_by_agent=rewards,
                done=done,
                info={"status": "mocked", "reason": "missing_orchestrator", "applied": action.kind.value},
            )

        previous = self._obs
        next_state = self._invoke_orchestrator_step(action)
        if next_state is None:
            self._obs = self._simulate_transition(previous, action)
            status = "adapter_fallback"
        else:
            self._obs = self._to_observation(next_state)
            status = "live_adapter"

        return StepResult(
            next_observation=self._obs,
            reward_by_agent=self._reward_from_observation(previous, action),
            done=done,
            info={"status": status, "applied": action.kind.value, "target": action.target},
        )

    def _to_observation(self, state: Any) -> Observation:
        # Convert AIOpsLab state (JSON/String/Prometheus) to orchestrator Observation
        return state_to_observation(state, fallback_timestamp=self.current_step)

    def _build_orchestrator(self) -> Any | None:
        if not HAS_AIOPSLAB:
            return None

        orchestrator_cls = _load_aiopslab_orchestrator_class()
        if orchestrator_cls is None:
            logger.warning("aiopslab package is available but Orchestrator class was not found.")
            return None

        try:
            orch = orchestrator_cls()
        except Exception as exc:  # pragma: no cover
            logger.warning("Failed to create aiopslab orchestrator: %s", exc)
            return None

        try:
            from orchestrator.layer2.aiopslab_contract import AIOpsLabPolicyAgent, initialize_aiopslab_problem

            self._session = initialize_aiopslab_problem(
                orch,
                problem_id=self.problem_id,
                agent=AIOpsLabPolicyAgent(),
            )
        except Exception as exc:  # pragma: no cover
            logger.warning("aiopslab init_problem failed for %s: %s", self.problem_id, exc)
        return orch

    def _invoke_orchestrator_reset(self) -> Any | None:
        if self._orch is None:
            return None

        for method_name in ("get_current_state", "observe", "current_state"):
            method = getattr(self._orch, method_name, None)
            if callable(method):
                return method()

        reset_method = getattr(self._orch, "reset", None)
        if callable(reset_method):
            try:
                state = reset_method()
            except TypeError:
                state = reset_method(self.problem_id)
            if state is not None:
                return state

        return None

    def _invoke_orchestrator_step(self, action: AgentAction) -> Any | None:
        if self._orch is None:
            return None

        command = self._map_action_to_cmd(action)
        for method_name in ("execute_action", "execute", "step", "act"):
            method = getattr(self._orch, method_name, None)
            if callable(method):
                result = method(command)
                if result is not None:
                    return result

        return self._invoke_orchestrator_reset()

    def _map_action_to_cmd(self, action: AgentAction) -> dict[str, Any]:
        return {
            "agent": action.agent_name,
            "kind": action.kind.value,
            "target": action.target,
            "payload": dict(action.payload),
            "score": float(action.score),
            "priority": int(action.priority),
        }

    def _reward_from_observation(self, obs: Observation, action: AgentAction) -> dict[str, float]:
        rewards = {"AgentA": 1.0, "AgentB": 1.0, "AgentC": 1.0}
        max_risk = max(obs.p_fail_scores.values(), default=max((n.cpu_util + n.mem_util) / 2.0 for n in obs.nodes) if obs.nodes else 0.0)
        min_demand = min(obs.demand_projection.values(), default=min((n.cpu_util + n.mem_util) / 2.0 for n in obs.nodes) if obs.nodes else 0.0)
        has_live_metrics = obs.sla_violations > 0 or obs.completed_tasks > 0 or obs.energy_watts > 0.0

        if action.agent_name == "AgentA" and action.kind in {ActionKind.MIGRATE, ActionKind.REPLICATE, ActionKind.THROTTLE}:
            is_valid_safety_action = (
                (action.kind == ActionKind.THROTTLE and max_risk >= 0.5)
                or (action.kind == ActionKind.MIGRATE and max_risk >= 0.7)
                or (action.kind == ActionKind.REPLICATE and max_risk >= 0.85)
            )
            rewards["AgentA"] += 10.0 if is_valid_safety_action else -20.0
        if action.agent_name == "AgentB" and action.kind in {
            ActionKind.POWER_STATE,
            ActionKind.DVFS,
            ActionKind.MEMORY_BALLOON,
        }:
            rewards["AgentB"] += 5.0 if min_demand < 0.35 else -30.0
        if action.agent_name == "AgentC" and action.kind == ActionKind.ADMISSION:
            decision = action.payload.get("decision", "admit")
            if decision == "admit":
                rewards["AgentC"] += 5.0 if obs.queue_length < 80 else -50.0
            elif decision == "reject" and obs.queue_length < 60:
                rewards["AgentC"] -= 20.0
            elif decision == "deprioritize" and obs.queue_length >= 80:
                rewards["AgentC"] += 3.0
        if action.agent_name == "AgentC" and action.kind == ActionKind.RESOURCE_CAP:
            rewards["AgentC"] += 4.0 if obs.queue_length >= 80 else -5.0

        if has_live_metrics:
            rewards["AgentA"] -= 50.0 * obs.sla_violations
            rewards["AgentB"] += max(0.0, (500.0 - obs.energy_watts) / 100.0)
            rewards["AgentC"] += min(10.0, obs.completed_tasks / 10.0)

        if any(not task.alive for task in obs.tasks):
            rewards["AgentA"] -= 100.0
        return rewards

    def _simulate_transition(self, obs: Observation, action: AgentAction) -> Observation:
        return _simulate_observation_transition(obs, action)

    def _mock_observation(self) -> Observation:
        return Observation(
            timestamp=0,
            nodes=[
                NodeState("node-1", cpu_util=0.82, mem_util=0.78, disk_util=0.45, net_util=0.36, power_state="on"),
                NodeState("node-2", cpu_util=0.34, mem_util=0.41, disk_util=0.31, net_util=0.22, power_state="on"),
                NodeState("node-3", cpu_util=0.19, mem_util=0.28, disk_util=0.25, net_util=0.18, power_state="sleep"),
            ],
            tasks=[
                TaskState("task-1", "node-1", urgency=0.9, queue_priority=3, alive=True),
                TaskState("task-2", "node-1", urgency=0.7, queue_priority=2, alive=True),
                TaskState("task-3", "node-2", urgency=0.4, queue_priority=1, alive=True),
            ],
            p_fail_scores={"node-1": 0.86, "node-2": 0.32, "node-3": 0.12},
            demand_projection={"node-1": 0.88, "node-2": 0.41, "node-3": 0.16},
            queue_length=7,
            energy_price=0.12,
        )
