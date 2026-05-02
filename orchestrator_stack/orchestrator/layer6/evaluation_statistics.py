from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any


T_CRITICAL_95 = {
    1: 12.706204736432095,
    2: 4.302652729749464,
    3: 3.182446305284263,
    4: 2.7764451051977987,
    5: 2.570581835636305,
    6: 2.4469118511449692,
    7: 2.3646242510102993,
    8: 2.306004135204166,
    9: 2.2621571628540993,
    10: 2.2281388519649385,
}


def mean_std_ci95(values: list[float]) -> dict[str, float | int | None]:
    if not values:
        return {"n": 0, "mean": None, "std": None, "ci95_low": None, "ci95_high": None, "ci95_half_width": None}
    n = len(values)
    mean = sum(values) / n
    if n == 1:
        return {"n": n, "mean": mean, "std": 0.0, "ci95_low": mean, "ci95_high": mean, "ci95_half_width": 0.0}
    std = math.sqrt(sum((value - mean) ** 2 for value in values) / (n - 1))
    t_critical = T_CRITICAL_95.get(n - 1, 1.96)
    half_width = t_critical * std / math.sqrt(n)
    return {
        "n": n,
        "mean": mean,
        "std": std,
        "ci95_low": mean - half_width,
        "ci95_high": mean + half_width,
        "ci95_half_width": half_width,
    }


def build_evaluation_statistics_report(
    *,
    repeated_seed_summary_path: str | Path,
    controlled_ablation_summary_path: str | Path,
) -> dict[str, Any]:
    repeated_seed_summary = json.loads(Path(repeated_seed_summary_path).read_text(encoding="utf-8"))
    controlled_ablation_summary = json.loads(Path(controlled_ablation_summary_path).read_text(encoding="utf-8"))

    repeated_seed_rows = []
    for evaluation_set in repeated_seed_summary.get("sets", []):
        deltas = [float(run["delta_vs_heuristic"]) for run in evaluation_set.get("runs", [])]
        repeated_seed_rows.append(
            {
                "evaluation_set": evaluation_set.get("evaluation_set"),
                "metric": "delta_vs_heuristic",
                **mean_std_ci95(deltas),
                "pass_rate": evaluation_set.get("pass_rate"),
            }
        )

    ablation_variant_rows = []
    for variant in controlled_ablation_summary.get("variant_summaries", []):
        runs = [
            row
            for row in controlled_ablation_summary.get("rows", [])
            if row.get("variant") == variant.get("variant")
        ]
        deltas = [float(run["delta_vs_heuristic"]) for run in runs]
        ablation_variant_rows.append(
            {
                "variant": variant.get("variant"),
                "metric": "delta_vs_heuristic",
                **mean_std_ci95(deltas),
                "pass_rate": variant.get("pass_rate"),
            }
        )

    ablation_effect_rows = []
    effect_keys = (
        "sla_preservation_delta_gain_with_predictor",
        "predictor_runtime_delta_change_without_sla_preservation",
    )
    for key in effect_keys:
        values = [float(row[key]) for row in controlled_ablation_summary.get("effects_by_seed", [])]
        ablation_effect_rows.append({"effect": key, **mean_std_ci95(values)})

    return {
        "status": "passed",
        "confidence_level": 0.95,
        "method": "Student t confidence intervals for seed-repeated deltas; n=3 intervals are descriptive and intentionally wide.",
        "inputs": {
            "repeated_seed_summary": str(repeated_seed_summary_path),
            "controlled_ablation_summary": str(controlled_ablation_summary_path),
        },
        "repeated_seed_policy_deltas": repeated_seed_rows,
        "controlled_ablation_variant_deltas": ablation_variant_rows,
        "controlled_ablation_effects": ablation_effect_rows,
    }


def write_evaluation_statistics_report(report: dict[str, Any], out_json: str | Path, out_md: str | Path | None = None) -> dict[str, str]:
    json_path = Path(out_json)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    outputs = {"json": str(json_path)}
    if out_md is not None:
        md_path = Path(out_md)
        md_path.parent.mkdir(parents=True, exist_ok=True)
        md_path.write_text(_statistics_markdown(report), encoding="utf-8")
        outputs["markdown"] = str(md_path)
    return outputs


def _fmt(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.12g}"
    return str(value)


def _statistics_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Evaluation Statistics",
        "",
        f"- Confidence level: `{report['confidence_level']}`",
        f"- Method: {report['method']}",
        f"- Repeated-seed input: `{report['inputs']['repeated_seed_summary']}`",
        f"- Controlled-ablation input: `{report['inputs']['controlled_ablation_summary']}`",
        "",
    ]
    lines.extend(_table("Repeated-Seed Policy Deltas", report["repeated_seed_policy_deltas"], "evaluation_set"))
    lines.extend(_table("Controlled Ablation Variant Deltas", report["controlled_ablation_variant_deltas"], "variant"))
    lines.extend(_table("Controlled Ablation Effects", report["controlled_ablation_effects"], "effect", include_pass_rate=False))
    return "\n".join(lines)


def _table(title: str, rows: list[dict[str, Any]], label_field: str, *, include_pass_rate: bool = True) -> list[str]:
    fields = [label_field, "n", "mean", "std", "ci95_low", "ci95_high", "ci95_half_width"]
    if include_pass_rate:
        fields.append("pass_rate")
    lines = [f"## {title}", "", "| " + " | ".join(fields) + " |", "| " + " | ".join("---" for _ in fields) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(_fmt(row.get(field)) for field in fields) + " |")
    lines.append("")
    return lines
