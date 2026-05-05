import json
import re
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


def test_dashboard_flow_diagram_uses_measured_card_connectors():
    app_js = Path("orchestrator_stack/dashboard/app.js").read_text(encoding="utf-8")
    styles = Path("orchestrator_stack/dashboard/styles.css").read_text(encoding="utf-8")
    index_html = Path("orchestrator_stack/dashboard/index.html").read_text(encoding="utf-8")

    required_lanes = [
        "lane-source",
        "lane-twin",
        "lane-brain",
        "lane-marl",
        "lane-referee",
        "lane-feedback",
    ]
    for lane in required_lanes:
        assert lane in app_js

    connector_ids = set(re.findall(r"\['[^']+', '[^']+', '[^']+', '(flow-[^']+)'\]", app_js))
    assert connector_ids == {
        "flow-cluster-simulator",
        "flow-exercise-simulator",
        "flow-simulator-brain",
        "flow-simulator-observation",
        "flow-brain-policy",
        "flow-observation-policy",
        "flow-policy-agent-a",
        "flow-policy-agent-b",
        "flow-policy-agent-c",
        "flow-agent-a-referee",
        "flow-agent-b-referee",
        "flow-agent-c-referee",
        "flow-referee-cluster",
        "flow-referee-scoreboard",
        "flow-scoreboard-optuna",
        "flow-scoreboard-policy",
        "flow-optuna-policy",
    }
    animated_ids = set(re.findall(r"'(flow-[^']+)'", app_js.split("const animatedConnectorIds = [", 1)[1].split("];", 1)[0]))
    assert animated_ids <= connector_ids

    assert "getBoundingClientRect" in app_js
    assert "data-node=" in app_js
    assert "diagram-action-trace" in app_js
    assert "diagram-stimulus" in app_js
    assert 'id="flowOperations"' in index_html
    assert "$('flowOperations').innerHTML" in app_js
    flow_diagram_template = app_js.split("$('flowDiagram').innerHTML = `", 1)[1].split("`;", 1)[0]
    assert "clusterStimulusMarkup" not in flow_diagram_template
    assert "actionTraceMarkup" not in flow_diagram_template
    assert ".diagram-action-trace {\n  position: relative;" in styles
    assert ".diagram-stimulus {\n  position: relative;" in styles
    assert "exerciseSummary" in app_js
    assert "telemetrySourceLabel" in app_js
    assert "kubectl + prometheus" in app_js
    assert "persisted Optuna study trial" in app_js
    assert "Showing all completed persisted Optuna trials" in app_js
    assert "optunaParamCanvas" in index_html
    assert "actionSemantics" in app_js
    for action_kind in ("migrate", "replicate", "throttle", "memory_balloon", "dvfs", "admission", "resource_cap"):
        assert f"{action_kind}:" in app_js
    assert "proposal-chip" in app_js
    assert 'id="repeatCount"' not in index_html
    assert "$('repeatCount')" not in app_js
    assert "repeat(6, minmax(0, 1fr))" in styles
    assert "<path id=\"flow-" not in app_js
    assert "rail-label" not in app_js
    assert ".rail-label" not in styles
    assert "style=\"left:" not in app_js
    assert "translateY(-50%)" not in styles


def test_live_kubernetes_run_cli_accepts_continuous_options():
    parser = build_parser()

    args = parser.parse_args(
        [
            "live-kubernetes-run",
            "--kubeconfig",
            "/tmp/kubeconfig",
            "--interval-seconds",
            "0.2",
            "--max-iterations",
            "2",
            "--namespace-prefixes",
            "test-,observe",
            "--prometheus-base-url",
            "http://127.0.0.1:19090",
            "--no-policy",
            "--no-tune",
            "--exercise-cluster",
            "--exercise-namespace",
            "demo-exercise",
            "--exercise-interval-iterations",
            "4",
            "--exercise-randomize",
            "--exercise-seed",
            "17",
        ]
    )

    assert args.kubeconfig == "/tmp/kubeconfig"
    assert args.interval_seconds == 0.2
    assert args.max_iterations == 2
    assert args.namespace_prefixes == "test-,observe"
    assert args.prometheus_base_url == "http://127.0.0.1:19090"
    assert args.no_policy is True
    assert args.no_tune is True
    assert args.exercise_cluster is True
    assert args.exercise_namespace == "demo-exercise"
    assert args.exercise_interval_iterations == 4
    assert args.exercise_randomize is True
    assert args.exercise_seed == 17


