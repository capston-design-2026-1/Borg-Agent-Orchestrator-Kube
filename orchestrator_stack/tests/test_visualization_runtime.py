import json
from pathlib import Path

from orchestrator.cli import build_parser
from orchestrator.runtime_state import VisualizationState


def test_visualized_run_cli_defaults():
    parser = build_parser()

    args = parser.parse_args(["visualized-run", "--trials", "2", "--no-policy", "--no-tune"])

    assert args.config == "orchestrator_stack/config/orchestrator.example.json"
    assert args.trials == 2
    assert args.no_policy is True
    assert args.no_tune is True


def test_visualization_state_writes_state_and_events(tmp_path: Path):
    state = VisualizationState(tmp_path)

    state.stage("episode", "running", detail="step 1/2", progress=0.5)
    state.reward(1, {"AgentA": 1.0, "AgentB": 2.0, "AgentC": -1.0}, 1.4, "AgentA:migrate")
    state.optuna_trial("study", 0, 3.2, {"alpha": 1.0}, 3.2)
    state.ray_update("trained", reward_mean=5.0, checkpoint="ckpt")

    payload = json.loads((tmp_path / "state.json").read_text(encoding="utf-8"))
    events = (tmp_path / "events.jsonl").read_text(encoding="utf-8").splitlines()

    assert payload["active_stage"] == "episode"
    assert payload["rewards"][-1]["action"] == "AgentA:migrate"
    assert payload["optuna"]["best_score"] == 3.2
    assert payload["ray"]["status"] == "trained"
    assert len(events) >= 4
