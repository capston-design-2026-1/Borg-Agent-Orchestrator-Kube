from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


def _load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def _label(path: Path) -> str:
    stem = path.stem
    prefix, _, rest = stem.partition("_")
    if len(prefix) == 12 and prefix.isdigit() and rest:
        return rest
    return stem


def _fmt(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        return f"{value:.12g}"
    if isinstance(value, (dict, list)):
        return json.dumps(value, sort_keys=True)
    return str(value)


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: _fmt(row.get(key)) for key in fieldnames})


def _markdown_table(title: str, rows: list[dict[str, Any]], fieldnames: list[str]) -> list[str]:
    lines = [f"## {title}", ""]
    if not rows:
        return lines + ["No rows discovered.", ""]
    lines.append("| " + " | ".join(fieldnames) + " |")
    lines.append("| " + " | ".join("---" for _ in fieldnames) + " |")
    for row in rows:
        values = [_fmt(row.get(field)).replace("|", "\\|") for field in fieldnames]
        lines.append("| " + " | ".join(values) + " |")
    lines.append("")
    return lines


def collect_thesis_evaluation_tables(evaluation_dir: str | Path) -> dict[str, list[dict[str, Any]]]:
    root = Path(evaluation_dir)
    live_tasks: list[dict[str, Any]] = []
    reward_audits: list[dict[str, Any]] = []
    policy_gates: list[dict[str, Any]] = []

    for path in sorted(root.glob("*_live_summary.json")):
        data = _load_json(path)
        results = data.get("results") if isinstance(data.get("results"), dict) else {}
        live_tasks.append(
            {
                "artifact": str(path),
                "label": _label(path),
                "problem_id": data.get("problem_id"),
                "final_state": data.get("final_state"),
                "success": results.get("success"),
                "trace_rows": data.get("trace_rows"),
                "capture_error_count": len(data.get("capture_errors") or []),
                "primary_result": _primary_result(results),
            }
        )

    for path in sorted(root.glob("*_reward_audit*.json")):
        data = _load_json(path)
        reward_audits.append(
            {
                "artifact": str(path),
                "label": _label(path),
                "steps": data.get("steps"),
                "telemetry_coverage": data.get("telemetry_coverage"),
                "max_sla_violations": data.get("max_sla_violations"),
                "max_completed_tasks": data.get("max_completed_tasks"),
                "max_energy_watts": data.get("max_energy_watts"),
                "actions": data.get("actions"),
                "weighted_telemetry_delta": (data.get("telemetry_reward_delta") or {}).get("weighted_total"),
            }
        )

    for path in sorted(root.glob("*_train_policy*.json")):
        data = _load_json(path)
        comparison = data.get("policy_vs_heuristic") or {}
        heuristic = data.get("heuristic_baseline") or {}
        policy_gates.append(
            {
                "artifact": str(path),
                "label": _label(path),
                "status": data.get("status"),
                "stage_count": data.get("stage_count"),
                "policy_episode_reward_mean": comparison.get("policy_episode_reward_mean"),
                "heuristic_total_score": comparison.get("heuristic_total_score") or heuristic.get("total_score"),
                "delta_vs_heuristic": comparison.get("delta_vs_heuristic"),
                "beats_heuristic": comparison.get("beats_heuristic"),
            }
        )

    return {"live_tasks": live_tasks, "reward_audits": reward_audits, "policy_gates": policy_gates}


def _primary_result(results: dict[str, Any]) -> str:
    for key in (
        "Detection Accuracy",
        "Localization Accuracy",
        "system_level_correct",
        "fault_type_correct",
        "success",
    ):
        if key in results:
            return f"{key}={_fmt(results[key])}"
    return ""


def write_thesis_evaluation_tables(
    *,
    evaluation_dir: str | Path,
    out_md: str | Path,
    out_csv_dir: str | Path | None = None,
) -> dict[str, str]:
    tables = collect_thesis_evaluation_tables(evaluation_dir)
    md_path = Path(out_md)
    csv_dir = Path(out_csv_dir) if out_csv_dir is not None else None

    live_fields = [
        "label",
        "problem_id",
        "final_state",
        "success",
        "trace_rows",
        "capture_error_count",
        "primary_result",
        "artifact",
    ]
    audit_fields = [
        "label",
        "steps",
        "telemetry_coverage",
        "max_sla_violations",
        "max_completed_tasks",
        "max_energy_watts",
        "actions",
        "weighted_telemetry_delta",
        "artifact",
    ]
    policy_fields = [
        "label",
        "status",
        "stage_count",
        "policy_episode_reward_mean",
        "heuristic_total_score",
        "delta_vs_heuristic",
        "beats_heuristic",
        "artifact",
    ]

    lines = [
        "# Thesis Evaluation Tables",
        "",
        f"- Source directory: `{evaluation_dir}`",
        "",
    ]
    lines.extend(_markdown_table("Live AIOpsLab Tasks", tables["live_tasks"], live_fields))
    lines.extend(_markdown_table("Telemetry Reward Audits", tables["reward_audits"], audit_fields))
    lines.extend(_markdown_table("PPO Policy Gates", tables["policy_gates"], policy_fields))

    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text("\n".join(lines), encoding="utf-8")

    outputs = {"markdown": str(md_path)}
    if csv_dir is not None:
        _write_csv(csv_dir / "live_tasks.csv", tables["live_tasks"], live_fields)
        _write_csv(csv_dir / "reward_audits.csv", tables["reward_audits"], audit_fields)
        _write_csv(csv_dir / "policy_gates.csv", tables["policy_gates"], policy_fields)
        outputs["csv_dir"] = str(csv_dir)
    return outputs