def test_visualization_state_writes_state_and_events(tmp_path: Path):
    state = VisualizationState(tmp_path)

    state.stage("episode", "running", detail="step 1/2", progress=0.5)
    state.reward(1, {"AgentA": 1.0, "AgentB": 2.0, "AgentC": -1.0}, 1.4, "AgentA:migrate")
    state.cluster_snapshot({"nodes": 1, "tasks": 2, "sla_violations": 0, "max_risk": 0.4})
    state.decision({"agent": "AgentA", "kind": "migrate", "target": "node-1", "repeat_count": 1, "reason": "risk=0.4"})
    state.optuna_trial("study", 0, 3.2, {"alpha": 1.0}, 3.2)
    state.ray_update("trained", reward_mean=5.0, checkpoint="ckpt")

    payload = json.loads((tmp_path / "state.json").read_text(encoding="utf-8"))
    events = (tmp_path / "events.jsonl").read_text(encoding="utf-8").splitlines()

    assert payload["active_stage"] == "episode"
    assert payload["rewards"][-1]["action"] == "AgentA:migrate"
    assert payload["reward_summary"]["count"] == 1
    assert payload["reward_summary"]["last_total"] == 1.4
    assert payload["cluster"]["max_risk"] == 0.4
    assert payload["decision"]["reason"] == "risk=0.4"
    assert payload["optuna"]["best_score"] == 3.2
    assert payload["optuna"]["history"][-1]["run_trial"] == 1
    assert payload["optuna"]["history"][-1]["trial"] == 0
    assert payload["ray"]["status"] == "trained"
    assert len(events) >= 4


def test_visualization_state_exports_persisted_optuna_history(tmp_path: Path):
    state = VisualizationState(tmp_path)
    history = [
        {"trial": 0, "value": 1.5, "params": {"alpha": 0.9}, "state": "COMPLETE"},
        {"trial": 1, "value": 4.2, "params": {"alpha": 1.4}, "state": "COMPLETE"},
    ]

    state.optuna_history(
        "study",
        history,
        best_score=4.2,
        best_params={"alpha": 1.4},
        latest_trial=1,
        status="complete",
    )

    payload = json.loads((tmp_path / "state.json").read_text(encoding="utf-8"))
    event = json.loads((tmp_path / "events.jsonl").read_text(encoding="utf-8").splitlines()[-1])

    assert payload["optuna"]["history_scope"] == "all_completed_study_trials"
    assert payload["optuna"]["completed_trials"] == 2
    assert payload["optuna"]["history"] == history
    assert payload["optuna"]["trial"] == 1
    assert payload["optuna"]["best_params"] == {"alpha": 1.4}
    assert "history" not in event


def test_optuna_study_history_keeps_all_completed_trials():
    from orchestrator.visualization import _optuna_study_history

    class TrialState:
        name = "COMPLETE"

    class Trial:
        def __init__(self, number, value, params):
            self.number = number
            self.value = value
            self.params = params
            self.state = TrialState()
            self.datetime_start = None
            self.datetime_complete = None

    class Study:
        trials = [
            Trial(2, 8.0, {"alpha": 1.2}),
            Trial(0, 3.0, {"alpha": 0.7}),
            Trial(1, None, {"alpha": 0.9}),
        ]

    history = _optuna_study_history(Study())

    assert [row["trial"] for row in history] == [0, 2]
    assert [row["value"] for row in history] == [3.0, 8.0]


