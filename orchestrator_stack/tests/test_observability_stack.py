from pathlib import Path


def test_observability_manifest_installs_metrics_prometheus_and_node_exporter():
    manifest = Path("orchestrator_stack/k8s/observability/metrics-prometheus.yaml").read_text(encoding="utf-8")

    assert "name: v1beta1.metrics.k8s.io" in manifest
    assert "image: registry.k8s.io/metrics-server/metrics-server:" in manifest
    assert "--kubelet-insecure-tls" in manifest
    assert "name: prometheus-server" in manifest
    assert "image: prom/prometheus:" in manifest
    assert "name: prometheus-node-exporter" in manifest
    assert "image: quay.io/prometheus/node-exporter:" in manifest
    assert "job_name: node-exporter" in manifest
    assert "role: node" in manifest
    assert "emptyDir: {}" in manifest
    assert "openebs-hostpath" not in manifest


def test_bootstrap_observability_waits_for_real_metric_endpoints():
    script = Path("orchestrator_stack/scripts/bootstrap_observability.sh").read_text(encoding="utf-8")

    assert "deployment/metrics-server" in script
    assert "apiservice/v1beta1.metrics.k8s.io" in script
    assert "deployment/prometheus-server" in script
    assert "daemonset/prometheus-node-exporter" in script
    assert "kubectl top nodes" in script
    assert "prometheus-pvc" in script
    assert "openebs-hostpath" in script


def test_live_launcher_bootstraps_observability_and_forwards_prometheus():
    launcher = Path("orchestrator_stack/scripts/launch_orchestration.sh").read_text(encoding="utf-8")

    assert "OBSERVABILITY_STACK" in launcher
    assert "bootstrap_observability.sh" in launcher
    assert "PROMETHEUS_PORT_FORWARD" in launcher
    assert "port-forward svc/prometheus-server" in launcher
    assert 'PROMETHEUS_BASE_URL="http://127.0.0.1:$PROMETHEUS_PORT"' in launcher
    assert "--prometheus-base-url" in launcher
    assert "prometheus_base_url" in launcher
    assert "PROMETHEUS_PF_PID" in launcher
