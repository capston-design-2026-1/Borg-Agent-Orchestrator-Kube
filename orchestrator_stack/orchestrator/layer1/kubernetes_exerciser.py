from __future__ import annotations

import subprocess
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any

LABEL = "app.kubernetes.io/part-of=borg-orchestrator-exerciser"


@dataclass(frozen=True, slots=True)
class ExercisePhase:
    name: str
    detail: str
    manifest: str | None = None
    operation: str = "delete"
    deployment: str | None = None
    cpu_request: str | None = None
    memory_request: str | None = None


def _deployment_manifest(namespace: str, name: str, *, cpu: str, memory: str) -> str:
    return f"""
apiVersion: v1
kind: Namespace
metadata:
  name: {namespace}
  labels:
    app.kubernetes.io/part-of: borg-orchestrator-exerciser
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {name}
  namespace: {namespace}
  labels:
    app.kubernetes.io/part-of: borg-orchestrator-exerciser
spec:
  replicas: 1
  selector:
    matchLabels:
      app.kubernetes.io/name: {name}
      app.kubernetes.io/part-of: borg-orchestrator-exerciser
  template:
    metadata:
      labels:
        app.kubernetes.io/name: {name}
        app.kubernetes.io/part-of: borg-orchestrator-exerciser
    spec:
      terminationGracePeriodSeconds: 0
      containers:
        - name: pause
          image: registry.k8s.io/pause:3.10
          resources:
            requests:
              cpu: {cpu}
              memory: {memory}
            limits:
              cpu: {cpu}
              memory: {memory}
""".strip()


def _namespace_manifest(namespace: str) -> str:
    return f"""
apiVersion: v1
kind: Namespace
metadata:
  name: {namespace}
  labels:
    app.kubernetes.io/part-of: borg-orchestrator-exerciser
""".strip()


def exercise_phases(namespace: str) -> list[ExercisePhase]:
    return [
        ExercisePhase(
            name="idle-efficiency",
            detail="clear exercise deployments so AgentB sees low demand and can recommend efficiency action",
        ),
        ExercisePhase(
            name="moderate-demand",
            detail="create moderate requested load so AgentC admission/referee path has a non-efficiency decision opportunity",
            manifest=_deployment_manifest(namespace, "moderate-demand", cpu="8500m", memory="128Mi"),
            operation="apply",
            deployment="moderate-demand",
            cpu_request="8500m",
            memory_request="128Mi",
        ),
        ExercisePhase(
            name="high-risk",
            detail="create high requested load so AgentA risk mitigation path has a safety decision opportunity",
            manifest=_deployment_manifest(namespace, "high-risk", cpu="8800m", memory="3Gi"),
            operation="apply",
            deployment="high-risk",
            cpu_request="8800m",
            memory_request="3Gi",
        ),
    ]


