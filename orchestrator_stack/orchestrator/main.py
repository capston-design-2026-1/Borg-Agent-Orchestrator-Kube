from __future__ import annotations

import logging
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from orchestrator.config import OrchestratorConfig
from orchestrator.layer1.collector import build_trace_file
from orchestrator.layer1.trace_ingestor import load_trace_rows
from orchestrator.layer2.simulator import AIOpsLabBackend, TraceDrivenTwinBackend
from orchestrator.layer3.predictors import (
    PredictorBackedBackend,
    ResourceDemandForecast,
    SafetyRiskForecast,
    train_models_from_trace,
)
from orchestrator.layer4.agents import AgentARiskMitigator, AgentBEfficiencyOptimizer, AgentCGatekeeper
from orchestrator.layer4.ppo_trainer import (
    compare_policy_training_to_heuristic,
    evaluate_heuristic_policy,
    train_curriculum_ppo,
    train_multiagent_ppo,
)
from orchestrator.layer4.referee import resolve
from orchestrator.layer5.optuna_tuner import tune_policy_and_rewards, tune_reward_weights
from orchestrator.layer6.scoreboard import Scoreboard

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class RunSummary:
    steps: int
    total_score: float
    avg_score: float
    agent_a: float
    agent_b: float
    agent_c: float


def _build_backend(rows: list[dict], config: OrchestratorConfig):
    if config.use_aiopslab_backend:
        return AIOpsLabBackend(config.aiopslab_problem_id, max_steps=config.aiopslab_max_steps)
    return TraceDrivenTwinBackend(rows)


def _build_predictor_runtime(rows: list[dict], config: OrchestratorConfig):
    return PredictorBackedBackend(
        _build_backend(rows, config),
        risk_model=SafetyRiskForecast.load(config.risk_model_path),
        demand_model=ResourceDemandForecast.load(config.demand_model_path),
    )


def ensure_trace_exists(config: OrchestratorConfig) -> Path:
    if config.trace_path.exists():
        return config.trace_path
    if config.raw_metrics_path is None:
        raise FileNotFoundError(
            f"Trace not found at {config.trace_path} and no raw_metrics_path provided in config for Layer1 build."
        )
    return build_trace_file(config.raw_metrics_path, config.trace_path)


def train_brain_models(config: OrchestratorConfig) -> dict[str, str]:
    trace_path = ensure_trace_exists(config)
    rows = load_trace_rows(trace_path)
    risk, demand = train_models_from_trace(rows, config.risk_model_path, config.demand_model_path)
    return {"risk_model": str(risk), "demand_model": str(demand)}


from datetime import datetime, timedelta, timezone


def run_episode(config: OrchestratorConfig, verbose: bool = True) -> RunSummary:
    trace_path = ensure_trace_exists(config)
    rows = load_trace_rows(trace_path)
    backend = _build_predictor_runtime(rows, config)

    agent_a = AgentARiskMitigator()
    agent_b = AgentBEfficiencyOptimizer()
    agent_c = AgentCGatekeeper()
    scoreboard = Scoreboard(alpha=config.alpha, beta=config.beta, gamma=config.gamma)

    obs = backend.reset()
    total_steps = min(config.episode_steps, len(rows))

    # Setup persistent trace logging
    kst = timezone(timedelta(hours=9))
    ts = datetime.now(kst).strftime("%Y%m%d%H%M")
    log_path = Path(f"reports/traces/{ts}_episode_trace.log")
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_buffer = [f"--- Episode Start: {total_steps} steps ---\n"]

    if verbose:
        print(f"\n--- Episode Start: {total_steps} steps ---")

    for step in range(total_steps):
        proposals = [agent_a.act(obs), agent_b.act(obs), agent_c.act(obs)]
        validated_action = resolve(proposals)

        result = backend.step(validated_action)
        scoreboard.update(result.reward_by_agent)

        p_str = ", ".join([f"{p.agent_name}:{p.kind.value}" for p in proposals if p.kind.value != "noop"])
        ref_str = f"{validated_action.agent_name}:{validated_action.kind.value}"
        rew_str = ", ".join([f"{k}:{v:+.1f}" for k, v in result.reward_by_agent.items()])
        
        line = f"Step {step:03d} | Proposals: [{p_str}] | Referee: {ref_str} | Rewards: [{rew_str}]"
        log_buffer.append(line + "\n")
        
        if verbose:
            print(line)

        obs = result.next_observation
        if result.done:
            break

    log_buffer.append("--- Episode End ---\n")
    log_path.write_text("".join(log_buffer), encoding="utf-8")
    
    if verbose:
        print(f"--- Episode Trace stored at: {log_path} ---\n")

    snap = scoreboard.snapshot()
    return RunSummary(
        steps=int(snap["steps"]),
        total_score=float(snap["total"]),
        avg_score=float(snap["average"]),
        agent_a=float(snap["agent_a"]),
        agent_b=float(snap["agent_b"]),
        agent_c=float(snap["agent_c"]),
    )


