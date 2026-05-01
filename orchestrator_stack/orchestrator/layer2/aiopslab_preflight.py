from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any


def aiopslab_preflight(
    *,
    python_version: tuple[int, int, int] | None = None,
    python_executable: str | None = None,
    import_name: str = "aiopslab",
) -> dict[str, Any]:
    version = python_version or sys.version_info[:3]
    executable = python_executable or sys.executable
    compatible_python = (3, 11, 0) <= version < (3, 13, 0)
    has_package = importlib.util.find_spec(import_name) is not None if compatible_python else False

    blockers: list[str] = []
    if not compatible_python:
        blockers.append("AIOpsLab requires Python >=3.11,<3.13")
    if compatible_python and not has_package:
        blockers.append("aiopslab package is not installed in this interpreter")

    return {
        "status": "ready" if compatible_python and has_package else "blocked",
        "python_executable": executable,
        "python_version": ".".join(str(part) for part in version),
        "compatible_python": compatible_python,
        "aiopslab_package_available": has_package,
        "blockers": blockers,
    }


def write_aiopslab_preflight_report(report: dict[str, Any], out_path: str | Path) -> Path:
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return out
