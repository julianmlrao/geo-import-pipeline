"""Demo web UI: sources, map, reports, import trigger, read-only config view."""

from __future__ import annotations

import hmac
import json
import logging
import os
import time
from collections import defaultdict, deque
from pathlib import Path
from typing import Any

import markdown
import psycopg
import requests
from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from psycopg.rows import dict_row
from starlette.middleware.sessions import SessionMiddleware

from geo_import import config, report

log = logging.getLogger("geo_import.web")
BASE = os.environ.get("WEB_BASE", "/demo").rstrip("/")
HERE = Path(__file__).parent
templates = Jinja2Templates(directory=str(HERE / "templates"))

CSP = (
    "default-src 'self'; img-src 'self' data: https://sgx.geodatenzentrum.de; "
    "worker-src blob:; child-src blob:; connect-src 'self' https://sgx.geodatenzentrum.de; "
    "style-src 'self' 'unsafe-inline'; "
    "script-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
)

_attempts: dict[str, deque[float]] = defaultdict(deque)


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


def _users() -> dict[str, tuple[str, str]]:
    users = {}
    if _env("DEMO_PASSWORD"):
        users[_env("DEMO_USER", "demo")] = (_env("DEMO_PASSWORD"), "demo")
    if _env("ADMIN_PASSWORD"):
        users["admin"] = (_env("ADMIN_PASSWORD"), "admin")
    return users


def _db() -> psycopg.Connection[dict[str, Any]]:
    dsn = (
        f"host={_env('POSTGRES_HOST', 'db')} dbname={_env('POSTGRES_DB', 'geo')} "
        f"user={_env('WEB_DB_USER', 'geo_reader')} password={_env('GEO_READER_PASSWORD', 'reader')}"
    )
    return psycopg.connect(dsn, row_factory=dict_row, connect_timeout=10)


def client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for")
    if fwd and _env("TRUST_PROXY") == "1":
        return fwd.split(",")[-1].strip()  # last hop = address seen by our own proxy
    return request.client.host if request.client else "?"


def rate_limited(ip: str, limit: int = 10, window: float = 60.0) -> bool:
    now = time.monotonic()
    q = _attempts[ip]
    while q and now - q[0] > window:
        q.popleft()
    if len(q) >= limit:
        return True
    q.append(now)
    return False


