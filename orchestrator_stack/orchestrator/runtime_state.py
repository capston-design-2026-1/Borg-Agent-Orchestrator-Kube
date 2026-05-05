from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

KST = timezone(timedelta(hours=9))


def kst_now_iso() -> str:
    return datetime.now(KST).isoformat(timespec="seconds")


class VisualizationState:
    """Small JSON/JSONL state store consumed by the local dashboard."""

    def __init__(self, event_dir: str | Path, *, architecture_path: str | Path = "docs/repository_architecture.mmd") -> None:
        self.event_dir = Path(event_dir)
        self.event_dir.mkdir(parents=True, exist_ok=True)
        self.state_path = self.event_dir / "state.json"
        self.events_path = self.event_dir / "events.jsonl"
        self.state: dict[str, Any] = {
            "status": "starting",
            "started_at": kst_now_iso(),
            "updated_at": kst_now_iso(),
            "active_stage": "boot",
            "architecture_path": str(architecture_path),
            "stages": [],
            "rewards": [],
            "reward_summary": {"count": 0, "last_total": None, "average_total": None, "last_by_agent": {}},
            "optuna": {"status": "idle", "study": None, "trial": None, "best_score": None, "best_params": {}, "history": []},
            "ray": {"status": "idle", "train_iters": None, "reward_mean": None, "checkpoint": None},
            "cluster": {},
            "decision": {},
            "artifacts": [],
            "errors": [],
            "summary": {},
        }
        self.events_path.write_text("", encoding="utf-8")
        self.write()

    def write(self) -> None:
        self.state["updated_at"] = kst_now_iso()
        tmp = self.state_path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(self.state, indent=2, sort_keys=True), encoding="utf-8")
        tmp.replace(self.state_path)

    def emit(self, kind: str, message: str, **data: Any) -> None:
        event = {"time": kst_now_iso(), "kind": kind, "stage": self.state.get("active_stage"), "message": message, **data}
        with self.events_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, sort_keys=True) + "\n")
        self.write()

    def set_status(self, status: str, *, stage: str | None = None) -> None:
        self.state["status"] = status
        if stage:
            self.state["active_stage"] = stage
        self.write()

    def stage(self, name: str, status: str, *, detail: str = "", progress: float | None = None) -> None:
        self.state["active_stage"] = name
        stages = self.state["stages"]
        existing = next((item for item in stages if item["name"] == name), None)
        payload = {"name": name, "status": status, "detail": detail, "updated_at": kst_now_iso()}
        if progress is not None:
            payload["progress"] = max(0.0, min(1.0, float(progress)))
        if existing:
            existing.update(payload)
        else:
            stages.append(payload)
        self.emit("stage", detail or f"{name}: {status}", name=name, status=status, progress=payload.get("progress"))

    def reward(self, step: int, rewards: dict[str, float], total: float, action: str) -> None:
        row = {"step": int(step), "rewards": rewards, "total": float(total), "action": action, "time": kst_now_iso()}
        history = self.state["rewards"]
        history.append(row)
        del history[:-80]
        previous = self.state["reward_summary"]
        count = int(previous.get("count") or 0) + 1
        old_average = float(previous.get("average_total") or 0.0)
        new_average = old_average + ((float(total) - old_average) / count)
        self.state["reward_summary"] = {
            "count": count,
            "last_total": float(total),
            "average_total": new_average,
            "last_by_agent": rewards,
            "last_action": action,
        }
        self.emit("reward", f"step {step}: {action}", **row)

    def cluster_snapshot(self, snapshot: dict[str, Any]) -> None:
        self.state["cluster"] = {"time": kst_now_iso(), **snapshot}
        self.emit(
            "cluster",
            (
                f"nodes={snapshot.get('nodes')} tasks={snapshot.get('tasks')} "
                f"sla={snapshot.get('sla_violations')} risk={snapshot.get('max_risk')}"
            ),
            **self.state["cluster"],
        )

    def decision(self, decision: dict[str, Any]) -> None:
        self.state["decision"] = {"time": kst_now_iso(), **decision}
        event_payload = dict(self.state["decision"])
        event_payload["action_kind"] = event_payload.pop("kind", None)
        label = decision.get("action_label") or f"{decision.get('agent')}:{decision.get('kind')}"
        self.emit(
            "decision",
            (
                f"{label} target={decision.get('target')} "
                f"repeat={decision.get('repeat_count')} reason={decision.get('reason')}"
            ),
            **event_payload,
        )

    def optuna_trial(self, study: str, number: int, value: float | None, params: dict[str, Any], best_value: float | None) -> None:
        optuna = self.state["optuna"]
        optuna.update({"status": "running", "study": study, "trial": int(number), "best_score": best_value, "best_params": params if value == best_value else optuna.get("best_params", {})})
        optuna["history"].append({"trial": int(number), "value": value, "params": params, "time": kst_now_iso()})
        del optuna["history"][:-40]
        self.emit("optuna", f"trial {number} value={value}", study=study, trial=number, value=value, params=params, best_score=best_value)

    def optuna_update(self, status: str, **data: Any) -> None:
        self.state["optuna"].update({"status": status, **data})
        self.emit("optuna", f"Optuna {status}", **self.state["optuna"])

    def ray_update(self, status: str, **data: Any) -> None:
        self.state["ray"].update({"status": status, **data})
        self.emit("ray", f"Ray/RLlib {status}", **self.state["ray"])

    def artifact(self, path: str | Path, label: str) -> None:
        item = {"label": label, "path": str(path), "time": kst_now_iso()}
        self.state["artifacts"].append(item)
        self.emit("artifact", f"{label}: {path}", **item)

    def error(self, message: str) -> None:
        self.state["errors"].append({"time": kst_now_iso(), "message": message})
        self.state["status"] = "failed"
        self.emit("error", message)
