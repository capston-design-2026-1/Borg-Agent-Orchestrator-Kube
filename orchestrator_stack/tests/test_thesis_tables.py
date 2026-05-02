import json

from orchestrator.layer6.thesis_tables import collect_thesis_evaluation_tables, write_thesis_evaluation_tables


def test_collect_thesis_evaluation_tables_extracts_live_audit_and_policy(tmp_path):
    eval_dir = tmp_path / "evals"
    eval_dir.mkdir()
    (eval_dir / "202605022020_aiopslab_mitigation_prometheus_live_summary.json").write_text(
        json.dumps(
            {
                "problem_id": "misconfig_app_hotel_res-mitigation-1",
                "final_state": "SubmissionStatus.VALID_SUBMISSION",
                "trace_rows": 15,
                "capture_errors": [],
                "results": {"success": True, "TTM": 2.9},
            }
        ),
        encoding="utf-8",
    )
    (eval_dir / "202605022020_aiopslab_mitigation_prometheus_reward_audit.json").write_text(
        json.dumps(
            {
                "steps": 14,
                "telemetry_coverage": 1.0,
                "max_sla_violations": 1,
                "max_completed_tasks": 2,
                "max_energy_watts": 128.083859,
                "actions": {"replicate": 13, "dvfs": 1},
                "telemetry_reward_delta": {"weighted_total": -665.8760897080001},
            }
        ),
        encoding="utf-8",
    )
    (eval_dir / "202605022025_aiopslab_prometheus_mitigation_train_policy.json").write_text(
        json.dumps(
            {
                "status": "trained",
                "stage_count": 3,
                "policy_vs_heuristic": {
                    "policy_episode_reward_mean": -663.0434828466666,
                    "heuristic_total_score": -740.276089708,
                    "delta_vs_heuristic": 77.23260686133335,
                    "beats_heuristic": True,
                },
            }
        ),
        encoding="utf-8",
    )

    tables = collect_thesis_evaluation_tables(eval_dir)

    assert tables["live_tasks"][0]["success"] is True
    assert tables["reward_audits"][0]["actions"] == {"replicate": 13, "dvfs": 1}
    assert tables["policy_gates"][0]["beats_heuristic"] is True


def test_write_thesis_evaluation_tables_writes_markdown_and_csv(tmp_path):
    eval_dir = tmp_path / "evals"
    eval_dir.mkdir()
    (eval_dir / "202605022025_aiopslab_prometheus_mitigation_train_policy.json").write_text(
        json.dumps({"status": "trained", "policy_vs_heuristic": {"beats_heuristic": True}}),
        encoding="utf-8",
    )

    outputs = write_thesis_evaluation_tables(
        evaluation_dir=eval_dir,
        out_md=tmp_path / "tables.md",
        out_csv_dir=tmp_path / "csv",
    )

    assert outputs["markdown"].endswith("tables.md")
    assert (tmp_path / "tables.md").read_text(encoding="utf-8").startswith("# Thesis Evaluation Tables")
    assert (tmp_path / "csv" / "policy_gates.csv").read_text(encoding="utf-8").startswith("label,status")
