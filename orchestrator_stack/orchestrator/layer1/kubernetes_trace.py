from __future__ import annotations

import json
import subprocess
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from orchestrator.layer1.prometheus import query_node_exporter_utilization

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


@dataclass(frozen=True, slots=True)
class PowerCalibration:
    idle_watts: float = 80.0
    cpu_full_scale_watts: float = 120.0
    mem_full_scale_watts: float = 60.0
    source: str = "default_utilization_model"

    @classmethod
    def from_mapping(cls, payload: dict[str, Any]) -> "PowerCalibration":
        return cls(
            idle_watts=max(0.0, float(payload.get("idle_watts", cls.idle_watts))),
            cpu_full_scale_watts=max(0.0, float(payload.get("cpu_full_scale_watts", cls.cpu_full_scale_watts))),
            mem_full_scale_watts=max(0.0, float(payload.get("mem_full_scale_watts", cls.mem_full_scale_watts))),
            source=str(payload.get("source", cls.source)),
        )


DEFAULT_POWER_CALIBRATION = PowerCalibration()


def load_power_calibration(path: str | Path | None) -> PowerCalibration:
    if path is None:
        return DEFAULT_POWER_CALIBRATION
    payload = json.loads(Path(path).expanduser().read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("power calibration file must contain a JSON object")
    return PowerCalibration.from_mapping(payload)


def estimate_node_power_watts(cpu_util: float, mem_util: float, calibration: PowerCalibration | None = None) -> float:
    calibrated = calibration or DEFAULT_POWER_CALIBRATION
    return (
        calibrated.idle_watts
        + (calibrated.cpu_full_scale_watts * _bounded_ratio(cpu_util))
        + (calibrated.mem_full_scale_watts * _bounded_ratio(mem_util))
    )


def _attach_power_metadata(row: dict[str, Any], calibration: PowerCalibration) -> None:
    row["power_calibration"] = asdict(calibration)


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
    if pod.get("status", {}).get("phase") == "Succeeded":
        return True
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
    completed = phase == "Succeeded"
    return {
        "task_id": f"{namespace}/{name}",
        "node_id": pod.get("spec", {}).get("nodeName") or "unscheduled",
        "urgency": 0.0 if completed else (1.0 if phase in {"Failed", "Pending"} or restarts > 0 or not ready else 0.2),
        "queue_priority": restarts,
        "alive": completed or (phase not in {"Failed", "Unknown"} and metadata.get("deletionTimestamp") is None),
    }


def _bounded_ratio(value: float) -> float:
    return min(1.0, max(0.0, float(value)))


def _sample_for_node(samples: dict[str, float], node_id: str, node_count: int) -> float | None:
    if node_id in samples:
        return samples[node_id]
    for key, value in samples.items():
        if node_id in key or key in node_id:
            return value
    if node_count == 1 and samples:
        return sum(samples.values()) / len(samples)
    return None


def enrich_trace_row_with_prometheus(
    row: dict[str, Any],
    samples: dict[str, dict[str, float]],
    *,
    power_calibration: PowerCalibration | None = None,
) -> dict[str, Any]:
    nodes = row.get("nodes", [])
    if not isinstance(nodes, list) or not nodes:
        return row

    total_energy = 0.0
    calibration = power_calibration or DEFAULT_POWER_CALIBRATION
    p_fail_scores = dict(row.get("p_fail_scores", {}))
    demand_projection = dict(row.get("demand_projection", {}))
    node_count = len(nodes)
    for node in nodes:
        if not isinstance(node, dict):
            continue
        node_id = str(node.get("node_id", "unknown-node"))
        cpu_sample = _sample_for_node(samples.get("cpu_util", {}), node_id, node_count)
        mem_sample = _sample_for_node(samples.get("mem_util", {}), node_id, node_count)
        if cpu_sample is not None:
            node["cpu_util"] = _bounded_ratio(cpu_sample)
        if mem_sample is not None:
            node["mem_util"] = _bounded_ratio(mem_sample)
        cpu_util = float(node.get("cpu_util", 0.0))
        mem_util = float(node.get("mem_util", 0.0))
        utilization_risk = (0.55 * cpu_util) + (0.35 * mem_util)
        p_fail_scores[node_id] = round(min(1.0, max(float(p_fail_scores.get(node_id, 0.0)), utilization_risk)), 6)
        demand_projection[node_id] = round(_bounded_ratio((0.55 * cpu_util) + (0.35 * mem_util)), 6)
        total_energy += estimate_node_power_watts(cpu_util, mem_util, calibration)

    row["p_fail_scores"] = p_fail_scores
    row["demand_projection"] = demand_projection
    row["energy_watts"] = round(total_energy, 6)
    _attach_power_metadata(row, calibration)
    row["telemetry_sources"] = sorted(set(row.get("telemetry_sources", ["kubernetes_api"])) | {"prometheus_node_exporter"})
    return row


def kubernetes_snapshot_to_trace_row(
    *,
    nodes_payload: dict[str, Any],
    pods_payload: dict[str, Any],
    jobs_payload: dict[str, Any] | None = None,
    timestamp: int | None = None,
    namespace_prefixes: tuple[str, ...] = ("test-", "default"),
    power_calibration: PowerCalibration | None = None,
) -> dict[str, Any]:
    pods = pods_payload.get("items", [])
    jobs = (jobs_payload or {}).get("items", [])
    pods_by_node: dict[str, list[dict[str, Any]]] = {}
    for pod in pods:
        node_name = pod.get("spec", {}).get("nodeName") or "unscheduled"
        pods_by_node.setdefault(node_name, []).append(pod)

    nodes = []
    p_fail_scores: dict[str, float] = {}
    demand_projection: dict[str, float] = {}
    total_energy = 0.0
    calibration = power_calibration or DEFAULT_POWER_CALIBRATION
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
        node_pods = pods_by_node.get(name, [])
        unhealthy_pods = [
            pod
            for pod in node_pods
            if pod.get("status", {}).get("phase") in {"Failed", "Pending", "Unknown"} or not _pod_ready(pod)
        ]
        restart_count = sum(_pod_restart_count(pod) for pod in node_pods)
        health_risk = 0.95 if unhealthy_pods else (0.7 if restart_count else 0.0)
        utilization_risk = (0.55 * cpu_util) + (0.35 * mem_util)
        p_fail_scores[name] = round(min(1.0, max(health_risk, utilization_risk)), 6)
        demand_projection[name] = round(min(1.0, max(0.0, (0.55 * cpu_util) + (0.35 * mem_util))), 6)
        node_energy = estimate_node_power_watts(cpu_util, mem_util, calibration)
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
    active_target_pods = [pod for pod in target_pods if pod.get("status", {}).get("phase") != "Succeeded"]
    tasks = [_pod_task(pod) for pod in active_target_pods]
    sla_violations = sum(
        1
        for pod in active_target_pods
        if pod.get("status", {}).get("phase") in {"Failed", "Pending", "Unknown"} or not _pod_ready(pod)
    )
    completed_tasks = sum(1 for pod in target_pods if pod.get("status", {}).get("phase") == "Succeeded")
    completed_tasks += sum(int(job.get("status", {}).get("succeeded", 0)) for job in jobs)
    queue_length = sum(1 for pod in target_pods if pod.get("status", {}).get("phase") == "Pending")
    task_death = any(not task["alive"] for task in tasks)

    row = {
        "timestamp": int(timestamp if timestamp is not None else time.time()),
        "nodes": nodes,
        "tasks": tasks,
        "queue_length": queue_length,
        "energy_price": 0.1,
        "task_death": task_death,
        "sla_violations": int(sla_violations),
        "completed_tasks": int(completed_tasks),
        "energy_watts": round(total_energy, 6),
        "p_fail_scores": p_fail_scores,
        "demand_projection": demand_projection,
    }
    _attach_power_metadata(row, calibration)
    return row


def capture_kubernetes_trace_row(
    *,
    kubeconfig: str | Path,
    namespace_prefixes: tuple[str, ...] = ("test-", "default"),
    prometheus_base_url: str | None = None,
    power_calibration: PowerCalibration | None = None,
) -> dict[str, Any]:
    row = kubernetes_snapshot_to_trace_row(
        nodes_payload=_kubectl_json(kubeconfig, "nodes"),
        pods_payload=_kubectl_json(kubeconfig, "pods"),
        jobs_payload=_kubectl_json(kubeconfig, "jobs"),
        namespace_prefixes=namespace_prefixes,
        power_calibration=power_calibration,
    )
    row["telemetry_sources"] = ["kubernetes_api"]
    if prometheus_base_url:
        try:
            samples = query_node_exporter_utilization(prometheus_base_url)
            row = enrich_trace_row_with_prometheus(row, samples, power_calibration=power_calibration)
        except Exception as exc:
            row["prometheus_error"] = str(exc)
    return row


def write_kubernetes_trace(rows: list[dict[str, Any]], out_path: str | Path) -> Path:
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    ordered = sorted(rows, key=lambda row: int(row.get("timestamp", 0)))
    out.write_text(json.dumps(ordered, indent=2), encoding="utf-8")
    return out
