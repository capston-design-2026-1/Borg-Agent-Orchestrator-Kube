from __future__ import annotations

import argparse
import json
import re
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse


class DashboardHandler(SimpleHTTPRequestHandler):
    event_dir = Path("orchestrator_stack/runtime/visualization")
    dashboard_dir = Path("orchestrator_stack/dashboard")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(self.dashboard_dir), **kwargs)

    def _json(self, payload: object, status: int = 200) -> None:
        body = json.dumps(payload, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _dashboard_version(self) -> str:
        index_path = self.dashboard_dir / "index.html"
        if index_path.exists():
            match = re.search(r'window\.DASHBOARD_VERSION\s*=\s*"([^"]+)"', index_path.read_text(encoding="utf-8"))
            if match:
                return match.group(1)
        return "0"

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path == "/api/state":
            state_path = self.event_dir / "state.json"
            if not state_path.exists():
                self._json({"status": "waiting", "message": "state.json not created yet"})
                return
            self._json(json.loads(state_path.read_text(encoding="utf-8")))
            return
        if path == "/api/events":
            events_path = self.event_dir / "events.jsonl"
            events = []
            if events_path.exists():
                events = [json.loads(line) for line in events_path.read_text(encoding="utf-8").splitlines()[-200:] if line.strip()]
            self._json(events)
            return
        if path == "/api/architecture":
            arch_path = Path("docs/repository_architecture.mmd")
            self._json({"path": str(arch_path), "text": arch_path.read_text(encoding="utf-8") if arch_path.exists() else ""})
            return
        if path == "/api/dashboard-version":
            self._json({"version": self._dashboard_version()})
            return
        return super().do_GET()


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve Borg orchestrator live dashboard")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--event-dir", default="orchestrator_stack/runtime/visualization")
    args = parser.parse_args()
    DashboardHandler.event_dir = Path(args.event_dir)
    server = ThreadingHTTPServer((args.host, args.port), DashboardHandler)
    print(f"dashboard=http://{args.host}:{args.port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
