from orchestrator.layer4.agents import AgentARiskMitigator, AgentCGatekeeper
from orchestrator.types import ActionKind, NodeState, Observation


def test_agent_a_throttles_live_moderate_risk():
    obs = Observation(
        timestamp=1,
        nodes=[NodeState("node-1", cpu_util=0.97, mem_util=0.42, disk_util=0.0, net_util=0.0)],
        tasks=[],
        p_fail_scores={"node-1": 0.52},
        demand_projection={"node-1": 0.32},
        queue_length=0,
        energy_price=0.1,
    )

    action = AgentARiskMitigator().act(obs)

    assert action.agent_name == "AgentA"
    assert action.kind == ActionKind.THROTTLE
    assert action.target == "node-1"


def test_agent_c_caps_single_overloaded_node():
    obs = Observation(
        timestamp=1,
        nodes=[NodeState("node-1", cpu_util=0.9, mem_util=0.2, disk_util=0.0, net_util=0.0)],
        tasks=[],
        p_fail_scores={"node-1": 0.5},
        demand_projection={"node-1": 0.55},
        queue_length=0,
        energy_price=0.1,
    )

    action = AgentCGatekeeper().act(obs)

    assert action.agent_name == "AgentC"
    assert action.kind == ActionKind.RESOURCE_CAP
    assert action.target == "node-1"
