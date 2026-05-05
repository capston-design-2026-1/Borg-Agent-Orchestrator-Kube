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
    replicas: int = 0
    node_selector: dict[str, str] | None = None
    intended_agent: str | None = None
    intended_action: str | None = None
    rollout_timeout_seconds: int = 8


def _deployment_manifest(
    namespace: str,
    name: str,
    *,
    cpu: str,
    memory: str,
    replicas: int = 1,
    node_selector: dict[str, str] | None = None,
) -> str:
    selector_block = ""
    if node_selector:
        entries = "\n".join(f"        {key}: {value}" for key, value in sorted(node_selector.items()))
        selector_block = f"\n      nodeSelector:\n{entries}"
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
  selector:
    matchLabels:
      app.kubernetes.io/name: {name}
      app.kubernetes.io/part-of: borg-orchestrator-exerciser
  replicas: {max(1, int(replicas))}
  template:
    metadata:
      labels:
        app.kubernetes.io/name: {name}
        app.kubernetes.io/part-of: borg-orchestrator-exerciser
    spec:
      terminationGracePeriodSeconds: 0{selector_block}
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
    unschedulable_selector = {"borg-orchestrator/exercise-slot": "unavailable"}
    return [
        ExercisePhase(
            name="idle-power-save",
            detail="clear exercise deployments so AgentB can evaluate an explicit low-demand power-state action",
            intended_agent="AgentB",
            intended_action="power_state:sleep",
        ),
        ExercisePhase(
            name="light-dvfs",
            detail="create light schedulable demand so AgentB can prefer DVFS over a full power-state transition",
            manifest=_deployment_manifest(namespace, "light-dvfs", cpu="2200m", memory="256Mi"),
            operation="apply",
            deployment="light-dvfs",
            cpu_request="2200m",
            memory_request="256Mi",
            replicas=1,
            intended_agent="AgentB",
            intended_action="dvfs",
        ),
        ExercisePhase(
            name="moderate-memory",
            detail="create moderate schedulable memory demand so AgentB can prefer memory ballooning",
            manifest=_deployment_manifest(namespace, "moderate-memory", cpu="6200m", memory="768Mi"),
            operation="apply",
            deployment="moderate-memory",
            cpu_request="6200m",
            memory_request="768Mi",
            replicas=1,
            intended_agent="AgentB",
            intended_action="memory_balloon",
        ),
        ExercisePhase(
            name="safety-throttle",
            detail="create moderate safety pressure so AgentA can throttle a risky node",
            manifest=_deployment_manifest(namespace, "safety-throttle", cpu="8600m", memory="1Gi"),
            operation="apply",
            deployment="safety-throttle",
            cpu_request="8600m",
            memory_request="1Gi",
            replicas=1,
            intended_agent="AgentA",
            intended_action="throttle",
        ),
        ExercisePhase(
            name="safety-migrate",
            detail="create high schedulable safety pressure so AgentA can select migration",
            manifest=_deployment_manifest(namespace, "safety-migrate", cpu="9200m", memory="5Gi"),
            operation="apply",
            deployment="safety-migrate",
            cpu_request="9200m",
            memory_request="5Gi",
            replicas=1,
            intended_agent="AgentA",
            intended_action="migrate",
        ),
        ExercisePhase(
            name="safety-replicate",
            detail="create severe schedulable pressure so AgentA can select replication before saturation",
            manifest=_deployment_manifest(namespace, "safety-replicate", cpu="9400m", memory="7Gi"),
            operation="apply",
            deployment="safety-replicate",
            cpu_request="9400m",
            memory_request="7Gi",
            replicas=1,
            intended_agent="AgentA",
            intended_action="replicate",
        ),
        ExercisePhase(
            name="admission-queue",
            detail="create unschedulable queued work so AgentC can explicitly queue work instead of optimizing energy",
            manifest=_deployment_manifest(
                namespace,
                "admission-queue",
                cpu="100m",
                memory="64Mi",
                replicas=12,
                node_selector=unschedulable_selector,
            ),
            operation="apply",
            deployment="admission-queue",
            cpu_request="100m",
            memory_request="64Mi",
            replicas=12,
            node_selector=unschedulable_selector,
            intended_agent="AgentC",
            intended_action="admission:queue",
            rollout_timeout_seconds=2,
        ),
        ExercisePhase(
            name="admission-deprioritize",
            detail="create a large unschedulable backlog so AgentC can deprioritize work",
            manifest=_deployment_manifest(
                namespace,
                "admission-deprioritize",
                cpu="100m",
                memory="64Mi",
                replicas=90,
                node_selector=unschedulable_selector,
            ),
            operation="apply",
            deployment="admission-deprioritize",
            cpu_request="100m",
            memory_request="64Mi",
            replicas=90,
            node_selector=unschedulable_selector,
            intended_agent="AgentC",
            intended_action="admission:deprioritize",
            rollout_timeout_seconds=2,
        ),
        ExercisePhase(
            name="admission-cap",
            detail="create a severe unschedulable backlog so AgentC can cap resources protectively",
            manifest=_deployment_manifest(
                namespace,
                "admission-cap",
                cpu="100m",
                memory="64Mi",
                replicas=130,
                node_selector=unschedulable_selector,
            ),
            operation="apply",
            deployment="admission-cap",
            cpu_request="100m",
            memory_request="64Mi",
            replicas=130,
            node_selector=unschedulable_selector,
            intended_agent="AgentC",
            intended_action="resource_cap",
            rollout_timeout_seconds=2,
        ),
    ]


