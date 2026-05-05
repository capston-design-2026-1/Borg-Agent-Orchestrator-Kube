from __future__ import annotations

from dataclasses import dataclass, field

from orchestrator.types import ActionKind, AgentAction


PRIORITY_ORDER = {"AgentA": 1, "AgentC": 2, "AgentB": 3}


@dataclass(slots=True)
class RefereeDecision:
    action: AgentAction
    rationale: str
    overridden: dict[str, str] = field(default_factory=dict)


def _admission_decision(action: AgentAction) -> str:
    return str(action.payload.get("decision", "admit"))


def _power_state(action: AgentAction) -> str:
    return str(action.payload.get("state", "on"))


SAFETY_ACTIONS = {ActionKind.MIGRATE, ActionKind.REPLICATE, ActionKind.THROTTLE}
EFFICIENCY_ACTIONS = {ActionKind.POWER_STATE, ActionKind.DVFS, ActionKind.MEMORY_BALLOON}
PROTECTIVE_ADMISSION_DECISIONS = {"queue", "reject", "deprioritize"}


def resolve_with_context(actions: list[AgentAction]) -> RefereeDecision:
    if not actions:
        return RefereeDecision(
            action=AgentAction("Referee", ActionKind.NOOP, score=0.0),
            rationale="no proposals",
        )

    meaningful = [action for action in actions if action.kind != ActionKind.NOOP]
    if not meaningful:
        fallback = min(
            actions,
            key=lambda action: (PRIORITY_ORDER.get(action.agent_name, action.priority or 99), -action.score),
        )
        return RefereeDecision(action=fallback, rationale="all agents proposed noop")

    agent_a_safety = next(
        (
            action
            for action in meaningful
            if action.agent_name == "AgentA" and action.kind in SAFETY_ACTIONS
        ),
        None,
    )
    if agent_a_safety is not None:
        safety_label = "migration" if agent_a_safety.kind == ActionKind.MIGRATE else agent_a_safety.kind.value
        overridden = {
            action.agent_name: f"safety-first {safety_label} takes precedence"
            for action in meaningful
            if action is not agent_a_safety
        }
        return RefereeDecision(
            action=agent_a_safety,
            rationale=f"agent-a {safety_label} preempts lower-priority actions",
            overridden=overridden,
        )

    restrictive_admission = next(
        (
            action
            for action in meaningful
            if action.agent_name == "AgentC"
            and (
                (action.kind == ActionKind.ADMISSION and _admission_decision(action) in PROTECTIVE_ADMISSION_DECISIONS)
                or action.kind == ActionKind.RESOURCE_CAP
            )
        ),
        None,
    )
    if restrictive_admission is not None:
        overridden = {
            action.agent_name: "admission protection overrides non-safety actions"
            for action in meaningful
            if action is not restrictive_admission
        }
        return RefereeDecision(
            action=restrictive_admission,
            rationale="agent-c admission protection preempts efficiency actions",
            overridden=overridden,
        )

    power_state_actions = [
        action
        for action in meaningful
        if action.kind in EFFICIENCY_ACTIONS
        and (action.kind != ActionKind.POWER_STATE or _power_state(action) in {"sleep", "off", "on"})
    ]
    if power_state_actions:
        selected = max(power_state_actions, key=lambda action: action.score)
        overridden = {
            action.agent_name: "higher-scoring power-state action selected"
            for action in meaningful
            if action is not selected
        }
        return RefereeDecision(
            action=selected,
            rationale="power-state proposal selected by score",
            overridden=overridden,
        )

    selected = min(
        meaningful,
        key=lambda action: (PRIORITY_ORDER.get(action.agent_name, action.priority or 99), -action.score),
    )
    overridden = {
        action.agent_name: "lower referee precedence"
        for action in meaningful
        if action is not selected
    }
    return RefereeDecision(
        action=selected,
        rationale="selected by deterministic referee priority",
        overridden=overridden,
    )


def resolve(actions: list[AgentAction]) -> AgentAction:
    return resolve_with_context(actions).action
