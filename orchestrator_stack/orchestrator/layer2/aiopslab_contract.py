from __future__ import annotations

import json
from typing import Any

from orchestrator.layer2.simulator import state_to_observation
from orchestrator.layer4.policy import decode_agent_action, default_policy_actions
from orchestrator.layer4.referee import resolve


class AIOpsLabPolicyAgent:
    """Agent object matching AIOpsLab's init_context/get_action interface."""

    def __init__(self) -> None:
        self.problem_desc: Any | None = None
        self.instructions: Any | None = None
        self.apis: Any | None = None

    def init_context(self, problem_desc: Any, instructions: Any, apis: Any) -> None:
        self.problem_desc = problem_desc
        self.instructions = instructions
        self.apis = apis

    async def get_action(self, state: str) -> str:
        obs = state_to_observation(state)
        action_ids = default_policy_actions(obs)
        action = resolve(
            [
                decode_agent_action("AgentA", action_ids["AgentA"], obs),
                decode_agent_action("AgentB", action_ids["AgentB"], obs),
                decode_agent_action("AgentC", action_ids["AgentC"], obs),
            ]
        )
        action_payload = json.dumps(
            {
                "agent": action.agent_name,
                "kind": action.kind.value,
                "target": action.target,
                "payload": action.payload,
                "score": action.score,
            },
            sort_keys=True,
        )
        return (
            f"Selected Borg orchestrator action: {action_payload}\n"
            "```\n"
            'exec_shell("kubectl get pods --all-namespaces")\n'
            "```"
        )


def initialize_aiopslab_problem(orchestrator: Any, *, problem_id: str, agent: Any) -> tuple[Any, Any, Any]:
    orchestrator.register_agent(agent)
    problem_desc, instructions, apis = orchestrator.init_problem(problem_id)
    init_context = getattr(agent, "init_context", None)
    if callable(init_context):
        init_context(problem_desc, instructions, apis)
    return problem_desc, instructions, apis
