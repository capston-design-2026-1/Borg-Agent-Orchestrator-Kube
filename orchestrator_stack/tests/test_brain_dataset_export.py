from pathlib import Path

import numpy as np

from orchestrator.layer2.feature_extractor import FEATURE_NAMES
from orchestrator.layer3.predictors import export_training_datasets_from_trace


def test_export_training_datasets_from_trace_writes_risk_and_demand_npz(tmp_path: Path):
    rows = [
        {
            "timestamp": 100,
            "nodes": [
                {"node_id": "n1", "cpu_util": 0.4, "mem_util": 0.5, "disk_util": 0.2, "net_util": 0.1},
                {"node_id": "n2", "cpu_util": 0.95, "mem_util": 0.3, "disk_util": 0.2, "net_util": 0.1},
            ],
            "tasks": [{"task_id": "t1", "node_id": "n1", "alive": True}],
            "queue_length": 3,
            "energy_price": 0.11,
        },
        {
            "timestamp": 160,
            "nodes": [
                {"node_id": "n1", "cpu_util": 0.6, "mem_util": 0.6, "disk_util": 0.2, "net_util": 0.1},
                {"node_id": "n2", "cpu_util": 0.4, "mem_util": 0.4, "disk_util": 0.2, "net_util": 0.1},
            ],
            "tasks": [{"task_id": "t2", "node_id": "n2", "alive": True}],
            "queue_length": 2,
            "energy_price": 0.1,
            "demand_projection": {"n1": 0.7, "n2": 0.2},
        },
    ]

    risk_path, demand_path = export_training_datasets_from_trace(
        rows,
        tmp_path / "risk_train.npz",
        tmp_path / "demand_train.npz",
    )

    risk = np.load(risk_path)
    demand = np.load(demand_path)

    assert risk["x"].shape == (4, len(FEATURE_NAMES))
    assert demand["x"].shape == risk["x"].shape
    assert risk["y"].dtype == np.int32
    assert demand["y"].dtype == np.float32
    assert risk["feature_names"].tolist() == list(FEATURE_NAMES)
    assert demand["target_name"].item() == "demand_target"
    assert risk["y"].tolist() == [0, 1, 0, 0]
