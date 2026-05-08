#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def run_json(kubeconfig: str, args: list[str]) -> dict[str, Any]:
    proc = subprocess.run(
        ["kubectl", "--kubeconfig", kubeconfig, *args, "-o", "json"],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return json.loads(proc.stdout)


def run(kubeconfig: str, args: list[str]) -> None:
    subprocess.run(["kubectl", "--kubeconfig", kubeconfig, *args], check=False, text=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def pod_is_pending(pod: dict[str, Any], namespace: str) -> bool:
    return pod.get("metadata", {}).get("namespace") == namespace and pod.get("status", {}).get("phase") == "Pending"


def workload_pods_on_node(pods: list[dict[str, Any]], node: str, namespace: str) -> int:
    count = 0
    for pod in pods:
        meta = pod.get("metadata", {})
        if meta.get("namespace") != namespace:
            continue
        if pod.get("spec", {}).get("nodeName") != node:
            continue
        if pod.get("status", {}).get("phase") in {"Running", "Pending"}:
            count += 1
    return count


def worker_nodes(nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        node
        for node in nodes
        if node.get("metadata", {}).get("labels", {}).get("borg.local/karpenter-node") == "true"
    ]


def node_name(node: dict[str, Any]) -> str:
    return str(node.get("metadata", {}).get("name"))


def node_state(node: dict[str, Any]) -> str:
    return str(node.get("metadata", {}).get("labels", {}).get("borg.local/provisioning-state", "unknown"))


def activate_node(kubeconfig: str, node: str) -> dict[str, Any]:
    run(kubeconfig, ["label", "node", node, "borg.local/provisioning-state=active", "--overwrite"])
    run(kubeconfig, ["uncordon", node])
    run(kubeconfig, ["taint", "node", node, "borg.local/capacity-"])
    return {"action": "activate", "node": node}


def warm_node(kubeconfig: str, node: str) -> dict[str, Any]:
    run(kubeconfig, ["label", "node", node, "borg.local/provisioning-state=warm", "--overwrite"])
    run(kubeconfig, ["cordon", node])
    run(kubeconfig, ["taint", "node", node, "borg.local/capacity=warm:NoSchedule", "--overwrite"])
    return {"action": "consolidate", "node": node}


def write_state(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    tmp.replace(path)


def reconcile(args: argparse.Namespace, idle_counts: dict[str, int]) -> dict[str, Any]:
    nodes_payload = run_json(args.kubeconfig, ["get", "nodes"])
    pods_payload = run_json(args.kubeconfig, ["get", "pods", "-A"])
    nodes = sorted(worker_nodes(nodes_payload.get("items", [])), key=node_name)
    pods = pods_payload.get("items", [])
    pending = [pod for pod in pods if pod_is_pending(pod, args.namespace)]
    active = [node for node in nodes if node_state(node) == "active"]
    warm = [node for node in nodes if node_state(node) == "warm"]
    actions: list[dict[str, Any]] = []

    if len(pending) >= args.pending_threshold and warm:
        actions.append(activate_node(args.kubeconfig, node_name(warm[0])))
    elif len(pending) == 0 and args.consolidate_after_iterations > 0:
        for node in active[1:]:
            name = node_name(node)
            if workload_pods_on_node(pods, name, args.namespace) == 0:
                idle_counts[name] = idle_counts.get(name, 0) + 1
                if idle_counts[name] >= args.consolidate_after_iterations:
                    actions.append(warm_node(args.kubeconfig, name))
                    idle_counts[name] = 0
                    break
            else:
                idle_counts[name] = 0

    refreshed_nodes = worker_nodes(run_json(args.kubeconfig, ["get", "nodes"]).get("items", []))
    active_count = sum(1 for node in refreshed_nodes if node_state(node) == "active")
    warm_count = sum(1 for node in refreshed_nodes if node_state(node) == "warm")
    return {
        "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "mode": "local-kind-karpenter-emulation",
        "namespace": args.namespace,
        "pending_pods": len(pending),
        "active_nodes": active_count,
        "warm_nodes": warm_count,
        "actions": actions,
        "nodes": [{"name": node_name(node), "state": node_state(node)} for node in refreshed_nodes],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Local Kind Karpenter-style warm-node controller for HPA baseline experiments")
    parser.add_argument("--kubeconfig", required=True)
    parser.add_argument("--namespace", default="borg-baseline")
    parser.add_argument("--state-out", default="orchestrator_stack/runtime/comparison/local_karpenter_state.json")
    parser.add_argument("--interval-seconds", type=float, default=5.0)
    parser.add_argument("--pending-threshold", type=int, default=1)
    parser.add_argument("--consolidate-after-iterations", type=int, default=18)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()

    idle_counts: dict[str, int] = {}
    while True:
        try:
            payload = reconcile(args, idle_counts)
        except Exception as exc:  # keep the controller observable instead of silently dying
            payload = {"updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "mode": "local-kind-karpenter-emulation", "error": str(exc)}
        write_state(Path(args.state_out), payload)
        print(json.dumps(payload, sort_keys=True), flush=True)
        if args.once:
            break
        time.sleep(args.interval_seconds)


if __name__ == "__main__":
    main()
