from orchestrator.layer4.rllib_env import OrchestratorMultiAgentEnv
from orchestrator.types import ActionKind, AgentAction, NodeState, Observation, StepResult, TaskState


class StubBackend:
    def __init__(self) -> None:
        self.last_action: AgentAction | None = None

    def reset(self) -> Observation:
        return Observation(
            timestamp=1,
            nodes=[
                NodeState("node-1", 0.85, 0.8, 0.2, 0.1),
                NodeState("node-2", 0.25, 0.2, 0.1, 0.1, power_state="sleep"),
            ],
            tasks=[TaskState("task-1", "node-1", urgency=0.9, queue_priority=3, alive=True)],
            p_fail_scores={"node-1": 0.91, "node-2": 0.12},
            demand_projection={"node-1": 0.84, "node-2": 0.14},
            queue_length=140,
            energy_price=0.15,
        )

    def step(self, action: AgentAction) -> StepResult:
        self.last_action = action
        next_obs = self.reset()
        next_obs.timestamp = 2
        next_obs.queue_length = 80
        return StepResult(
            next_observation=next_obs,
            reward_by_agent={"AgentA": 11.0, "AgentB": 1.0, "AgentC": 4.0},
            done=False,
            info={"status": "stubbed"},
        )


def test_rllib_env_exposes_referee_metadata_in_infos():
    backend = StubBackend()
    env = OrchestratorMultiAgentEnv({"backend": backend, "alpha": 1.0, "beta": 0.6, "gamma": 0.8})

    obs, info = env.reset()

    assert set(obs) == {"AgentA", "AgentB", "AgentC"}
    assert info == {}

    _, rewards, terminated, truncated, infos = env.step({"AgentB": 1, "AgentC": 1})

    assert backend.last_action is not None
    assert backend.last_action.agent_name == "AgentA"
    assert backend.last_action.kind == ActionKind.REPLICATE
    assert rewards == {"AgentA": 11.0, "AgentB": 1.0, "AgentC": 4.0}
    assert terminated["__all__"] is False
    assert truncated["__all__"] is False
    assert infos["AgentB"]["proposal"]["overridden"] is True
    assert infos["AgentC"]["proposal"]["overridden"] is True
    assert infos["AgentA"]["resolved_action"]["agent_name"] == "AgentA"
    assert infos["AgentA"]["resolved_action"]["kind"] == "replicate"
    assert infos["AgentA"]["referee_rationale"] == "agent-a replicate preempts lower-priority actions"
    assert infos["AgentA"]["global_score_total"] == 14.8
