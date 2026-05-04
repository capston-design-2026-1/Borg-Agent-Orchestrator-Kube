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


def _load_npz_dataset(path: Path) -> dict[str, object]:
    try:
        import numpy as np
    except ModuleNotFoundError as exc:
        raise _missing_dependency(exc, "loading NPZ datasets") from exc

    data = np.load(path)
    result: dict[str, object] = {"x": data["x"], "y": data["y"]}
    if "feature_names" in data:
        result["feature_names"] = data["feature_names"]
    return result


def _load_npz(path: Path) -> tuple[object, object]:
    data = _load_npz_dataset(path)
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

    data = _load_npz_dataset(Path(args.dataset))
    report = diagnose_xgboost_model(
        model_path=args.model,
        x=data["x"],
        y=data["y"],
        task=args.task,
        feature_names=data.get("feature_names"),
    )
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


def cmd_visualized_run(args: argparse.Namespace) -> None:
    try:
        from orchestrator.visualization import run_visualized_orchestration
    except ModuleNotFoundError as exc:
        raise _missing_dependency(exc, "loading visualization runtime") from exc

    result = run_visualized_orchestration(
        args.config,
        trials=args.trials,
        event_dir=args.event_dir,
        train_policy=not args.no_policy,
        tune_rewards=not args.no_tune,
    )
    print(json.dumps(result, indent=2))


def cmd_live_kubernetes_run(args: argparse.Namespace) -> None:
    try:
        from orchestrator.visualization import run_live_kubernetes_orchestration
    except ModuleNotFoundError as exc:
        raise _missing_dependency(exc, "loading live Kubernetes visualization runtime") from exc

    prefixes = tuple(prefix.strip() for prefix in args.namespace_prefixes.split(",") if prefix.strip())
    result = run_live_kubernetes_orchestration(
        args.config,
        event_dir=args.event_dir,
        kubeconfig=args.kubeconfig,
        interval_seconds=args.interval_seconds,
        max_iterations=args.max_iterations,
        namespace_prefixes=prefixes,
        prometheus_base_url=args.prometheus_base_url,
        power_calibration_path=args.power_calibration,
        trace_out=args.trace_out,
        train_policy=not args.no_policy,
        tune_rewards=not args.no_tune,
        trials=args.trials,
        exercise_cluster=args.exercise_cluster,
        exercise_namespace=args.exercise_namespace,
        exercise_interval_iterations=args.exercise_interval_iterations,
        exercise_randomize=args.exercise_randomize,
        exercise_seed=args.exercise_seed,
    )
    print(json.dumps(result, indent=2))


def cmd_architecture_status(args: argparse.Namespace) -> None:
    from orchestrator.layer6.architecture_report import write_architecture_status_report

    out = write_architecture_status_report(out_path=args.out, source_architecture=args.source_architecture)
    print(json.dumps({"architecture_status_path": str(out)}, indent=2))


def cmd_thesis_tables(args: argparse.Namespace) -> None:
    from orchestrator.layer6.thesis_tables import write_thesis_evaluation_tables

    result = write_thesis_evaluation_tables(
        evaluation_dir=args.evaluation_dir,
        out_md=args.out_md,
        out_csv_dir=args.out_csv_dir,
    )
    print(json.dumps(result, indent=2))


def cmd_evaluation_statistics(args: argparse.Namespace) -> None:
    from orchestrator.layer6.evaluation_statistics import build_evaluation_statistics_report, write_evaluation_statistics_report

    report = build_evaluation_statistics_report(
        repeated_seed_summary_path=args.repeated_seed_summary,
        controlled_ablation_summary_path=args.controlled_ablation_summary,
    )
    outputs = write_evaluation_statistics_report(report, args.out_json, args.out_md)
    print(json.dumps(outputs, indent=2))


def cmd_policy_gate_suite(args: argparse.Namespace) -> None:
    from orchestrator.layer6.policy_gate_suite import evaluate_policy_gate_suite, write_policy_gate_suite_report

    report = evaluate_policy_gate_suite(args.manifest)
    out = write_policy_gate_suite_report(report, args.out)
    print(json.dumps({"policy_gate_suite_path": str(out), **report}, indent=2))


def cmd_telemetry_reward_audit(args: argparse.Namespace) -> None:
    from orchestrator.layer1.trace_ingestor import load_trace_rows
    from orchestrator.layer6.telemetry_audit import audit_trace_telemetry_rewards, write_telemetry_audit_report

    rows = load_trace_rows(args.trace)
    report = audit_trace_telemetry_rewards(
        rows,
        alpha=args.alpha,
        beta=args.beta,
        gamma=args.gamma,
        max_steps=args.max_steps,
    )
    out = write_telemetry_audit_report(report, args.out)
    print(json.dumps({"telemetry_audit_path": str(out)}, indent=2))


