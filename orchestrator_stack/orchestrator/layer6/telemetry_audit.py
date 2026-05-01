from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from orchestrator.layer2.simulator import TraceDrivenTwinBackend
from orchestrator.layer4.agents import AgentARiskMitigator, AgentBEfficiencyOptimizer, AgentCGatekeeper
from orchestrator.layer4.referee import resolve
from orchestrator.layer6.scoreboard import Scoreboard
from orchestrator.types import Observation


def telemetry_reward_delta(obs: Observation, *, alpha: float, beta: float, gamma: float) -> dict[str, float]:
    has_live_metrics = obs.sla_violations > 0 or obs.completed_tasks > 0 or obs.energy_watts > 0.0
    if not has_live_metrics:
        return {"AgentA": 0.0, "AgentB": 0.0, "AgentC": 0.0, "weighted_total": 0.0}

    agent_a = -50.0 * float(obs.sla_violations)
    agent_b = max(0.0, (500.0 - float(obs.energy_watts)) / 100.0)
    agent_c = min(10.0, float(obs.completed_tasks) / 10.0)
    return {
        "AgentA": agent_a,
        "AgentB": agent_b,
        "AgentC": agent_c,
        "weighted_total": (alpha * agent_a) + (beta * agent_b) + (gamma * agent_c),
    }


def audit_trace_telemetry_rewards(
    rows: list[dict[str, Any]],
    *,
    alpha: float = 1.0,
    beta: float = 0.6,
    gamma: float = 0.8,
    max_steps: int | None = None,
) -> dict[str, Any]:
    if not rows:
        return {
            "steps": 0,
            "telemetry_steps": 0,
            "telemetry_coverage": 0.0,
            "score": {"total": 0.0, "average": 0.0, "agent_a": 0.0, "agent_b": 0.0, "agent_c": 0.0},
            "telemetry_reward_delta": {"AgentA": 0.0, "AgentB": 0.0, "AgentC": 0.0, "weighted_total": 0.0},
            "actions": {},
        }

    backend = TraceDrivenTwinBackend(rows)
    agents = [AgentARiskMitigator(), AgentBEfficiencyOptimizer(), AgentCGatekeeper()]
    scoreboard = Scoreboard(alpha=alpha, beta=beta, gamma=gamma)
    obs = backend.reset()
    total_steps = min(max_steps if max_steps is not None else len(rows), len(rows))

    telemetry_steps = 0
    action_counts: dict[str, int] = {}
    delta_totals = {"AgentA": 0.0, "AgentB": 0.0, "AgentC": 0.0, "weighted_total": 0.0}
    max_sla_violations = 0
    max_energy_watts = 0.0
    max_completed_tasks = 0

    for _ in range(total_steps):
        delta = telemetry_reward_delta(obs, alpha=alpha, beta=beta, gamma=gamma)
        if any(delta[agent] != 0.0 for agent in ("AgentA", "AgentB", "AgentC")):
            telemetry_steps += 1
        for key, value in delta.items():
            delta_totals[key] += float(value)
        max_sla_violations = max(max_sla_violations, int(obs.sla_violations))
        max_energy_watts = max(max_energy_watts, float(obs.energy_watts))
        max_completed_tasks = max(max_completed_tasks, int(obs.completed_tasks))

        proposals = [agent.act(obs) for agent in agents]
        action = resolve(proposals)
        action_counts[action.kind.value] = action_counts.get(action.kind.value, 0) + 1
        result = backend.step(action)
        scoreboard.update(result.reward_by_agent)
        obs = result.next_observation
        if result.done:
            break

    snap = scoreboard.snapshot()
    steps = int(snap["steps"])
    return {
        "steps": steps,
        "telemetry_steps": telemetry_steps,
        "telemetry_coverage": telemetry_steps / max(1, steps),
        "score": snap,
        "telemetry_reward_delta": delta_totals,
        "max_sla_violations": max_sla_violations,
        "max_completed_tasks": max_completed_tasks,
        "max_energy_watts": max_energy_watts,
        "actions": action_counts,
    }


def write_telemetry_audit_report(report: dict[str, Any], out_path: str | Path) -> Path:
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return out
