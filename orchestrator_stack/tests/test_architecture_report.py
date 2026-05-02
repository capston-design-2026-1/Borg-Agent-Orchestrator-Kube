from datetime import datetime, timezone

from orchestrator.layer6.architecture_report import architecture_status_markdown, write_architecture_status_report


def test_architecture_status_markdown_reports_current_gaps():
    report = architecture_status_markdown(generated_at=datetime(2026, 5, 1, 12, 0, tzinfo=timezone.utc))

    assert "Generated (KST): 2026-05-01 21:00" in report
    assert "Trace-derived brain datasets" in report
    assert "export-brain-datasets" in report
    assert "Live Kind/AIOpsLab validation" in report
    assert "Prometheus/node-exporter enrichment covers all 15 rows" in report
    assert "k8s_target_port-misconfig-*" in report
    assert "+18.01204388800005" in report
    assert "scale_pod_zero_social_net-*" in report
    assert "+20.700478922666548" in report
    assert "passes `3/3` held-out entries" in report
    assert "202605030205_repeated_seed_ppo_summary.json" in report
    assert "passes `3/3` seeds on all three reported families" in report
    assert "Ablation evidence matrix" in report
    assert "202605030225_controlled_ablation_repeated_seed_summary.json" in report
    assert "+10.428703703703718" in report
    assert "202605030240_evaluation_statistics.json" in report
    assert "86 passed" in report


def test_write_architecture_status_report_uses_requested_path(tmp_path):
    out = tmp_path / "architecture.md"

    result = write_architecture_status_report(
        out_path=out,
        generated_at=datetime(2026, 5, 1, 12, 0, tzinfo=timezone.utc),
    )

    assert result == out
    assert out.read_text(encoding="utf-8").startswith("# Orchestrator Architecture Status")
