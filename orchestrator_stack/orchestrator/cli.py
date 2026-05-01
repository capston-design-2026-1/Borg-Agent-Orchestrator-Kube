from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path


def _missing_dependency(exc: ModuleNotFoundError, context: str) -> SystemExit:
    return SystemExit(
        f"missing dependency '{exc.name}' while {context}; install orchestrator_stack/requirements.txt "
        "before running this command"
    )


def _load_npz(path: Path) -> tuple[object, object]:
    try:
        import numpy as np
    except ModuleNotFoundError as exc:
        raise _missing_dependency(exc, "loading NPZ datasets") from exc

    data = np.load(path)
    return data["x"], data["y"]


def cmd_build_trace(args: argparse.Namespace) -> None:
    from orchestrator.layer1.collector import build_trace_file

    out = build_trace_file(args.metrics, args.out, interval_seconds=args.interval_seconds)
    print(json.dumps({"trace_path": str(out)}, indent=2))


def cmd_scrape_prometheus(args: argparse.Namespace) -> None:
    from orchestrator.layer1.prometheus import export_prometheus_metric_rows

    query_map = json.loads(Path(args.queries).read_text(encoding="utf-8"))
    if not isinstance(query_map, dict):
        raise SystemExit("--queries must point to a JSON object mapping output fields to PromQL queries")
    out = export_prometheus_metric_rows(
        base_url=args.base_url,
        query_map={str(key): str(value) for key, value in query_map.items()},
        start=args.start,
        end=args.end,
        step=args.step,
        out_path=args.out,
    )
    print(json.dumps({"metrics_path": str(out)}, indent=2))


def cmd_train_risk(args: argparse.Namespace) -> None:
    try:
        from orchestrator.layer3.predictors import train_safety_model
    except ModuleNotFoundError as exc:
        raise _missing_dependency(exc, "loading Layer 3 training code") from exc

    x, y = _load_npz(Path(args.dataset))
    path = train_safety_model(x, y.astype("int32"), args.out)
    print(json.dumps({"risk_model": str(path)}, indent=2))


def cmd_train_demand(args: argparse.Namespace) -> None:
    try:
        from orchestrator.layer3.predictors import train_demand_model
    except ModuleNotFoundError as exc:
        raise _missing_dependency(exc, "loading Layer 3 training code") from exc

    x, y = _load_npz(Path(args.dataset))
    path = train_demand_model(x, y.astype("float32"), args.out)
    print(json.dumps({"demand_model": str(path)}, indent=2))


def cmd_diagnose_brain(args: argparse.Namespace) -> None:
    try:
        from orchestrator.layer3.diagnostics import diagnose_xgboost_model, write_diagnostics_report
    except ModuleNotFoundError as exc:
        raise _missing_dependency(exc, "loading Layer 3 diagnostics") from exc

    x, y = _load_npz(Path(args.dataset))
    report = diagnose_xgboost_model(model_path=args.model, x=x, y=y, task=args.task)
    out = write_diagnostics_report(report, args.out)
    print(json.dumps({"diagnostics_path": str(out)}, indent=2))


def cmd_train_brains(args: argparse.Namespace) -> None:
    try:
        from orchestrator.layer1.trace_ingestor import load_trace_rows
        from orchestrator.layer3.predictors import train_models_from_trace
    except ModuleNotFoundError as exc:
        raise _missing_dependency(exc, "loading trace-driven training code") from exc

    rows = load_trace_rows(args.trace)
    risk, demand = train_models_from_trace(rows, args.risk_out, args.demand_out)
    print(json.dumps({"risk_model": str(risk), "demand_model": str(demand)}, indent=2))


def cmd_export_brain_datasets(args: argparse.Namespace) -> None:
    try:
        from orchestrator.layer1.trace_ingestor import load_trace_rows
        from orchestrator.layer3.predictors import export_training_datasets_from_trace
    except ModuleNotFoundError as exc:
        raise _missing_dependency(exc, "exporting trace-driven brain datasets") from exc

    rows = load_trace_rows(args.trace)
    risk, demand = export_training_datasets_from_trace(rows, args.risk_out, args.demand_out)
    print(json.dumps({"risk_dataset": str(risk), "demand_dataset": str(demand)}, indent=2))


def cmd_train_brains_from_config(args: argparse.Namespace) -> None:
    try:
        from orchestrator.config import OrchestratorConfig
        from orchestrator.main import train_brain_models
    except ModuleNotFoundError as exc:
        raise _missing_dependency(exc, "loading orchestrator training runtime") from exc

    cfg = OrchestratorConfig.load(args.config)
    result = train_brain_models(cfg)
    print(json.dumps(result, indent=2))


def cmd_run(args: argparse.Namespace) -> None:
    try:
        from orchestrator.config import OrchestratorConfig
        from orchestrator.main import run_episode
    except ModuleNotFoundError as exc:
        raise _missing_dependency(exc, "loading orchestrator runtime") from exc

    cfg = OrchestratorConfig.load(args.config)
    summary = run_episode(cfg)
    print(json.dumps(asdict(summary), indent=2))


def cmd_train_policy(args: argparse.Namespace) -> None:
    try:
        from orchestrator.config import OrchestratorConfig
        from orchestrator.main import run_policy_training
    except ModuleNotFoundError as exc:
        raise _missing_dependency(exc, "loading policy training runtime") from exc

    cfg = OrchestratorConfig.load(args.config)
    result = run_policy_training(cfg, output_dir=args.output_dir)
    print(json.dumps(result, indent=2))


