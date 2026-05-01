from orchestrator.cli import build_parser


def test_aiopslab_preflight_cli_accepts_kube_config():
    parser = build_parser()

    args = parser.parse_args(["aiopslab-preflight", "--kube-config", "/tmp/kubeconfig", "--out", "/tmp/report.json"])

    assert args.kube_config == "/tmp/kubeconfig"
    assert args.out == "/tmp/report.json"
