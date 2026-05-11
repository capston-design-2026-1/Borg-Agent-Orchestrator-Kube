from __future__ import annotations

import json
import re
import time
from dataclasses import replace
from pathlib import Path
from typing import Any

from orchestrator.config import OrchestratorConfig
from orchestrator.layer1.kubernetes_exerciser import apply_exercise_phase_to_clusters
from orchestrator.layer1.kubernetes_trace import capture_kubernetes_trace_row, load_power_calibration, write_kubernetes_trace
from orchestrator.layer1.trace_ingestor import load_trace_rows
from orchestrator.layer2.simulator import AIOpsLabBackend, TraceDrivenTwinBackend
from orchestrator.layer3.predictors import PredictorBackedBackend, ResourceDemandForecast, SafetyRiskForecast
from orchestrator.layer4.agents import AgentARiskMitigator, AgentBEfficiencyOptimizer, AgentCGatekeeper
from orchestrator.layer4.referee import resolve
from orchestrator.layer5.optuna_tuner import export_study_report
from orchestrator.layer6.scoreboard import Scoreboard
from orchestrator.main import ensure_trace_exists, run_episode, run_policy_training, train_brain_models
from orchestrator.runtime_state import VisualizationState, json_safe

try:
    import optuna
except Exception:  # pragma: no cover
    optuna = None


def _backend(rows: list[dict[str, Any]], config: OrchestratorConfig):
    base = (
        AIOpsLabBackend(config.aiopslab_problem_id, max_steps=config.aiopslab_max_steps)
        if config.use_aiopslab_backend
        else TraceDrivenTwinBackend(rows, preserve_live_sla_risk=config.preserve_live_sla_risk)
    )
    if not config.use_predictor_runtime:
        return base
    return PredictorBackedBackend(
        base,
        risk_model=SafetyRiskForecast.load(config.risk_model_path),
        demand_model=ResourceDemandForecast.load(config.demand_model_path),
    )


def _visual_episode(config: OrchestratorConfig, rows: list[dict[str, Any]], state: VisualizationState) -> dict[str, Any]:
    backend = _backend(rows, config)
    agents = [AgentARiskMitigator(), AgentBEfficiencyOptimizer(), AgentCGatekeeper()]
    scoreboard = Scoreboard(alpha=config.alpha, beta=config.beta, gamma=config.gamma)
    obs = backend.reset()
    total_steps = min(config.episode_steps, len(rows))
    for step in range(total_steps):
        proposals = [agent.act(obs) for agent in agents]
        action = resolve(proposals)
        result = backend.step(action)
        score = scoreboard.update(result.reward_by_agent)
        state.reward(
            step,
            {key: float(value) for key, value in result.reward_by_agent.items()},
            score.total,
            f"{action.agent_name}:{action.kind.value}",
        )
        state.stage("episode", "running", detail=f"step {step + 1}/{total_steps}", progress=(step + 1) / max(1, total_steps))
        obs = result.next_observation
        if result.done:
            break
    return scoreboard.snapshot()


def _cluster_snapshot(obs: Any) -> dict[str, Any]:
    max_risk_node, max_risk = max(obs.p_fail_scores.items(), key=lambda item: item[1], default=(None, 0.0))
    min_demand_node, min_demand = min(obs.demand_projection.items(), key=lambda item: item[1], default=(None, 0.0))
    avg_cpu = sum(node.cpu_util for node in obs.nodes) / max(1, len(obs.nodes))
    avg_mem = sum(node.mem_util for node in obs.nodes) / max(1, len(obs.nodes))
    return {
        "nodes": len(obs.nodes),
        "tasks": len(obs.tasks),
        "queue_length": obs.queue_length,
        "sla_violations": obs.sla_violations,
        "completed_tasks": obs.completed_tasks,
        "energy_watts": obs.energy_watts,
        "max_risk": round(float(max_risk), 6),
        "max_risk_node": max_risk_node,
        "min_demand": round(float(min_demand), 6),
        "min_demand_node": min_demand_node,
        "avg_cpu": round(float(avg_cpu), 6),
        "avg_mem": round(float(avg_mem), 6),
    }