def _randomized_phase(namespace: str, phase_index: int, *, seed: int | None = None) -> ExercisePhase:
    rng = random.Random(None if seed is None else seed + phase_index)
    phase_name = rng.choices(
        ["idle-efficiency", "moderate-demand", "high-risk", "bursty-safety", "memory-pressure"],
        weights=[0.18, 0.28, 0.28, 0.16, 0.10],
        k=1,
    )[0]
    if phase_name == "idle-efficiency":
        return ExercisePhase(
            name=phase_name,
            detail="randomized idle window: clear exercise deployments so efficiency and observation paths can settle",
        )
    if phase_name == "moderate-demand":
        cpu_milli = rng.randint(6500, 8800)
        mem_mi = rng.randint(96, 768)
        return ExercisePhase(
            name=phase_name,
            detail=f"randomized moderate demand: cpu={cpu_milli}m memory={mem_mi}Mi",
            manifest=_deployment_manifest(namespace, phase_name, cpu=f"{cpu_milli}m", memory=f"{mem_mi}Mi"),
            operation="apply",
            deployment=phase_name,
            cpu_request=f"{cpu_milli}m",
            memory_request=f"{mem_mi}Mi",
        )
    if phase_name == "high-risk":
        cpu_milli = rng.randint(8600, 9900)
        mem_mi = rng.randint(1536, 4096)
        return ExercisePhase(
            name=phase_name,
            detail=f"randomized high risk: cpu={cpu_milli}m memory={mem_mi}Mi",
            manifest=_deployment_manifest(namespace, phase_name, cpu=f"{cpu_milli}m", memory=f"{mem_mi}Mi"),
            operation="apply",
            deployment=phase_name,
            cpu_request=f"{cpu_milli}m",
            memory_request=f"{mem_mi}Mi",
        )
    if phase_name == "bursty-safety":
        cpu_milli = rng.randint(9000, 10000)
        mem_mi = rng.randint(512, 2048)
        return ExercisePhase(
            name=phase_name,
            detail=f"randomized burst: cpu={cpu_milli}m memory={mem_mi}Mi",
            manifest=_deployment_manifest(namespace, phase_name, cpu=f"{cpu_milli}m", memory=f"{mem_mi}Mi"),
            operation="apply",
            deployment=phase_name,
            cpu_request=f"{cpu_milli}m",
            memory_request=f"{mem_mi}Mi",
        )
    cpu_milli = rng.randint(4000, 7200)
    mem_mi = rng.randint(2048, 5120)
    return ExercisePhase(
        name=phase_name,
        detail=f"randomized memory pressure: cpu={cpu_milli}m memory={mem_mi}Mi",
        manifest=_deployment_manifest(namespace, phase_name, cpu=f"{cpu_milli}m", memory=f"{mem_mi}Mi"),
        operation="apply",
        deployment=phase_name,
        cpu_request=f"{cpu_milli}m",
        memory_request=f"{mem_mi}Mi",
    )


def _run_kubectl(kubeconfig: str | Path, args: list[str], *, stdin: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["kubectl", "--kubeconfig", str(kubeconfig), *args],
        input=stdin,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def cleanup_exercise_workloads(kubeconfig: str | Path, namespace: str) -> dict[str, Any]:
    namespace_apply = _run_kubectl(kubeconfig, ["apply", "-f", "-"], stdin=_namespace_manifest(namespace))
    completed = _run_kubectl(
        kubeconfig,
        ["-n", namespace, "delete", "deployment", "-l", LABEL, "--ignore-not-found"],
    )
    return {
        "command": "delete exercise deployments",
        "namespace": {
            "returncode": namespace_apply.returncode,
            "stdout": namespace_apply.stdout.strip(),
            "stderr": namespace_apply.stderr.strip(),
        },
        "returncode": completed.returncode,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
    }


def apply_exercise_phase(
    kubeconfig: str | Path,
    namespace: str,
    phase_index: int,
    *,
    randomize: bool = False,
    seed: int | None = None,
) -> dict[str, Any]:
    phases = exercise_phases(namespace)
    phase = _randomized_phase(namespace, phase_index, seed=seed) if randomize else phases[phase_index % len(phases)]
    cleanup = cleanup_exercise_workloads(kubeconfig, namespace)
    result = {
        "phase": phase.name,
        "detail": phase.detail,
        "namespace": namespace,
        "operation": phase.operation,
        "deployment": phase.deployment,
        "resources": {
            "cpu_request": phase.cpu_request,
            "memory_request": phase.memory_request,
        },
        "cleanup": cleanup,
        "applied": None,
        "randomized": randomize,
    }
    if phase.manifest is not None:
        completed = _run_kubectl(kubeconfig, ["apply", "-f", "-"], stdin=phase.manifest)
        rollout = _run_kubectl(
            kubeconfig,
            ["-n", namespace, "rollout", "status", f"deployment/{phase.name}", "--timeout=30s"],
        )
        result["applied"] = {
            "command": "apply exercise manifest",
            "returncode": completed.returncode,
            "stdout": completed.stdout.strip(),
            "stderr": completed.stderr.strip(),
        }
        result["rollout"] = {
            "command": f"rollout status deployment/{phase.name}",
            "returncode": rollout.returncode,
            "stdout": rollout.stdout.strip(),
            "stderr": rollout.stderr.strip(),
        }
    return result
