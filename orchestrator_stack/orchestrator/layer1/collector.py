from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


METRIC_KEYS = ("cpu_util", "mem_util", "disk_util", "net_util")
TELEMETRY_REWARD_KEYS = ("sla_violations", "completed_tasks", "energy_watts")
TRUE_LITERALS = {"1", "true", "t", "yes", "y", "on"}
FALSE_LITERALS = {"0", "false", "f", "no", "n", "off"}


def _metric_value(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _bool_value(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        if value in (0, 1):
            return bool(value)
        return default
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in TRUE_LITERALS:
            return True
        if lowered in FALSE_LITERALS:
            return False
    return default


def _normalize_node(raw: dict[str, Any]) -> dict[str, Any]:
    node = {
        "node_id": str(raw.get("node_id", "unknown-node")),
        "cpu_util": _metric_value(raw.get("cpu_util")),
        "mem_util": _metric_value(raw.get("mem_util")),
        "disk_util": _metric_value(raw.get("disk_util")),
        "net_util": _metric_value(raw.get("net_util")),
        "power_state": str(raw.get("power_state", "on")),
    }
    for key in METRIC_KEYS:
        node[key] = min(1.0, max(0.0, node[key]))
    return node


def _normalize_task(raw: dict[str, Any], fallback_node_id: str) -> dict[str, Any]:
    queue_priority = raw.get("queue_priority", 1)
    try:
        parsed_queue_priority = int(queue_priority)
    except (TypeError, ValueError):
        parsed_queue_priority = 1
    return {
        "task_id": str(raw.get("task_id", "unknown-task")),
        "node_id": str(raw.get("node_id", fallback_node_id)),
        "urgency": min(1.0, max(0.0, _metric_value(raw.get("urgency", 0.5), 0.5))),
        "queue_priority": max(0, parsed_queue_priority),
        "alive": _bool_value(raw.get("alive"), default=True),
    }


def _parse_int(value: Any, *, field: str, row_index: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Schema drift: row[{row_index}] field '{field}' must be integer-like, got {value!r}.") from exc


def _parse_non_negative_int(value: Any, *, field: str, row_index: int) -> int:
    parsed = _parse_int(value, field=field, row_index=row_index)
    if parsed < 0:
        raise ValueError(f"Schema drift: row[{row_index}] field '{field}' must be non-negative, got {value!r}.")
    return parsed


def _parse_float(value: Any, *, field: str, row_index: int) -> float:
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Schema drift: row[{row_index}] field '{field}' must be numeric, got {value!r}.") from exc


def _ensure_dict_row(row: Any, row_index: int) -> dict[str, Any]:
    if not isinstance(row, dict):
        raise ValueError(f"Schema drift: row[{row_index}] must be an object, got {type(row).__name__}.")
    return row


def _validate_grouped_row(row: dict[str, Any], row_index: int) -> None:
    if "timestamp" not in row:
        raise ValueError(f"Schema drift: grouped row[{row_index}] missing 'timestamp' key.")
    _parse_int(row["timestamp"], field="timestamp", row_index=row_index)

    nodes = row.get("nodes", [])
    if not isinstance(nodes, list):
        raise ValueError(f"Schema drift: grouped row[{row_index}] field 'nodes' must be a list.")
    for node_index, node in enumerate(nodes):
        if not isinstance(node, dict):
            raise ValueError(
                f"Schema drift: grouped row[{row_index}] node[{node_index}] must be an object, got {type(node).__name__}."
            )
        if "node_id" not in node:
            raise ValueError(f"Schema drift: grouped row[{row_index}] node[{node_index}] missing 'node_id' key.")

    tasks = row.get("tasks", [])
    if not isinstance(tasks, list):
        raise ValueError(f"Schema drift: grouped row[{row_index}] field 'tasks' must be a list.")
    for task_index, task in enumerate(tasks):
        if not isinstance(task, dict):
            raise ValueError(
                f"Schema drift: grouped row[{row_index}] task[{task_index}] must be an object, got {type(task).__name__}."
            )
        for key in ("task_id", "node_id"):
            if key not in task:
                raise ValueError(f"Schema drift: grouped row[{row_index}] task[{task_index}] missing '{key}' key.")
        if "queue_priority" in task:
            _parse_non_negative_int(task["queue_priority"], field="queue_priority", row_index=row_index)
        if "urgency" in task:
            _parse_float(task["urgency"], field="urgency", row_index=row_index)
    if "queue_length" in row:
        _parse_non_negative_int(row["queue_length"], field="queue_length", row_index=row_index)
    if "energy_price" in row:
        _parse_float(row["energy_price"], field="energy_price", row_index=row_index)
    if "sla_violations" in row:
        _parse_non_negative_int(row["sla_violations"], field="sla_violations", row_index=row_index)
    if "completed_tasks" in row:
        _parse_non_negative_int(row["completed_tasks"], field="completed_tasks", row_index=row_index)
    if "energy_watts" in row:
        parsed_energy_watts = _parse_float(row["energy_watts"], field="energy_watts", row_index=row_index)
        if parsed_energy_watts < 0:
            raise ValueError(f"Schema drift: row[{row_index}] field 'energy_watts' must be non-negative, got {row['energy_watts']!r}.")


def _validate_flat_row(row: dict[str, Any], row_index: int) -> None:
    for key in ("timestamp", "node_id"):
        if key not in row:
            raise ValueError(f"Schema drift: flat row[{row_index}] missing mandatory key '{key}'.")
    _parse_int(row["timestamp"], field="timestamp", row_index=row_index)
    if not any(k in row for k in METRIC_KEYS):
        raise ValueError(f"Schema drift: flat row[{row_index}] missing metric keys {METRIC_KEYS}.")
    if "queue_length" in row:
        _parse_non_negative_int(row["queue_length"], field="queue_length", row_index=row_index)
    if "energy_price" in row:
        _parse_float(row["energy_price"], field="energy_price", row_index=row_index)
    if "sla_violations" in row:
        _parse_non_negative_int(row["sla_violations"], field="sla_violations", row_index=row_index)
    if "completed_tasks" in row:
        _parse_non_negative_int(row["completed_tasks"], field="completed_tasks", row_index=row_index)
    if "energy_watts" in row:
        parsed_energy_watts = _parse_float(row["energy_watts"], field="energy_watts", row_index=row_index)
        if parsed_energy_watts < 0:
            raise ValueError(f"Schema drift: row[{row_index}] field 'energy_watts' must be non-negative, got {row['energy_watts']!r}.")


def _reward_telemetry(raw: dict[str, Any]) -> dict[str, int | float]:
    return {
        "sla_violations": max(0, int(raw.get("sla_violations", 0))),
        "completed_tasks": max(0, int(raw.get("completed_tasks", 0))),
        "energy_watts": max(0.0, _metric_value(raw.get("energy_watts", 0.0))),
    }


def prometheus_rows_to_trace(rows: list[dict[str, Any]], interval_seconds: int = 60) -> list[dict[str, Any]]:
    """
    Convert Prometheus/JSON-ish rows into orchestrator trace rows.

    Expected input row shapes (either):
    1) already grouped by timestamp with keys {timestamp, nodes, tasks}
    2) flat point rows with keys {timestamp, node_id, cpu_util, mem_util, disk_util, net_util, ...}
    """
    if not rows:
        return []
    if interval_seconds <= 0:
        raise ValueError(f"interval_seconds must be positive, got {interval_seconds}.")

    if "nodes" in rows[0]:
        normalized: list[dict[str, Any]] = []
        for row in rows:
            nodes = [_normalize_node(n) for n in row.get("nodes", [])]
            fallback_node = nodes[0]["node_id"] if nodes else "unknown-node"
            tasks = [_normalize_task(t, fallback_node) for t in row.get("tasks", [])]
            normalized.append(
                {
                    "timestamp": int(row.get("timestamp", 0)),
                    "nodes": nodes,
                    "tasks": tasks,
                    "queue_length": max(0, int(row.get("queue_length", len(tasks)))),
                    "energy_price": max(0.0, _metric_value(row.get("energy_price", 0.1), 0.1)),
                    "task_death": _bool_value(row.get("task_death"), default=False),
                    **_reward_telemetry(row),
                }
            )
        return normalized

    buckets: dict[int, dict[str, Any]] = {}
    for raw in rows:
        ts = int(raw.get("timestamp", 0))
        bucket_ts = ts - (ts % max(1, interval_seconds))
        bucket = buckets.setdefault(
            bucket_ts,
            {
                "timestamp": bucket_ts,
                "nodes": {},
                "tasks": [],
                "queue_length": 0,
                "energy_price": 0.1,
                "task_death": False,
                "sla_violations": 0,
                "completed_tasks": 0,
                "energy_watts": 0.0,
            },
        )
        node_id = str(raw.get("node_id", "unknown-node"))
        bucket["nodes"][node_id] = _normalize_node(raw)
        if "task_id" in raw:
            bucket["tasks"].append(_normalize_task(raw, node_id))

        if "queue_length" in raw:
            bucket["queue_length"] = max(max(0, int(raw["queue_length"])), int(bucket["queue_length"]))
        if "energy_price" in raw:
            bucket["energy_price"] = max(0.0, _metric_value(raw["energy_price"], 0.1))
        if _bool_value(raw.get("task_death"), default=False):
            bucket["task_death"] = True
        if "sla_violations" in raw:
            bucket["sla_violations"] = max(int(bucket["sla_violations"]), max(0, int(raw["sla_violations"])))
        if "completed_tasks" in raw:
            bucket["completed_tasks"] = max(int(bucket["completed_tasks"]), max(0, int(raw["completed_tasks"])))
        if "energy_watts" in raw:
            bucket["energy_watts"] = max(float(bucket["energy_watts"]), max(0.0, _metric_value(raw["energy_watts"])))

    trace: list[dict[str, Any]] = []
    for ts in sorted(buckets.keys()):
        bucket = buckets[ts]
        nodes = list(bucket["nodes"].values())
        tasks = bucket["tasks"]
        trace.append(
            {
                "timestamp": ts,
                "nodes": nodes,
                "tasks": tasks,
                "queue_length": int(bucket["queue_length"] or len(tasks)),
                "energy_price": float(bucket["energy_price"]),
                "task_death": bool(bucket["task_death"]),
                "sla_violations": int(bucket["sla_violations"]),
                "completed_tasks": int(bucket["completed_tasks"]),
                "energy_watts": float(bucket["energy_watts"]),
            }
        )
    return trace


def validate_prometheus_schema(rows: list[dict[str, Any]]) -> None:
    """Detect metric/key drift in Prometheus JSON before trace conversion."""
    if not isinstance(rows, list):
        raise ValueError(f"Schema drift: expected top-level list of rows, got {type(rows).__name__}.")
    if not rows:
        return

    # Check first row for mandatory fields
    first = _ensure_dict_row(rows[0], 0)
    is_grouped = "nodes" in first

    for row_index, raw_row in enumerate(rows):
        row = _ensure_dict_row(raw_row, row_index)
        row_is_grouped = "nodes" in row
        if row_is_grouped != is_grouped:
            expected = "grouped" if is_grouped else "flat"
            got = "grouped" if row_is_grouped else "flat"
            raise ValueError(
                f"Schema drift: mixed row shapes detected at row[{row_index}] "
                f"(expected {expected}, got {got})."
            )
        if row_is_grouped:
            _validate_grouped_row(row, row_index)
        else:
            _validate_flat_row(row, row_index)


def load_metric_rows(metrics_path: str | Path) -> list[dict[str, Any]]:
    source = Path(metrics_path)
    if source.suffix.lower() == ".csv":
        with source.open("r", encoding="utf-8", newline="") as handle:
            return [dict(row) for row in csv.DictReader(handle)]

    try:
        raw = json.loads(source.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Failed to parse metrics JSON at {source}: {exc}") from exc
    if not isinstance(raw, list):
        raise ValueError(f"Schema drift: metrics payload at {source} must be a list, got {type(raw).__name__}.")
    return raw


def build_trace_file(metrics_path: str | Path, trace_path: str | Path, interval_seconds: int = 60) -> Path:
    source = Path(metrics_path)
    raw = load_metric_rows(source)
    validate_prometheus_schema(raw)
    trace = prometheus_rows_to_trace(raw, interval_seconds=interval_seconds)
    if not trace:
        raise ValueError(f"Trace build produced zero rows from {source}.")
    out = Path(trace_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(trace, indent=2), encoding="utf-8")
    return out
