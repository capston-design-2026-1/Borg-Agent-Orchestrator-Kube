from __future__ import annotations

import os
from hashlib import sha1
from pathlib import Path
from typing import Any

from orchestrator.layer4.policy import default_policy_actions
from orchestrator.layer4.rllib_env import OrchestratorMultiAgentEnv
from orchestrator.layer4.referee import resolve
from orchestrator.layer4.policy import decode_agent_action
from orchestrator.layer6.scoreboard import Scoreboard

try:
    from ray.rllib.algorithms.ppo import PPOConfig
except Exception:  # pragma: no cover
    PPOConfig = None


def _init_ray(ray_module: Any, *, temp_dir: Path) -> None:
    safe_temp_dir = Path("/tmp") / f"borg_ray_{sha1(str(temp_dir.resolve()).encode()).hexdigest()[:10]}"
    safe_temp_dir.mkdir(parents=True, exist_ok=True)
    init_kwargs = {
        "include_dashboard": False,
        "ignore_reinit_error": True,
        "num_cpus": 1,
        "_temp_dir": str(safe_temp_dir),
    }
    try:
        ray_module.init(local_mode=True, **init_kwargs)
    except RuntimeError as exc:
        if "local_mode" not in str(exc):
            raise
        ray_module.init(**init_kwargs)


def train_multiagent_ppo(
    backend,
    *,
    alpha: float,
    beta: float,
    gamma: float,
    learning_rate: float,
    train_iters: int,
    train_batch_size: int = 32,
    minibatch_size: int = 16,
    num_epochs: int = 1,
    rollout_fragment_length: int = 8,
    seed: int | None = None,
    output_dir: str | Path,
) -> dict[str, Any]:
    os.environ.setdefault("OMP_NUM_THREADS", "1")
    os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
    os.environ.setdefault("MKL_NUM_THREADS", "1")
    os.environ.setdefault("VECLIB_MAXIMUM_THREADS", "1")
    os.environ.setdefault("NUMEXPR_NUM_THREADS", "1")
    os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
    os.environ.setdefault("KMP_INIT_AT_FORK", "FALSE")
    os.environ.setdefault("RAY_ENABLE_UV_RUN_RUNTIME_ENV", "0")

    out = Path(output_dir).resolve()
    out.mkdir(parents=True, exist_ok=True)

    if PPOConfig is None:
        return {
            "status": "skipped",
            "reason": "ray[rllib] is not installed",
            "output_dir": str(out),
        }

    env_name = "OrchestratorMultiAgentEnv"

    # Delayed import avoids hard dependency when RLlib is not installed.
    from ray.tune.registry import register_env

    try:
        import ray
        import ray.train.constants as ray_train_constants
        import ray.tune.trainable.trainable as ray_trainable
    except Exception as exc:
        return {
            "status": "skipped",
            "reason": f"ray initialization modules unavailable: {exc}",
            "output_dir": str(out),
        }

    ray_train_constants.DEFAULT_STORAGE_PATH = str(out)
    ray_trainable.DEFAULT_STORAGE_PATH = str(out)
    if not ray.is_initialized():
        _init_ray(ray, temp_dir=out / "ray_cluster")

    register_env(env_name, lambda cfg: OrchestratorMultiAgentEnv(cfg))

    policies = {"AgentA", "AgentB", "AgentC"}

    config = (
        PPOConfig()
        .environment(env=env_name, env_config={"backend": backend, "alpha": alpha, "beta": beta, "gamma": gamma})
        .framework("torch")
        .training(
            lr=learning_rate,
            train_batch_size=train_batch_size,
            minibatch_size=minibatch_size,
            num_epochs=num_epochs,
        )
        .multi_agent(
            policies=policies,
            policy_mapping_fn=lambda agent_id, *args, **kwargs: agent_id,
        )
        .resources(num_gpus=0)
        .env_runners(
            num_env_runners=0,
            num_envs_per_env_runner=1,
            rollout_fragment_length=rollout_fragment_length,
            batch_mode="truncate_episodes",
        )
        .reporting(min_sample_timesteps_per_iteration=8, min_train_timesteps_per_iteration=8, min_time_s_per_iteration=0)
    )
    if seed is not None:
        config = config.debugging(seed=int(seed))

    algo = config.build_algo()
    last_result: dict[str, Any] = {}
    for _ in range(max(1, train_iters)):
        last_result = algo.train()

    checkpoint_result = algo.save(checkpoint_dir=str(out))
    checkpoint_path = str(out)
    try:
        checkpoint_path = str(checkpoint_result.checkpoint.path)
    except Exception:
        checkpoint_path = str(checkpoint_result)

    algo.stop()
    try:
        ray.shutdown()
    except Exception:
        pass

    env_runners = last_result.get("env_runners", {})
    objective_reward = float(
        last_result.get(
            "episode_reward_mean",
            env_runners.get("episode_return_mean", env_runners.get("agent_episode_returns_mean", 0.0)),
        )
    )

    return {
        "status": "trained",
        "checkpoint": checkpoint_path,
        "train_iters": int(train_iters),
        "episode_reward_mean": objective_reward,
        "train_batch_size": int(train_batch_size),
        "minibatch_size": int(minibatch_size),
        "num_epochs": int(num_epochs),
        "rollout_fragment_length": int(rollout_fragment_length),
        "learning_rate": float(learning_rate),
        "seed": int(seed) if seed is not None else None,
    }