def _decision_reason(snapshot: dict[str, Any], action_agent: str, action_kind: str) -> str:
    if action_agent == "AgentA":
        return f"risk={snapshot['max_risk']} on {snapshot['max_risk_node']}; sla={snapshot['sla_violations']}"
    if action_agent == "AgentB":
        source = snapshot.get("power_calibration_source", "calibrated")
        return f"low demand={snapshot['min_demand']} on {snapshot['min_demand_node']}; est_power={snapshot['energy_watts']:.3f}W ({source})"
    if action_agent == "AgentC":
        return f"queue={snapshot['queue_length']}; avg_cpu={snapshot['avg_cpu']}; avg_mem={snapshot['avg_mem']}"
    return "no-op or unknown action"


def _action_label(action: Any) -> str:
    label = f"{action.agent_name}:{action.kind.value}"
    if action.kind.value == "admission":
        decision = action.payload.get("decision")
        return f"{label}:{decision}" if decision else label
    if action.kind.value == "power_state":
        state = action.payload.get("state")
        return f"{label}:{state}" if state else label
    return label


def _write_live_summary(event_dir: str | Path, state: VisualizationState, *, status: str = "running") -> Path:
    summary = {
        "status": status,
        "updated_at": state.state.get("updated_at"),
        "active_stage": state.state.get("active_stage"),
        "cluster": state.state.get("cluster"),
        "decision": state.state.get("decision"),
        "ray": state.state.get("ray"),
        "optuna": state.state.get("optuna"),
        "reward_summary": state.state.get("reward_summary"),
        "summary": state.state.get("summary"),
        "data_source": state.state.get("data_source"),
        "errors": state.state.get("errors"),
    }
    out = Path(event_dir) / "summary.json"
    tmp = out.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(json_safe(summary), indent=2, sort_keys=True, allow_nan=False), encoding="utf-8")
    tmp.replace(out)
    return out


def _slug(value: str, *, fallback: str = "trace") -> str:
    slug = re.sub(r"[^a-zA-Z0-9_.-]+", "_", value).strip("._-")
    return slug[:80] or fallback


def _trace_provenance(trace: str | Path, rows: list[dict[str, Any]], config_path: str | Path, config: OrchestratorConfig) -> dict[str, Any]:
    first = rows[0] if rows else {}
    telemetry_sources = first.get("telemetry_sources") if isinstance(first, dict) else None
    source_platform = str(first.get("source_platform") or "") if isinstance(first, dict) else ""
    source = str(first.get("source") or "") if isinstance(first, dict) else ""
    source_tokens = {str(item).lower() for item in telemetry_sources} if isinstance(telemetry_sources, list) else set()
    if "google_trace" in source_platform.lower() or "google" in source.lower() or "google_cluster_trace" in source_tokens:
        kind = "Google Trace"
    elif any("kubernetes" in token or "prometheus" in token for token in source_tokens) or config.use_aiopslab_backend:
        kind = "AIOpsLab / Kubernetes"
    elif "sample" in Path(trace).name or "synthetic" in Path(trace).name:
        kind = "Synthetic Sample"
    else:
        kind = "Trace File"
    return {
        "kind": kind,
        "trace_path": str(trace),
        "config_path": str(config_path),
        "rows": len(rows),
        "telemetry_sources": sorted(source_tokens),
        "source_platform": source_platform or None,
        "source": source or None,
        "aiopslab_backend": bool(config.use_aiopslab_backend),
    }


def _optuna_study_history(study: Any) -> list[dict[str, Any]]:
    history: list[dict[str, Any]] = []
    for trial in sorted(study.trials, key=lambda item: int(item.number)):
        if trial.value is None:
            continue
        started = getattr(trial, "datetime_start", None)
        completed = getattr(trial, "datetime_complete", None)
        history.append(
            {
                "trial": int(trial.number),
                "value": float(trial.value),
                "params": dict(trial.params),
                "state": getattr(getattr(trial, "state", None), "name", str(getattr(trial, "state", "UNKNOWN"))),
                "datetime_start": started.isoformat() if started else None,
                "datetime_complete": completed.isoformat() if completed else None,
            }
        )
    return history


def _sync_optuna_study_history(study: Any, study_name: str, state: VisualizationState, *, status: str | None = None) -> None:
    history = _optuna_study_history(study)
    best_score: float | None = None
    best_params: dict[str, Any] | None = None
    try:
        best = study.best_trial
        best_score = float(best.value) if best.value is not None else None
        best_params = dict(best.params)
    except ValueError:
        best_params = {}
    state.optuna_history(
        study_name,
        history,
        best_score=best_score,
        best_params=best_params,
        latest_trial=history[-1]["trial"] if history else None,
        status=status,
    )


