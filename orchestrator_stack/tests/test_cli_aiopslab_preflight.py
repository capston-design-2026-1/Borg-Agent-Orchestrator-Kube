from orchestrator.cli import build_parser


def test_aiopslab_preflight_cli_accepts_kube_config():
    parser = build_parser()

    args = parser.parse_args(["aiopslab-preflight", "--kube-config", "/tmp/kubeconfig", "--out", "/tmp/report.json"])

    assert args.kube_config == "/tmp/kubeconfig"
    assert args.out == "/tmp/report.json"


def test_evaluation_statistics_cli_accepts_summary_paths():
    parser = build_parser()

    args = parser.parse_args(
        [
            "evaluation-statistics",
            "--repeated-seed-summary",
            "/tmp/repeated.json",
            "--controlled-ablation-summary",
            "/tmp/controlled.json",
            "--out-json",
            "/tmp/stats.json",
            "--out-md",
            "/tmp/stats.md",
        ]
    )

    assert args.repeated_seed_summary == "/tmp/repeated.json"
    assert args.controlled_ablation_summary == "/tmp/controlled.json"
    assert args.out_json == "/tmp/stats.json"
    assert args.out_md == "/tmp/stats.md"
