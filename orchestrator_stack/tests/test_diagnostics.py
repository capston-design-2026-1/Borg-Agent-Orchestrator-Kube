from orchestrator.layer3 import diagnostics
from orchestrator.layer3.diagnostics import (
    _feature_importance,
    _safe_contribution_summary,
    calibration_bins,
    calibration_summary,
    optimize_binary_threshold,
)


def test_optimize_binary_threshold_returns_best_f1_cutoff():
    result = optimize_binary_threshold([0, 0, 1, 1], [0.1, 0.2, 0.8, 0.9])

    assert 0.2 < result["threshold"] <= 0.8
    assert result["f1"] == 1.0
    assert result["precision"] == 1.0
    assert result["recall"] == 1.0


def test_calibration_bins_reports_predicted_and_observed_rates():
    bins = calibration_bins([0, 1, 1], [0.1, 0.6, 0.8], bins=2)

    assert bins[0]["count"] == 1
    assert bins[0]["observed_rate"] == 0.0
    assert bins[1]["count"] == 2
    assert bins[1]["observed_rate"] == 1.0


def test_calibration_summary_reports_brier_and_error_rates():
    summary = calibration_summary([0, 1], [0.25, 0.75], bins=2)

    assert summary["brier_score"] == 0.0625
    assert summary["expected_calibration_error"] == 0.25
    assert summary["max_calibration_error"] == 0.25


def test_feature_importance_uses_feature_names_when_available():
    class Booster:
        def get_score(self, importance_type):
            return {"f0": 2.0, "f2": 3.0}

    result = _feature_importance(Booster(), feature_names=["cpu_util", "mem_util", "disk_util"])

    assert result["weight"] == {"cpu_util": 2.0, "disk_util": 3.0}


def test_safe_contribution_summary_reports_skipped_on_xgboost_error(monkeypatch):
    def broken_summary(booster, x, feature_names=None):
        raise RuntimeError("shape mismatch")

    monkeypatch.setattr(diagnostics, "_contribution_summary", broken_summary)

    result = _safe_contribution_summary(object(), object())

    assert result["status"] == "skipped"
    assert "shape mismatch" in result["reason"]
