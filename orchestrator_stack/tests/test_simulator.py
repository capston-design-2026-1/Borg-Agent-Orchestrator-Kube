import json
import pytest

from orchestrator.layer2.simulator import TraceDrivenTwinBackend, sla_pressure_penalty, state_to_observation
from orchestrator.types import ActionKind, AgentAction


def test_state_to_observation_normalizes_nested_aiopslab_payload():
    payload = {
        "state": {
            "hosts": [
                {"id": "node-a", "cpu": "1.2", "mem": "0.7", "disk": 0.3, "network": 0.4, "state": "sleep"}
            ],
            "pods": [
                {"id": "task-a", "assigned_node": "missing-node", "priority_score": "0.9", "priority": "4", "alive": "true"}
            ],
            "metrics": {"pending_queue_length": "3", "energy_price": "0.21"},
            "risk_scores": {"node-a": "0.95"},
            "demand_scores": {"node-a": "0.66"},
            "ts": "101",
        }
    }

    obs = state_to_observation(json.dumps(payload))
    assert obs.timestamp == 101
    assert obs.nodes[0].node_id == "node-a"
    assert obs.nodes[0].cpu_util == 1.0
    assert obs.nodes[0].power_state == "sleep"
    assert obs.tasks[0].node_id == "queue"
    assert obs.queue_length == 3
    assert obs.p_fail_scores["node-a"] == 0.95
    assert obs.demand_projection["node-a"] == 0.66


def test_state_to_observation_reads_nested_resource_metrics():
    payload = {
        "current_state": {
            "timestamp": 17,
            "machines": [
                {
                    "id": "node-a",
                    "resources": {
                        "cpu": {"percent": 72},
                        "memory": {"utilization": "0.81"},
                        "disk": {"used_ratio": "0.34"},
                        "network": {"usage": 18},
                    },
                    "power": "sleep",
                    "risk_score": "0.91",
                    "demand_score": "0.63",
                }
            ],
            "pods": [
                {"pod_id": "pod-1", "placement": {"node": "node-a"}, "status": {"healthy": "false"}},
                {"pod_id": "pod-2", "queued": True},
            ],
            "metrics": {"pending_queue_length": "3", "energyPrice": "0.14"},
        }
    }

    obs = state_to_observation(json.dumps(payload))

    assert obs.nodes[0].cpu_util == 0.72
    assert obs.nodes[0].mem_util == 0.81
    assert obs.nodes[0].disk_util == 0.34
    assert obs.nodes[0].net_util == 0.18
    assert obs.nodes[0].power_state == "sleep"
    assert obs.p_fail_scores["node-a"] == 0.91
    assert obs.demand_projection["node-a"] == 0.63
    assert obs.tasks[1].node_id == "queue"
    assert obs.tasks[1].alive is False


def test_state_to_observation_reads_live_reward_metrics():
    payload = {
        "timestamp": 1,
        "nodes": [{"node_id": "n1", "cpu_util": 0.4, "mem_util": 0.3, "disk_util": 0.2, "net_util": 0.1}],
        "tasks": [],
        "metrics": {"sla_violations": 2, "completed_tasks": 25, "energy_watts": 320.0},
    }

    obs = state_to_observation(payload)

    assert obs.sla_violations == 2
    assert obs.completed_tasks == 25
    assert obs.energy_watts == 320.0


def test_trace_driven_backend_applies_migration_before_advancing_trace():
    rows = [
        {
            "timestamp": 100,
            "nodes": [
                {"node_id": "n1", "cpu_util": 0.9, "mem_util": 0.85, "disk_util": 0.2, "net_util": 0.2},
                {"node_id": "n2", "cpu_util": 0.3, "mem_util": 0.25, "disk_util": 0.2, "net_util": 0.2},
            ],
            "tasks": [
                {"task_id": "t1", "node_id": "n1", "urgency": 0.8, "queue_priority": 2, "alive": True},
            ],
            "queue_length": 2,
            "energy_price": 0.10,
            "p_fail_scores": {"n1": 0.88, "n2": 0.2},
            "demand_projection": {"n1": 0.8, "n2": 0.3},
        },
        {
            "timestamp": 160,
            "nodes": [
                {"node_id": "n1", "cpu_util": 0.86, "mem_util": 0.8, "disk_util": 0.2, "net_util": 0.2},
                {"node_id": "n2", "cpu_util": 0.35, "mem_util": 0.28, "disk_util": 0.2, "net_util": 0.2},
            ],
            "tasks": [
                {"task_id": "t1", "node_id": "n1", "urgency": 0.8, "queue_priority": 2, "alive": True},
            ],
            "queue_length": 2,
            "energy_price": 0.11,
            "p_fail_scores": {"n1": 0.8, "n2": 0.25},
            "demand_projection": {"n1": 0.78, "n2": 0.34},
        },
    ]

    backend = TraceDrivenTwinBackend(rows)
    backend.reset()
    result = backend.step(AgentAction(agent_name="AgentA", kind=ActionKind.MIGRATE, target="n2"))

    task_map = {task.task_id: task.node_id for task in result.next_observation.tasks}
    assert task_map["t1"] == "n2"
    cpu_by_node = {node.node_id: node.cpu_util for node in result.next_observation.nodes}
    assert cpu_by_node["n1"] < 0.86
    assert cpu_by_node["n2"] > 0.35
    assert result.reward_by_agent["AgentA"] > 10.0