def _tune_rewards(config: OrchestratorConfig, rows: list[dict[str, Any]], state: VisualizationState, *, trials: int) -> dict[str, Any]:
    if optuna is None:
        return {"status": "skipped", "reason": "optuna is not installed"}
    config.optuna_storage_path.parent.mkdir(parents=True, exist_ok=True)
    storage = f"sqlite:///{config.optuna_storage_path.resolve()}"
    trace_stem = _slug(Path(config.trace_path).stem)
    run_stamp = str(state.state.get("started_at", "")).replace(":", "").replace("+", "_")
    study_name = f"visualized_{trace_stem}_{_slug(run_stamp, fallback='run')}_reward_weights"
    state.optuna_update("initializing", study=study_name, trials=trials, storage_path=str(config.optuna_storage_path))
    study = optuna.create_study(direction="maximize", storage=storage, study_name=study_name, load_if_exists=True)
    _sync_optuna_study_history(study, study_name, state, status="running")

    def objective(trial: Any) -> float:
        alpha = trial.suggest_float("alpha", 0.5, 2.5)
        beta = trial.suggest_float("beta", 0.1, 2.0)
        gamma = trial.suggest_float("gamma", 0.1, 2.0)
        trial_cfg = OrchestratorConfig(
            trace_path=config.trace_path,
            risk_model_path=config.risk_model_path,
            demand_model_path=config.demand_model_path,
            raw_metrics_path=config.raw_metrics_path,
            use_aiopslab_backend=config.use_aiopslab_backend,
            aiopslab_problem_id=config.aiopslab_problem_id,
            aiopslab_max_steps=config.aiopslab_max_steps,
            episode_steps=config.episode_steps,
            alpha=alpha,
            beta=beta,
            gamma=gamma,
            rllib_train_iters=config.rllib_train_iters,
            ppo_learning_rate=config.ppo_learning_rate,
            ppo_train_batch_size=config.ppo_train_batch_size,
            ppo_minibatch_size=config.ppo_minibatch_size,
            ppo_num_epochs=config.ppo_num_epochs,
            ppo_rollout_fragment_length=config.ppo_rollout_fragment_length,
            ppo_curriculum=config.ppo_curriculum,
            random_seed=config.random_seed,
            use_predictor_runtime=config.use_predictor_runtime,
            preserve_live_sla_risk=config.preserve_live_sla_risk,
            optuna_storage_path=config.optuna_storage_path,
        )
        return float(run_episode(trial_cfg, verbose=False).total_score)

    def callback(study: Any, trial: Any) -> None:
        best_value: float | None = None
        try:
            best_value = float(study.best_value)
        except ValueError:
            pass
        state.optuna_trial(study_name, trial.number, trial.value, dict(trial.params), best_value)
        _sync_optuna_study_history(study, study_name, state, status="running")

    study.optimize(objective, n_trials=max(1, trials), callbacks=[callback], catch=(Exception,))
    _sync_optuna_study_history(study, study_name, state, status="complete")
    report = export_study_report(study, study_name)
    state.artifact(report, "Optuna reward report")
    best = study.best_trial
    return {"alpha": best.params["alpha"], "beta": best.params["beta"], "gamma": best.params["gamma"], "score": best.value}


