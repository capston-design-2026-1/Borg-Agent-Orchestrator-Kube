from __future__ import annotations

import importlib.util
import importlib
import json
import os
import sys
from pathlib import Path
from typing import Any


def aiopslab_preflight(
    *,
    python_version: tuple[int, int, int] | None = None,
    python_executable: str | None = None,
    import_name: str = "aiopslab",
    import_checks: tuple[str, ...] = ("aiopslab", "aiopslab.paths", "aiopslab.orchestrator.orchestrator"),
    kube_config: str | None = None,
) -> dict[str, Any]:
    version = python_version or sys.version_info[:3]
    executable = python_executable or sys.executable
    compatible_python = (3, 11, 0) <= version < (3, 13, 0)
    has_package = importlib.util.find_spec(import_name) is not None if compatible_python else False
    kube_config_paths = _kube_config_paths(kube_config)
    kube_config_available = any(path.exists() for path in kube_config_paths)
    import_errors: dict[str, str] = {}
    if compatible_python and has_package:
        for module_name in import_checks:
            try:
                importlib.import_module(module_name)
            except Exception as exc:
                import_errors[module_name] = f"{type(exc).__name__}: {exc}"

    blockers: list[str] = []
    if not compatible_python:
        blockers.append("AIOpsLab requires Python >=3.11,<3.13")
    if compatible_python and not has_package:
        blockers.append("aiopslab package is not installed in this interpreter")
    if compatible_python and has_package and not kube_config_available:
        blockers.append("Kubernetes config not found; set KUBECONFIG or create ~/.kube/config before live AIOpsLab runs")
    for module_name, error in import_errors.items():
        blockers.append(f"import check failed for {module_name}: {error}")

    return {
        "status": "ready" if compatible_python and has_package and not import_errors else "blocked",
        "python_executable": executable,
        "python_version": ".".join(str(part) for part in version),
        "compatible_python": compatible_python,
        "aiopslab_package_available": has_package,
        "kube_config_available": kube_config_available,
        "kube_config_paths": [str(path) for path in kube_config_paths],
        "import_errors": import_errors,
        "blockers": blockers,
    }


def _kube_config_paths(kube_config: str | None = None) -> list[Path]:
    raw = kube_config if kube_config is not None else os.environ.get("KUBECONFIG", "")
    if raw:
        return [Path(item).expanduser() for item in raw.split(os.pathsep) if item]
    return [Path("~/.kube/config").expanduser()]


def write_aiopslab_preflight_report(report: dict[str, Any], out_path: str | Path) -> Path:
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return out
