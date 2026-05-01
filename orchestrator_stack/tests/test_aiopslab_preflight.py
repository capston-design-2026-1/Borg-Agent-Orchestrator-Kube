from pathlib import Path

from orchestrator.layer2.aiopslab_preflight import aiopslab_preflight, write_aiopslab_preflight_report


def test_aiopslab_preflight_blocks_incompatible_python():
    report = aiopslab_preflight(python_version=(3, 13, 12), python_executable="/tmp/python")

    assert report["status"] == "blocked"
    assert report["compatible_python"] is False
    assert report["aiopslab_package_available"] is False
    assert report["kube_config_available"] is False
    assert report["import_errors"] == {}
    assert report["blockers"] == ["AIOpsLab requires Python >=3.11,<3.13"]


def test_aiopslab_preflight_checks_package_when_python_is_compatible(tmp_path):
    kube_config = tmp_path / "config"
    kube_config.write_text("apiVersion: v1\n", encoding="utf-8")

    report = aiopslab_preflight(
        python_version=(3, 12, 8),
        import_name="json",
        import_checks=("json",),
        kube_config=str(kube_config),
    )

    assert report["status"] == "ready"
    assert report["compatible_python"] is True
    assert report["aiopslab_package_available"] is True
    assert report["kube_config_available"] is True
    assert report["import_errors"] == {}
    assert report["blockers"] == []


def test_aiopslab_preflight_reports_import_check_failures(tmp_path):
    report = aiopslab_preflight(
        python_version=(3, 12, 8),
        import_name="json",
        import_checks=("json", "definitely_missing_aiopslab_module"),
        kube_config=str(tmp_path / "missing-kube-config"),
    )

    assert report["status"] == "blocked"
    assert "definitely_missing_aiopslab_module" in report["import_errors"]
    assert any("Kubernetes config not found" in blocker for blocker in report["blockers"])
    assert any("import check failed for definitely_missing_aiopslab_module" in blocker for blocker in report["blockers"])


def test_write_aiopslab_preflight_report_writes_json(tmp_path: Path):
    out = write_aiopslab_preflight_report({"status": "blocked"}, tmp_path / "preflight.json")

    assert out.read_text(encoding="utf-8") == '{\n  "status": "blocked"\n}'
