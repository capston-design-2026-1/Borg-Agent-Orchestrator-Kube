import json

from orchestrator.layer6.policy_gate_suite import evaluate_policy_gate_suite, write_policy_gate_suite_report


def test_evaluate_policy_gate_suite_requires_all_heldout_entries_to_pass(tmp_path):
    trace = tmp_path / "trace.json"
    trace.write_text(json.dumps([{"timestamp": 1}, {"timestamp": 2}]), encoding="utf-8")
    passing_policy = tmp_path / "passing_policy.json"
    passing_policy.write_text(
        json.dumps(
            {
                "policy_vs_heuristic": {
                    "policy_episode_reward_mean": 5.0,
                    "heuristic_total_score": 3.0,
                    "delta_vs_heuristic": 2.0,
                    "beats_heuristic": True,
                }
            }
        ),
        encoding="utf-8",
    )
    failing_policy = tmp_path / "failing_policy.json"
    failing_policy.write_text(
        json.dumps({"policy_vs_heuristic": {"beats_heuristic": False}}),
        encoding="utf-8",
    )
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "suite_name": "unit",
                "entries": [
                    {"family": "a", "slice": "x", "trace_path": str(trace), "policy_gate_path": str(passing_policy)},
                    {"family": "b", "slice": "y", "trace_path": str(trace), "policy_gate_path": str(failing_policy)},
                ],
            }
        ),
        encoding="utf-8",
    )

    report = evaluate_policy_gate_suite(manifest)

    assert report["status"] == "failed"
    assert report["heldout_entries"] == 2
    assert report["heldout_passes"] == 1
    assert report["entries"][0]["trace_rows"] == 2


def test_write_policy_gate_suite_report_writes_json(tmp_path):
    out = tmp_path / "suite.json"

    result = write_policy_gate_suite_report({"status": "passed"}, out)

    assert result == out
    assert json.loads(out.read_text(encoding="utf-8"))["status"] == "passed"