def train_curriculum_ppo(
    backend_factory,
    *,
    alpha: float,
    beta: float,
    gamma: float,
    stages: list[dict[str, Any]],
    seed: int | None = None,
    output_dir: str | Path,
) -> dict[str, Any]:
    out = Path(output_dir)
    stage_results = []
    for index, stage in enumerate(stages, start=1):
        stage_output = out / f"stage_{index:02d}"
        stage_seed = stage.get("seed")
        if stage_seed is None and seed is not None:
            stage_seed = seed + index - 1
        result = train_multiagent_ppo(
            backend_factory(),
            alpha=float(stage.get("alpha", alpha)),
            beta=float(stage.get("beta", beta)),
            gamma=float(stage.get("gamma", gamma)),
            learning_rate=float(stage["learning_rate"]),
            train_iters=int(stage["train_iters"]),
            train_batch_size=int(stage["train_batch_size"]),
            minibatch_size=int(stage["minibatch_size"]),
            num_epochs=int(stage["num_epochs"]),
            rollout_fragment_length=int(stage["rollout_fragment_length"]),
            seed=int(stage_seed) if stage_seed is not None else None,
            output_dir=stage_output,
        )
        stage_results.append({"stage": index, **result})
        if result.get("status") != "trained":
            return {"status": "skipped", "reason": result.get("reason", "curriculum stage did not train"), "stages": stage_results}

    return {"status": "trained", "stages": stage_results, "stage_count": len(stage_results)}


def policy_training_reward_mean(training_summary: dict[str, Any]) -> float | None:
    if training_summary.get("status") != "trained":
        return None
    if "episode_reward_mean" in training_summary:
        return float(training_summary["episode_reward_mean"])
    stage_rewards = [
        float(stage["episode_reward_mean"])
        for stage in training_summary.get("stages", [])
        if stage.get("status") == "trained" and "episode_reward_mean" in stage
    ]
    if not stage_rewards:
        return None
    return stage_rewards[-1]


def compare_policy_training_to_heuristic(
    training_summary: dict[str, Any],
    heuristic_summary: dict[str, float | int],
) -> dict[str, Any]:
    policy_reward = policy_training_reward_mean(training_summary)
    heuristic_total = float(heuristic_summary.get("total_score", heuristic_summary.get("avg_score", 0.0)))
    heuristic_average = float(heuristic_summary.get("avg_score", heuristic_total))
    if policy_reward is None:
        return {
            "status": "skipped",
            "reason": "policy training did not produce an episode_reward_mean",
            "heuristic_total_score": heuristic_total,
            "heuristic_avg_score": heuristic_average,
        }
    return {
        "status": "compared",
        "policy_episode_reward_mean": policy_reward,
        "heuristic_total_score": heuristic_total,
        "heuristic_avg_score": heuristic_average,
        "delta_vs_heuristic": policy_reward - heuristic_total,
        "beats_heuristic": policy_reward > heuristic_total,
    }


def evaluate_heuristic_policy(backend, *, alpha: float, beta: float, gamma: float, steps: int) -> dict[str, float | int]:
    obs = backend.reset()
    scoreboard = Scoreboard(alpha=alpha, beta=beta, gamma=gamma)

    for _ in range(max(1, steps)):
        action_ids = default_policy_actions(obs)
        proposals = [
            decode_agent_action("AgentA", action_ids["AgentA"], obs),
            decode_agent_action("AgentB", action_ids["AgentB"], obs),
            decode_agent_action("AgentC", action_ids["AgentC"], obs),
        ]
        action = resolve(proposals)
        result = backend.step(action)
        scoreboard.update(result.reward_by_agent)
        obs = result.next_observation
        if result.done:
            break

    return {
        "steps": len(scoreboard.history),
        "total_score": scoreboard.total(),
        "avg_score": scoreboard.average(),
    }
