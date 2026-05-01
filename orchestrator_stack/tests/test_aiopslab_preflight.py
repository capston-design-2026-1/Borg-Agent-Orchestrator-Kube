from pathlib import Path

from orchestrator.layer2.aiopslab_preflight import aiopslab_preflight, write_aiopslab_preflight_report


def test_aiopslab_preflight_blocks_incompatible_python():
    report = aiopslab_preflight(python_version=(3, 13, 12), python_executable="/tmp/python")

    assert report["status"] == "blocked"
    assert report["compatible_python"] is False
    assert report["aiopslab_package_available"] is False
    assert report["blockers"] == ["AIOpsLab requires Python >=3.11,<3.13"]


def test_aiopslab_preflight_checks_package_when_python_is_compatible():
    report = aiopslab_preflight(python_version=(3, 12, 8), import_name="json")

    assert report["status"] == "ready"
    assert report["compatible_python"] is True
    assert report["aiopslab_package_available"] is True
    assert report["blockers"] == []


def test_write_aiopslab_preflight_report_writes_json(tmp_path: Path):
    out = write_aiopslab_preflight_report({"status": "blocked"}, tmp_path / "preflight.json")

    assert out.read_text(encoding="utf-8") == '{\n  "status": "blocked"\n}'
