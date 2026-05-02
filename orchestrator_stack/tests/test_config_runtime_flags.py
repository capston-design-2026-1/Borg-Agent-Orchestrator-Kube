import json

from orchestrator.config import OrchestratorConfig


def test_orchestrator_config_loads_runtime_ablation_flags(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(
        json.dumps(
            {
                "trace_path": "trace.json",
                "risk_model_path": "risk.json",
                "demand_model_path": "demand.json",
                "use_predictor_runtime": False,
                "preserve_live_sla_risk": False,
                "random_seed": 123,
            }
        ),
        encoding="utf-8",
    )

    config = OrchestratorConfig.load(path)

    assert config.use_predictor_runtime is False
    assert config.preserve_live_sla_risk is False
    assert config.random_seed == 123
