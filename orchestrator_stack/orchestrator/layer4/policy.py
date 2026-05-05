from __future__ import annotations

from dataclasses import dataclass

from orchestrator.types import ActionKind, AgentAction, Observation


@dataclass(slots=True)
class AgentPolicySpace:
    name: str
    action_count: int


POLICY_SPACES = {
    "AgentA": AgentPolicySpace("AgentA", action_count=4),  # 0 noop, 1 migrate, 2 replicate, 3 throttle
    "AgentB": AgentPolicySpace("AgentB", action_count=5),  # 0 noop, 1 sleep, 2 wake, 3 dvfs, 4 mem-balloon
    "AgentC": AgentPolicySpace("AgentC", action_count=5),  # 0 admit, 1 queue, 2 reject, 3 deprioritize, 4 cap
}


def default_policy_actions(obs: Observation) -> dict[str, int]:
    max_risk = max(obs.p_fail_scores.values(), default=0.0)
    min_demand = min(obs.demand_projection.values(), default=1.0)

    agent_a = 0
    if max_risk >= 0.83:
        agent_a = 2
    elif max_risk >= 0.7:
        agent_a = 1
    elif max_risk >= 0.5:
        agent_a = 3

    agent_b = 0
    if min_demand < 0.12:
        agent_b = 1
    elif min_demand < 0.3:
        agent_b = 3
    elif min_demand < 0.45:
        agent_b = 4
    elif max(obs.demand_projection.values(), default=0.0) > 0.8:
        agent_b = 2

    agent_c = 0
    if obs.queue_length >= 120:
        agent_c = 4
    elif obs.queue_length >= 80:
        agent_c = 3
    elif obs.queue_length >= 8:
        agent_c = 1
    elif obs.sla_violations > 0 and obs.queue_length > 0:
        agent_c = 2
    return {"AgentA": agent_a, "AgentB": agent_b, "AgentC": agent_c}


def decode_agent_action(agent_name: str, action_id: int, obs: Observation) -> AgentAction:
    if agent_name == "AgentA":
        if action_id in {1, 2, 3} and obs.p_fail_scores:
            node_id, score = max(obs.p_fail_scores.items(), key=lambda kv: kv[1])
            if action_id == 1:
                return AgentAction("AgentA", ActionKind.MIGRATE, target=node_id, score=float(score), priority=1)
            if action_id == 2:
                return AgentAction("AgentA", ActionKind.REPLICATE, target=node_id, score=float(score), priority=1)
            return AgentAction("AgentA", ActionKind.THROTTLE, target=node_id, score=float(score), priority=1)
        return AgentAction("AgentA", ActionKind.NOOP, score=0.0, priority=1)

    if agent_name == "AgentB":
        if action_id == 1 and obs.demand_projection:
            node_id, demand = min(obs.demand_projection.items(), key=lambda kv: kv[1])
            return AgentAction(
                "AgentB",
                ActionKind.POWER_STATE,
                target=node_id,
                payload={"state": "sleep"},
                score=1.0 - float(demand),
                priority=3,
            )
        if action_id == 2 and obs.demand_projection:
            node_id, demand = max(obs.demand_projection.items(), key=lambda kv: kv[1])
            return AgentAction(
                "AgentB",
                ActionKind.POWER_STATE,
                target=node_id,
                payload={"state": "on"},
                score=float(demand),
                priority=3,
            )
        if action_id == 3 and obs.demand_projection:
            node_id, demand = min(obs.demand_projection.items(), key=lambda kv: kv[1])
            return AgentAction(
                "AgentB",
                ActionKind.DVFS,
                target=node_id,
                payload={"clock_scale": 0.65},
                score=1.0 - float(demand),
                priority=3,
            )
        if action_id == 4 and obs.demand_projection:
            node_id, demand = min(obs.demand_projection.items(), key=lambda kv: kv[1])
            return AgentAction(
                "AgentB",
                ActionKind.MEMORY_BALLOON,
                target=node_id,
                payload={"mem_scale": 0.75},
                score=1.0 - float(demand),
                priority=3,
            )
        return AgentAction("AgentB", ActionKind.NOOP, score=0.0, priority=3)

    if agent_name == "AgentC":
        if action_id == 1:
            return AgentAction("AgentC", ActionKind.ADMISSION, payload={"decision": "queue"}, score=1.0, priority=2)
        if action_id == 2:
            return AgentAction("AgentC", ActionKind.ADMISSION, payload={"decision": "reject"}, score=1.0, priority=2)
        if action_id == 3:
            return AgentAction(
                "AgentC",
                ActionKind.ADMISSION,
                payload={"decision": "deprioritize"},
                score=0.8,
                priority=2,
            )
        if action_id == 4:
            target = max(obs.nodes, key=lambda node: node.cpu_util + node.mem_util).node_id if obs.nodes else None
            return AgentAction(
                "AgentC",
                ActionKind.RESOURCE_CAP,
                target=target,
                payload={"cpu_cap": 0.85, "mem_cap": 0.85},
                score=0.8,
                priority=2,
            )
        return AgentAction("AgentC", ActionKind.ADMISSION, payload={"decision": "admit"}, score=0.5, priority=2)

    return AgentAction(agent_name, ActionKind.NOOP, score=0.0, priority=99)
