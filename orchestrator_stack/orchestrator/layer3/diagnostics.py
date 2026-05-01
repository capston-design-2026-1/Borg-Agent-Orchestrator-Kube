from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _require_numpy():
    import numpy as np

    return np


def _require_xgboost():
    import xgboost as xgb

    return xgb


def calibration_bins(y_true: Any, y_score: Any, *, bins: int = 10) -> list[dict[str, float | int]]:
    np = _require_numpy()
    true = np.asarray(y_true, dtype=float)
    score = np.asarray(y_score, dtype=float).clip(0.0, 1.0)
    edges = np.linspace(0.0, 1.0, bins + 1)
    output = []
    for idx in range(bins):
        left = edges[idx]
        right = edges[idx + 1]
        mask = (score >= left) & (score <= right if idx == bins - 1 else score < right)
        count = int(mask.sum())
        output.append(
            {
                "bin_start": float(left),
                "bin_end": float(right),
                "count": count,
                "predicted_rate": float(score[mask].mean()) if count else 0.0,
                "observed_rate": float(true[mask].mean()) if count else 0.0,
            }
        )
    return output


def calibration_summary(y_true: Any, y_score: Any, *, bins: int = 10) -> dict[str, float]:
    np = _require_numpy()
    true = np.asarray(y_true, dtype=float)
    score = np.asarray(y_score, dtype=float).clip(0.0, 1.0)
    binned = calibration_bins(true, score, bins=bins)
    row_count = max(1, int(true.size))
    expected_error = 0.0
    max_error = 0.0
    for item in binned:
        gap = abs(float(item["predicted_rate"]) - float(item["observed_rate"]))
        expected_error += (int(item["count"]) / row_count) * gap
        max_error = max(max_error, gap)
    return {
        "brier_score": float(np.mean((score - true) ** 2)) if row_count else 0.0,
        "expected_calibration_error": float(expected_error),
        "max_calibration_error": float(max_error),
    }


def optimize_binary_threshold(y_true: Any, y_score: Any) -> dict[str, float]:
    np = _require_numpy()
    true = np.asarray(y_true, dtype=int)
    score = np.asarray(y_score, dtype=float)
    best = {"threshold": 0.5, "f1": -1.0, "precision": 0.0, "recall": 0.0}
    for threshold in np.linspace(0.05, 0.95, 91):
        pred = score >= threshold
        tp = float(((pred == 1) & (true == 1)).sum())
        fp = float(((pred == 1) & (true == 0)).sum())
        fn = float(((pred == 0) & (true == 1)).sum())
        precision = tp / max(1.0, tp + fp)
        recall = tp / max(1.0, tp + fn)
        f1 = (2.0 * precision * recall) / max(1e-12, precision + recall)
        if f1 > best["f1"]:
            best = {
                "threshold": float(threshold),
                "f1": float(f1),
                "precision": float(precision),
                "recall": float(recall),
            }
    return best


def _feature_name(key: str, feature_names: Any | None = None) -> str:
    if feature_names is None or not key.startswith("f"):
        return key
    try:
        idx = int(key[1:])
        if 0 <= idx < len(feature_names):
            return str(feature_names[idx])
    except (TypeError, ValueError):
        return key
    return key


def _feature_importance(booster: Any, feature_names: Any | None = None) -> dict[str, dict[str, float]]:
    return {
        importance_type: {
            _feature_name(str(key), feature_names): float(value)
            for key, value in booster.get_score(importance_type=importance_type).items()
        }
        for importance_type in ("weight", "gain", "cover")
    }


def _contribution_summary(booster: Any, x: Any, feature_names: Any | None = None) -> dict[str, float]:
    np = _require_numpy()
    xgb = _require_xgboost()
    contributions = booster.predict(xgb.DMatrix(x), pred_contribs=True)
    mean_abs = np.abs(contributions).mean(axis=0)
    return {
        ("bias" if idx == len(mean_abs) - 1 else _feature_name(f"f{idx}", feature_names)): float(value)
        for idx, value in enumerate(mean_abs.tolist())
    }


def _safe_contribution_summary(booster: Any, x: Any, feature_names: Any | None = None) -> dict[str, Any]:
    try:
        return {"status": "ok", "mean_abs": _contribution_summary(booster, x, feature_names=feature_names)}
    except Exception as exc:
        return {"status": "skipped", "reason": str(exc)}


def diagnose_xgboost_model(
    *,
    model_path: str | Path,
    x: Any,
    y: Any | None = None,
    task: str,
    feature_names: Any | None = None,
) -> dict[str, Any]:
    xgb = _require_xgboost()
    booster = xgb.Booster()
    booster.load_model(str(model_path))
    dmat = xgb.DMatrix(x)
    predictions = booster.predict(dmat)
    report: dict[str, Any] = {
        "model_path": str(model_path),
        "task": task,
        "rows": int(len(predictions)),
        "feature_names": [str(name) for name in feature_names] if feature_names is not None else [],
        "feature_importance": _feature_importance(booster, feature_names=feature_names),
        "contribution_summary": _safe_contribution_summary(booster, x, feature_names=feature_names),
    }
    if y is not None and task == "risk":
        report["threshold"] = optimize_binary_threshold(y, predictions)
        report["calibration_summary"] = calibration_summary(y, predictions)
        report["calibration_bins"] = calibration_bins(y, predictions)
    return report


def write_diagnostics_report(report: dict[str, Any], out_path: str | Path) -> Path:
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return out