def run_visualized_orchestration(
    config_path: str | Path,
    *,
    trials: int = 3,
    event_dir: str | Path = "orchestrator_stack/runtime/visualization",
    train_policy: bool = True,
    tune_rewards: bool = True,
) -> dict[str, Any]:
    state = VisualizationState(event_dir)
    config = OrchestratorConfig.load(config_path)
    state.state["summary"]["config"] = str(config_path)
    state.set_status("running", stage="boot")
    try:
        state.stage("trace", "running", detail="build or load Layer 1 trace", progress=0.1)
        trace = ensure_trace_exists(config)
        state.artifact(trace, "Layer 1 trace")
        rows = load_trace_rows(trace)
        data_source = _trace_provenance(trace, rows, config_path, config)
        state.state["data_source"] = data_source
        state.state["summary"]["data_source"] = data_source
        state.emit("data_source", f"{data_source['kind']} rows={data_source['rows']}", **data_source)
        state.stage("trace", "complete", detail=f"loaded {len(rows)} trace rows", progress=1.0)

        state.stage("brains", "running", detail="train XGBoost risk and demand predictors", progress=0.2)
        models = train_brain_models(config)
        for label, path in models.items():
            state.artifact(path, label)
        state.stage("brains", "complete", detail="predictor models ready", progress=1.0)

        state.stage("episode", "running", detail="heuristic MARL/referee episode", progress=0.0)
        episode = _visual_episode(config, rows, state)
        state.stage("episode", "complete", detail=f"total score {float(episode['total']):.3f}", progress=1.0)

        ppo: dict[str, Any] = {"status": "skipped", "reason": "disabled"}
        if train_policy:
            state.stage("ray_ppo", "running", detail="RLlib PPO training", progress=0.05)
            state.ray_update("initializing", train_iters=config.rllib_train_iters)
            ppo = run_policy_training(config, output_dir="orchestrator_stack/runtime/rllib")
            state.ray_update(
                str(ppo.get("status", "complete")),
                reward_mean=ppo.get("episode_reward_mean"),
                checkpoint=ppo.get("checkpoint"),
            )
            state.stage("ray_ppo", "complete", detail=str(ppo.get("status", "complete")), progress=1.0)

        tuning: dict[str, Any] = {"status": "skipped", "reason": "disabled"}
        if tune_rewards:
            state.stage("optuna", "running", detail=f"reward tuning, {trials} trials", progress=0.1)
            tuning = _tune_rewards(config, rows, state, trials=trials)
            state.stage("optuna", "complete", detail=f"best score {float(tuning.get('score', 0.0)):.3f}", progress=1.0)

        summary = {"trace": str(trace), "models": models, "episode": episode, "ppo": ppo, "reward_tuning": tuning, "data_source": data_source}
        out = Path(event_dir) / "summary.json"
        out.write_text(json.dumps(json_safe(summary), indent=2, sort_keys=True, allow_nan=False), encoding="utf-8")
        state.artifact(out, "launch summary")
        state.state["summary"].update(summary)
        state.set_status("complete", stage="complete")
        state.emit("complete", "orchestration run complete")
        return summary
    except Exception as exc:
        state.error(str(exc))
        raise


