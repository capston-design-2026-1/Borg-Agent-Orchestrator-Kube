import csv
import json

import pytest

from orchestrator.layer1.google_trace import build_google_trace_file, google_trace_frames_to_trace, load_google_trace_frames
from orchestrator.layer1.trace_ingestor import load_trace_rows


def _frame() -> dict:
    return {
        "frame_index": 7,
        "ts": 1700000000,
        "observed_nodes": 100,
        "active_tasks": 240,
        "mean_cpu_util": 0.62,
        "std_cpu_util": 0.12,
        "max_cpu_util": 0.97,
        "mean_mem_util": 0.55,
        "max_mem_util": 0.91,
        "hot_nodes": 11,
        "cold_nodes": 18,
        "dense_nodes": 9,
        "empty_nodes": 20,
        "arriving_jobs": 13,
        "top_task_cpu": 0.83,
        "top_task_memory": 0.71,
        "distinct_collections": 42,
    }


def test_google_trace_frames_to_valid_orchestrator_trace():
    trace = google_trace_frames_to_trace([_frame()], max_nodes=10, max_tasks_per_row=12, cell="cell-a")

    assert len(trace) == 1
    row = trace[0]
    assert row["timestamp"] == 1700000000
    assert row["source_platform"] == "google_trace"
    assert row["telemetry_sources"] == ["google_cluster_trace"]
    assert row["cell"] == "cell-a"
    assert len(row["nodes"]) == 10
    assert len(row["tasks"]) == 12
    assert row["queue_length"] == 13
    assert row["sla_violations"] > 0
    assert row["completed_tasks"] > 0
    assert row["energy_watts"] > 0


def test_build_google_trace_file_accepts_csv_and_validates_output(tmp_path):
    frames = tmp_path / "frames.csv"
    out = tmp_path / "trace.json"
    with frames.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(_frame().keys()))
        writer.writeheader()
        writer.writerow(_frame())

    build_google_trace_file(frames, out, max_nodes=6, max_tasks_per_row=8)
    loaded = load_trace_rows(out)

    assert len(loaded) == 1
    assert len(loaded[0]["nodes"]) == 6
    assert len(loaded[0]["tasks"]) == 8


def test_load_google_trace_frames_supports_wrapped_json_with_offset_and_limit(tmp_path):
    frames = tmp_path / "frames.json"
    rows = [{**_frame(), "frame_index": 1}, {**_frame(), "frame_index": 2}, {**_frame(), "frame_index": 3}]
    frames.write_text(json.dumps({"frames": rows}), encoding="utf-8")

    loaded = load_google_trace_frames(frames, offset=1, limit=1)

    assert loaded == [rows[1]]


def test_google_trace_frames_require_core_aggregate_columns():
    bad = {"ts": 1, "observed_nodes": 3, "active_tasks": 4, "mean_cpu_util": 0.5}

    with pytest.raises(ValueError, match="mean_mem_util"):
        google_trace_frames_to_trace([bad])


def test_google_trace_rejects_empty_source():
    with pytest.raises(ValueError, match="zero rows"):
        google_trace_frames_to_trace([])
