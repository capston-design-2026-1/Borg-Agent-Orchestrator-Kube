from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol

from orchestrator.layer2.simulator import SimulatorBackend
from orchestrator.types import AgentAction, Observation, StepResult


def _require_xgboost():
    import xgboost as xgb

    return xgb


def _require_numpy():
    import numpy as np

    return np


def _feature_extractors():
    from orchestrator.layer2.feature_extractor import observation_matrix, trace_rows_to_training_matrices

    return observation_matrix, trace_rows_to_training_matrices


class ObservationPredictor(Protocol):
    def predict(self, obs: Observation) -> dict[str, float]: ...


class SafetyRiskForecast:
    def __init__(self, booster: Any):
        self.booster = booster

    @classmethod
    def load(cls, path: str | Path) -> "SafetyRiskForecast":
        xgb = _require_xgboost()
        booster = xgb.Booster()
        booster.load_model(str(path))
        return cls(booster)

    def predict(self, obs: Observation) -> dict[str, float]:
        xgb = _require_xgboost()
        observation_matrix, _ = _feature_extractors()
        x, node_ids = observation_matrix(obs)
        dmat = xgb.DMatrix(x)
        preds = self.booster.predict(dmat)
        return {node_id: float(pred) for node_id, pred in zip(node_ids, preds, strict=False)}


class ResourceDemandForecast:
    def __init__(self, booster: Any):
        self.booster = booster

    @classmethod
    def load(cls, path: str | Path) -> "ResourceDemandForecast":
        xgb = _require_xgboost()
        booster = xgb.Booster()
        booster.load_model(str(path))
        return cls(booster)

    def predict(self, obs: Observation) -> dict[str, float]:
        xgb = _require_xgboost()
        observation_matrix, _ = _feature_extractors()
        x, node_ids = observation_matrix(obs)
        dmat = xgb.DMatrix(x)
        preds = self.booster.predict(dmat)
        return {node_id: max(0.0, float(pred)) for node_id, pred in zip(node_ids, preds, strict=False)}


def enrich_observation_with_predictions(
    obs: Observation,
    *,
    risk_model: ObservationPredictor,
    demand_model: ObservationPredictor,
) -> Observation:
    obs.p_fail_scores = risk_model.predict(obs)
    obs.demand_projection = demand_model.predict(obs)
    return obs


class PredictorBackedBackend(SimulatorBackend):
    def __init__(
        self,
        backend: SimulatorBackend,
        *,
        risk_model: ObservationPredictor,
        demand_model: ObservationPredictor,
    ) -> None:
        self.backend = backend
        self.risk_model = risk_model
        self.demand_model = demand_model

    def reset(self) -> Observation:
        return enrich_observation_with_predictions(
            self.backend.reset(),
            risk_model=self.risk_model,
            demand_model=self.demand_model,
        )

    def step(self, action: AgentAction) -> StepResult:
        result = self.backend.step(action)
        result.next_observation = enrich_observation_with_predictions(
            result.next_observation,
            risk_model=self.risk_model,
            demand_model=self.demand_model,
        )
        return result


def train_safety_model(x: np.ndarray, y: np.ndarray, out_path: str | Path) -> Path:
    xgb = _require_xgboost()
    dtrain = xgb.DMatrix(x, label=y)
    params = {
        "max_depth": 6,
        "eta": 0.06,
        "subsample": 0.9,
        "colsample_bytree": 0.9,
        "objective": "binary:logistic",
        "eval_metric": "aucpr",
        "tree_method": "hist",
    }
    booster = xgb.train(params=params, dtrain=dtrain, num_boost_round=300)
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    booster.save_model(str(out))
    return out


def train_demand_model(x: np.ndarray, y: np.ndarray, out_path: str | Path) -> Path:
    xgb = _require_xgboost()
    dtrain = xgb.DMatrix(x, label=y)
    params = {
        "max_depth": 6,
        "eta": 0.06,
        "subsample": 0.9,
        "colsample_bytree": 0.9,
        "objective": "reg:squarederror",
        "tree_method": "hist",
    }
    booster = xgb.train(params=params, dtrain=dtrain, num_boost_round=300)
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    booster.save_model(str(out))
    return out


def train_models_from_trace(rows: list[dict], risk_out: str | Path, demand_out: str | Path) -> tuple[Path, Path]:
    np = _require_numpy()
    _, trace_rows_to_training_matrices = _feature_extractors()
    matrices = trace_rows_to_training_matrices(rows)
    if not isinstance(matrices.x, np.ndarray):
        raise TypeError("expected numpy-backed training matrices from trace rows")
    risk_path = train_safety_model(matrices.x, matrices.y_risk, risk_out)
    demand_path = train_demand_model(matrices.x, matrices.y_demand, demand_out)
    return risk_path, demand_path


def export_training_datasets_from_trace(
    rows: list[dict],
    risk_out: str | Path,
    demand_out: str | Path,
) -> tuple[Path, Path]:
    np = _require_numpy()
    from orchestrator.layer2.feature_extractor import FEATURE_NAMES, trace_rows_to_training_matrices

    matrices = trace_rows_to_training_matrices(rows)
    if not isinstance(matrices.x, np.ndarray):
        raise TypeError("expected numpy-backed training matrices from trace rows")

    feature_names = np.asarray(FEATURE_NAMES)
    risk_path = Path(risk_out)
    demand_path = Path(demand_out)
    risk_path.parent.mkdir(parents=True, exist_ok=True)
    demand_path.parent.mkdir(parents=True, exist_ok=True)

    np.savez(
        risk_path,
        x=matrices.x,
        y=matrices.y_risk.astype("int32"),
        feature_names=feature_names,
        target_name=np.asarray("risk_label"),
    )
    np.savez(
        demand_path,
        x=matrices.x,
        y=matrices.y_demand.astype("float32"),
        feature_names=feature_names,
        target_name=np.asarray("demand_target"),
    )
    return risk_path, demand_path
