from orchestrator.layer4.referee import resolve, resolve_with_context
from orchestrator.types import ActionKind, AgentAction


def test_referee_prioritizes_agent_a_migration():
    action = resolve(
        [
            AgentAction("AgentB", ActionKind.POWER_STATE, target="node-1", score=0.9),
            AgentAction("AgentA", ActionKind.MIGRATE, target="node-1", score=0.7),
            AgentAction("AgentC", ActionKind.ADMISSION, score=0.8),
        ]
    )
    assert action.agent_name == "AgentA"
    assert action.kind == ActionKind.MIGRATE


def test_referee_blocks_efficiency_when_gatekeeper_queues():
    decision = resolve_with_context(
        [
            AgentAction("AgentB", ActionKind.POWER_STATE, target="node-3", payload={"state": "sleep"}, score=0.9),
            AgentAction("AgentC", ActionKind.ADMISSION, payload={"decision": "queue"}, score=1.0),
        ]
    )

    assert decision.action.agent_name == "AgentC"
    assert decision.action.payload["decision"] == "queue"
    assert decision.overridden == {"AgentB": "admission protection overrides non-safety actions"}
    assert "preempts efficiency actions" in decision.rationale


def test_referee_treats_secondary_safety_actions_as_top_priority():
    decision = resolve_with_context(
        [
            AgentAction("AgentB", ActionKind.DVFS, target="node-2", payload={"clock_scale": 0.65}, score=0.9),
            AgentAction("AgentA", ActionKind.REPLICATE, target="node-1", score=0.8),
            AgentAction("AgentC", ActionKind.ADMISSION, payload={"decision": "queue"}, score=1.0),
        ]
    )

    assert decision.action.agent_name == "AgentA"
    assert decision.action.kind == ActionKind.REPLICATE
    assert decision.overridden["AgentB"] == "safety-first replicate takes precedence"


def test_referee_returns_priority_noop_when_everyone_is_idle():
    decision = resolve_with_context(
        [
            AgentAction("AgentB", ActionKind.NOOP, score=0.1, priority=3),
            AgentAction("AgentA", ActionKind.NOOP, score=0.0, priority=1),
            AgentAction("AgentC", ActionKind.NOOP, score=0.3, priority=2),
        ]
    )

    assert decision.action.agent_name == "AgentA"
    assert decision.action.kind == ActionKind.NOOP
    assert decision.rationale == "all agents proposed noop"
