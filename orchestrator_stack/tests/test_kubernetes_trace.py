from orchestrator.layer1.kubernetes_trace import kubernetes_snapshot_to_trace_row, parse_cpu_milli, parse_memory_bytes


def test_parse_kubernetes_quantities():
    assert parse_cpu_milli("250m") == 250
    assert parse_cpu_milli("2") == 2000
    assert parse_memory_bytes("128Mi") == 128 * 1024 * 1024
    assert parse_memory_bytes("1Gi") == 1024 * 1024 * 1024


def test_kubernetes_snapshot_to_trace_row_uses_real_kube_payload_shape():
    nodes = {
        "items": [
            {
                "metadata": {"name": "kind-control-plane"},
                "status": {"allocatable": {"cpu": "2000m", "memory": "1Gi"}},
            }
        ]
    }
    pods = {
        "items": [
            {
                "metadata": {"namespace": "test-hotel-reservation", "name": "frontend"},
                "spec": {
                    "nodeName": "kind-control-plane",
                    "containers": [{"resources": {"requests": {"cpu": "500m", "memory": "128Mi"}}}],
                },
                "status": {"phase": "Running", "containerStatuses": [{"ready": True, "restartCount": 0}]},
            },
            {
                "metadata": {"namespace": "test-hotel-reservation", "name": "pending"},
                "spec": {"containers": [{"resources": {"requests": {"cpu": "250m", "memory": "64Mi"}}}]},
                "status": {"phase": "Pending", "containerStatuses": []},
            },
        ]
    }
    jobs = {"items": [{"status": {"succeeded": 3}}]}

    row = kubernetes_snapshot_to_trace_row(
        nodes_payload=nodes,
        pods_payload=pods,
        jobs_payload=jobs,
        timestamp=123,
        namespace_prefixes=("test-",),
    )

    assert row["timestamp"] == 123
    assert row["nodes"][0]["node_id"] == "kind-control-plane"
    assert row["nodes"][0]["cpu_util"] == 0.25
    assert row["nodes"][0]["mem_util"] == 0.125
    assert row["sla_violations"] == 1
    assert row["completed_tasks"] == 3
    assert row["queue_length"] == 1
    assert row["energy_watts"] > 0
    assert {task["task_id"] for task in row["tasks"]} == {
        "test-hotel-reservation/frontend",
        "test-hotel-reservation/pending",
    }
