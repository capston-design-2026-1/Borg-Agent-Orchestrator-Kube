#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json
import os
import subprocess
import threading
import time
from pathlib import Path

from aiopslab.orchestrator.orchestrator import Orchestrator
from orchestrator.layer1.kubernetes_trace import capture_kubernetes_trace_row, write_kubernetes_trace
from orchestrator.layer2.aiopslab_contract import AIOpsLabPolicyAgent, initialize_aiopslab_problem


def _run(cmd: list[str], *, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, check=check, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def _openebs_kind_compat(kubeconfig: Path, stop: threading.Event) -> None:
    while not stop.is_set():
        subprocess.run(
            ["kubectl", "--kubeconfig", str(kubeconfig), "-n", "openebs", "delete", "daemonset", "openebs-ndm", "--ignore-not-found"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        stop.wait(2)


def _ensure_aiopslab_applications(env_dir: Path, source_repo: Path) -> None:
    target = env_dir / "lib/python3.12/site-packages/aiopslab-applications"
    source = source_repo / "aiopslab-applications"
    if not source.exists():
        raise SystemExit(f"missing AIOpsLab applications at {source}; clone upstream repo with submodules first")
    if target.exists() or target.is_symlink():
        target.unlink()
    target.symlink_to(source)


def _patch_aiopslab_config(env_dir: Path, kubeconfig: Path) -> None:
    package_dir = env_dir / "lib/python3.12/site-packages/aiopslab"
    config_file = package_dir / "config.yml"
    example_file = package_dir / "config.yml.example"
    if not config_file.exists() and example_file.exists():
        config_file.write_text(example_file.read_text(encoding="utf-8"), encoding="utf-8")
    text = config_file.read_text(encoding="utf-8")
    text = text.replace("k8s_host: control_node_hostname", "k8s_host: localhost")
    text = text.replace("k8s_host: kind", "k8s_host: localhost")
    config_file.write_text(text, encoding="utf-8")

    monitor_file = package_dir / "observer/monitor_config.yaml"
    text = monitor_file.read_text(encoding="utf-8")
    lines = []
    for line in text.splitlines():
        if line.startswith("kubernetes_path:"):
            lines.append(f"kubernetes_path: '{kubeconfig}'")
        else:
            lines.append(line)
    monitor_file.write_text("\n".join(lines) + "\n", encoding="utf-8")


class CapturingAIOpsLabPolicyAgent(AIOpsLabPolicyAgent):
    def __init__(self, *, kubeconfig: Path, namespace_prefixes: tuple[str, ...], detection_answer: str) -> None:
        super().__init__(detection_answer=detection_answer)
        self.kubeconfig = kubeconfig
        self.namespace_prefixes = namespace_prefixes
        self.trace_rows: list[dict] = []
        self.capture_errors: list[str] = []

    async def get_action(self, state: str) -> str:
        try:
            self.trace_rows.append(
                capture_kubernetes_trace_row(
                    kubeconfig=self.kubeconfig,
                    namespace_prefixes=self.namespace_prefixes,
                )
            )
        except Exception as exc:  # pragma: no cover - live cluster diagnostics only.
            self.capture_errors.append(str(exc))
        return await super().get_action(state)


def run_smoke(args: argparse.Namespace) -> dict:
    env_dir = Path(args.env_dir).expanduser().resolve()
    kubeconfig = Path(args.kubeconfig).expanduser().resolve()
    source_repo = Path(args.aiopslab_repo).expanduser().resolve()
    results_dir = Path(args.results_dir).expanduser().resolve()
    results_dir.mkdir(parents=True, exist_ok=True)

    _ensure_aiopslab_applications(env_dir, source_repo)
    _patch_aiopslab_config(env_dir, kubeconfig)

    stop = threading.Event()
    watcher = threading.Thread(target=_openebs_kind_compat, args=(kubeconfig, stop), daemon=True)
    watcher.start()
    os.environ["KUBECONFIG"] = str(kubeconfig)
    try:
        orch = Orchestrator(results_dir=results_dir)
        namespace_prefixes = tuple(prefix.strip() for prefix in args.namespace_prefixes.split(",") if prefix.strip())
        agent = CapturingAIOpsLabPolicyAgent(
            kubeconfig=kubeconfig,
            namespace_prefixes=namespace_prefixes,
            detection_answer=args.detection_answer,
        )
        initialize_aiopslab_problem(orch, problem_id=args.problem_id, agent=agent)
        result = asyncio.run(orch.start_problem(max_steps=args.max_steps))
    finally:
        stop.set()
        watcher.join(timeout=5)

    if args.trace_out:
        write_kubernetes_trace(agent.trace_rows, args.trace_out)

    return {
        "problem_id": args.problem_id,
        "final_state": str(result.get("final_state")),
        "history_len": len(result.get("history", [])),
        "results": result.get("results", {}),
        "results_dir": str(results_dir),
        "trace_rows": len(agent.trace_rows),
        "trace_out": str(Path(args.trace_out)) if args.trace_out else None,
        "capture_errors": agent.capture_errors,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a live AIOpsLab no-op smoke on a real Kubernetes config.")
    parser.add_argument("--env-dir", default="~/Documents/aiopslab_validation_env")
    parser.add_argument("--kubeconfig", default="~/Documents/aiopslab_validation_env/kubeconfig")
    parser.add_argument("--aiopslab-repo", default="~/Documents/AIOpsLab")
    parser.add_argument("--problem-id", default="noop_detection_hotel_reservation-1")
    parser.add_argument("--max-steps", type=int, default=2)
    parser.add_argument("--results-dir", default="/private/tmp/aiopslab_results")
    parser.add_argument("--trace-out", help="Write Kubernetes-derived trace rows captured during the live AIOpsLab run.")
    parser.add_argument("--namespace-prefixes", default="test-,default")
    parser.add_argument("--detection-answer", default="No", help="Answer submitted after the observation turn for detection tasks.")
    parser.add_argument("--out")
    args = parser.parse_args()

    report = run_smoke(args)
    print(json.dumps(report, indent=2))
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
