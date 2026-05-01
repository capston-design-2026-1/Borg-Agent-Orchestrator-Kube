from __future__ import annotations

import json
from pathlib import Path
from typing import Any


REQUIRED_TRACE_ROW_KEYS = ("timestamp", "nodes", "tasks")
REQUIRED_NODE_KEYS = ("node_id", "cpu_util", "mem_util")
REQUIRED_TASK_KEYS = ("task_id", "node_id")
TRUE_LITERALS = {"1", "true", "t", "yes", "y", "on"}
FALSE_LITERALS = {"0", "false", "f", "no", "n", "off"}


def _int_like(value: Any, *, field: str, row_index: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Trace contract error: row[{row_index}] field '{field}' must be integer-like.") from exc


def _non_negative_int_like(value: Any, *, field: str, row_index: int) -> int:
    parsed = _int_like(value, field=field, row_index=row_index)
    if parsed < 0:
        raise ValueError(f"Trace contract error: row[{row_index}] field '{field}' must be non-negative.")
    return parsed


def _float_like(value: Any, *, field: str, row_index: int, default: float | None = None) -> float:
    if value is None and default is not None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Trace contract error: row[{row_index}] field '{field}' must be numeric.") from exc


def _bool_like(value: Any, *, field: str, row_index: int, default: bool | None = None) -> bool:
    if value is None and default is not None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and value in (0, 1):
        return bool(value)
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in TRUE_LITERALS:
            return True
        if lowered in FALSE_LITERALS:
            return False
    raise ValueError(f"Trace contract error: row[{row_index}] field '{field}' must be bool-like.")


def validate_trace_rows(rows: list[dict[str, Any]], *, source: Path) -> None:
    if not isinstance(rows, list):
        raise ValueError(f"Trace contract error: {source} must contain a top-level JSON array (or JSONL rows).")
    if not rows:
        raise ValueError(f"Trace contract error: {source} contains zero rows.")

    for row_index, raw_row in enumerate(rows):
        if not isinstance(raw_row, dict):
            raise ValueError(f"Trace contract error: row[{row_index}] must be an object.")
        for key in REQUIRED_TRACE_ROW_KEYS:
            if key not in raw_row:
                raise ValueError(f"Trace contract error: row[{row_index}] missing required key '{key}'.")
        _int_like(raw_row.get("timestamp"), field="timestamp", row_index=row_index)

        nodes = raw_row.get("nodes")
        if not isinstance(nodes, list):
            raise ValueError(f"Trace contract error: row[{row_index}] field 'nodes' must be a list.")
        for node_index, node in enumerate(nodes):
            if not isinstance(node, dict):
                raise ValueError(f"Trace contract error: row[{row_index}] node[{node_index}] must be an object.")
            for key in REQUIRED_NODE_KEYS:
                if key not in node:
                    raise ValueError(
                        f"Trace contract error: row[{row_index}] node[{node_index}] missing required key '{key}'."
                    )
            _float_like(node.get("cpu_util"), field="cpu_util", row_index=row_index)
            _float_like(node.get("mem_util"), field="mem_util", row_index=row_index)
            _float_like(node.get("disk_util"), field="disk_util", row_index=row_index, default=0.0)
            _float_like(node.get("net_util"), field="net_util", row_index=row_index, default=0.0)

        tasks = raw_row.get("tasks")
        if not isinstance(tasks, list):
            raise ValueError(f"Trace contract error: row[{row_index}] field 'tasks' must be a list.")
        for task_index, task in enumerate(tasks):
            if not isinstance(task, dict):
                raise ValueError(f"Trace contract error: row[{row_index}] task[{task_index}] must be an object.")
            for key in REQUIRED_TASK_KEYS:
                if key not in task:
                    raise ValueError(
                        f"Trace contract error: row[{row_index}] task[{task_index}] missing required key '{key}'."
                    )
            if "urgency" in task:
                _float_like(task.get("urgency"), field="urgency", row_index=row_index)
            if "queue_priority" in task:
                _non_negative_int_like(task.get("queue_priority"), field="queue_priority", row_index=row_index)
            if "alive" in task:
                _bool_like(task.get("alive"), field="alive", row_index=row_index)

        _non_negative_int_like(raw_row.get("queue_length", 0), field="queue_length", row_index=row_index)
        _float_like(raw_row.get("energy_price", 0.1), field="energy_price", row_index=row_index)
        _bool_like(raw_row.get("task_death", False), field="task_death", row_index=row_index, default=False)
        _non_negative_int_like(raw_row.get("sla_violations", 0), field="sla_violations", row_index=row_index)
        _non_negative_int_like(raw_row.get("completed_tasks", 0), field="completed_tasks", row_index=row_index)
        energy_watts = _float_like(raw_row.get("energy_watts", 0.0), field="energy_watts", row_index=row_index)
        if energy_watts < 0:
            raise ValueError(f"Trace contract error: row[{row_index}] field 'energy_watts' must be non-negative.")


def load_trace_rows(path: str | Path) -> list[dict[str, Any]]:
    source = Path(path)
    if not source.exists() or not source.is_file():
        raise ValueError(f"Trace source not found: {source}")

    suffix = source.suffix.lower()
    if suffix == ".jsonl":
        rows: list[dict[str, Any]] = []
        with source.open("r", encoding="utf-8") as f:
            for line_number, line in enumerate(f, start=1):
                line = line.strip()
                if line:
                    try:
                        rows.append(json.loads(line))
                    except json.JSONDecodeError as exc:
                        raise ValueError(f"Failed to parse JSONL in {source} at line {line_number}: {exc}") from exc
        validate_trace_rows(rows, source=source)
        return rows

    if suffix != ".json":
        raise ValueError(f"Unsupported trace format for {source}. Expected .json or .jsonl.")

    try:
        rows = json.loads(source.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Failed to parse trace JSON at {source}: {exc}") from exc

    validate_trace_rows(rows, source=source)
    return rows
