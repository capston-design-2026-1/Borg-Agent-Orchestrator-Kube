import json

from orchestrator.layer1 import prometheus


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


def test_query_prometheus_metric_rows_merges_series_by_node_and_time(monkeypatch):
    payloads = [
        {
            "status": "success",
            "data": {
                "result": [
                    {"metric": {"node": "n1"}, "values": [[100, "0.5"], [160, "0.6"]]},
                    {"metric": {"node": "n2"}, "values": [[100, "0.2"]]},
                ]
            },
        },
        {
            "status": "success",
            "data": {
                "result": [
                    {"metric": {"node": "n1"}, "values": [[100, "0.4"], [160, "0.5"]]},
                    {"metric": {"node": "n2"}, "values": [[100, "0.3"]]},
                ]
            },
        },
    ]

    def fake_urlopen(url, timeout):
        return FakeResponse(payloads.pop(0))

    monkeypatch.setattr(prometheus, "urlopen", fake_urlopen)

    rows = prometheus.query_prometheus_metric_rows(
        base_url="http://prometheus.local",
        query_map={"cpu_util": "cpu_query", "mem_util": "mem_query"},
        start="100",
        end="160",
        step="60",
    )

    assert rows == [
        {"timestamp": 100, "node_id": "n1", "cpu_util": 0.5, "mem_util": 0.4},
        {"timestamp": 100, "node_id": "n2", "cpu_util": 0.2, "mem_util": 0.3},
        {"timestamp": 160, "node_id": "n1", "cpu_util": 0.6, "mem_util": 0.5},
    ]


def test_query_prometheus_instant_samples_merges_series_by_node(monkeypatch):
    payloads = [
        {
            "status": "success",
            "data": {
                "result": [
                    {"metric": {"instance": "node-1:9100"}, "value": [100, "0.25"]},
                    {"metric": {"instance": "node-2:9100"}, "value": [100, "0.50"]},
                ]
            },
        },
        {
            "status": "success",
            "data": {"result": [{"metric": {"instance": "node-1:9100"}, "value": [100, "0.75"]}]},
        },
    ]

    def fake_urlopen(url, timeout):
        return FakeResponse(payloads.pop(0))

    monkeypatch.setattr(prometheus, "urlopen", fake_urlopen)

    samples = prometheus.query_prometheus_instant_samples(
        base_url="http://prometheus.local",
        query_map={"cpu_util": "cpu", "mem_util": "mem"},
    )

    assert samples == {
        "cpu_util": {"node-1:9100": 0.25, "node-2:9100": 0.5},
        "mem_util": {"node-1:9100": 0.75},
    }
