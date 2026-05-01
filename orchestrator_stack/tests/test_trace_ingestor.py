import json

import pytest

from orchestrator.layer1.trace_ingestor import load_trace_rows


def _sample_trace_row() -> dict:
    return {
        "timestamp": 1700000000,
        "nodes": [{"node_id": "n1", "cpu_util": 0.5, "mem_util": 0.4, "disk_util": 0.2, "net_util": 0.1}],
        "tasks": [{"task_id": "t1", "node_id": "n1", "urgency": 0.8, "queue_priority": 2, "alive": True}],
        "queue_length": 1,
        "energy_price": 0.12,
        "sla_violations": 0,
        "completed_tasks": 2,
        "energy_watts": 180.0,
    }


def test_load_trace_rows_rejects_missing_required_keys(tmp_path):
    path = tmp_path / "trace.json"
    path.write_text(json.dumps([{"timestamp": 1, "nodes": []}]), encoding="utf-8")

    with pytest.raises(ValueError, match="missing required key 'tasks'"):
        load_trace_rows(path)


def test_load_trace_rows_jsonl_parses_and_validates(tmp_path):
    path = tmp_path / "trace.jsonl"
    rows = [_sample_trace_row(), {**_sample_trace_row(), "timestamp": 1700000060}]
    path.write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")

    loaded = load_trace_rows(path)
    assert len(loaded) == 2
    assert loaded[1]["timestamp"] == 1700000060


def test_load_trace_rows_jsonl_reports_decode_line(tmp_path):
    path = tmp_path / "trace.jsonl"
    path.write_text(f"{json.dumps(_sample_trace_row())}\n{{bad-json}}\n", encoding="utf-8")

    with pytest.raises(ValueError, match="line 2"):
        load_trace_rows(path)


def test_load_trace_rows_rejects_negative_queue_length(tmp_path):
    path = tmp_path / "trace.json"
    bad = _sample_trace_row()
    bad["queue_length"] = -1
    path.write_text(json.dumps([bad]), encoding="utf-8")

    with pytest.raises(ValueError, match="queue_length.*non-negative"):
        load_trace_rows(path)


def test_load_trace_rows_rejects_invalid_task_alive_literal(tmp_path):
    path = tmp_path / "trace.json"
    bad = _sample_trace_row()
    bad["tasks"][0]["alive"] = "sometimes"
    path.write_text(json.dumps([bad]), encoding="utf-8")

    with pytest.raises(ValueError, match="field 'alive' must be bool-like"):
        load_trace_rows(path)


def test_load_trace_rows_rejects_negative_live_reward_metrics(tmp_path):
    path = tmp_path / "trace.json"
    bad = _sample_trace_row()
    bad["sla_violations"] = -1
    path.write_text(json.dumps([bad]), encoding="utf-8")

    with pytest.raises(ValueError, match="sla_violations.*non-negative"):
        load_trace_rows(path)


def test_load_trace_rows_rejects_missing_source(tmp_path):
    path = tmp_path / "missing.json"

    with pytest.raises(ValueError, match="Trace source not found"):
        load_trace_rows(path)
