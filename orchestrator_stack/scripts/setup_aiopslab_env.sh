#!/usr/bin/env bash
set -euo pipefail

ENV_DIR="${AIOPSLAB_ENV_DIR:-$HOME/Documents/aiopslab_validation_env}"
PYTHON_BIN="${PYTHON_BIN:-/opt/homebrew/bin/python3.12}"
AIOPSLAB_PIP_SPEC="${AIOPSLAB_PIP_SPEC:-git+https://github.com/microsoft/AIOpsLab.git}"
AIOPSLAB_REPO_DIR="${AIOPSLAB_REPO_DIR:-$HOME/Documents/AIOpsLab}"
KUBECONFIG_PATH="${AIOPSLAB_KUBECONFIG:-$ENV_DIR/kubeconfig}"

if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "Python 3.12 not found at $PYTHON_BIN" >&2
  echo "Install it first, for example: brew install python@3.12" >&2
  exit 1
fi

"$PYTHON_BIN" -m venv "$ENV_DIR"
"$ENV_DIR/bin/python" -m pip install --upgrade pip setuptools wheel
"$ENV_DIR/bin/python" -m pip install "$AIOPSLAB_PIP_SPEC"

if [[ ! -d "$AIOPSLAB_REPO_DIR/.git" ]]; then
  git clone --recurse-submodules https://github.com/microsoft/AIOpsLab.git "$AIOPSLAB_REPO_DIR"
else
  git -C "$AIOPSLAB_REPO_DIR" submodule update --init --recursive
fi

APP_TARGET="$ENV_DIR/lib/python3.12/site-packages/aiopslab-applications"
ln -sfn "$AIOPSLAB_REPO_DIR/aiopslab-applications" "$APP_TARGET"

CONFIG_EXAMPLE="$ENV_DIR/lib/python3.12/site-packages/aiopslab/config.yml.example"
CONFIG_FILE="$ENV_DIR/lib/python3.12/site-packages/aiopslab/config.yml"
if [[ -f "$CONFIG_EXAMPLE" && ! -f "$CONFIG_FILE" ]]; then
  cp "$CONFIG_EXAMPLE" "$CONFIG_FILE"
fi
if [[ -f "$CONFIG_FILE" ]]; then
  sed -i.bak 's/^k8s_host:.*/k8s_host: localhost/' "$CONFIG_FILE"
fi

MONITOR_CONFIG="$ENV_DIR/lib/python3.12/site-packages/aiopslab/observer/monitor_config.yaml"
if [[ -f "$MONITOR_CONFIG" ]]; then
  python3 - "$MONITOR_CONFIG" "$KUBECONFIG_PATH" <<'PY'
from pathlib import Path
import sys
path = Path(sys.argv[1])
kubeconfig = Path(sys.argv[2]).expanduser()
lines = []
for line in path.read_text(encoding='utf-8').splitlines():
    if line.startswith('kubernetes_path:'):
        lines.append(f"kubernetes_path: '{kubeconfig}'")
    else:
        lines.append(line)
path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
PY
fi

cat <<EOF
AIOpsLab validation environment ready:
  env: $ENV_DIR
  python: $($ENV_DIR/bin/python --version)
  applications: $APP_TARGET -> $AIOPSLAB_REPO_DIR/aiopslab-applications
  kubeconfig: $KUBECONFIG_PATH

Next validation command:
  PYTHONPATH=orchestrator_stack $ENV_DIR/bin/python orchestrator_stack/run.py aiopslab-preflight --kube-config $KUBECONFIG_PATH
EOF
