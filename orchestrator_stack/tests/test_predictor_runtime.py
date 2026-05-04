import unittest

from orchestrator.layer3.predictors import PredictorBackedBackend
from orchestrator.types import ActionKind, AgentAction, NodeState, Observation, StepResult, TaskState


class StaticPredictor:
    def __init__(self, values):
        self.values = dict(values)

    def predict(self, obs: Observation) -> dict[str, float]:
        return {node.node_id: float(self.values.get(node.node_id, 0.0)) for node in obs.nodes}


class StubBackend:
    def __init__(self) -> None:
        self.last_action: AgentAction | None = None
        self.reset_observation = Observation(
            timestamp=1,
            nodes=[NodeState("node-1", 0.72, 0.55, 0.2, 0.1), NodeState("node-2", 0.28, 0.25, 0.1, 0.1)],
            tasks=[TaskState("task-1", "node-1", urgency=0.9, queue_priority=2, alive=True)],
            p_fail_scores={},
            demand_projection={},
            queue_length=30,
            energy_price=0.11,
        )

    def reset(self) -> Observation:
        return self.reset_observation

    def step(self, action: AgentAction) -> StepResult:
        self.last_action = action
        next_obs = Observation(
            timestamp=2,
            nodes=[NodeState("node-1", 0.4, 0.35, 0.2, 0.1), NodeState("node-2", 0.8, 0.78, 0.1, 0.2)],
            tasks=[TaskState("task-2", "node-2", urgency=0.7, queue_priority=3, alive=True)],
            p_fail_scores={},
            demand_projection={},
            queue_length=90,
            energy_price=0.18,
        )
        return StepResult(
            next_observation=next_obs,
            reward_by_agent={"AgentA": 1.0, "AgentB": 2.0, "AgentC": 3.0},
            done=False,
            info={"status": "stubbed"},
        )


class PredictorRuntimeTest(unittest.TestCase):
    def test_predictor_backed_backend_enriches_reset_and_step_observations(self) -> None:
        backend = PredictorBackedBackend(
            StubBackend(),
            risk_model=StaticPredictor({"node-1": 0.83, "node-2": 0.21}),
            demand_model=StaticPredictor({"node-1": 0.62, "node-2": 0.14}),
        )

        reset_obs = backend.reset()

        self.assertEqual(reset_obs.p_fail_scores, {"node-1": 0.83, "node-2": 0.21})
        self.assertEqual(reset_obs.demand_projection, {"node-1": 0.62, "node-2": 0.14})

        result = backend.step(AgentAction("AgentA", ActionKind.MIGRATE, target="node-1"))

        self.assertEqual(result.next_observation.p_fail_scores, {"node-1": 0.83, "node-2": 0.21})
        self.assertEqual(result.next_observation.demand_projection, {"node-1": 0.62, "node-2": 0.14})
        self.assertEqual(result.info["status"], "stubbed")

    def test_predictor_backed_backend_preserves_higher_live_telemetry(self) -> None:
        source = StubBackend()
        source.reset_observation.p_fail_scores = {"node-1": 0.91, "node-2": 0.12}
        source.reset_observation.demand_projection = {"node-1": 0.87, "node-2": 0.18}
        backend = PredictorBackedBackend(
            source,
            risk_model=StaticPredictor({"node-1": 0.42, "node-2": 0.21}),
            demand_model=StaticPredictor({"node-1": 0.31, "node-2": 0.14}),
        )

        reset_obs = backend.reset()

        self.assertEqual(reset_obs.p_fail_scores, {"node-1": 0.91, "node-2": 0.21})
        self.assertEqual(reset_obs.demand_projection, {"node-1": 0.87, "node-2": 0.18})
