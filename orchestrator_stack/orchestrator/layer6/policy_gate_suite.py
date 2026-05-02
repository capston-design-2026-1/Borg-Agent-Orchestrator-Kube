from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _load_object(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def _load_trace_rows(path: Path) -> int:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"{path} must contain a JSON array")
    return len(data)


def evaluate_policy_gate_suite(manifest_path: str | Path) -> dict[str, Any]:
    manifest_file = Path(manifest_path)
    manifest = _load_object(manifest_file)
    entries = manifest.get("entries")
    if not isinstance(entries, list) or not entries:
        raise ValueError("manifest must contain a non-empty 'entries' list")

    evaluated: list[dict[str, Any]] = []
    heldout_entries = 0
    heldout_passes = 0
    for raw_entry in entries:
        if not isinstance(raw_entry, dict):
            raise ValueError("each manifest entry must be an object")
        policy_path = Path(raw_entry["policy_gate_path"])
        trace_path = Path(raw_entry["trace_path"])
        policy = _load_object(policy_path)
        comparison = policy.get("policy_vs_heuristic") or {}
        split = str(raw_entry.get("split", "heldout_eval"))
        beats = bool(comparison.get("beats_heuristic", False))
        if split == "heldout_eval":
            heldout_entries += 1
            heldout_passes += int(beats)
        evaluated.append(
            {
                "family": raw_entry.get("family"),
                "slice": raw_entry.get("slice"),
                "split": split,
                "trace_path": str(trace_path),
                "trace_rows": _load_trace_rows(trace_path),
                "policy_gate_path": str(policy_path),
                "policy_episode_reward_mean": comparison.get("policy_episode_reward_mean"),
                "heuristic_total_score": comparison.get("heuristic_total_score"),
                "delta_vs_heuristic": comparison.get("delta_vs_heuristic"),
                "beats_heuristic": beats,
            }
        )

    return {
        "manifest_path": str(manifest_file),
        "suite_name": manifest.get("suite_name", manifest_file.stem),
        "status": "passed" if heldout_entries > 0 and heldout_passes == heldout_entries else "failed",
        "heldout_entries": heldout_entries,
        "heldout_passes": heldout_passes,
        "entries": evaluated,
    }


def write_policy_gate_suite_report(report: dict[str, Any], out_path: str | Path) -> Path:
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return out