def test_live_kubernetes_orchestration_loop_uses_cluster_snapshots(monkeypatch, tmp_path: Path):
    from orchestrator import visualization

    trace_path = tmp_path / "trace.json"
    trace_path.write_text(
        json.dumps(
            [
                {
                    "timestamp": 1,
                    "nodes": [{"node_id": "node-1", "cpu_util": 0.7, "mem_util": 0.6, "disk_util": 0.0, "net_util": 0.0}],
                    "tasks": [{"task_id": "task-1", "node_id": "node-1", "urgency": 0.5, "queue_priority": 1, "alive": True}],
                    "p_fail_scores": {"node-1": 0.8},
                    "demand_projection": {"node-1": 0.7},
                    "queue_length": 1,
                    "energy_price": 0.1,
                }
            ]
        ),
        encoding="utf-8",
    )
    cfg = tmp_path / "config.json"
    cfg.write_text(
        json.dumps(
            {
                "trace_path": str(trace_path),
                "risk_model_path": str(tmp_path / "risk.json"),
                "demand_model_path": str(tmp_path / "demand.json"),
                "episode_steps": 1,
                "use_predictor_runtime": False,
            }
        ),
        encoding="utf-8",
    )
    live_row = {
        "timestamp": 2,
        "nodes": [{"node_id": "node-1", "cpu_util": 0.95, "mem_util": 0.9, "disk_util": 0.0, "net_util": 0.0}],
        "tasks": [{"task_id": "pod-1", "node_id": "node-1", "urgency": 1.0, "queue_priority": 1, "alive": True}],
        "p_fail_scores": {"node-1": 0.96},
        "demand_projection": {"node-1": 0.9},
        "queue_length": 4,
        "energy_price": 0.1,
        "sla_violations": 0,
        "completed_tasks": 0,
        "energy_watts": 210.0,
        "power_calibration": {"source": "default_utilization_model"},
        "telemetry_sources": ["kubernetes_api", "prometheus_node_exporter"],
    }
    monkeypatch.setattr(visualization, "capture_kubernetes_trace_row", lambda **kwargs: dict(live_row))
    monkeypatch.setattr(
        visualization,
        "train_brain_models",
        lambda config: {"risk_model": str(tmp_path / "risk.json"), "demand_model": str(tmp_path / "demand.json")},
    )

    summary = visualization.run_live_kubernetes_orchestration(
        cfg,
        event_dir=tmp_path / "events",
        kubeconfig="/tmp/kubeconfig",
        interval_seconds=0.1,
        max_iterations=2,
        trace_out=tmp_path / "live_trace.json",
        train_policy=False,
        tune_rewards=False,
    )

    state = json.loads((tmp_path / "events" / "state.json").read_text(encoding="utf-8"))
    rows = json.loads((tmp_path / "live_trace.json").read_text(encoding="utf-8"))

    assert summary["iterations"] == 2
    assert len(rows) == 2
    assert state["summary"]["mode"] == "live_kubernetes"
    assert state["ray"]["status"] == "disabled"
    assert state["optuna"]["status"] == "disabled"
    assert state["reward_summary"]["count"] == 2
    assert state["summary"]["last_action"]["kind"] == "replicate"
    assert state["summary"]["last_action"]["reason"].startswith("risk=0.96")
    assert state["summary"]["last_action"]["proposals"][0]["agent"] == "AgentA"
    assert state["decision"]["repeat_count"] == 2
    assert state["cluster"]["sla_violations"] == 0
    assert state["cluster"]["power_metric_kind"] == "estimated"
    assert state["cluster"]["power_calibration_source"] == "default_utilization_model"
    assert state["cluster"]["telemetry_sources"] == ["kubernetes_api", "prometheus_node_exporter"]


def test_live_kubernetes_loop_continues_without_xgboost(monkeypatch, tmp_path: Path):
    from orchestrator import visualization

    trace_path = tmp_path / "trace.json"
    trace_path.write_text(
        json.dumps(
            [
                {
                    "timestamp": 1,
                    "nodes": [{"node_id": "node-1", "cpu_util": 0.3, "mem_util": 0.3, "disk_util": 0.0, "net_util": 0.0}],
                    "tasks": [],
                    "p_fail_scores": {"node-1": 0.2},
                    "demand_projection": {"node-1": 0.2},
                    "queue_length": 0,
                    "energy_price": 0.1,
                }
            ]
        ),
        encoding="utf-8",
    )
    cfg = tmp_path / "config.json"
    cfg.write_text(
        json.dumps(
            {
                "trace_path": str(trace_path),
                "risk_model_path": str(tmp_path / "risk.json"),
                "demand_model_path": str(tmp_path / "demand.json"),
                "episode_steps": 1,
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        visualization,
        "capture_kubernetes_trace_row",
        lambda **kwargs: {
            "timestamp": 2,
            "nodes": [{"node_id": "node-1", "cpu_util": 0.2, "mem_util": 0.2, "disk_util": 0.0, "net_util": 0.0}],
            "tasks": [],
            "p_fail_scores": {"node-1": 0.2},
            "demand_projection": {"node-1": 0.2},
            "queue_length": 0,
            "energy_price": 0.1,
        },
    )

    def missing_xgboost(config):
        raise ModuleNotFoundError("No module named 'xgboost'", name="xgboost")

    monkeypatch.setattr(visualization, "train_brain_models", missing_xgboost)

    summary = visualization.run_live_kubernetes_orchestration(
        cfg,
        event_dir=tmp_path / "events",
        kubeconfig="/tmp/kubeconfig",
        max_iterations=1,
        trace_out=tmp_path / "live_trace.json",
        train_policy=False,
        tune_rewards=False,
    )
    state = json.loads((tmp_path / "events" / "state.json").read_text(encoding="utf-8"))

    assert summary["iterations"] == 1
    assert state["stages"][0]["status"] == "skipped"
