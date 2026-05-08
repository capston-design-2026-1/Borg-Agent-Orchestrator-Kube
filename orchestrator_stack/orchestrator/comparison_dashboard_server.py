from __future__ import annotations

import argparse
import json
import subprocess
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


class ComparisonDashboardHandler(SimpleHTTPRequestHandler):
    dashboard_dir = Path("orchestrator_stack/comparison_dashboard")
    experimental_kubeconfig = Path("~/Documents/borg_orchestrator_clusters/kubeconfig-experimental").expanduser()
    baseline_kubeconfig = Path("~/Documents/borg_orchestrator_clusters/kubeconfig-baseline").expanduser()
    experimental_event_dir = Path("orchestrator_stack/runtime/visualization-experimental")
    karpenter_state_path = Path("orchestrator_stack/runtime/comparison/local_karpenter_state.json")

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
    def _ready(node: dict[str, Any]) -> bool:
        for condition in node.get("status", {}).get("conditions", []):
            if condition.get("type") == "Ready":
                return condition.get("status") == "True"
        return False

    @staticmethod
    def _is_control_plane(node: dict[str, Any]) -> bool:
        labels = node.get("metadata", {}).get("labels", {})
        return "node-role.kubernetes.io/control-plane" in labels or "node-role.kubernetes.io/master" in labels

    @classmethod
    def _cluster_summary(cls, kubeconfig: Path, *, name: str, role: str) -> dict[str, Any]:
        nodes_payload = cls._kubectl_json(kubeconfig, ["get", "nodes"])
        pods_payload = cls._kubectl_json(kubeconfig, ["get", "pods", "-A"])
        hpa_payload = cls._kubectl_json(kubeconfig, ["get", "hpa", "-A"])
        nodes = nodes_payload.get("items", [])
        pods = pods_payload.get("items", [])
        hpas = hpa_payload.get("items", [])
        workers = [node for node in nodes if not cls._is_control_plane(node)]
        pending = [pod for pod in pods if pod.get("status", {}).get("phase") == "Pending"]
        running = [pod for pod in pods if pod.get("status", {}).get("phase") == "Running"]
        baseline_pods = [pod for pod in pods if pod.get("metadata", {}).get("namespace") == "borg-baseline"]
        states: dict[str, int] = {}
        for node in workers:
            labels = node.get("metadata", {}).get("labels", {})
            if "borg.local/provisioning-state" in labels:
                state = labels["borg.local/provisioning-state"]
                states[state] = states.get(state, 0) + 1
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
            "hpa": [
                {
                    "namespace": item.get("metadata", {}).get("namespace"),
                    "name": item.get("metadata", {}).get("name"),
                    "min": item.get("spec", {}).get("minReplicas"),
                    "max": item.get("spec", {}).get("maxReplicas"),
                    "current": item.get("status", {}).get("currentReplicas"),
                    "desired": item.get("status", {}).get("desiredReplicas"),
                    "current_metrics": item.get("status", {}).get("currentMetrics", []),
                }
                for item in hpas
            ],
            "errors": [value for value in [nodes_payload.get("error"), pods_payload.get("error"), hpa_payload.get("error")] if value],
        }

    @staticmethod
    def _read_json(path: Path) -> dict[str, Any]:
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))

    @classmethod
    def comparison_payload(cls) -> dict[str, Any]:
        experimental_state = cls._read_json(cls.experimental_event_dir / "state.json")
        karpenter_state = cls._read_json(cls.karpenter_state_path)
        experimental = cls._cluster_summary(cls.experimental_kubeconfig, name="borg-experimental", role="experimental-orchestrator")
        baseline = cls._cluster_summary(cls.baseline_kubeconfig, name="borg-baseline", role="hpa-local-karpenter")
        exp_reward = experimental_state.get("reward_summary", {})
        exp_cluster = experimental_state.get("cluster", {})
        exp_decision = experimental_state.get("decision", {})
        return {
            "experimental": {
                **experimental,
                "orchestrator_status": experimental_state.get("status", "not-running"),
                "active_stage": experimental_state.get("active_stage"),
                "last_reward": exp_reward.get("last_total"),
                "avg_reward": exp_reward.get("average_total"),
                "max_risk": exp_cluster.get("max_risk"),
                "last_decision": exp_decision.get("action_label") or (f"{exp_decision.get('agent')}:{exp_decision.get('kind')}" if exp_decision.get("agent") else None),
            },
            "baseline": {
                **baseline,
                "karpenter": karpenter_state,
            },
            "notes": [
                "Baseline uses real Kubernetes HPA plus local Kind warm-node provisioning emulation.",
                "This is intentionally local-only; upstream AWS Karpenter requires AWS/EKS cloud APIs to create real nodes.",
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
    args = parser.parse_args()
    ComparisonDashboardHandler.experimental_kubeconfig = Path(args.experimental_kubeconfig).expanduser()
    ComparisonDashboardHandler.baseline_kubeconfig = Path(args.baseline_kubeconfig).expanduser()
    ComparisonDashboardHandler.experimental_event_dir = Path(args.experimental_event_dir)
    ComparisonDashboardHandler.karpenter_state_path = Path(args.karpenter_state)
    server = ThreadingHTTPServer((args.host, args.port), ComparisonDashboardHandler)
    print(f"comparison_dashboard=http://{args.host}:{args.port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
