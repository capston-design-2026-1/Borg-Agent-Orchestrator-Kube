from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

KST = timezone(timedelta(hours=9))


@dataclass(frozen=True, slots=True)
class ArchitectureItem:
    name: str
    status: str
    evidence: str


ARCHITECTURE_ITEMS = (
    ArchitectureItem(
        "Historical trace ingestion",
        "Implemented",
        "JSON/JSONL traces, JSON/CSV metrics, Prometheus export, telemetry reward fields",
    ),
    ArchitectureItem(
        "AIOpsLab simulator / cluster state engine",
        "Partially implemented",
        "Trace-driven twin, local fallback, Python 3.12 validation env, and upstream package preflight; live run still needs Kubernetes config",
    ),
    ArchitectureItem(
        "Feature extractor",
        "Implemented",
        "8-feature node vectors with stable feature-name metadata",
    ),
    ArchitectureItem(
        "Trace-derived brain datasets",
        "Implemented",
        "`export-brain-datasets` writes reusable risk/demand NPZ matrices",
    ),
    ArchitectureItem(
        "XGBoost risk model",
        "Implemented with diagnostics",
        "Training, threshold optimization, calibration bins, feature importance, contribution-summary path",
    ),
    ArchitectureItem(
        "XGBoost demand model",
        "Implemented with diagnostics",
        "Training, diagnostics, and trace-derived demand targets",
    ),
    ArchitectureItem(
        "PettingZoo bridge",
        "Implemented",
        "`OrchestratorParallelEnv` exposes parallel multi-agent reset/step behavior",
    ),
    ArchitectureItem(
        "Ray RLlib PPO env",
        "Implemented",
        "RLlib MultiAgentEnv plus staged PPO curriculum command",
    ),
    ArchitectureItem("Agent A: risk survival", "Implemented", "migrate, replicate, throttle actions"),
    ArchitectureItem("Agent B: power/cost", "Implemented", "sleep/wake, DVFS, memory balloon actions"),
    ArchitectureItem(
        "Agent C: throughput/load",
        "Implemented",
        "admit, queue, reject, deprioritize, resource-cap actions",
    ),
    ArchitectureItem(
        "Referee logic gate",
        "Implemented",
        "Safety-first and protective-admission/resource-cap priority rules",
    ),
    ArchitectureItem(
        "Optuna reward/policy tuning",
        "Implemented locally",
        "Reward tuning plus PPO-backed objective path; long-run quality remains open",
    ),
    ArchitectureItem("Global scoreboard", "Implemented", "Weighted alpha/beta/gamma score aggregation"),
    ArchitectureItem(
        "Real SLA/energy/task reward metrics",
        "Interface implemented",
        "`sla_violations`, `completed_tasks`, and `energy_watts` preserved into trace rows",
    ),
)

NEXT_ENGINEERING_WORK = (
    "Create a Python 3.12 AIOpsLab validation environment and run `AIOpsLabPolicyAgent` against a real problem ID.",
    "Provide Kubernetes config for the AIOpsLab validation environment and rerun `aiopslab-preflight` until ready.",
    "Validate live Prometheus/AIOpsLab telemetry fields with `telemetry-reward-audit`.",
    "Tune PPO curriculum until `policy_vs_heuristic.beats_heuristic` is true on representative telemetry traces.",
    "Export representative trace-derived matrices, retrain/calibrate boosters, and promote thresholds only after diagnostics.",
)


def architecture_status_markdown(
    *,
    generated_at: datetime | None = None,
    source_architecture: str = "docs/project_architecture.pdf",
) -> str:
    generated = generated_at.astimezone(KST) if generated_at else datetime.now(KST)
    lines = [
        "# Orchestrator Architecture Status",
        "",
        f"- Generated (KST): {generated:%Y-%m-%d %H:%M}",
        f"- Source architecture: `{source_architecture}`",
        "- Implementation root: `orchestrator_stack/`",
        "",
        "## Completion Summary",
        "",
        "| Architecture item | Status | Evidence |",
        "| --- | --- | --- |",
    ]
    lines.extend(f"| {item.name} | {item.status} | {item.evidence} |" for item in ARCHITECTURE_ITEMS)
    lines.extend(
        [
            "",
            "## Current Validation Baseline",
            "",
            "- Full test suite: `PYTHONPATH=orchestrator_stack .venv/bin/python -m pytest orchestrator_stack/tests -q` -> `62 passed` on 2026-05-02 KST.",
            "- `export-brain-datasets` smoke ran against `orchestrator_stack/examples/sample_trace.json` and wrote risk/demand NPZ files.",
            "- `train-policy` smoke reports `heuristic_baseline` and `policy_vs_heuristic` gates.",
            "- `aiopslab-preflight` is ready for Python/package checks in `~/Documents/aiopslab_validation_env` but blocked on Kubernetes config.",
            "",
            "## External Blockers",
            "",
            "- Live AIOpsLab validation still needs a valid Kubernetes config; Python 3.12 and the upstream package are installed in `~/Documents/aiopslab_validation_env`.",
            "- Real SLA/energy/task reward replacement needs live Prometheus/AIOpsLab payloads audited by `telemetry-reward-audit`.",
            "- PPO policy quality remains open until `policy_vs_heuristic.beats_heuristic` is true on telemetry-backed traces.",
            "",
            "## Recommended Next Engineering Work",
            "",
        ]
    )
    lines.extend(f"{idx}. {item}" for idx, item in enumerate(NEXT_ENGINEERING_WORK, start=1))
    lines.append("")
    return "\n".join(lines)


def write_architecture_status_report(
    *,
    out_path: str | Path | None = None,
    source_architecture: str = "docs/project_architecture.pdf",
    generated_at: datetime | None = None,
) -> Path:
    generated = generated_at.astimezone(KST) if generated_at else datetime.now(KST)
    out = Path(out_path) if out_path is not None else Path(f"reports/evaluations/{generated:%Y%m%d%H%M}_orchestrator_architecture_status.md")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        architecture_status_markdown(generated_at=generated, source_architecture=source_architecture),
        encoding="utf-8",
    )
    return out
