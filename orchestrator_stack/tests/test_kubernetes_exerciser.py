from orchestrator.layer1 import kubernetes_exerciser


def test_exercise_phases_cover_idle_moderate_and_high_risk():
    phases = kubernetes_exerciser.exercise_phases("demo")

    assert [phase.name for phase in phases] == [
        "idle-power-save",
        "light-dvfs",
        "moderate-memory",
        "safety-throttle",
        "safety-migrate",
        "safety-replicate",
        "admission-queue",
        "admission-deprioritize",
        "admission-cap",
    ]
    assert phases[0].manifest is None
    assert phases[0].operation == "delete"
    assert phases[0].intended_action == "power_state:sleep"
    assert "2200m" in phases[1].manifest
    assert phases[1].operation == "apply"
    assert phases[1].deployment == "light-dvfs"
    assert phases[1].cpu_request == "2200m"
    assert "9400m" in phases[5].manifest
    assert "7Gi" in phases[5].manifest
    assert "namespace: demo" in phases[5].manifest
    assert phases[6].replicas == 12
    assert phases[6].node_selector == {"borg-orchestrator/exercise-slot": "unavailable"}
    assert phases[8].intended_action == "resource_cap"


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

    assert result["phase"] == "light-dvfs"
    assert result["operation"] == "apply"
    assert result["deployment"] == "light-dvfs"
    assert result["resources"]["cpu_request"] == "2200m"
    assert result["resources"]["memory_request"] == "256Mi"
    assert result["resources"]["replicas"] == 1
    assert result["intended_action"] == "dvfs"
    assert calls[0]["args"] == ["apply", "-f", "-"]
    assert "name: demo" in calls[0]["stdin"]
    assert calls[1]["args"] == ["-n", "demo", "delete", "deployment", "-l", kubernetes_exerciser.LABEL, "--ignore-not-found"]
    assert calls[2]["args"] == ["apply", "-f", "-"]
    assert "light-dvfs" in calls[2]["stdin"]
    assert calls[3]["args"] == ["-n", "demo", "rollout", "status", "deployment/light-dvfs", "--timeout=8s"]
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
    assert result["phase"] in {phase.name for phase in kubernetes_exerciser.exercise_phases("demo")}
    if result["phase"] != "idle-power-save":
        assert "randomized" in result["detail"]
        assert "cpu=" in result["detail"]
        assert "memory=" in result["detail"]
        assert any("resources:" in call["stdin"] for call in calls if call["stdin"])