def test_trace_driven_backend_applies_secondary_architecture_actions():
    rows = [
        {
            "timestamp": 100,
            "nodes": [
                {"node_id": "n1", "cpu_util": 0.92, "mem_util": 0.88, "disk_util": 0.2, "net_util": 0.5},
                {"node_id": "n2", "cpu_util": 0.2, "mem_util": 0.25, "disk_util": 0.2, "net_util": 0.2},
            ],
            "tasks": [{"task_id": "t1", "node_id": "n1", "urgency": 0.9, "queue_priority": 3, "alive": True}],
            "queue_length": 130,
            "energy_price": 0.12,
            "p_fail_scores": {"n1": 0.92, "n2": 0.1},
            "demand_projection": {"n1": 0.82, "n2": 0.2},
        }
    ]

    replicate_backend = TraceDrivenTwinBackend(rows)
    replicate_backend.reset()
    replicate = replicate_backend.step(AgentAction("AgentA", ActionKind.REPLICATE, target="n1"))
    assert any(task.task_id.startswith("t1-replica") for task in replicate.next_observation.tasks)

    cap_backend = TraceDrivenTwinBackend(rows)
    cap_backend.reset()
    capped = cap_backend.step(
        AgentAction("AgentC", ActionKind.RESOURCE_CAP, target="n1", payload={"cpu_cap": 0.85, "mem_cap": 0.85})
    )
    n1 = next(node for node in capped.next_observation.nodes if node.node_id == "n1")
    assert n1.cpu_util <= 0.85
    assert n1.mem_util <= 0.85


def test_trace_driven_backend_rewards_moderate_risk_throttle():
    rows = [
        {
            "timestamp": 100,
            "nodes": [{"node_id": "n1", "cpu_util": 0.97, "mem_util": 0.42, "disk_util": 0.2, "net_util": 0.2}],
            "tasks": [{"task_id": "t1", "node_id": "n1", "urgency": 0.8, "queue_priority": 2, "alive": True}],
            "queue_length": 0,
            "energy_price": 0.1,
            "p_fail_scores": {"n1": 0.52},
            "demand_projection": {"n1": 0.32},
        }
    ]

    backend = TraceDrivenTwinBackend(rows)
    backend.reset()
    result = backend.step(AgentAction("AgentA", ActionKind.THROTTLE, target="n1"))

    assert result.reward_by_agent["AgentA"] > 1.0


def test_trace_driven_backend_rewards_live_sla_energy_and_completion_metrics():
    rows = [
        {
            "timestamp": 100,
            "nodes": [{"node_id": "n1", "cpu_util": 0.4, "mem_util": 0.3, "disk_util": 0.2, "net_util": 0.1}],
            "tasks": [],
            "queue_length": 10,
            "energy_price": 0.1,
            "sla_violations": 1,
            "completed_tasks": 20,
            "energy_watts": 300.0,
        }
    ]

    backend = TraceDrivenTwinBackend(rows)
    backend.reset()
    result = backend.step(AgentAction("AgentC", ActionKind.ADMISSION, payload={"decision": "admit"}))

    assert result.reward_by_agent["AgentA"] == pytest.approx(1.0 + sla_pressure_penalty(1))
    assert result.reward_by_agent["AgentB"] == 3.0
    assert result.reward_by_agent["AgentC"] == 8.0


