from pathlib import Path


def test_local_comparison_cluster_assets_are_tracked():
    expected = [
        "orchestrator_stack/k8s/kind/experimental-multinode.yaml",
        "orchestrator_stack/k8s/kind/baseline-hpa-karpenter-multinode.yaml",
        "orchestrator_stack/k8s/kind/aiopslab-multinode.yaml",
        "orchestrator_stack/k8s/baseline/hpa-workload.yaml",
        "orchestrator_stack/k8s/baseline/karpenter-surge-workload.yaml",
        "orchestrator_stack/scripts/create_local_comparison_clusters.sh",
        "orchestrator_stack/scripts/local_karpenter_controller.py",
        "orchestrator_stack/scripts/apply_comparison_stimulus.sh",
        "orchestrator_stack/scripts/launch_cluster_comparison.sh",
        "orchestrator_stack/scripts/launch_experimental_multinode_orchestration.sh",
        "orchestrator_stack/comparison_dashboard/index.html",
        "docs/LOCAL_CLUSTER_COMPARISON.md",
    ]
    for path in expected:
        assert Path(path).exists(), path


def test_baseline_manifest_uses_real_hpa_and_local_karpenter_boundary():
    hpa = Path("orchestrator_stack/k8s/baseline/hpa-workload.yaml").read_text(encoding="utf-8")
    controller = Path("orchestrator_stack/scripts/local_karpenter_controller.py").read_text(encoding="utf-8")
    guide = Path("docs/LOCAL_CLUSTER_COMPARISON.md").read_text(encoding="utf-8")
    setup = Path("orchestrator_stack/scripts/setup_kind_cluster.sh").read_text(encoding="utf-8")

    assert "kind: HorizontalPodAutoscaler" in hpa
    assert "autoscaling/v2" in hpa
    assert "registry.k8s.io/hpa-example" in hpa
    assert "local-kind-karpenter-emulation" in controller
    assert "borg.local/provisioning-state=active" in controller
    assert "borg.local/capacity=warm:NoSchedule" in controller
    assert "This is not real AWS Karpenter" in guide
    assert "aiopslab-multinode.yaml" in setup
    assert "RECREATE" in setup


def test_comparison_dashboard_exposes_expected_api_and_signals():
    server = Path("orchestrator_stack/orchestrator/comparison_dashboard_server.py").read_text(encoding="utf-8")
    app = Path("orchestrator_stack/comparison_dashboard/app.js").read_text(encoding="utf-8")

    assert "/api/comparison" in server
    assert "experimental" in server
    assert "baseline" in server
    assert "shared_stimulus" in server
    assert "_difference_rows" in server
    assert "resource_totals" in server
    assert "pod_summary" in server
    assert "HPA + Local Karpenter" in Path("orchestrator_stack/comparison_dashboard/index.html").read_text(encoding="utf-8")
    assert "experimentalPending" in app
    assert "baselinePending" in app
    assert "hpaDesired" in app
    assert "timelineCanvas" in app
    assert "resourcePieCanvas" in app
    assert "capacityCanvas" in app
    assert "shared intentional stimulus" in app
