import json

from orchestrator.layer6.evaluation_statistics import (
    build_evaluation_statistics_report,
    mean_std_ci95,
    write_evaluation_statistics_report,
)


def test_mean_std_ci95_uses_student_t_interval_for_three_values():
    stats = mean_std_ci95([1.0, 2.0, 3.0])

    assert stats["n"] == 3
    assert stats["mean"] == 2.0
    assert stats["std"] == 1.0
    assert round(stats["ci95_half_width"], 6) == 2.484138


def test_build_evaluation_statistics_report_summarizes_seed_artifacts(tmp_path):
    repeated = tmp_path / "repeated.json"
    repeated.write_text(
        json.dumps(
            {
                "sets": [
                    {
                        "evaluation_set": "family_a",
                        "pass_rate": 1.0,
                        "runs": [
                            {"delta_vs_heuristic": 1.0},
                            {"delta_vs_heuristic": 2.0},
                            {"delta_vs_heuristic": 3.0},
                        ],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    controlled = tmp_path / "controlled.json"
    controlled.write_text(
        json.dumps(
            {
                "rows": [
                    {"variant": "baseline", "delta_vs_heuristic": 1.0},
                    {"variant": "baseline", "delta_vs_heuristic": 2.0},
                    {"variant": "baseline", "delta_vs_heuristic": 3.0},
                ],
                "variant_summaries": [{"variant": "baseline", "pass_rate": 1.0}],
                "effects_by_seed": [
                    {
                        "sla_preservation_delta_gain_with_predictor": 1.0,
                        "predictor_runtime_delta_change_without_sla_preservation": -1.0,
                    },
                    {
                        "sla_preservation_delta_gain_with_predictor": 2.0,
                        "predictor_runtime_delta_change_without_sla_preservation": -2.0,
                    },
                    {
                        "sla_preservation_delta_gain_with_predictor": 3.0,
                        "predictor_runtime_delta_change_without_sla_preservation": -3.0,
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    report = build_evaluation_statistics_report(
        repeated_seed_summary_path=repeated,
        controlled_ablation_summary_path=controlled,
    )
    outputs = write_evaluation_statistics_report(report, tmp_path / "stats.json", tmp_path / "stats.md")

    assert report["repeated_seed_policy_deltas"][0]["mean"] == 2.0
    assert report["controlled_ablation_effects"][0]["mean"] == 2.0
    assert outputs["markdown"].endswith("stats.md")
    assert (tmp_path / "stats.md").read_text(encoding="utf-8").startswith("# Evaluation Statistics")