def _randomized_phase(namespace: str, phase_index: int, *, seed: int | None = None) -> ExercisePhase:
    rng = random.Random(None if seed is None else seed + phase_index)
    phases = exercise_phases(namespace)
    template = phases[rng.randrange(len(phases))]
    if template.manifest is None:
        return ExercisePhase(
            name=template.name,
            detail=f"randomized {template.detail}",
            intended_agent=template.intended_agent,
            intended_action=template.intended_action,
            rollout_timeout_seconds=template.rollout_timeout_seconds,
        )

    if template.name == "light-dvfs":
        cpu_milli, mem_mi = rng.randint(1600, 2800), rng.randint(128, 512)
    elif template.name == "moderate-memory":
        cpu_milli, mem_mi = rng.randint(5200, 6800), rng.randint(512, 1280)
    elif template.name == "safety-throttle":
        cpu_milli, mem_mi = rng.randint(8200, 8800), rng.randint(768, 1536)
    elif template.name == "safety-migrate":
        cpu_milli, mem_mi = rng.randint(9000, 9300), rng.randint(4096, 5632)
    elif template.name == "safety-replicate":
        cpu_milli, mem_mi = rng.randint(9300, 9450), rng.randint(6656, 7424)
    else:
        cpu_milli, mem_mi = rng.randint(80, 200), rng.randint(48, 128)

    return ExercisePhase(
        name=template.name,
        detail=f"randomized {template.detail}: cpu={cpu_milli}m memory={mem_mi}Mi replicas={template.replicas}",
        manifest=_deployment_manifest(
            namespace,
            template.name,
            cpu=f"{cpu_milli}m",
            memory=f"{mem_mi}Mi",
            replicas=template.replicas or 1,
            node_selector=template.node_selector,
        ),
        operation="apply",
        deployment=template.name,
        cpu_request=f"{cpu_milli}m",
        memory_request=f"{mem_mi}Mi",
        replicas=template.replicas or 1,
        node_selector=template.node_selector,
        intended_agent=template.intended_agent,
        intended_action=template.intended_action,
        rollout_timeout_seconds=template.rollout_timeout_seconds,
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
            "replicas": phase.replicas,
            "node_selector": phase.node_selector,
        },
        "intended_agent": phase.intended_agent,
        "intended_action": phase.intended_action,
        "rollout_timeout_seconds": phase.rollout_timeout_seconds,
        "cleanup": cleanup,
        "applied": None,
        "randomized": randomize,
    }
    if phase.manifest is not None:
        completed = _run_kubectl(kubeconfig, ["apply", "-f", "-"], stdin=phase.manifest)
        rollout = _run_kubectl(
            kubeconfig,
            ["-n", namespace, "rollout", "status", f"deployment/{phase.name}", f"--timeout={phase.rollout_timeout_seconds}s"],
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
