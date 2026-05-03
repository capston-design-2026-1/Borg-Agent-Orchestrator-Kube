from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from orchestrator.config import OrchestratorConfig
from orchestrator.layer1.trace_ingestor import load_trace_rows
from orchestrator.layer2.simulator import AIOpsLabBackend, TraceDrivenTwinBackend
from orchestrator.layer3.predictors import PredictorBackedBackend, ResourceDemandForecast, SafetyRiskForecast
from orchestrator.layer4.agents import AgentARiskMitigator, AgentBEfficiencyOptimizer, AgentCGatekeeper
from orchestrator.layer4.referee import resolve
from orchestrator.layer5.optuna_tuner import export_study_report
from orchestrator.layer6.scoreboard import Scoreboard
from orchestrator.main import ensure_trace_exists, run_episode, run_policy_training, train_brain_models
from orchestrator.runtime_state import VisualizationState

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


def _tune_rewards(config: OrchestratorConfig, rows: list[dict[str, Any]], state: VisualizationState, *, trials: int) -> dict[str, Any]:
    if optuna is None:
        return {"status": "skipped", "reason": "optuna is not installed"}
    config.optuna_storage_path.parent.mkdir(parents=True, exist_ok=True)
    storage = f"sqlite:///{config.optuna_storage_path.resolve()}"
    study_name = "visualized_orchestrator_reward_weights"
    study = optuna.create_study(direction="maximize", storage=storage, study_name=study_name, load_if_exists=True)

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
        state.optuna_trial(study_name, trial.number, trial.value, dict(trial.params), float(study.best_value))

    study.optimize(objective, n_trials=max(1, trials), callbacks=[callback], catch=(Exception,))
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

        summary = {"trace": str(trace), "models": models, "episode": episode, "ppo": ppo, "reward_tuning": tuning}
        out = Path(event_dir) / "summary.json"
        out.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
        state.artifact(out, "launch summary")
        state.state["summary"].update(summary)
        state.set_status("complete", stage="complete")
        state.emit("complete", "orchestration run complete")
        return summary
    except Exception as exc:
        state.error(str(exc))
        raise
