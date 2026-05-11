from orchestrator.layer4.policy import decode_agent_action, default_policy_actions
from orchestrator.types import NodeState, Observation


def test_decode_agent_a_migrate_action():
    obs = Observation(
        timestamp=1,
        nodes=[NodeState("n1", 0.9, 0.8, 0.2, 0.1), NodeState("n2", 0.2, 0.2, 0.1, 0.1)],
        tasks=[],
        p_fail_scores={"n1": 0.95, "n2": 0.1},
        demand_projection={"n1": 0.8, "n2": 0.2},
        queue_length=10,
        energy_price=0.1,
    )

    action = decode_agent_action("AgentA", 1, obs)
    assert action.target == "n1"


def test_decode_secondary_architecture_actions():
    obs = Observation(
        timestamp=1,
        nodes=[NodeState("n1", 0.9, 0.8, 0.2, 0.1), NodeState("n2", 0.2, 0.2, 0.1, 0.1)],
        tasks=[],
        p_fail_scores={"n1": 0.95, "n2": 0.1},
        demand_projection={"n1": 0.8, "n2": 0.2},
        queue_length=10,
        energy_price=0.1,
    )

    assert decode_agent_action("AgentA", 2, obs).kind.value == "replicate"
    assert decode_agent_action("AgentA", 3, obs).kind.value == "throttle"
    assert decode_agent_action("AgentB", 3, obs).kind.value == "dvfs"
    assert decode_agent_action("AgentB", 4, obs).kind.value == "memory_balloon"
    assert decode_agent_action("AgentC", 3, obs).payload["decision"] == "deprioritize"
    assert decode_agent_action("AgentC", 4, obs).kind.value == "resource_cap"


def test_default_policy_defers_moderate_agent_a_backlog_risk_to_agent_c():
    obs = Observation(
        timestamp=1,
        nodes=[NodeState("n1", 0.5, 0.45, 0.2, 0.1)],
        tasks=[],
        p_fail_scores={"n1": 0.52},
        demand_projection={"n1": 0.5},
        queue_length=95,
        energy_price=0.1,
        sla_violations=1,
    )

    actions = default_policy_actions(obs)

    assert actions["AgentA"] == 0
    assert actions["AgentC"] == 3


def test_default_policy_keeps_moderate_agent_a_throttle_for_node_pressure():
    obs = Observation(
        timestamp=1,
        nodes=[NodeState("n1", 0.74, 0.45, 0.2, 0.1)],
        tasks=[],
        p_fail_scores={"n1": 0.52},
        demand_projection={"n1": 0.5},
        queue_length=95,
        energy_price=0.1,
        sla_violations=1,
    )

    actions = default_policy_actions(obs)

    assert actions["AgentA"] == 3