def run_live_kubernetes_orchestration(
    config_path: str | Path,
    *,
    event_dir: str | Path = "orchestrator_stack/runtime/visualization",
    kubeconfig: str | Path = "~/.kube/config",
    interval_seconds: float = 10.0,
    max_iterations: int | None = None,
    namespace_prefixes: tuple[str, ...] = ("test-", "default"),
    prometheus_base_url: str | None = None,
    power_calibration_path: str | Path | None = None,
    trace_out: str | Path = "orchestrator_stack/runtime/visualization/live_kubernetes_trace.json",
    train_policy: bool = True,
    tune_rewards: bool = False,
    trials: int = 3,
    exercise_cluster: bool = False,
    exercise_namespace: str = "borg-orchestrator-exercise",
    exercise_interval_iterations: int = 3,
    exercise_randomize: bool = False,
    exercise_seed: int | None = None,
    mirror_exercise_kubeconfigs: tuple[str | Path, ...] = (),
    mirror_exercise_namespace: str | None = None,
) -> dict[str, Any]:
    state = VisualizationState(event_dir)
    config = OrchestratorConfig.load(config_path)
    kubeconfig_path = Path(kubeconfig).expanduser()
    calibration = load_power_calibration(power_calibration_path)
    trace_rows: list[dict[str, Any]] = []
    scoreboard = Scoreboard(alpha=config.alpha, beta=config.beta, gamma=config.gamma)
    state.state["summary"].update(
        {
            "mode": "live_kubernetes",
            "config": str(config_path),
            "kubeconfig": str(kubeconfig_path),
            "interval_seconds": interval_seconds,
            "exercise_cluster": exercise_cluster,
            "exercise_namespace": exercise_namespace if exercise_cluster else None,
            "exercise_randomize": exercise_randomize if exercise_cluster else None,
            "exercise_seed": exercise_seed if exercise_cluster else None,
            "mirror_exercise_kubeconfigs": [str(Path(path).expanduser()) for path in mirror_exercise_kubeconfigs] if exercise_cluster else [],
            "mirror_exercise_namespace": mirror_exercise_namespace if exercise_cluster and mirror_exercise_kubeconfigs else None,
        }
    )
    state.state["data_source"] = {
        "kind": "AIOpsLab / Kubernetes",
        "trace_path": str(trace_out),
        "config_path": str(config_path),
        "rows": 0,
        "telemetry_sources": ["kubernetes_api"] + (["prometheus_node_exporter"] if prometheus_base_url else []),
        "source_platform": "kubernetes",
        "source": "live_kubernetes",
        "aiopslab_backend": bool(config.use_aiopslab_backend),
    }
    state.state["summary"]["data_source"] = dict(state.state["data_source"])
    if exercise_cluster and exercise_namespace not in namespace_prefixes:
        namespace_prefixes = (*namespace_prefixes, exercise_namespace)
    state.set_status("running", stage="live_boot")

    try:
        state.stage("brains", "running", detail="ensure XGBoost risk and demand predictors", progress=0.2)
        try:
            models = train_brain_models(config)
            for label, path in models.items():
                state.artifact(path, label)
            state.stage("brains", "complete", detail="predictor models ready", progress=1.0)
        except ModuleNotFoundError as exc:
            if exc.name != "xgboost":
                raise
            config = replace(config, use_predictor_runtime=False)
            state.stage(
                "brains",
                "skipped",
                detail="xgboost missing; live kube risk/demand telemetry drives decisions",
                progress=1.0,
            )

        if train_policy:
            state.stage("ray_ppo", "running", detail="bootstrap RLlib PPO policy before live loop", progress=0.1)
            state.ray_update("initializing", train_iters=config.rllib_train_iters)
            ppo = run_policy_training(config, output_dir="orchestrator_stack/runtime/rllib")
            state.ray_update(str(ppo.get("status", "complete")), reward_mean=ppo.get("episode_reward_mean"), checkpoint=ppo.get("checkpoint"))
            state.stage("ray_ppo", "complete", detail=str(ppo.get("status", "complete")), progress=1.0)
        else:
            state.ray_update("disabled", reason="live fast mode sets --no-policy; use NO_POLICY=0 to bootstrap Ray/RLlib")

        if tune_rewards:
            rows = load_trace_rows(ensure_trace_exists(config))
            state.stage("optuna", "running", detail=f"bootstrap reward tuning, {trials} trials", progress=0.1)
            state.optuna_update("initializing", trials=trials)
            tuning = _tune_rewards(config, rows, state, trials=trials)
            if tuning.get("status") == "skipped":
                state.optuna_update("skipped", reason=tuning.get("reason", "Optuna tuning skipped"))
                state.stage("optuna", "skipped", detail=str(tuning.get("reason", "Optuna tuning skipped")), progress=1.0)
            else:
                state.optuna_update("complete", best_score=tuning.get("score"), best_params={k: tuning.get(k) for k in ("alpha", "beta", "gamma") if k in tuning})
                state.stage("optuna", "complete", detail=f"best score {float(tuning.get('score', 0.0)):.3f}", progress=1.0)
        else:
            state.optuna_update("disabled", reason="live fast mode sets --no-tune; use NO_TUNE=0 to bootstrap Optuna")

        state.stage("live_kubernetes_loop", "running", detail="capturing cluster snapshots until stopped", progress=0.0)
        agents = [AgentARiskMitigator(), AgentBEfficiencyOptimizer(), AgentCGatekeeper()]
        iteration = 0
        trace_artifact_announced = False
        last_signature: tuple[str, str, str | None, str] | None = None
        repeat_count = 0
        while max_iterations is None or iteration < max_iterations:
            if exercise_cluster and iteration % max(1, exercise_interval_iterations) == 0:
                phase = apply_exercise_phase_to_clusters(
                    kubeconfig=kubeconfig_path,
                    namespace=exercise_namespace,
                    phase_index=iteration // max(1, exercise_interval_iterations),
                    mirror_kubeconfigs=[Path(path).expanduser() for path in mirror_exercise_kubeconfigs],
                    mirror_namespace=mirror_exercise_namespace,
                    randomize=exercise_randomize,
                    seed=exercise_seed,
                )
                state.emit(
                    "exercise",
                    f"{phase['phase']}: {phase['detail']}",
                    phase=phase["phase"],
                    namespace=phase["namespace"],
                    operation=phase.get("operation"),
                    deployment=phase.get("deployment"),
                    resources=phase.get("resources"),
                    randomized=phase.get("randomized"),
                    cleanup=phase.get("cleanup"),
                    applied=phase.get("applied"),
                    rollout=phase.get("rollout"),
                    mirrors=phase.get("mirrors"),
                    mirror_count=phase.get("mirror_count", 0),
                )
            row = capture_kubernetes_trace_row(
                kubeconfig=kubeconfig_path,
                namespace_prefixes=namespace_prefixes,
                prometheus_base_url=prometheus_base_url,
                power_calibration=calibration,
            )
            trace_rows.append(row)
            state.state["data_source"]["rows"] = len(trace_rows)
            state.state["summary"]["data_source"] = dict(state.state["data_source"])
            write_kubernetes_trace(trace_rows, trace_out)
            if not trace_artifact_announced or (iteration + 1) % 10 == 0:
                state.artifact(trace_out, "live Kubernetes trace")
                trace_artifact_announced = True

            backend = _backend([row], config)
            obs = backend.reset()
            snapshot = _cluster_snapshot(obs)
            power_calibration = row.get("power_calibration") if isinstance(row, dict) else None
            if isinstance(power_calibration, dict):
                snapshot["power_metric_kind"] = "estimated"
                snapshot["power_calibration_source"] = str(power_calibration.get("source", "calibrated"))
            telemetry_sources = row.get("telemetry_sources") if isinstance(row, dict) else None
            if isinstance(telemetry_sources, list):
                snapshot["telemetry_sources"] = [str(source) for source in telemetry_sources]
            if isinstance(row, dict) and row.get("prometheus_error"):
                snapshot["prometheus_error"] = str(row["prometheus_error"])
            state.cluster_snapshot(snapshot)
            proposals = [agent.act(obs) for agent in agents]
            action = resolve(proposals)
            reason = _decision_reason(snapshot, action.agent_name, action.kind.value)
            action_label = _action_label(action)
            signature = (action.agent_name, action.kind.value, action.target, json.dumps(snapshot, sort_keys=True))
            if signature == last_signature:
                repeat_count += 1
            else:
                repeat_count = 1
                last_signature = signature
            decision_payload = {
                "agent": action.agent_name,
                "kind": action.kind.value,
                "target": action.target,
                "payload": dict(action.payload),
                "action_label": action_label,
                "score": float(action.score),
                "priority": int(action.priority),
                "repeat_count": repeat_count,
                "reason": reason,
                "proposal_count": len(proposals),
                "proposals": [
                    {
                        "agent": proposal.agent_name,
                        "kind": proposal.kind.value,
                        "target": proposal.target,
                        "score": float(proposal.score),
                        "priority": int(proposal.priority),
                    }
                    for proposal in proposals
                ],
            }
            state.decision(decision_payload)
            result = backend.step(action)
            score = scoreboard.update(result.reward_by_agent)
            state.reward(
                iteration,
                {key: float(value) for key, value in result.reward_by_agent.items()},
                score.total,
                action_label,
            )
            state.state["summary"].update(
                {
                    "iterations": iteration + 1,
                    "last_action": decision_payload,
                    "last_cluster": snapshot,
                    "scoreboard": scoreboard.snapshot(),
                }
            )
            progress = 0.0 if max_iterations is None else (iteration + 1) / max(1, max_iterations)
            state.stage(
                "live_kubernetes_loop",
                "running",
                detail=(
                    f"iteration {iteration + 1}; recommendation {action_label}; "
                    f"repeat={repeat_count}; {reason}"
                ),
                progress=progress,
            )
            _write_live_summary(event_dir, state)
            iteration += 1
            if max_iterations is not None and iteration >= max_iterations:
                break
            time.sleep(max(0.1, float(interval_seconds)))

        summary = {
            "mode": "live_kubernetes",
            "iterations": iteration,
            "trace_out": str(trace_out),
            "scoreboard": scoreboard.snapshot(),
        }
        state.state["summary"].update(summary)
        out = _write_live_summary(event_dir, state, status="complete")
        state.artifact(out, "live launch summary")
        state.stage("live_kubernetes_loop", "complete", detail=f"completed {iteration} iterations", progress=1.0)
        state.set_status("complete", stage="complete")
        _write_live_summary(event_dir, state, status="complete")
        return summary
    except KeyboardInterrupt:
        summary = {
            "mode": "live_kubernetes",
            "status": "stopped",
            "iterations": len(trace_rows),
            "trace_out": str(trace_out),
            "scoreboard": scoreboard.snapshot(),
        }
        state.state["summary"].update(summary)
        out = _write_live_summary(event_dir, state, status="stopped")
        state.artifact(out, "live launch summary")
        state.set_status("stopped", stage="stopped")
        _write_live_summary(event_dir, state, status="stopped")
        return summary
    except Exception as exc:
        state.error(str(exc))
        raise
