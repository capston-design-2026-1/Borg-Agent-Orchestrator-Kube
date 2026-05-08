from __future__ import annotations

import argparse
import json
import subprocess
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


CPU_SUFFIXES = {"n": 0.000001, "u": 0.001, "m": 1.0}
MEMORY_SUFFIXES = {
    "Ki": 1 / 1024,
    "Mi": 1.0,
    "Gi": 1024.0,
    "Ti": 1024.0 * 1024.0,
    "K": 1000 / 1024 / 1024,
    "M": 1000 * 1000 / 1024 / 1024,
    "G": 1000 * 1000 * 1000 / 1024 / 1024,
}


class ComparisonDashboardHandler(SimpleHTTPRequestHandler):
    dashboard_dir = Path("orchestrator_stack/comparison_dashboard")
    experimental_kubeconfig = Path("~/Documents/borg_orchestrator_clusters/kubeconfig-experimental").expanduser()
    baseline_kubeconfig = Path("~/Documents/borg_orchestrator_clusters/kubeconfig-baseline").expanduser()
    experimental_event_dir = Path("orchestrator_stack/runtime/visualization-experimental")
    karpenter_state_path = Path("orchestrator_stack/runtime/comparison/local_karpenter_state.json")
    shared_stimulus_path = Path("orchestrator_stack/runtime/comparison/shared_stimulus.json")

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, directory=str(self.dashboard_dir), **kwargs)

    def _json(self, payload: object, status: int = 200) -> None:
        body = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()

    @staticmethod
    def _kubectl_json(kubeconfig: Path, args: list[str]) -> dict[str, Any]:
        proc = subprocess.run(
            ["kubectl", "--kubeconfig", str(kubeconfig), *args, "-o", "json"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=8,
        )
        if proc.returncode != 0:
            return {"items": [], "error": proc.stderr.strip() or proc.stdout.strip()}
        return json.loads(proc.stdout)

    @staticmethod
    def _kubectl_text(kubeconfig: Path, args: list[str]) -> tuple[str, str | None]:
        proc = subprocess.run(
            ["kubectl", "--kubeconfig", str(kubeconfig), *args],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=8,
        )
        if proc.returncode != 0:
            return "", proc.stderr.strip() or proc.stdout.strip()
        return proc.stdout, None

    @staticmethod
    def _ready(node: dict[str, Any]) -> bool:
        for condition in node.get("status", {}).get("conditions", []):
            if condition.get("type") == "Ready":
                return condition.get("status") == "True"
        return False

    @staticmethod
    def _is_control_plane(node: dict[str, Any]) -> bool:
        labels = node.get("metadata", {}).get("labels", {})
        return "node-role.kubernetes.io/control-plane" in labels or "node-role.kubernetes.io/master" in labels

    @staticmethod
    def _parse_cpu_m(value: object) -> float:
        if value is None:
            return 0.0
        text = str(value).strip()
        if not text:
            return 0.0
        suffix = text[-1]
        if suffix in CPU_SUFFIXES:
            return float(text[:-1] or 0) * CPU_SUFFIXES[suffix]
        return float(text) * 1000.0

    @staticmethod
    def _parse_memory_mi(value: object) -> float:
        if value is None:
            return 0.0
        text = str(value).strip()
        if not text:
            return 0.0
        for suffix, multiplier in MEMORY_SUFFIXES.items():
            if text.endswith(suffix):
                return float(text[: -len(suffix)] or 0) * multiplier
        return float(text) / 1024 / 1024

    @staticmethod
    def _percent(value: float, total: float) -> float | None:
        if total <= 0:
            return None
        return round((value / total) * 100, 3)

    @staticmethod
    def _inc(counter: dict[str, int], key: str) -> None:
        counter[key] = counter.get(key, 0) + 1

    @classmethod
    def _node_top(cls, kubeconfig: Path) -> tuple[dict[str, dict[str, float]], str | None]:
        text, error = cls._kubectl_text(kubeconfig, ["top", "nodes", "--no-headers"])
        rows: dict[str, dict[str, float]] = {}
        for line in text.splitlines():
            parts = line.split()
            if len(parts) >= 5:
                rows[parts[0]] = {
                    "cpu_m": cls._parse_cpu_m(parts[1]),
                    "cpu_percent": float(parts[2].rstrip("%")),
                    "memory_mi": cls._parse_memory_mi(parts[3]),
                    "memory_percent": float(parts[4].rstrip("%")),
                }
        return rows, error

    @classmethod
    def _pod_top(cls, kubeconfig: Path) -> tuple[dict[str, dict[str, float]], str | None]:
        text, error = cls._kubectl_text(kubeconfig, ["top", "pods", "-A", "--no-headers"])
        by_namespace: dict[str, dict[str, float]] = {}
        for line in text.splitlines():
            parts = line.split()
            if len(parts) >= 4:
                namespace = parts[0]
                row = by_namespace.setdefault(namespace, {"cpu_m": 0.0, "memory_mi": 0.0, "pods": 0})
                row["cpu_m"] += cls._parse_cpu_m(parts[2])
                row["memory_mi"] += cls._parse_memory_mi(parts[3])
                row["pods"] += 1
        return by_namespace, error

    @classmethod
    def _node_summary(cls, nodes: list[dict[str, Any]], node_metrics: dict[str, dict[str, float]]) -> tuple[list[dict[str, Any]], dict[str, float]]:
        summaries: list[dict[str, Any]] = []
        totals = {
            "allocatable_cpu_m": 0.0,
            "allocatable_memory_mi": 0.0,
            "capacity_cpu_m": 0.0,
            "capacity_memory_mi": 0.0,
            "usage_cpu_m": 0.0,
            "usage_memory_mi": 0.0,
        }
        for node in sorted(nodes, key=lambda item: item.get("metadata", {}).get("name", "")):
            meta = node.get("metadata", {})
            labels = meta.get("labels", {})
            status = node.get("status", {})
            capacity = status.get("capacity", {})
            allocatable = status.get("allocatable", {})
            name = meta.get("name")
            metrics = node_metrics.get(name, {})
            row = {
                "name": name,
                "ready": cls._ready(node),
                "role": "control-plane" if cls._is_control_plane(node) else "worker",
                "unschedulable": bool(node.get("spec", {}).get("unschedulable")),
                "cluster_role": labels.get("borg.local/cluster-role"),
                "node_size": labels.get("borg.local/node-size"),
                "node_index": labels.get("borg.local/node-index"),
                "provisioning_state": labels.get("borg.local/provisioning-state"),
                "capacity_cpu_m": cls._parse_cpu_m(capacity.get("cpu")),
                "allocatable_cpu_m": cls._parse_cpu_m(allocatable.get("cpu")),
                "capacity_memory_mi": round(cls._parse_memory_mi(capacity.get("memory")), 3),
                "allocatable_memory_mi": round(cls._parse_memory_mi(allocatable.get("memory")), 3),
                "usage_cpu_m": round(float(metrics.get("cpu_m", 0.0)), 3),
                "usage_memory_mi": round(float(metrics.get("memory_mi", 0.0)), 3),
                "usage_cpu_percent": metrics.get("cpu_percent"),
                "usage_memory_percent": metrics.get("memory_percent"),
            }
            totals["allocatable_cpu_m"] += row["allocatable_cpu_m"]
            totals["allocatable_memory_mi"] += row["allocatable_memory_mi"]
            totals["capacity_cpu_m"] += row["capacity_cpu_m"]
            totals["capacity_memory_mi"] += row["capacity_memory_mi"]
            totals["usage_cpu_m"] += row["usage_cpu_m"]
            totals["usage_memory_mi"] += row["usage_memory_mi"]
            summaries.append(row)
        totals["usage_cpu_percent"] = cls._percent(totals["usage_cpu_m"], totals["allocatable_cpu_m"])
        totals["usage_memory_percent"] = cls._percent(totals["usage_memory_mi"], totals["allocatable_memory_mi"])
        return summaries, {key: round(value, 3) if isinstance(value, float) else value for key, value in totals.items()}

    @classmethod
    def _pod_summary(cls, pods: list[dict[str, Any]], workers: list[dict[str, Any]]) -> dict[str, Any]:
        phase_counts: dict[str, int] = {}
        namespace_counts: dict[str, int] = {}
        owner_counts: dict[str, int] = {}
        node_counts: dict[str, int] = {}
        restarts = 0
        request_cpu_m = 0.0
        request_memory_mi = 0.0
        limit_cpu_m = 0.0
        limit_memory_mi = 0.0
        unscheduled = 0
        pending_reasons: dict[str, int] = {}
        worker_names = {node.get("metadata", {}).get("name") for node in workers}

        for pod in pods:
            meta = pod.get("metadata", {})
            spec = pod.get("spec", {})
            status = pod.get("status", {})
            phase = status.get("phase", "Unknown")
            namespace = meta.get("namespace", "unknown")
            node = spec.get("nodeName") or "unscheduled"
            owners = meta.get("ownerReferences", [])
            owner = owners[0].get("kind", "BarePod") if owners else "BarePod"
            cls._inc(phase_counts, phase)
            cls._inc(namespace_counts, namespace)
            cls._inc(owner_counts, owner)
            cls._inc(node_counts, node)
            if node == "unscheduled":
                unscheduled += 1
            if phase == "Pending":
                for condition in status.get("conditions", []):
                    if condition.get("type") == "PodScheduled" and condition.get("status") == "False":
                        cls._inc(pending_reasons, condition.get("reason", "Pending"))
            for container_status in status.get("containerStatuses", []):
                restarts += int(container_status.get("restartCount", 0) or 0)
            for container in [*spec.get("initContainers", []), *spec.get("containers", [])]:
                resources = container.get("resources", {})
                requests = resources.get("requests", {})
                limits = resources.get("limits", {})
                request_cpu_m += cls._parse_cpu_m(requests.get("cpu"))
                request_memory_mi += cls._parse_memory_mi(requests.get("memory"))
                limit_cpu_m += cls._parse_cpu_m(limits.get("cpu"))
                limit_memory_mi += cls._parse_memory_mi(limits.get("memory"))

        pods_on_workers = sum(count for node, count in node_counts.items() if node in worker_names)
        return {
            "phase_counts": phase_counts,
            "namespace_counts": dict(sorted(namespace_counts.items(), key=lambda item: (-item[1], item[0]))),
            "owner_counts": dict(sorted(owner_counts.items(), key=lambda item: (-item[1], item[0]))),
            "node_counts": dict(sorted(node_counts.items(), key=lambda item: (-item[1], item[0]))),
            "pending_reasons": pending_reasons,
            "restarts": restarts,
            "unscheduled": unscheduled,
            "pods_on_workers": pods_on_workers,
            "request_cpu_m": round(request_cpu_m, 3),
            "request_memory_mi": round(request_memory_mi, 3),
            "limit_cpu_m": round(limit_cpu_m, 3),
            "limit_memory_mi": round(limit_memory_mi, 3),
        }

    @classmethod
    def _workload_summary(cls, kubeconfig: Path) -> tuple[list[dict[str, Any]], dict[str, int], str | None]:
        payload = cls._kubectl_json(kubeconfig, ["get", "deploy,ds,sts,job", "-A"])
        items = payload.get("items", [])
        counts: dict[str, int] = {}
        rows: list[dict[str, Any]] = []
        for item in items:
            kind = item.get("kind", "Unknown")
            meta = item.get("metadata", {})
            spec = item.get("spec", {})
            status = item.get("status", {})
            cls._inc(counts, kind)
            rows.append(
                {
                    "kind": kind,
                    "namespace": meta.get("namespace"),
                    "name": meta.get("name"),
                    "desired": spec.get("replicas") if kind != "DaemonSet" else status.get("desiredNumberScheduled"),
                    "ready": status.get("readyReplicas") or status.get("numberReady") or status.get("succeeded") or 0,
                    "available": status.get("availableReplicas") or status.get("numberAvailable") or 0,
                }
            )
        rows.sort(key=lambda item: (item.get("namespace") or "", item.get("kind") or "", item.get("name") or ""))
        return rows, counts, payload.get("error")

    @classmethod
    def _hpa_summary(cls, hpas: list[dict[str, Any]]) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for item in hpas:
            status = item.get("status", {})
            metrics = status.get("currentMetrics", [])
            cpu_utilization = None
            cpu_average_value = None
            for metric in metrics:
                resource = metric.get("resource", {})
                if resource.get("name") == "cpu":
                    current = resource.get("current", {})
                    cpu_utilization = current.get("averageUtilization")
                    cpu_average_value = current.get("averageValue")
            desired = status.get("desiredReplicas")
            current = status.get("currentReplicas")
            rows.append(
                {
                    "namespace": item.get("metadata", {}).get("namespace"),
                    "name": item.get("metadata", {}).get("name"),
                    "target": item.get("spec", {}).get("scaleTargetRef", {}).get("name"),
                    "min": item.get("spec", {}).get("minReplicas"),
                    "max": item.get("spec", {}).get("maxReplicas"),
                    "current": current,
                    "desired": desired,
                    "delta": (desired - current) if isinstance(desired, int) and isinstance(current, int) else None,
                    "cpu_utilization": cpu_utilization,
                    "cpu_average_value": cpu_average_value,
                    "conditions": [
                        {"type": condition.get("type"), "status": condition.get("status"), "reason": condition.get("reason")}
                        for condition in status.get("conditions", [])
                    ],
                }
            )
        return rows

    @classmethod
    def _cluster_summary(cls, kubeconfig: Path, *, name: str, role: str) -> dict[str, Any]:
        nodes_payload = cls._kubectl_json(kubeconfig, ["get", "nodes"])
        pods_payload = cls._kubectl_json(kubeconfig, ["get", "pods", "-A"])
        hpa_payload = cls._kubectl_json(kubeconfig, ["get", "hpa", "-A"])
        node_metrics, node_top_error = cls._node_top(kubeconfig)
        pod_metrics, pod_top_error = cls._pod_top(kubeconfig)
        workload_rows, workload_counts, workload_error = cls._workload_summary(kubeconfig)
        nodes = nodes_payload.get("items", [])
        pods = pods_payload.get("items", [])
        hpas = hpa_payload.get("items", [])
        workers = [node for node in nodes if not cls._is_control_plane(node)]
        pending = [pod for pod in pods if pod.get("status", {}).get("phase") == "Pending"]
        running = [pod for pod in pods if pod.get("status", {}).get("phase") == "Running"]
        baseline_pods = [pod for pod in pods if pod.get("metadata", {}).get("namespace") == "borg-baseline"]
        node_rows, resource_totals = cls._node_summary(nodes, node_metrics)
        pod_summary = cls._pod_summary(pods, workers)
        hpa = cls._hpa_summary(hpas)
        states: dict[str, int] = {}
        for node in workers:
            labels = node.get("metadata", {}).get("labels", {})
            if "borg.local/provisioning-state" in labels:
                state = labels["borg.local/provisioning-state"]
                states[state] = states.get(state, 0) + 1
        pod_summary["request_cpu_percent"] = cls._percent(pod_summary["request_cpu_m"], resource_totals["allocatable_cpu_m"])
        pod_summary["request_memory_percent"] = cls._percent(pod_summary["request_memory_mi"], resource_totals["allocatable_memory_mi"])
        return {
            "name": name,
            "role": role,
            "kubeconfig": str(kubeconfig),
            "nodes": len(nodes),
            "ready_nodes": sum(1 for node in nodes if cls._ready(node)),
            "worker_nodes": len(workers),
            "ready_workers": sum(1 for node in workers if cls._ready(node)),
            "schedulable_nodes": sum(1 for node in workers if not node.get("spec", {}).get("unschedulable")),
            "node_states": states,
            "pods": len(pods),
            "running_pods": len(running),
            "pending_pods": len(pending),
            "baseline_pods": len(baseline_pods),
            "resource_totals": resource_totals,
            "pod_summary": pod_summary,
            "node_rows": node_rows,
            "pod_metrics_by_namespace": pod_metrics,
            "workloads": workload_rows,
            "workload_counts": workload_counts,
            "hpa": hpa,
            "errors": [
                value
                for value in [
                    nodes_payload.get("error"),
                    pods_payload.get("error"),
                    hpa_payload.get("error"),
                    node_top_error,
                    pod_top_error,
                    workload_error,
                ]
                if value
            ],
        }

    @staticmethod
    def _read_json(path: Path) -> dict[str, Any]:
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))

    @staticmethod
    def _latest_event(path: Path, kind: str) -> dict[str, Any]:
        if not path.exists():
            return {}
        latest: dict[str, Any] = {}
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if event.get("kind") == kind:
                latest = event
        return latest

    @staticmethod
    def _safe_number(value: Any) -> float | None:
        if isinstance(value, (int, float)):
            return float(value)
        return None

    @classmethod
    def _difference_rows(cls, experimental: dict[str, Any], baseline: dict[str, Any]) -> list[dict[str, Any]]:
        def get(path: tuple[str, ...], source: dict[str, Any]) -> Any:
            value: Any = source
            for key in path:
                if not isinstance(value, dict):
                    return None
                value = value.get(key)
            return value

        specs = [
            ("Ready workers", ("ready_workers",), "Higher means more schedulable worker capacity is available."),
            ("Schedulable workers", ("schedulable_nodes",), "Baseline warm nodes may stay cordoned until local Karpenter activates them."),
            ("Running pods", ("running_pods",), "Shows admitted and scheduled workload volume."),
            ("Pending pods", ("pending_pods",), "Higher pending count means queue/backlog pressure."),
            ("Restarts", ("pod_summary", "restarts"), "Container restarts indicate instability or churn."),
            ("CPU usage m", ("resource_totals", "usage_cpu_m"), "Live Metrics Server CPU usage in millicores."),
            ("Memory usage Mi", ("resource_totals", "usage_memory_mi"), "Live Metrics Server memory usage."),
            ("CPU requests m", ("pod_summary", "request_cpu_m"), "Declared scheduling demand from pod requests."),
            ("Memory requests Mi", ("pod_summary", "request_memory_mi"), "Declared scheduling demand from pod requests."),
            ("CPU request percent", ("pod_summary", "request_cpu_percent"), "Requested CPU as percent of allocatable cluster CPU."),
            ("Memory request percent", ("pod_summary", "request_memory_percent"), "Requested memory as percent of allocatable cluster memory."),
        ]
        rows: list[dict[str, Any]] = []
        for label, path, note in specs:
            exp_value = cls._safe_number(get(path, experimental))
            base_value = cls._safe_number(get(path, baseline))
            delta = None if exp_value is None or base_value is None else round(exp_value - base_value, 3)
            rows.append({"metric": label, "experimental": exp_value, "baseline": base_value, "delta": delta, "note": note})
        return rows

    @classmethod
    def _scorecards(cls, experimental: dict[str, Any], baseline: dict[str, Any], experimental_state: dict[str, Any]) -> list[dict[str, Any]]:
        exp_pending = experimental.get("pending_pods", 0)
        base_pending = baseline.get("pending_pods", 0)
        exp_cpu = experimental.get("resource_totals", {}).get("usage_cpu_percent")
        base_cpu = baseline.get("resource_totals", {}).get("usage_cpu_percent")
        hpa_desired = sum(int(item.get("desired") or 0) for item in baseline.get("hpa", []))
        hpa_current = sum(int(item.get("current") or 0) for item in baseline.get("hpa", []))
        karpenter = baseline.get("karpenter", {})
        return [
            {
                "label": "Queue pressure",
                "experimental": exp_pending,
                "baseline": base_pending,
                "interpretation": "Experimental controller exposes admission pressure directly; HPA baseline should reduce pending pods after scaling and warm-node activation.",
            },
            {
                "label": "CPU utilization",
                "experimental": exp_cpu,
                "baseline": base_cpu,
                "interpretation": "Shows actual live resource consumption rather than only requested resources.",
            },
            {
                "label": "Replica reaction",
                "experimental": experimental_state.get("decision", {}).get("action_label") or "n/a",
                "baseline": f"HPA {hpa_current}->{hpa_desired}",
                "interpretation": "Experimental side chooses Agent A/B/C actions; baseline reacts through HPA desired replicas.",
            },
            {
                "label": "Capacity reaction",
                "experimental": f"{experimental.get('schedulable_nodes', 0)} schedulable workers",
                "baseline": f"{karpenter.get('active_nodes', 0)} active / {karpenter.get('warm_nodes', 0)} warm",
                "interpretation": "Local Karpenter emulation activates pre-created Kind workers; experimental workers remain directly visible to the orchestrator.",
            },
        ]

    @classmethod
    def comparison_payload(cls) -> dict[str, Any]:
        experimental_state = cls._read_json(cls.experimental_event_dir / "state.json")
        latest_exercise = cls._latest_event(cls.experimental_event_dir / "events.jsonl", "exercise")
        manual_stimulus = cls._read_json(cls.shared_stimulus_path)
        karpenter_state = cls._read_json(cls.karpenter_state_path)
        experimental = cls._cluster_summary(cls.experimental_kubeconfig, name="borg-experimental", role="experimental-orchestrator")
        baseline = cls._cluster_summary(cls.baseline_kubeconfig, name="borg-baseline", role="hpa-local-karpenter")
        baseline["karpenter"] = karpenter_state
        exp_reward = experimental_state.get("reward_summary", {})
        exp_cluster = experimental_state.get("cluster", {})
        exp_decision = experimental_state.get("decision", {})
        experimental = {
            **experimental,
            "orchestrator_status": experimental_state.get("status", "not-running"),
            "active_stage": experimental_state.get("active_stage"),
            "last_reward": exp_reward.get("last_total"),
            "avg_reward": exp_reward.get("average_total"),
            "reward_summary": exp_reward,
            "max_risk": exp_cluster.get("max_risk"),
            "energy_watts": exp_cluster.get("energy_watts"),
            "power_metric_kind": exp_cluster.get("power_metric_kind"),
            "telemetry_sources": exp_cluster.get("telemetry_sources", []),
            "last_decision": exp_decision.get("action_label") or (f"{exp_decision.get('agent')}:{exp_decision.get('kind')}" if exp_decision.get("agent") else None),
            "decision": exp_decision,
            "ray": experimental_state.get("ray", {}),
            "optuna": experimental_state.get("optuna", {}),
        }
        return {
            "experimental": experimental,
            "baseline": baseline,
            "differences": cls._difference_rows(experimental, baseline),
            "scorecards": cls._scorecards(experimental, baseline, experimental_state),
            "shared_stimulus": manual_stimulus or latest_exercise,
            "live_loop_stimulus": latest_exercise,
            "manual_stimulus": manual_stimulus,
            "notes": [
                "Baseline uses real Kubernetes HPA plus local Kind warm-node provisioning emulation.",
                "This is intentionally local-only; upstream AWS Karpenter requires AWS/EKS cloud APIs to create real nodes.",
                "Metrics marked from kubectl top come from Metrics Server and are live cluster observations.",
            ],
        }

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path == "/api/comparison":
            self._json(self.comparison_payload())
            return
        return super().do_GET()


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve local experimental-vs-HPA/Karpenter comparison dashboard")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8876)
    parser.add_argument("--experimental-kubeconfig", default="~/Documents/borg_orchestrator_clusters/kubeconfig-experimental")
    parser.add_argument("--baseline-kubeconfig", default="~/Documents/borg_orchestrator_clusters/kubeconfig-baseline")
    parser.add_argument("--experimental-event-dir", default="orchestrator_stack/runtime/visualization-experimental")
    parser.add_argument("--karpenter-state", default="orchestrator_stack/runtime/comparison/local_karpenter_state.json")
    parser.add_argument("--shared-stimulus", default="orchestrator_stack/runtime/comparison/shared_stimulus.json")
    args = parser.parse_args()
    ComparisonDashboardHandler.experimental_kubeconfig = Path(args.experimental_kubeconfig).expanduser()
    ComparisonDashboardHandler.baseline_kubeconfig = Path(args.baseline_kubeconfig).expanduser()
    ComparisonDashboardHandler.experimental_event_dir = Path(args.experimental_event_dir)
    ComparisonDashboardHandler.karpenter_state_path = Path(args.karpenter_state)
    ComparisonDashboardHandler.shared_stimulus_path = Path(args.shared_stimulus)
    server = ThreadingHTTPServer((args.host, args.port), ComparisonDashboardHandler)
    print(f"comparison_dashboard=http://{args.host}:{args.port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
