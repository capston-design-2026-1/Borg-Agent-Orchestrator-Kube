from pathlib import Path

import pytest

from orchestrator.layer2.simulator import sla_pressure_penalty
from orchestrator.layer6.telemetry_audit import (
    audit_trace_telemetry_rewards,
    telemetry_reward_delta,
    write_telemetry_audit_report,
)
from orchestrator.types import Observation


def test_telemetry_reward_delta_reports_weighted_components():
    obs = Observation(
        timestamp=1,
        nodes=[],
        tasks=[],
        p_fail_scores={},
        demand_projection={},
        queue_length=0,
        energy_price=0.1,
        sla_violations=2,
        completed_tasks=25,
        energy_watts=300.0,
    )

    delta = telemetry_reward_delta(obs, alpha=1.0, beta=0.6, gamma=0.8)

    assert delta["AgentA"] == pytest.approx(sla_pressure_penalty(2))
    assert delta["AgentB"] == 2.0
    assert delta["AgentC"] == 2.5
    assert delta["weighted_total"] == pytest.approx(sla_pressure_penalty(2) + 1.2 + 2.0)


def test_audit_trace_telemetry_rewards_replays_trace_and_counts_coverage():
    rows = [
        {
            "timestamp": 1,
            "nodes": [{"node_id": "n1", "cpu_util": 0.9, "mem_util": 0.8, "disk_util": 0.2, "net_util": 0.1}],
            "tasks": [{"task_id": "t1", "node_id": "n1", "alive": True}],
            "p_fail_scores": {"n1": 0.8},
            "demand_projection": {"n1": 0.2},
            "queue_length": 5,
            "energy_price": 0.1,
            "sla_violations": 1,
            "completed_tasks": 10,
            "energy_watts": 250.0,
        },
        {
            "timestamp": 2,
            "nodes": [{"node_id": "n1", "cpu_util": 0.4, "mem_util": 0.3, "disk_util": 0.2, "net_util": 0.1}],
            "tasks": [{"task_id": "t2", "node_id": "n1", "alive": True}],
            "p_fail_scores": {"n1": 0.1},
            "demand_projection": {"n1": 0.6},
            "queue_length": 3,
            "energy_price": 0.1,
        },
    ]

    report = audit_trace_telemetry_rewards(rows)

    assert report["steps"] == 1
    assert report["telemetry_steps"] == 1
    assert report["telemetry_coverage"] == 1.0
    assert report["max_sla_violations"] == 1
    assert report["telemetry_reward_delta"]["AgentA"] == pytest.approx(sla_pressure_penalty(1))
    assert report["actions"] == {"migrate": 1}


def test_write_telemetry_audit_report_writes_json(tmp_path: Path):
    out = write_telemetry_audit_report({"steps": 1}, tmp_path / "audit.json")

    assert out.read_text(encoding="utf-8") == '{\n  "steps": 1\n}'
