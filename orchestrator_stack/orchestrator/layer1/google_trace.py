from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from typing import Any, Iterable

from orchestrator.layer1.trace_ingestor import validate_trace_rows

TIMESTAMP_KEYS = ("timestamp", "ts", "time")
FRAME_KEYS = ("frame_index", "frame", "window_index")
OBSERVED_NODE_KEYS = ("observed_nodes", "node_count", "nodes")
ACTIVE_TASK_KEYS = ("active_tasks", "running_tasks", "task_count", "tasks")
ARRIVING_JOB_KEYS = ("arriving_jobs", "queued_jobs", "pending_tasks", "queue_length")
MEAN_CPU_KEYS = ("mean_cpu_util", "avg_cpu_util", "cpu_util")
STD_CPU_KEYS = ("std_cpu_util", "cpu_util_std")
MAX_CPU_KEYS = ("max_cpu_util", "peak_cpu_util")
MEAN_MEM_KEYS = ("mean_mem_util", "avg_mem_util", "mem_util")
MAX_MEM_KEYS = ("max_mem_util", "peak_mem_util")


def _finite_float(value: Any, default: float = 0.0) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return default
    return parsed if math.isfinite(parsed) else default


def _int_value(value: Any, default: int = 0) -> int:
    try:
        parsed = int(float(value))
    except (TypeError, ValueError):
        return default
    return parsed


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def _first(row: dict[str, Any], keys: Iterable[str], default: Any = None) -> Any:
    for key in keys:
        if key in row and row[key] not in (None, ""):
            return row[key]
    return default