def run_policy_training(config: OrchestratorConfig, output_dir: str | Path) -> dict[str, Any]:
    rows = load_trace_rows(ensure_trace_exists(config))
    if config.ppo_curriculum:
        training_summary = train_curriculum_ppo(
            lambda: _build_predictor_runtime(rows, config),
            alpha=config.alpha,
            beta=config.beta,
            gamma=config.gamma,
            stages=config.ppo_curriculum,
            seed=config.random_seed,
            output_dir=output_dir,
        )
    else:
        backend = _build_predictor_runtime(rows, config)
        training_summary = train_multiagent_ppo(
            backend,
            alpha=config.alpha,
            beta=config.beta,
            gamma=config.gamma,
            learning_rate=config.ppo_learning_rate,
            train_iters=config.rllib_train_iters,
            train_batch_size=config.ppo_train_batch_size,
            minibatch_size=config.ppo_minibatch_size,
            num_epochs=config.ppo_num_epochs,
            rollout_fragment_length=config.ppo_rollout_fragment_length,
            seed=config.random_seed,
            output_dir=output_dir,
        )
    heuristic_summary = evaluate_heuristic_policy(
        _build_predictor_runtime(rows, config),
        alpha=config.alpha,
        beta=config.beta,
        gamma=config.gamma,
        steps=config.episode_steps,
    )
    training_summary["heuristic_baseline"] = heuristic_summary
    training_summary["policy_vs_heuristic"] = compare_policy_training_to_heuristic(training_summary, heuristic_summary)
    return training_summary


def tune_reward_layer(config: OrchestratorConfig, *, trials: int) -> dict[str, Any]:
    def objective(alpha: float, beta: float, gamma: float) -> float:
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
            optuna_storage_path=config.optuna_storage_path,
        )
        return run_episode(trial_cfg, verbose=False).total_score

    config.optuna_storage_path.parent.mkdir(parents=True, exist_ok=True)
    storage = f"sqlite:///{config.optuna_storage_path.resolve()}"
    try:
        result = tune_reward_weights(objective, n_trials=trials, storage=storage)
        return asdict(result)
    except RuntimeError as exc:
        return {"status": "skipped", "reason": str(exc), "alpha": config.alpha, "beta": config.beta, "gamma": config.gamma}


def tune_policy_and_reward_layer(config: OrchestratorConfig, *, trials: int) -> dict[str, Any]:
    rows = load_trace_rows(ensure_trace_exists(config))

    def objective(
        alpha: float,
        beta: float,
        gamma: float,
        learning_rate: float,
        train_batch_size: int,
        minibatch_size: int,
        num_epochs: int,
        rollout_fragment_length: int,
    ) -> float:
        backend = _build_predictor_runtime(rows, config)
        trial_output = config.optuna_storage_path.parent / "rllib_trials"
        training_summary = train_multiagent_ppo(
            backend,
            alpha=alpha,
            beta=beta,
            gamma=gamma,
            learning_rate=learning_rate,
            train_iters=config.rllib_train_iters,
            train_batch_size=train_batch_size,
            minibatch_size=minibatch_size,
            num_epochs=num_epochs,
            rollout_fragment_length=rollout_fragment_length,
            seed=config.random_seed,
            output_dir=trial_output,
        )
        if training_summary.get("status") != "trained":
            raise RuntimeError(str(training_summary.get("reason", "RLlib training did not complete")))

        eval_backend = _build_predictor_runtime(rows, config)
        eval_summary = evaluate_heuristic_policy(
            eval_backend,
            alpha=alpha,
            beta=beta,
            gamma=gamma,
            steps=config.episode_steps,
        )
        return float(training_summary["episode_reward_mean"]) + (float(eval_summary["total_score"]) * 0.05)

    try:
        result = tune_policy_and_rewards(
            objective,
            n_trials=trials,
            storage_path=config.optuna_storage_path,
        )
        return asdict(result)
    except RuntimeError as exc:
        return {
            "status": "skipped",
            "reason": str(exc),
            "alpha": config.alpha,
            "beta": config.beta,
            "gamma": config.gamma,
            "learning_rate": config.ppo_learning_rate,
            "train_batch_size": config.ppo_train_batch_size,
            "minibatch_size": config.ppo_minibatch_size,
            "num_epochs": config.ppo_num_epochs,
            "rollout_fragment_length": config.ppo_rollout_fragment_length,
        }


def run_full_process(config: OrchestratorConfig, *, tune_trials: int) -> dict[str, Any]:
    trace = ensure_trace_exists(config)
    models = train_brain_models(config)
    episode = run_episode(config)
    ppo = run_policy_training(config, output_dir="orchestrator_stack/runtime/rllib")
    reward_tune = tune_reward_layer(config, trials=tune_trials)
    policy_tune = tune_policy_and_reward_layer(config, trials=tune_trials)

    return {
        "trace": str(trace),
        "models": models,
        "episode": asdict(episode),
        "ppo": ppo,
        "reward_tuning": reward_tune,
        "policy_reward_tuning": policy_tune,
    }