def cmd_tune(args: argparse.Namespace) -> None:
    try:
        from orchestrator.config import OrchestratorConfig
    except ModuleNotFoundError as exc:
        raise _missing_dependency(exc, "loading tune command configuration") from exc
    cfg = OrchestratorConfig.load(args.config)
    try:
        from orchestrator.main import tune_reward_layer
    except ModuleNotFoundError as exc:
        raise _missing_dependency(exc, "loading reward tuning runtime") from exc

    result = tune_reward_layer(cfg, trials=args.trials)
    print(json.dumps(result, indent=2))


def cmd_tune_policy_and_rewards(args: argparse.Namespace) -> None:
    try:
        from orchestrator.config import OrchestratorConfig
    except ModuleNotFoundError as exc:
        raise _missing_dependency(exc, "loading tune-policy-rewards configuration") from exc
    cfg = OrchestratorConfig.load(args.config)
    try:
        from orchestrator.main import tune_policy_and_reward_layer
    except ModuleNotFoundError as exc:
        raise _missing_dependency(exc, "loading PPO-backed reward tuning runtime") from exc

    result = tune_policy_and_reward_layer(cfg, trials=args.trials)
    print(json.dumps(result, indent=2))


def cmd_full_process(args: argparse.Namespace) -> None:
    try:
        from orchestrator.config import OrchestratorConfig
        from orchestrator.main import run_full_process
    except ModuleNotFoundError as exc:
        raise _missing_dependency(exc, "loading full orchestrator process runtime") from exc

    cfg = OrchestratorConfig.load(args.config)
    result = run_full_process(cfg, tune_trials=args.trials)
    print(json.dumps(result, indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Borg full orchestrator")
    sub = parser.add_subparsers(dest="command", required=True)

    p_build_trace = sub.add_parser("build-trace")
    p_build_trace.add_argument("--metrics", required=True)
    p_build_trace.add_argument("--out", required=True)
    p_build_trace.add_argument("--interval-seconds", type=int, default=60)
    p_build_trace.set_defaults(func=cmd_build_trace)

    p_scrape = sub.add_parser("scrape-prometheus")
    p_scrape.add_argument("--base-url", required=True)
    p_scrape.add_argument("--queries", required=True, help="JSON object mapping output fields to PromQL queries")
    p_scrape.add_argument("--start", required=True)
    p_scrape.add_argument("--end", required=True)
    p_scrape.add_argument("--step", required=True)
    p_scrape.add_argument("--out", required=True)
    p_scrape.set_defaults(func=cmd_scrape_prometheus)

    p_train_risk = sub.add_parser("train-risk")
    p_train_risk.add_argument("--dataset", required=True)
    p_train_risk.add_argument("--out", required=True)
    p_train_risk.set_defaults(func=cmd_train_risk)

    p_train_demand = sub.add_parser("train-demand")
    p_train_demand.add_argument("--dataset", required=True)
    p_train_demand.add_argument("--out", required=True)
    p_train_demand.set_defaults(func=cmd_train_demand)

    p_diagnose = sub.add_parser("diagnose-brain")
    p_diagnose.add_argument("--model", required=True)
    p_diagnose.add_argument("--dataset", required=True)
    p_diagnose.add_argument("--task", choices=["risk", "demand"], required=True)
    p_diagnose.add_argument("--out", required=True)
    p_diagnose.set_defaults(func=cmd_diagnose_brain)

    p_train_brains = sub.add_parser("train-brains")
    p_train_brains.add_argument("--trace", required=True)
    p_train_brains.add_argument("--risk-out", required=True)
    p_train_brains.add_argument("--demand-out", required=True)
    p_train_brains.set_defaults(func=cmd_train_brains)

    p_export_brain_datasets = sub.add_parser("export-brain-datasets")
    p_export_brain_datasets.add_argument("--trace", required=True)
    p_export_brain_datasets.add_argument("--risk-out", required=True)
    p_export_brain_datasets.add_argument("--demand-out", required=True)
    p_export_brain_datasets.set_defaults(func=cmd_export_brain_datasets)

    p_train_brains_cfg = sub.add_parser("train-brains-from-config")
    p_train_brains_cfg.add_argument("--config", required=True)
    p_train_brains_cfg.set_defaults(func=cmd_train_brains_from_config)

    p_run = sub.add_parser("run")
    p_run.add_argument("--config", required=True)
    p_run.set_defaults(func=cmd_run)

    p_train_policy = sub.add_parser("train-policy")
    p_train_policy.add_argument("--config", required=True)
    p_train_policy.add_argument("--output-dir", default="orchestrator_stack/runtime/rllib")
    p_train_policy.set_defaults(func=cmd_train_policy)

    p_tune = sub.add_parser("tune")
    p_tune.add_argument("--config", required=True)
    p_tune.add_argument("--trials", type=int, default=20)
    p_tune.set_defaults(func=cmd_tune)

    p_tune_policy = sub.add_parser("tune-policy-rewards")
    p_tune_policy.add_argument("--config", required=True)
    p_tune_policy.add_argument("--trials", type=int, default=20)
    p_tune_policy.set_defaults(func=cmd_tune_policy_and_rewards)

    p_full = sub.add_parser("full-process")
    p_full.add_argument("--config", required=True)
    p_full.add_argument("--trials", type=int, default=5)
    p_full.set_defaults(func=cmd_full_process)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