def _read_json(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        for key in ("frames", "rows", "data"):
            if isinstance(payload.get(key), list):
                payload = payload[key]
                break
    if not isinstance(payload, list):
        raise ValueError(f"Google Trace source {path} must contain a top-level list or a frames/rows/data list.")
    return [_ensure_row(row, index, source=path) for index, row in enumerate(payload)]


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            rows.append(_ensure_row(json.loads(line), line_number - 1, source=path))
        except json.JSONDecodeError as exc:
            raise ValueError(f"Failed to parse Google Trace JSONL in {path} at line {line_number}: {exc}") from exc
    return rows


def _read_csv(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def _read_parquet(path: Path) -> list[dict[str, Any]]:
    try:
        import pyarrow.parquet as pq
    except ModuleNotFoundError as exc:
        raise ValueError("Reading Google Trace Parquet frames requires pyarrow; install orchestrator_stack/requirements.txt.") from exc

    table = pq.read_table(path)
    return [dict(row) for row in table.to_pylist()]


def _ensure_row(row: Any, row_index: int, *, source: Path) -> dict[str, Any]:
    if not isinstance(row, dict):
        raise ValueError(f"Google Trace contract error: {source} row[{row_index}] must be an object.")
    return dict(row)


def load_google_trace_frames(path: str | Path, *, limit: int | None = None, offset: int = 0) -> list[dict[str, Any]]:
    source = Path(path)
    if not source.exists() or not source.is_file():
        raise ValueError(f"Google Trace source not found: {source}")
    if offset < 0:
        raise ValueError("offset must be non-negative.")
    if limit is not None and limit <= 0:
        raise ValueError("limit must be positive when provided.")

    suffix = source.suffix.lower()
    if suffix == ".json":
        rows = _read_json(source)
    elif suffix == ".jsonl":
        rows = _read_jsonl(source)
    elif suffix == ".csv":
        rows = _read_csv(source)
    elif suffix == ".parquet":
        rows = _read_parquet(source)
    else:
        raise ValueError(f"Unsupported Google Trace frame format for {source}. Expected .json, .jsonl, .csv, or .parquet.")

    if limit is None:
        return rows[offset:]
    return rows[offset : offset + limit]


def _validate_frame(row: dict[str, Any], row_index: int) -> None:
    required_groups = {
        "timestamp/ts": TIMESTAMP_KEYS,
        "observed_nodes/node_count": OBSERVED_NODE_KEYS,
        "active_tasks/task_count": ACTIVE_TASK_KEYS,
        "mean_cpu_util/cpu_util": MEAN_CPU_KEYS,
        "mean_mem_util/mem_util": MEAN_MEM_KEYS,
    }
    missing = [label for label, keys in required_groups.items() if _first(row, keys) is None]
    if missing:
        raise ValueError(f"Google Trace contract error: row[{row_index}] missing {', '.join(missing)}.")


def _scaled_count(row: dict[str, Any], key: str, observed_nodes: int, emitted_nodes: int) -> int:
    raw = max(0, _int_value(row.get(key), 0))
    if observed_nodes <= emitted_nodes:
        return min(raw, emitted_nodes)
    return min(emitted_nodes, round(raw * (emitted_nodes / max(1, observed_nodes))))


def _profile_counts(row: dict[str, Any], observed_nodes: int, emitted_nodes: int) -> dict[str, int]:
    counts = {
        "hot": _scaled_count(row, "hot_nodes", observed_nodes, emitted_nodes),
        "cold": _scaled_count(row, "cold_nodes", observed_nodes, emitted_nodes),
        "dense": _scaled_count(row, "dense_nodes", observed_nodes, emitted_nodes),
        "empty": _scaled_count(row, "empty_nodes", observed_nodes, emitted_nodes),
    }
    assigned = sum(counts.values())
    counts["normal"] = max(0, emitted_nodes - assigned)
    if assigned > emitted_nodes:
        overflow = assigned - emitted_nodes
        for key in ("empty", "cold", "dense", "hot"):
            take = min(overflow, counts[key])
            counts[key] -= take
            overflow -= take
            if overflow <= 0:
                break
        counts["normal"] = 0
    return counts


def _node_profiles(counts: dict[str, int]) -> list[str]:
    profiles: list[str] = []
    for profile in ("hot", "dense", "normal", "cold", "empty"):
        profiles.extend([profile] * max(0, counts.get(profile, 0)))
    return profiles


def _nodes_for_frame(row: dict[str, Any], row_index: int, *, max_nodes: int) -> list[dict[str, Any]]:
    observed_nodes = max(1, _int_value(_first(row, OBSERVED_NODE_KEYS), 1))
    emitted_nodes = max(1, min(max_nodes, observed_nodes))
    counts = _profile_counts(row, observed_nodes, emitted_nodes)
    profiles = _node_profiles(counts)[:emitted_nodes]
    profiles.extend(["normal"] * (emitted_nodes - len(profiles)))

    mean_cpu = _clamp(_finite_float(_first(row, MEAN_CPU_KEYS), 0.0))
    std_cpu = _clamp(_finite_float(_first(row, STD_CPU_KEYS), 0.08), 0.0, 0.5)
    max_cpu = max(mean_cpu, _clamp(_finite_float(_first(row, MAX_CPU_KEYS), mean_cpu)))
    mean_mem = _clamp(_finite_float(_first(row, MEAN_MEM_KEYS), 0.0))
    max_mem = max(mean_mem, _clamp(_finite_float(_first(row, MAX_MEM_KEYS), mean_mem)))

    nodes: list[dict[str, Any]] = []
    for index, profile in enumerate(profiles):
        if profile == "hot":
            cpu = max(mean_cpu + std_cpu, max_cpu * 0.94, 0.86)
            mem = max(mean_mem + (std_cpu * 0.5), max_mem * 0.82, 0.72)
        elif profile == "dense":
            cpu = max(mean_cpu + std_cpu * 0.35, 0.64)
            mem = max(mean_mem + std_cpu * 0.45, 0.72)
        elif profile == "cold":
            cpu = min(mean_cpu * 0.45, 0.18)
            mem = min(mean_mem * 0.55, 0.24)
        elif profile == "empty":
            cpu = min(mean_cpu * 0.12, 0.04)
            mem = min(mean_mem * 0.20, 0.08)
        else:
            drift = ((index % 5) - 2) * std_cpu * 0.18
            cpu = mean_cpu + drift
            mem = mean_mem - drift * 0.5
        cpu = _clamp(cpu)
        mem = _clamp(mem)
        nodes.append(
            {
                "node_id": f"gtrace-node-{row_index:05d}-{index:03d}",
                "cpu_util": round(cpu, 6),
                "mem_util": round(mem, 6),
                "disk_util": round(_clamp((cpu * 0.28) + (mem * 0.22)), 6),
                "net_util": round(_clamp(cpu * 0.34), 6),
                "power_state": "sleep" if profile == "empty" else "on",
                "source_profile": profile,
            }
        )
    return nodes


def _tasks_for_frame(row: dict[str, Any], row_index: int, nodes: list[dict[str, Any]], *, max_tasks_per_row: int) -> list[dict[str, Any]]:
    active_tasks = max(0, _int_value(_first(row, ACTIVE_TASK_KEYS), 0))
    arriving_jobs = max(0, _int_value(_first(row, ARRIVING_JOB_KEYS), 0))
    task_count = min(max_tasks_per_row, active_tasks + arriving_jobs)
    if task_count <= 0:
        return []

    top_cpu = _clamp(_finite_float(row.get("top_task_cpu"), _finite_float(_first(row, MEAN_CPU_KEYS), 0.5)))
    top_mem = _clamp(_finite_float(row.get("top_task_memory"), _finite_float(_first(row, MEAN_MEM_KEYS), 0.5)))
    node_ids = [str(node["node_id"]) for node in sorted(nodes, key=lambda node: node.get("cpu_util", 0.0), reverse=True)]
    tasks: list[dict[str, Any]] = []
    for index in range(task_count):
        queued = index >= active_tasks
        if queued:
            node_id = "queue"
            urgency = max(top_cpu, top_mem, 0.55)
        else:
            node_id = node_ids[index % max(1, len(node_ids))]
            urgency = max(top_cpu * (1.0 - min(index, 12) * 0.025), top_mem * 0.75, 0.2)
        tasks.append(
            {
                "task_id": f"gtrace-task-{row_index:05d}-{index:04d}",
                "node_id": node_id,
                "urgency": round(_clamp(urgency), 6),
                "queue_priority": 3 if queued or urgency >= 0.8 else 2 if urgency >= 0.55 else 1,
                "alive": True,
            }
        )
    return tasks


def _frame_timestamp(row: dict[str, Any], row_index: int, *, interval_seconds: int) -> int:
    timestamp = _first(row, TIMESTAMP_KEYS)
    if timestamp is not None:
        return max(0, _int_value(timestamp, row_index * interval_seconds))
    frame = _int_value(_first(row, FRAME_KEYS), row_index)
    return max(0, frame * interval_seconds)


def google_trace_frames_to_trace(
    rows: list[dict[str, Any]],
    *,
    max_nodes: int = 32,
    max_tasks_per_row: int = 64,
    interval_seconds: int = 300,
    source_label: str = "google_cluster_trace",
    cell: str | None = None,
) -> list[dict[str, Any]]:
    if not rows:
        raise ValueError("Google Trace source contains zero rows.")
    if max_nodes <= 0:
        raise ValueError("max_nodes must be positive.")
    if max_tasks_per_row <= 0:
        raise ValueError("max_tasks_per_row must be positive.")
    if interval_seconds <= 0:
        raise ValueError("interval_seconds must be positive.")

    trace: list[dict[str, Any]] = []
    for row_index, row in enumerate(rows):
        _validate_frame(row, row_index)
        nodes = _nodes_for_frame(row, row_index, max_nodes=max_nodes)
        tasks = _tasks_for_frame(row, row_index, nodes, max_tasks_per_row=max_tasks_per_row)
        observed_nodes = max(1, _int_value(_first(row, OBSERVED_NODE_KEYS), len(nodes)))
        active_tasks = max(0, _int_value(_first(row, ACTIVE_TASK_KEYS), 0))
        arriving_jobs = max(0, _int_value(_first(row, ARRIVING_JOB_KEYS), 0))
        mean_cpu = _clamp(_finite_float(_first(row, MEAN_CPU_KEYS), 0.0))
        mean_mem = _clamp(_finite_float(_first(row, MEAN_MEM_KEYS), 0.0))
        hot_nodes = max(0, _int_value(row.get("hot_nodes"), 0))
        completed_tasks = max(0, min(active_tasks, int(active_tasks * max(0.05, 1.0 - mean_cpu * 0.28))))
        sla_violations = max(0, hot_nodes + int(max(0.0, mean_cpu - 0.82) * observed_nodes) + int(max(0, arriving_jobs - completed_tasks) * 0.08))
        energy_watts = max(0.0, observed_nodes * (72.0 + (mean_cpu * 118.0) + (mean_mem * 42.0)))
        trace.append(
            {
                "timestamp": _frame_timestamp(row, row_index, interval_seconds=interval_seconds),
                "nodes": nodes,
                "tasks": tasks,
                "queue_length": max(0, arriving_jobs),
                "energy_price": 0.1,
                "task_death": False,
                "sla_violations": sla_violations,
                "completed_tasks": completed_tasks,
                "energy_watts": round(energy_watts, 6),
                "source": source_label,
                "source_platform": "google_trace",
                "telemetry_sources": ["google_cluster_trace"],
                "frame_index": _int_value(_first(row, FRAME_KEYS), row_index),
                "observed_nodes": observed_nodes,
                "active_tasks": active_tasks,
                "arriving_jobs": arriving_jobs,
                "distinct_collections": max(0, _int_value(row.get("distinct_collections"), 0)),
                "cell": cell or row.get("cell") or row.get("collection_cell"),
            }
        )
    validate_trace_rows(trace, source=Path("<google-trace-adapter>"))
    return trace


def build_google_trace_file(
    frames_path: str | Path,
    out_path: str | Path,
    *,
    limit: int | None = None,
    offset: int = 0,
    max_nodes: int = 32,
    max_tasks_per_row: int = 64,
    interval_seconds: int = 300,
    source_label: str = "google_cluster_trace",
    cell: str | None = None,
) -> Path:
    rows = load_google_trace_frames(frames_path, limit=limit, offset=offset)
    trace = google_trace_frames_to_trace(
        rows,
        max_nodes=max_nodes,
        max_tasks_per_row=max_tasks_per_row,
        interval_seconds=interval_seconds,
        source_label=source_label,
        cell=cell,
    )
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(trace, indent=2, sort_keys=True, allow_nan=False), encoding="utf-8")
    return out
