from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path
from typing import Any

CPU_MILLI = 1000.0
MEMORY_UNITS = {
    "Ki": 1024,
    "Mi": 1024**2,
    "Gi": 1024**3,
    "Ti": 1024**4,
    "Pi": 1024**5,
    "Ei": 1024**6,
    "K": 1000,
    "M": 1000**2,
    "G": 1000**3,
    "T": 1000**4,
    "P": 1000**5,
    "E": 1000**6,
}


def parse_cpu_milli(value: str | int | float | None) -> float:
    if value is None:
        return 0.0
    if isinstance(value, int | float):
        return float(value) * CPU_MILLI
    text = str(value).strip()
    if not text:
        return 0.0
    if text.endswith("m"):
        return float(text[:-1] or 0)
    return float(text) * CPU_MILLI


def parse_memory_bytes(value: str | int | float | None) -> float:
    if value is None:
        return 0.0
    if isinstance(value, int | float):
        return float(value)
    text = str(value).strip()
    if not text:
        return 0.0
    for suffix, multiplier in MEMORY_UNITS.items():
        if text.endswith(suffix):
            return float(text[: -len(suffix)] or 0) * multiplier
    return float(text)


def _kubectl_json(kubeconfig: str | Path, resource: str) -> dict[str, Any]:
    completed = subprocess.run(
        ["kubectl", "--kubeconfig", str(kubeconfig), "get", resource, "-A", "-o", "json"],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return json.loads(completed.stdout)


def _container_requests(pod: dict[str, Any]) -> tuple[float, float]:
    cpu_milli = 0.0
    memory_bytes = 0.0
    for container in pod.get("spec", {}).get("containers", []):
        requests = container.get("resources", {}).get("requests", {})
        cpu_milli += parse_cpu_milli(requests.get("cpu"))
        memory_bytes += parse_memory_bytes(requests.get("memory"))
    return cpu_milli, memory_bytes


def _pod_restart_count(pod: dict[str, Any]) -> int:
    return sum(int(status.get("restartCount", 0)) for status in pod.get("status", {}).get("containerStatuses", []))


def _pod_ready(pod: dict[str, Any]) -> bool:
    statuses = pod.get("status", {}).get("containerStatuses", [])
    if not statuses:
        return pod.get("status", {}).get("phase") == "Succeeded"
    return all(bool(status.get("ready")) for status in statuses)


def _pod_task(pod: dict[str, Any]) -> dict[str, Any]:
    metadata = pod.get("metadata", {})
    status = pod.get("status", {})
    namespace = metadata.get("namespace", "default")
    name = metadata.get("name", "unknown-pod")
    phase = status.get("phase", "Unknown")
    restarts = _pod_restart_count(pod)
    ready = _pod_ready(pod)
    return {
        "task_id": f"{namespace}/{name}",
        "node_id": pod.get("spec", {}).get("nodeName") or "unscheduled",
        "urgency": 1.0 if phase in {"Failed", "Pending"} or restarts > 0 or not ready else 0.2,
        "queue_priority": restarts,
        "alive": phase not in {"Failed", "Unknown"} and metadata.get("deletionTimestamp") is None,
    }


def kubernetes_snapshot_to_trace_row(
    *,
    nodes_payload: dict[str, Any],
    pods_payload: dict[str, Any],
    jobs_payload: dict[str, Any] | None = None,
    timestamp: int | None = None,
    namespace_prefixes: tuple[str, ...] = ("test-", "default"),
) -> dict[str, Any]:
    pods = pods_payload.get("items", [])
    jobs = (jobs_payload or {}).get("items", [])
    pods_by_node: dict[str, list[dict[str, Any]]] = {}
    for pod in pods:
        node_name = pod.get("spec", {}).get("nodeName") or "unscheduled"
        pods_by_node.setdefault(node_name, []).append(pod)

    nodes = []
    total_energy = 0.0
    for node in nodes_payload.get("items", []):
        name = node.get("metadata", {}).get("name", "unknown-node")
        allocatable = node.get("status", {}).get("allocatable", {})
        alloc_cpu = max(parse_cpu_milli(allocatable.get("cpu")), 1.0)
        alloc_mem = max(parse_memory_bytes(allocatable.get("memory")), 1.0)
        req_cpu = 0.0
        req_mem = 0.0
        for pod in pods_by_node.get(name, []):
            cpu, mem = _container_requests(pod)
            req_cpu += cpu
            req_mem += mem
        cpu_util = min(1.0, max(0.0, req_cpu / alloc_cpu))
        mem_util = min(1.0, max(0.0, req_mem / alloc_mem))
        node_energy = 80.0 + (120.0 * cpu_util) + (60.0 * mem_util)
        total_energy += node_energy
        nodes.append(
            {
                "node_id": name,
                "cpu_util": cpu_util,
                "mem_util": mem_util,
                "disk_util": 0.0,
                "net_util": 0.0,
                "power_state": "on",
            }
        )

    target_pods = [
        pod
        for pod in pods
        if pod.get("metadata", {}).get("namespace", "").startswith(namespace_prefixes)
    ]
    tasks = [_pod_task(pod) for pod in target_pods]
    sla_violations = sum(
        1
        for pod in target_pods
        if pod.get("status", {}).get("phase") in {"Failed", "Pending", "Unknown"} or not _pod_ready(pod)
    )
    completed_tasks = sum(1 for pod in target_pods if pod.get("status", {}).get("phase") == "Succeeded")
    completed_tasks += sum(int(job.get("status", {}).get("succeeded", 0)) for job in jobs)
    queue_length = sum(1 for pod in target_pods if pod.get("status", {}).get("phase") == "Pending")
    task_death = any(not task["alive"] for task in tasks)

    return {
        "timestamp": int(timestamp if timestamp is not None else time.time()),
        "nodes": nodes,
        "tasks": tasks,
        "queue_length": queue_length,
        "energy_price": 0.1,
        "task_death": task_death,
        "sla_violations": int(sla_violations),
        "completed_tasks": int(completed_tasks),
        "energy_watts": round(total_energy, 6),
    }


def capture_kubernetes_trace_row(
    *,
    kubeconfig: str | Path,
    namespace_prefixes: tuple[str, ...] = ("test-", "default"),
) -> dict[str, Any]:
    return kubernetes_snapshot_to_trace_row(
        nodes_payload=_kubectl_json(kubeconfig, "nodes"),
        pods_payload=_kubectl_json(kubeconfig, "pods"),
        jobs_payload=_kubectl_json(kubeconfig, "jobs"),
        namespace_prefixes=namespace_prefixes,
    )


def write_kubernetes_trace(rows: list[dict[str, Any]], out_path: str | Path) -> Path:
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    return out
