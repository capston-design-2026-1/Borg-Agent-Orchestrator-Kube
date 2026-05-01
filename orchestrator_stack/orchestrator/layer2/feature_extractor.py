from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from orchestrator.layer1.collector import prometheus_rows_to_trace
from orchestrator.layer2.simulator import state_to_observation
from orchestrator.types import Observation

FEATURE_NAMES = (
    "cpu_util",
    "mem_util",
    "disk_util",
    "net_util",
    "task_pressure",
    "queue_pressure",
    "energy_price",
    "power_state_on",
)
FEATURE_COUNT = len(FEATURE_NAMES)


@dataclass(slots=True)
class TrainingMatrices:
    x: np.ndarray
    y_risk: np.ndarray
    y_demand: np.ndarray


def _node_lookup(obs: Observation) -> dict[str, Any]:
    return {node.node_id: node for node in obs.nodes}


def _risk_label(current_obs: Observation, next_obs: Observation, node_id: str) -> int:
    current_node = _node_lookup(current_obs).get(node_id)
    next_node = _node_lookup(next_obs).get(node_id, current_node)
    current_fail_signal = float(current_obs.p_fail_scores.get(node_id, 0.0))
    next_fail_signal = float(next_obs.p_fail_scores.get(node_id, 0.0))
    death_signal = int(
        any(not task.alive for task in current_obs.tasks if task.node_id == node_id)
        or any(not task.alive for task in next_obs.tasks if task.node_id == node_id)
    )
    overloaded_signal = int(
        (current_node is not None and (float(current_node.cpu_util) >= 0.9 or float(current_node.mem_util) >= 0.9))
        or (next_node is not None and (float(next_node.cpu_util) >= 0.9 or float(next_node.mem_util) >= 0.9))
    )
    return int(current_fail_signal > 0.75 or next_fail_signal > 0.75 or death_signal or overloaded_signal)


def _demand_heuristic(obs: Observation, node_id: str) -> float:
    node = _node_lookup(obs).get(node_id)
    if node is None:
        return 0.0
    return (
        0.25 * float(node.cpu_util)
        + 0.25 * float(node.mem_util)
        + 0.15 * float(node.net_util)
        + 0.15 * _task_pressure(obs, node_id)
        + 0.10 * _queue_pressure(obs)
        + 0.05 * float(obs.energy_price)
        - 0.05 * (1.0 if node.power_state == "on" else 0.0)
    )


def _demand_target(current_obs: Observation, next_obs: Observation, node_id: str) -> float:
    demand = float(next_obs.demand_projection.get(node_id, 0.0))
    if demand <= 0.0:
        demand = _demand_heuristic(next_obs, node_id)
    if demand <= 0.0:
        demand = _demand_heuristic(current_obs, node_id)
    return max(0.0, min(1.0, demand))


def _queue_pressure(obs: Observation) -> float:
    return min(1.0, obs.queue_length / max(1.0, len(obs.tasks) + len(obs.nodes) + 1.0))


def _task_pressure(obs: Observation, node_id: str) -> float:
    live_task_count = sum(1 for task in obs.tasks if task.node_id == node_id and task.alive)
    return min(1.0, live_task_count / max(1.0, len(obs.tasks) + 1.0))


def node_feature_vector(obs: Observation, node_id: str) -> list[float]:
    node = next((n for n in obs.nodes if n.node_id == node_id), None)
    if node is None:
        return [0.0, 0.0, 0.0, 0.0, 0.0, _queue_pressure(obs), float(obs.energy_price), 0.0]
    return [
        float(node.cpu_util),
        float(node.mem_util),
        float(node.disk_util),
        float(node.net_util),
        _task_pressure(obs, node_id),
        _queue_pressure(obs),
        float(obs.energy_price),
        1.0 if node.power_state == "on" else 0.0,
    ]


def observation_matrix(obs: Observation) -> tuple[np.ndarray, list[str]]:
    node_ids = [n.node_id for n in obs.nodes]
    rows = [node_feature_vector(obs, node_id) for node_id in node_ids]
    if not rows:
        rows = [[0.0] * (FEATURE_COUNT - 2) + [float(obs.energy_price), 0.0]]
        node_ids = ["unknown-node"]
    return np.asarray(rows, dtype=np.float32), node_ids


def _normalize_training_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not rows:
        return rows
    first = rows[0]
    if isinstance(first, dict) and "nodes" not in first and "timestamp" in first:
        return prometheus_rows_to_trace(rows)
    return rows


def trace_rows_to_training_matrices(rows: list[dict[str, Any]]) -> TrainingMatrices:
    normalized_rows = _normalize_training_rows(rows)
    x_rows: list[list[float]] = []
    risk_labels: list[int] = []
    demand_targets: list[float] = []

    for idx, row in enumerate(normalized_rows):
        obs = state_to_observation(row)
        next_obs = state_to_observation(
            normalized_rows[min(idx + 1, len(normalized_rows) - 1)],
            fallback_timestamp=obs.timestamp + 1,
        )
        x_matrix, node_ids = observation_matrix(obs)
        current_nodes_by_id = _node_lookup(obs)

        for feature_row, node_id in zip(x_matrix, node_ids, strict=False):
            node = current_nodes_by_id.get(node_id)
            if node is None:
                continue
            x_rows.append(feature_row.tolist() if hasattr(feature_row, "tolist") else list(feature_row))
            risk_labels.append(_risk_label(obs, next_obs, node_id))
            demand_targets.append(_demand_target(obs, next_obs, node_id))

    if not x_rows:
        x_rows = [[0.0] * (FEATURE_COUNT - 2) + [0.1, 0.0]]
        risk_labels = [0]
        demand_targets = [0.0]

    return TrainingMatrices(
        x=np.asarray(x_rows, dtype=np.float32),
        y_risk=np.asarray(risk_labels, dtype=np.int32),
        y_demand=np.asarray(demand_targets, dtype=np.float32),
    )