def create_app() -> FastAPI:
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    app.add_middleware(
        SessionMiddleware,
        secret_key=_env("SESSION_SECRET") or os.urandom(32).hex(),
        session_cookie="geo_session",
        max_age=8 * 3600,
        same_site="lax",
        https_only=_env("COOKIE_SECURE") == "1",
        path=BASE or "/",
    )

    @app.middleware("http")
    async def security_headers(request: Request, call_next: Any) -> Response:
        try:
            resp: Response = await call_next(request)
        except Exception:
            log.exception("unhandled error on %s", request.url.path)
            resp = HTMLResponse("<h1>Interner Fehler</h1>", status_code=500)
        resp.headers["Content-Security-Policy"] = CSP
        resp.headers["X-Content-Type-Options"] = "nosniff"
        resp.headers["X-Frame-Options"] = "DENY"
        resp.headers["Referrer-Policy"] = "same-origin"
        resp.headers["Cache-Control"] = resp.headers.get("Cache-Control", "no-store")
        return resp

    app.mount(f"{BASE}/static", StaticFiles(directory=str(HERE / "static")), name="static")
    app.mount(
        f"{BASE}/vendor",
        StaticFiles(directory=_env("WEB_VENDOR_DIR", "site/vendor"), check_dir=False),
        name="vendor",
    )

    def user_of(request: Request) -> dict[str, str] | None:
        u = request.session.get("user")
        return u if isinstance(u, dict) else None

    def page(request: Request, name: str, **ctx: Any) -> HTMLResponse:
        return templates.TemplateResponse(
            request, name, {"base": BASE, "user": user_of(request), **ctx}
        )

    def require(request: Request) -> dict[str, str]:
        u = user_of(request)
        if not u:
            raise HTTPException(status_code=401)
        return u

    @app.exception_handler(HTTPException)
    async def http_exc(request: Request, exc: HTTPException) -> Response:
        if exc.status_code == 401 and not request.url.path.startswith(f"{BASE}/api/"):
            return RedirectResponse(f"{BASE}/login", status_code=303)
        return JSONResponse({"error": exc.detail}, status_code=exc.status_code)

    @app.get(BASE + "/", include_in_schema=False)
    def index(request: Request) -> Response:
        return RedirectResponse(f"{BASE}/sources" if user_of(request) else f"{BASE}/login")

    @app.get(BASE + "/login", response_class=HTMLResponse)
    def login_form(request: Request) -> HTMLResponse:
        return page(request, "login.html", error=None)

    @app.post(BASE + "/login")
    def login(request: Request, username: str = Form(""), password: str = Form("")) -> Response:
        if rate_limited(client_ip(request)):
            return page(request, "login.html", error="Zu viele Versuche. Bitte kurz warten.")
        entry = _users().get(username)
        ok = entry is not None and hmac.compare_digest(entry[0].encode(), password.encode())
        if not ok or entry is None:
            log.warning("failed login for %r from %s", username[:32], client_ip(request))
            resp = page(request, "login.html", error="Benutzer oder Passwort falsch.")
            resp.status_code = 401
            return resp
        request.session["user"] = {"name": username, "role": entry[1]}
        return RedirectResponse(f"{BASE}/sources", status_code=303)

    @app.post(BASE + "/logout")
    def logout(request: Request) -> Response:
        request.session.clear()
        return RedirectResponse(f"{BASE}/login", status_code=303)

    @app.get(BASE + "/sources", response_class=HTMLResponse)
    def sources(request: Request) -> HTMLResponse:
        require(request)
        with _db() as conn:
            rows = conn.execute(
                "SELECT source_id, title, source_type, license, attribution, last_import_at, "
                "record_count, url, layer FROM geo_import.metadata ORDER BY source_id"
            ).fetchall()
        return page(request, "sources.html", rows=rows, api=_env("API_PATH", "/api"))

    @app.get(BASE + "/map", response_class=HTMLResponse)
    def map_page(request: Request) -> HTMLResponse:
        require(request)
        return page(request, "map.html", tiles=_env("TILES_PATH", "/tiles"))

    @app.get(BASE + "/api/layers")
    def layers(request: Request) -> JSONResponse:
        require(request)
        with _db() as conn:
            rows = conn.execute(
                "SELECT m.source_id, m.title, m.attribution, "
                "       max(CASE WHEN GeometryType(g.geom) LIKE '%%POINT' THEN 'point' "
                "                WHEN GeometryType(g.geom) LIKE '%%LINESTRING' THEN 'line' "
                "                ELSE 'polygon' END) AS kind, "
                "       ST_AsGeoJSON(ST_Extent(g.geom))::json AS extent "
                "FROM geo_import.metadata m JOIN geo_import.geometries g USING (source_id) "
                "WHERE g.valid_to IS NULL GROUP BY m.source_id, m.title, m.attribution "
                "ORDER BY 1"
            ).fetchall()
        return JSONResponse(rows)

    @app.get(BASE + "/api/feature")
    def feature(request: Request, source: str, key: str) -> JSONResponse:
        """Attributes of a feature, including attributes of sources joined onto it."""
        require(request)
        with _db() as conn:
            rows = conn.execute(
                "SELECT a.source_id, m.title, a.key, a.value_text, a.value_num, a.value_date, "
                "a.unit FROM geo_import.attributes a "
                "JOIN geo_import.metadata m USING (source_id) "
                "WHERE a.feature_key = %s AND a.valid_to IS NULL AND (a.source_id = %s "
                "  OR m.details->>'join_target' = %s) ORDER BY (a.source_id = %s) DESC, a.key",
                (key, source, source, source),
            ).fetchall()
        out = []
        for r in rows:
            val = (
                r["value_num"]
                if r["value_num"] is not None
                else (str(r["value_date"]) if r["value_date"] else r["value_text"])
            )
            out.append({"source": r["title"], "key": r["key"], "value": val, "unit": r["unit"]})
        return JSONResponse(out)

    @app.get(BASE + "/reports", response_class=HTMLResponse)
    def reports(request: Request) -> HTMLResponse:
        require(request)
        with _db() as conn:
            rows = conn.execute(
                "SELECT run_id, started_at, ended_at, status FROM geo_import.import_runs "
                "ORDER BY started_at DESC LIMIT 50"
            ).fetchall()
        return page(request, "reports.html", rows=rows)

    def _report(run_id: str) -> dict[str, Any]:
        with _db() as conn:
            row = conn.execute(
                "SELECT report FROM geo_import.import_runs WHERE run_id = %s", (run_id,)
            ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="report not found")
        data: dict[str, Any] = row["report"]
        return data

    @app.get(BASE + "/reports/{run_id}", response_class=HTMLResponse)
    def report_detail(request: Request, run_id: str) -> HTMLResponse:
        require(request)
        data = _report(run_id)
        html = markdown.markdown(report.to_markdown(data), extensions=["tables"])
        return page(request, "report.html", run_id=run_id, html=html)

    @app.get(BASE + "/reports/{run_id}.json")
    def report_json(request: Request, run_id: str) -> Response:
        require(request)
        return Response(
            json.dumps(_report(run_id), indent=2, ensure_ascii=False),
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="{run_id}.json"'},
        )

    @app.get(BASE + "/config", response_class=HTMLResponse)
    def config_view(request: Request) -> HTMLResponse:
        require(request)
        files = {
            p.name: p.read_text(encoding="utf-8")
            for p in sorted(config.sources_dir().glob("*.y*ml"))
        }
        return page(request, "config.html", files=files)

    def _trigger(method: str, body: dict[str, Any] | None = None) -> requests.Response:
        url = _env("TRIGGER_URL", "http://importer:8099")
        headers = {"X-Token": _env("GEO_IMPORT_TRIGGER_TOKEN")}
        if method == "POST":
            return requests.post(f"{url}/run", json=body, headers=headers, timeout=10)
        return requests.get(f"{url}/status", headers=headers, timeout=10)

    @app.get(BASE + "/import", response_class=HTMLResponse)
    def import_page(request: Request) -> HTMLResponse:
        require(request)
        ids = [s.source_id for s in config.load_sources(config.sources_dir())]
        return page(request, "import.html", source_ids=ids)

    @app.post(BASE + "/api/import")
    def start_import(request: Request, source: str = Form("")) -> JSONResponse:
        user = require(request)
        body = {"sources": [source] if source else None, "role": user["role"]}
        try:
            r = _trigger("POST", body)
        except requests.RequestException:
            return JSONResponse({"status": "error", "error": "Importer nicht erreichbar"}, 503)
        return JSONResponse(r.json(), r.status_code)

    @app.get(BASE + "/api/import/status")
    def import_status(request: Request) -> JSONResponse:
        require(request)
        try:
            r = _trigger("GET")
        except requests.RequestException:
            return JSONResponse({"error": "Importer nicht erreichbar"}, 503)
        return JSONResponse(r.json(), r.status_code)

    @app.get("/healthz", include_in_schema=False)
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
