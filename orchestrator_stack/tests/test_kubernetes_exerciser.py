from orchestrator.layer1 import kubernetes_exerciser


def test_exercise_phases_cover_idle_moderate_and_high_risk():
    phases = kubernetes_exerciser.exercise_phases("demo")

    assert [phase.name for phase in phases] == ["idle-efficiency", "moderate-demand", "high-risk"]
    assert phases[0].manifest is None
    assert "8500m" in phases[1].manifest
    assert "8800m" in phases[2].manifest
    assert "3Gi" in phases[2].manifest
    assert "namespace: demo" in phases[2].manifest


def test_apply_exercise_phase_deletes_before_apply(monkeypatch):
    calls = []

    def fake_run(kubeconfig, args, *, stdin=None):
        calls.append({"kubeconfig": kubeconfig, "args": args, "stdin": stdin})

        class Completed:
            returncode = 0
            stdout = "ok"
            stderr = ""

        return Completed()

    monkeypatch.setattr(kubernetes_exerciser, "_run_kubectl", fake_run)

    result = kubernetes_exerciser.apply_exercise_phase("/tmp/kubeconfig", "demo", 1)

    assert result["phase"] == "moderate-demand"
    assert calls[0]["args"] == ["apply", "-f", "-"]
    assert "name: demo" in calls[0]["stdin"]
    assert calls[1]["args"] == ["-n", "demo", "delete", "deployment", "-l", kubernetes_exerciser.LABEL, "--ignore-not-found"]
    assert calls[2]["args"] == ["apply", "-f", "-"]
    assert "moderate-demand" in calls[2]["stdin"]
    assert calls[3]["args"] == ["-n", "demo", "rollout", "status", "deployment/moderate-demand", "--timeout=30s"]
    assert result["rollout"]["returncode"] == 0


def test_apply_exercise_phase_can_randomize_workload_shape(monkeypatch):
    calls = []

    def fake_run(kubeconfig, args, *, stdin=None):
        calls.append({"kubeconfig": kubeconfig, "args": args, "stdin": stdin})

        class Completed:
            returncode = 0
            stdout = "ok"
            stderr = ""

        return Completed()

    monkeypatch.setattr(kubernetes_exerciser, "_run_kubectl", fake_run)

    result = kubernetes_exerciser.apply_exercise_phase("/tmp/kubeconfig", "demo", 3, randomize=True, seed=7)

    assert result["randomized"] is True
    assert result["phase"] in {"idle-efficiency", "moderate-demand", "high-risk", "bursty-safety", "memory-pressure"}
    if result["phase"] != "idle-efficiency":
        assert "randomized" in result["detail"]
        assert "cpu=" in result["detail"]
        assert "memory=" in result["detail"]
        assert any("resources:" in call["stdin"] for call in calls if call["stdin"])
