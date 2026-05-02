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
        "Implemented for local validation",
        "Trace-driven twin, local fallback, Python 3.12 validation env, Kind kubeconfig, upstream package preflight, and live AIOpsLab runs",
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
        "Implemented for live traces",
        "`sla_violations`, `completed_tasks`, `energy_watts`, and Prometheus CPU/memory utilization preserved into trace rows",
    ),
)

NEXT_ENGINEERING_WORK = (
    "Repeat controlled ablations across multiple seeds for predictor runtime and SLA-risk preservation.",
    "Expand the current two-entry multi-family gate suite to a third full-phase AIOpsLab family.",
    "Add measured or externally calibrated node-power telemetry when a power exporter is available.",
    "Export thesis-ready tables from raw JSON artifacts for reproducible evaluation appendices.",
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
            "- Full test suite: `PYTHONPATH=orchestrator_stack .venv/bin/python -m pytest orchestrator_stack/tests -q` -> `82 passed` on 2026-05-03 KST.",
            "- `export-brain-datasets` smoke ran against `orchestrator_stack/examples/sample_trace.json` and wrote risk/demand NPZ files.",
            "- `train-policy` smoke reports `heuristic_baseline` and `policy_vs_heuristic` gates.",
            "- Live Kind/AIOpsLab validation uses `~/Documents/aiopslab_validation_env/kubeconfig` and covers no-op, Hotel Reservation misconfiguration, and SocialNetwork Kubernetes target-port misconfiguration.",
            "- Prometheus/node-exporter enrichment covers all 15 rows in `reports/evaluations/202605022020_aiopslab_mitigation_prometheus_kube_trace.json`.",
            "- PPO beats heuristic on the Prometheus-enriched mitigation trace by `+77.23260686133335` total reward.",
            "- `k8s_target_port-misconfig-*` validates a second full-phase family; stronger PPO beats heuristic by `+18.01204388800005` on that family trace.",
            "- Multi-family gate suite `reports/evaluations/202605030020_aiopslab_multi_family_policy_gate_suite.json` passes `2/2` held-out entries.",
            "- Repeated-seed PPO summary `reports/evaluations/202605030040_repeated_seed_ppo_summary.json` passes `3/3` seeds on both reported families.",
            "- Ablation evidence matrix `reports/evaluations/202605030050_ablation_evidence_matrix.md` records sequential evidence with an explicit non-causal caveat.",
            "- Controlled single-seed ablation `reports/evaluations/202605030110_controlled_ablation_summary.json` shows SLA-risk preservation improves predictor-runtime delta by `+27.90277777777783` on a fixed trace.",
            "",
            "## Remaining Research Gaps",
            "",
            "- PPO quality is proven on two held-out gate-suite entries and three repeated seeds per reported family; repeated-seed controlled ablations and broader family coverage remain open.",
            "- Energy watts remain model-derived from utilization unless a measured node-power exporter is added.",
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
