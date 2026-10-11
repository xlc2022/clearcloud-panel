"""Application entry point: ``uvicorn clearcloud_panel.main:app``."""

import logging
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from . import api, db, grafana_proxy
from .config import Settings, load_settings
from .crypto import SecretBox, load_or_create_key
from .status import StatusMonitor
from .store import Store

log = logging.getLogger(__name__)


def create_app(settings: Settings | None = None, *, background: bool = True) -> FastAPI:
    settings = settings or load_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if background:
            app.state.status.start()
        try:
            yield
        finally:
            await app.state.status.stop()
            await app.state.proxy_client.aclose()

    app = FastAPI(
        title="Clear Cloud Farm panel",
        lifespan=lifespan,
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
        redoc_url=None,
    )
    store = Store(db.connect(settings.db_path), SecretBox(load_or_create_key(settings.key_path)))
    store.seed_defaults()
    app.state.settings = settings
    app.state.store = store
    app.state.status = StatusMonitor(store)
    app.state.proxy_client = httpx.AsyncClient(
        timeout=httpx.Timeout(60.0, connect=5.0), follow_redirects=False
    )

    app.include_router(api.router)
    app.include_router(grafana_proxy.router)

    @app.get("/healthz", include_in_schema=False)
    def healthz():
        return {"ok": True}

    @app.api_route(
        "/api/{path:path}",
        methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        include_in_schema=False,
    )
    def api_not_found(path: str):
        raise HTTPException(status_code=404, detail="Not found")

    static = settings.static_dir
    index = static / "index.html"
    if (static / "assets").is_dir():
        app.mount("/assets", StaticFiles(directory=static / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str, request: Request):
        candidate = (static / path).resolve()
        if path and candidate.is_file() and candidate.is_relative_to(static):
            return FileResponse(candidate)
        if index.is_file():
            return FileResponse(index, headers={"Cache-Control": "no-cache"})
        return JSONResponse(
            {"detail": "Frontend not built. Run npm run build in panel/frontend."}, status_code=404
        )

    return app


def __getattr__(name: str):
    # Built lazily so importing the package (tests, tooling) does not touch the data directory.
    if name == "app":
        logging.basicConfig(level=logging.INFO)
        return create_app()
    raise AttributeError(name)