def test_trace_driven_backend_bounds_intentional_sla_backlog_penalty():
    rows = [
        {
            "timestamp": 100,
            "nodes": [{"node_id": "n1", "cpu_util": 0.2, "mem_util": 0.2, "disk_util": 0.0, "net_util": 0.0}],
            "tasks": [],
            "queue_length": 130,
            "energy_price": 0.1,
            "sla_violations": 130,
            "completed_tasks": 0,
            "energy_watts": 100.0,
        }
    ]

    backend = TraceDrivenTwinBackend(rows)
    backend.reset()
    result = backend.step(AgentAction("AgentC", ActionKind.RESOURCE_CAP, target="n1"))

    assert result.reward_by_agent["AgentA"] > -220.0
    assert result.reward_by_agent["AgentA"] == pytest.approx(1.0 + sla_pressure_penalty(130))


def test_trace_driven_backend_preserves_live_sla_risk_after_action_delta():
    rows = [
        {
            "timestamp": 100,
            "nodes": [{"node_id": "n1", "cpu_util": 0.1, "mem_util": 0.1, "disk_util": 0.0, "net_util": 0.0}],
            "tasks": [{"task_id": "t1", "node_id": "n1", "urgency": 0.8, "queue_priority": 1, "alive": True}],
            "queue_length": 0,
            "energy_price": 0.1,
            "sla_violations": 1,
            "p_fail_scores": {"n1": 0.95},
            "demand_projection": {"n1": 0.1},
        },
        {
            "timestamp": 102,
            "nodes": [{"node_id": "n1", "cpu_util": 0.1, "mem_util": 0.1, "disk_util": 0.0, "net_util": 0.0}],
            "tasks": [{"task_id": "t1", "node_id": "n1", "urgency": 0.8, "queue_priority": 1, "alive": True}],
            "queue_length": 0,
            "energy_price": 0.1,
            "sla_violations": 1,
            "p_fail_scores": {"n1": 0.95},
            "demand_projection": {"n1": 0.1},
        },
    ]

    backend = TraceDrivenTwinBackend(rows)
    backend.reset()
    result = backend.step(AgentAction("AgentA", ActionKind.REPLICATE, target="n1"))

    assert result.next_observation.p_fail_scores["n1"] == 0.95


def test_trace_driven_backend_can_disable_live_sla_risk_preservation():
    rows = [
        {
            "timestamp": 100,
            "nodes": [{"node_id": "n1", "cpu_util": 0.1, "mem_util": 0.1, "disk_util": 0.0, "net_util": 0.0}],
            "tasks": [{"task_id": "t1", "node_id": "n1", "urgency": 0.8, "queue_priority": 1, "alive": True}],
            "queue_length": 0,
            "energy_price": 0.1,
            "sla_violations": 1,
            "p_fail_scores": {"n1": 0.95},
            "demand_projection": {"n1": 0.1},
        },
        {
            "timestamp": 102,
            "nodes": [{"node_id": "n1", "cpu_util": 0.1, "mem_util": 0.1, "disk_util": 0.0, "net_util": 0.0}],
            "tasks": [{"task_id": "t1", "node_id": "n1", "urgency": 0.8, "queue_priority": 1, "alive": True}],
            "queue_length": 0,
            "energy_price": 0.1,
            "sla_violations": 1,
            "p_fail_scores": {"n1": 0.95},
            "demand_projection": {"n1": 0.1},
        },
    ]

    backend = TraceDrivenTwinBackend(rows, preserve_live_sla_risk=False)
    backend.reset()
    result = backend.step(AgentAction("AgentA", ActionKind.REPLICATE, target="n1"))

    assert result.next_observation.p_fail_scores["n1"] < 0.95


def test_aiopslab_backend_loads_upstream_orchestrator_class(monkeypatch):
    from orchestrator.layer2 import simulator

    events = []

    class FakeOrchestrator:
        def register_agent(self, agent, name="agent"):
            events.append(("register_agent", name, type(agent).__name__))
            self.agent_name = name

        def init_problem(self, problem_id):
            events.append(("init_problem", problem_id, self.agent_name))
            return "desc", "instructions", ["exec_shell"]

        def get_current_state(self):
            return {
                "timestamp": 1,
                "nodes": [{"node_id": "n1", "cpu_util": 0.1, "mem_util": 0.2, "disk_util": 0.1, "net_util": 0.1}],
                "tasks": [],
                "queue_length": 0,
                "energy_price": 0.1,
            }

    monkeypatch.setattr(simulator, "HAS_AIOPSLAB", True)
    monkeypatch.setattr(simulator, "_load_aiopslab_orchestrator_class", lambda: FakeOrchestrator)

    backend = simulator.AIOpsLabBackend("problem-1")
    obs = backend.reset()

    assert obs.nodes[0].node_id == "n1"
    assert events == [
        ("register_agent", "agent", "AIOpsLabPolicyAgent"),
        ("init_problem", "problem-1", "agent"),
    ]
