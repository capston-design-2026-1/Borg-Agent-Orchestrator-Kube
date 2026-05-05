from orchestrator.layer4.agents import AgentARiskMitigator, AgentBEfficiencyOptimizer, AgentCGatekeeper
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


def test_agent_a_replicates_severe_live_risk():
    obs = Observation(
        timestamp=1,
        nodes=[NodeState("node-1", cpu_util=0.94, mem_util=0.9, disk_util=0.0, net_util=0.0)],
        tasks=[],
        p_fail_scores={"node-1": 0.83},
        demand_projection={"node-1": 0.82},
        queue_length=0,
        energy_price=0.1,
    )

    action = AgentARiskMitigator().act(obs)

    assert action.kind == ActionKind.REPLICATE
    assert action.target == "node-1"


def test_agent_b_splits_power_dvfs_and_memory_balloon_bands():
    base = dict(
        timestamp=1,
        nodes=[NodeState("node-1", cpu_util=0.1, mem_util=0.1, disk_util=0.0, net_util=0.0)],
        tasks=[],
        p_fail_scores={"node-1": 0.05},
        queue_length=0,
        energy_price=0.1,
    )

    assert AgentBEfficiencyOptimizer().act(Observation(**base, demand_projection={"node-1": 0.08})).kind == ActionKind.POWER_STATE
    assert AgentBEfficiencyOptimizer().act(Observation(**base, demand_projection={"node-1": 0.2})).kind == ActionKind.DVFS
    assert AgentBEfficiencyOptimizer().act(Observation(**base, demand_projection={"node-1": 0.36})).kind == ActionKind.MEMORY_BALLOON


def test_agent_c_uses_queue_deprioritize_and_cap_bands():
    base = dict(
        timestamp=1,
        nodes=[NodeState("node-1", cpu_util=0.2, mem_util=0.2, disk_util=0.0, net_util=0.0)],
        tasks=[],
        p_fail_scores={"node-1": 0.1},
        demand_projection={"node-1": 0.2},
        energy_price=0.1,
    )

    queue = AgentCGatekeeper().act(Observation(**base, queue_length=12))
    deprioritize = AgentCGatekeeper().act(Observation(**base, queue_length=90))
    cap = AgentCGatekeeper().act(Observation(**base, queue_length=130))

    assert queue.kind == ActionKind.ADMISSION
    assert queue.payload["decision"] == "queue"
    assert deprioritize.kind == ActionKind.ADMISSION
    assert deprioritize.payload["decision"] == "deprioritize"
    assert cap.kind == ActionKind.RESOURCE_CAP