def cmd_aiopslab_preflight(args: argparse.Namespace) -> None:
    from orchestrator.layer2.aiopslab_preflight import aiopslab_preflight, write_aiopslab_preflight_report

    report = aiopslab_preflight(kube_config=args.kube_config)
    if args.out:
        out = write_aiopslab_preflight_report(report, args.out)
        print(json.dumps({"aiopslab_preflight_path": str(out), **report}, indent=2))
    else:
        print(json.dumps(report, indent=2))


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

    p_visualized = sub.add_parser("visualized-run")
    p_visualized.add_argument("--config", default="orchestrator_stack/config/orchestrator.example.json")
    p_visualized.add_argument("--trials", type=int, default=3)
    p_visualized.add_argument("--event-dir", default="orchestrator_stack/runtime/visualization")
    p_visualized.add_argument("--no-policy", action="store_true", help="Skip Ray/RLlib PPO training")
    p_visualized.add_argument("--no-tune", action="store_true", help="Skip Optuna reward tuning")
    p_visualized.set_defaults(func=cmd_visualized_run)

    p_live = sub.add_parser("live-kubernetes-run")
    p_live.add_argument("--config", default="orchestrator_stack/config/orchestrator.example.json")
    p_live.add_argument("--event-dir", default="orchestrator_stack/runtime/visualization")
    p_live.add_argument("--kubeconfig", default="~/.kube/config")
    p_live.add_argument("--interval-seconds", type=float, default=10.0)
    p_live.add_argument("--max-iterations", type=int)
    p_live.add_argument("--namespace-prefixes", default="test-,default")
    p_live.add_argument("--prometheus-base-url")
    p_live.add_argument("--power-calibration")
    p_live.add_argument("--trace-out", default="orchestrator_stack/runtime/visualization/live_kubernetes_trace.json")
    p_live.add_argument("--trials", type=int, default=3)
    p_live.add_argument("--no-policy", action="store_true", help="Skip Ray/RLlib PPO bootstrap")
    p_live.add_argument("--no-tune", action="store_true", help="Skip Optuna reward bootstrap")
    p_live.add_argument("--exercise-cluster", action="store_true", help="Rotate safe load patterns in a dedicated namespace to force varied agent decisions")
    p_live.add_argument("--exercise-namespace", default="borg-orchestrator-exercise")
    p_live.add_argument("--exercise-interval-iterations", type=int, default=3)
    p_live.add_argument("--exercise-randomize", action="store_true", help="Randomize exercise phase selection and workload request sizes")
    p_live.add_argument("--exercise-seed", type=int, help="Optional deterministic seed for randomized exercise phases")
    p_live.set_defaults(func=cmd_live_kubernetes_run)

    p_arch = sub.add_parser("architecture-status")
    p_arch.add_argument("--out")
    p_arch.add_argument("--source-architecture", default="docs/project_architecture.pdf")
    p_arch.set_defaults(func=cmd_architecture_status)

    p_thesis_tables = sub.add_parser("thesis-tables")
    p_thesis_tables.add_argument("--evaluation-dir", default="reports/evaluations")
    p_thesis_tables.add_argument("--out-md", required=True)
    p_thesis_tables.add_argument("--out-csv-dir")
    p_thesis_tables.set_defaults(func=cmd_thesis_tables)

    p_eval_stats = sub.add_parser("evaluation-statistics")
    p_eval_stats.add_argument("--repeated-seed-summary", required=True)
    p_eval_stats.add_argument("--controlled-ablation-summary", required=True)
    p_eval_stats.add_argument("--out-json", required=True)
    p_eval_stats.add_argument("--out-md")
    p_eval_stats.set_defaults(func=cmd_evaluation_statistics)

    p_gate_suite = sub.add_parser("policy-gate-suite")
    p_gate_suite.add_argument("--manifest", required=True)
    p_gate_suite.add_argument("--out", required=True)
    p_gate_suite.set_defaults(func=cmd_policy_gate_suite)

    p_telemetry = sub.add_parser("telemetry-reward-audit")
    p_telemetry.add_argument("--trace", required=True)
    p_telemetry.add_argument("--out", required=True)
    p_telemetry.add_argument("--alpha", type=float, default=1.0)
    p_telemetry.add_argument("--beta", type=float, default=0.6)
    p_telemetry.add_argument("--gamma", type=float, default=0.8)
    p_telemetry.add_argument("--max-steps", type=int)
    p_telemetry.set_defaults(func=cmd_telemetry_reward_audit)

    p_aiopslab_preflight = sub.add_parser("aiopslab-preflight")
    p_aiopslab_preflight.add_argument("--out")
    p_aiopslab_preflight.add_argument("--kube-config", help="Path list for Kubernetes config; defaults to KUBECONFIG or ~/.kube/config")
    p_aiopslab_preflight.set_defaults(func=cmd_aiopslab_preflight)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
