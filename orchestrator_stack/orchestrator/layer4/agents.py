from __future__ import annotations

from dataclasses import dataclass

from orchestrator.types import ActionKind, AgentAction, Observation


@dataclass(slots=True)
class AgentARiskMitigator:
    priority: int = 1

    def act(self, obs: Observation) -> AgentAction:
        if not obs.p_fail_scores:
            return AgentAction("AgentA", ActionKind.NOOP, score=0.0, priority=self.priority)
        node_id, score = max(obs.p_fail_scores.items(), key=lambda kv: kv[1])
        if score >= 0.83:
            return AgentAction("AgentA", ActionKind.REPLICATE, target=node_id, score=float(score), priority=self.priority)
        if score >= 0.7:
            return AgentAction("AgentA", ActionKind.MIGRATE, target=node_id, score=float(score), priority=self.priority)
        if score >= 0.5:
            return AgentAction("AgentA", ActionKind.THROTTLE, target=node_id, score=float(score), priority=self.priority)
        return AgentAction("AgentA", ActionKind.NOOP, score=float(score), priority=self.priority)


@dataclass(slots=True)
class AgentBEfficiencyOptimizer:
    priority: int = 3

    def act(self, obs: Observation) -> AgentAction:
        if not obs.demand_projection:
            return AgentAction("AgentB", ActionKind.NOOP, score=0.0, priority=self.priority)

        node_id, demand = min(obs.demand_projection.items(), key=lambda kv: kv[1])
        if demand < 0.12:
            return AgentAction(
                "AgentB",
                ActionKind.POWER_STATE,
                target=node_id,
                payload={"state": "sleep"},
                score=1.0 - float(demand),
                priority=self.priority,
            )
        if demand < 0.3:
            return AgentAction(
                "AgentB",
                ActionKind.DVFS,
                target=node_id,
                payload={"clock_scale": 0.65},
                score=1.0 - float(demand),
                priority=self.priority,
            )
        if demand < 0.45:
            return AgentAction(
                "AgentB",
                ActionKind.MEMORY_BALLOON,
                target=node_id,
                payload={"mem_scale": 0.75},
                score=1.0 - float(demand),
                priority=self.priority,
            )
        return AgentAction("AgentB", ActionKind.NOOP, score=1.0 - float(demand), priority=self.priority)


@dataclass(slots=True)
class AgentCGatekeeper:
    priority: int = 2

    def act(self, obs: Observation) -> AgentAction:
        overloaded = sum(1 for n in obs.nodes if n.cpu_util > 0.85 or n.mem_util > 0.85)
        if obs.queue_length >= 120:
            return AgentAction(
                "AgentC",
                ActionKind.RESOURCE_CAP,
                target=max(obs.nodes, key=lambda node: node.cpu_util + node.mem_util).node_id if obs.nodes else None,
                payload={"cpu_cap": 0.85, "mem_cap": 0.85},
                score=1.0,
                priority=self.priority,
            )
        if obs.queue_length >= 80:
            return AgentAction(
                "AgentC",
                ActionKind.ADMISSION,
                payload={"decision": "deprioritize"},
                score=0.95,
                priority=self.priority,
            )
        if obs.queue_length >= 8:
            return AgentAction(
                "AgentC",
                ActionKind.ADMISSION,
                payload={"decision": "queue"},
                score=0.9,
                priority=self.priority,
            )
        if obs.sla_violations > 0 and obs.queue_length > 0:
            return AgentAction(
                "AgentC",
                ActionKind.ADMISSION,
                payload={"decision": "reject"},
                score=0.85,
                priority=self.priority,
            )
        if overloaded >= max(1, len(obs.nodes) // 2):
            return AgentAction(
                "AgentC",
                ActionKind.RESOURCE_CAP,
                target=max(obs.nodes, key=lambda node: node.cpu_util + node.mem_util).node_id if obs.nodes else None,
                payload={"cpu_cap": 0.85, "mem_cap": 0.85},
                score=1.0,
                priority=self.priority,
            )
        if obs.queue_length < 20 and overloaded == 0:
            return AgentAction(
                "AgentC",
                ActionKind.ADMISSION,
                payload={"decision": "admit"},
                score=1.0,
                priority=self.priority,
            )
        return AgentAction(
            "AgentC",
            ActionKind.ADMISSION,
            payload={"decision": "admit"},
            score=0.5,
            priority=self.priority,
        )
