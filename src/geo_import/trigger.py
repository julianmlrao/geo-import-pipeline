"""Tiny HTTP endpoint so the web UI can start an import without write access to the database.

POST /run   {"sources": ["id", ...] | null, "role": "demo" | "admin"}  (header X-Token)
GET  /status
Only the importer container writes to the database; this endpoint is not published.
"""

from __future__ import annotations

import hmac
import json
import logging
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from geo_import import config, pipeline

log = logging.getLogger(__name__)
DEMO_INTERVAL_S = int(os.environ.get("GEO_IMPORT_DEMO_INTERVAL", "600"))


class State:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.running = False
        self.run_id: str | None = None
        self.last_demo_start = 0.0
        self.last_status: str | None = None

    def start(self, source_ids: list[str] | None, role: str) -> tuple[int, dict[str, Any]]:
        with self.lock:
            if self.running:
                return 409, {"status": "running", "run_id": self.run_id}
            wait = DEMO_INTERVAL_S - (time.time() - self.last_demo_start)
            if role != "admin" and wait > 0:
                return 429, {"status": "rate_limited", "retry_after": int(wait)}
            sources = config.load_sources(config.sources_dir())
            if source_ids:
                sources = [s for s in sources if s.source_id in source_ids]
                if not sources:
                    return 400, {"status": "error", "error": "unknown source"}
            self.running = True
            if role != "admin":
                self.last_demo_start = time.time()
        threading.Thread(target=self._work, args=(sources,), daemon=True).start()
        return 202, {"status": "started"}

    def _work(self, sources: list[Any]) -> None:
        try:
            rr = pipeline.run(sources, on_start=lambda rid: setattr(self, "run_id", rid))
            self.last_status = rr.status
        except Exception:
            log.exception("triggered run crashed")
            self.last_status = "failed"
        finally:
            with self.lock:
                self.running = False

    def status(self) -> dict[str, Any]:
        return {"running": self.running, "run_id": self.run_id, "last_status": self.last_status}


def make_handler(state: State, token: str) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def _send(self, code: int, body: dict[str, Any]) -> None:
            data = json.dumps(body).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _authorized(self) -> bool:
            return bool(token) and hmac.compare_digest(self.headers.get("X-Token", ""), token)

        def do_GET(self) -> None:
            if not self._authorized():
                return self._send(401, {"error": "unauthorized"})
            self._send(200, state.status())

        def do_POST(self) -> None:
            if not self._authorized():
                return self._send(401, {"error": "unauthorized"})
            try:
                body = json.loads(
                    self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}"
                )
            except ValueError:
                return self._send(400, {"error": "bad json"})
            code, payload = state.start(body.get("sources"), str(body.get("role", "demo")))
            self._send(code, payload)

        def log_message(self, format: str, *args: Any) -> None:
            log.debug(format, *args)

    return Handler


def start_background(port: int = 8099) -> None:
    token = os.environ.get("GEO_IMPORT_TRIGGER_TOKEN", "")
    if not token:
        log.info("GEO_IMPORT_TRIGGER_TOKEN not set; trigger endpoint disabled")
        return
    server = ThreadingHTTPServer(("0.0.0.0", port), make_handler(State(), token))  # noqa: S104
    threading.Thread(target=server.serve_forever, daemon=True).start()
    log.info("trigger endpoint listening on :%d", port)
