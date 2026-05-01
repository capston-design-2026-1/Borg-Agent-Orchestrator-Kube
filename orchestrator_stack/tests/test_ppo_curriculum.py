from orchestrator.layer4 import ppo_trainer


class RayInitStub:
    def __init__(self):
        self.calls = []

    def init(self, **kwargs):
        self.calls.append(kwargs)
        if kwargs.get("local_mode") is True:
            raise RuntimeError("`local_mode` is no longer supported")


def test_init_ray_falls_back_when_local_mode_is_removed(tmp_path):
    ray = RayInitStub()

    ppo_trainer._init_ray(ray, temp_dir=tmp_path)

    assert len(ray.calls) == 2
    assert ray.calls[0]["local_mode"] is True
    assert "local_mode" not in ray.calls[1]
    assert "/borg_ray_" in str(ray.calls[1]["_temp_dir"])


def test_train_curriculum_ppo_runs_each_stage_with_fresh_backend(monkeypatch, tmp_path):
    calls = []

    def backend_factory():
        return {"backend": len(calls)}

    def fake_train_multiagent_ppo(backend, **kwargs):
        calls.append({"backend": backend, **kwargs})
        return {"status": "trained", "episode_reward_mean": 1.0, "checkpoint": str(kwargs["output_dir"])}

    monkeypatch.setattr(ppo_trainer, "train_multiagent_ppo", fake_train_multiagent_ppo)

    result = ppo_trainer.train_curriculum_ppo(
        backend_factory,
        alpha=1.0,
        beta=0.6,
        gamma=0.8,
        stages=[
            {
                "train_iters": 1,
                "learning_rate": 3e-4,
                "train_batch_size": 32,
                "minibatch_size": 16,
                "num_epochs": 1,
                "rollout_fragment_length": 8,
            },
            {
                "train_iters": 2,
                "learning_rate": 2e-4,
                "train_batch_size": 64,
                "minibatch_size": 32,
                "num_epochs": 2,
                "rollout_fragment_length": 16,
            },
        ],
        output_dir=tmp_path,
    )

    assert result["status"] == "trained"
    assert result["stage_count"] == 2
    assert len(calls) == 2
    assert calls[0]["train_iters"] == 1
    assert calls[1]["train_batch_size"] == 64


def test_compare_policy_training_to_heuristic_reports_delta_for_curriculum():
    result = ppo_trainer.compare_policy_training_to_heuristic(
        {
            "status": "trained",
            "stages": [
                {"status": "trained", "episode_reward_mean": 1.0},
                {"status": "trained", "episode_reward_mean": 3.5},
            ],
        },
        {"avg_score": 2.0},
    )

    assert result == {
        "status": "compared",
        "policy_episode_reward_mean": 3.5,
        "heuristic_avg_score": 2.0,
        "delta_vs_heuristic": 1.5,
        "beats_heuristic": True,
    }


def test_compare_policy_training_to_heuristic_skips_untrained_policy():
    result = ppo_trainer.compare_policy_training_to_heuristic({"status": "skipped"}, {"avg_score": 2.0})

    assert result["status"] == "skipped"
    assert result["heuristic_avg_score"] == 2.0
