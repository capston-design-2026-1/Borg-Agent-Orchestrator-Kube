#!/usr/bin/env bash
set -euo pipefail

ENV_DIR="${AIOPSLAB_ENV_DIR:-$HOME/Documents/aiopslab_validation_env}"
PYTHON_BIN="${PYTHON_BIN:-/opt/homebrew/bin/python3.12}"
AIOPSLAB_REPO="${AIOPSLAB_REPO:-git+https://github.com/microsoft/AIOpsLab.git}"

if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "Python 3.12 not found at $PYTHON_BIN" >&2
  echo "Install it first, for example: brew install python@3.12" >&2
  exit 1
fi

"$PYTHON_BIN" -m venv "$ENV_DIR"
"$ENV_DIR/bin/python" -m pip install --upgrade pip setuptools wheel
"$ENV_DIR/bin/python" -m pip install "$AIOPSLAB_REPO"

CONFIG_EXAMPLE="$ENV_DIR/lib/python3.12/site-packages/aiopslab/config.yml.example"
CONFIG_FILE="$ENV_DIR/lib/python3.12/site-packages/aiopslab/config.yml"
if [[ -f "$CONFIG_EXAMPLE" && ! -f "$CONFIG_FILE" ]]; then
  cp "$CONFIG_EXAMPLE" "$CONFIG_FILE"
fi

cat <<EOF
AIOpsLab validation environment ready:
  env: $ENV_DIR
  python: $($ENV_DIR/bin/python --version)

Next validation command:
  PYTHONPATH=orchestrator_stack $ENV_DIR/bin/python orchestrator_stack/run.py aiopslab-preflight
EOF
