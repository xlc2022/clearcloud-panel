"""Same-origin reverse proxy to Grafana at /grafana.

The panel's own session gates every request, then the panel signs in to
Grafana on the user's behalf, so there is one login.
"""

import asyncio
import contextlib
import logging

import httpx
import websockets
from fastapi import APIRouter, Request, WebSocket
from fastapi.responses import JSONResponse, StreamingResponse
from starlette.background import BackgroundTask

from . import auth
from .integrations import grafana
from .store import Store

log = logging.getLogger(__name__)
router = APIRouter()

HOP_BY_HOP = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailer",
    "transfer-encoding",
    "upgrade",
    "host",
}
# Never let a browser supply its own Grafana identity.
STRIPPED_REQUEST = HOP_BY_HOP | {"authorization", "x-webauth-user", "content-length"}
METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"]


def _grafana(store: Store) -> tuple[dict, dict] | None:
    integration_id = store.first_of_kind("grafana")
    if integration_id is None:
        return None
    _, config, secrets = store.resolved(integration_id)
    return config, secrets


def _strip_panel_cookie(cookie_header: str | None) -> str | None:
    if not cookie_header:
        return None
    kept = [
        c for c in cookie_header.split(";") if c.strip().split("=", 1)[0] != auth.SESSION_COOKIE
    ]
    return ";".join(kept).strip() or None


def _upstream_headers(raw, config, secrets) -> dict[str, str]:
    headers = {
        k: v for k, v in raw.items() if k.lower() not in STRIPPED_REQUEST and k.lower() != "cookie"
    }
    cookie = _strip_panel_cookie(raw.get("cookie"))
    if cookie:
        headers["cookie"] = cookie
    headers.update(grafana.auth_headers(config, secrets))
    return headers


def _rewrite_location(location: str, upstream_root: str) -> str:
    base = upstream_root[: -len(grafana.SUB_PATH)]
    return location[len(base) :] if location.startswith(base) else location


@router.api_route("/grafana", methods=METHODS, include_in_schema=False)
@router.api_route("/grafana/{path:path}", methods=METHODS, include_in_schema=False)
async def proxy(request: Request, path: str = ""):
    if auth.current_user(request) is None:
        return JSONResponse({"detail": "Sign in required"}, status_code=401)
    store: Store = request.app.state.store
    found = _grafana(store)
    if found is None:
        return JSONResponse({"detail": "Grafana is not set up yet"}, status_code=503)
    config, secrets = found
    root = grafana.upstream_root(config)
    client: httpx.AsyncClient = request.app.state.proxy_client
    upstream = client.build_request(
        request.method,
        f"{root}/{path}",
        params=request.query_params.multi_items(),
        headers=_upstream_headers(request.headers, config, secrets),
        content=request.stream(),
    )
    try:
        response = await client.send(upstream, stream=True)
    except httpx.HTTPError as exc:
        log.warning("Grafana proxy error: %s", exc)
        return JSONResponse({"detail": "Grafana is not reachable"}, status_code=502)
    headers = [(k, v) for k, v in response.headers.multi_items() if k.lower() not in HOP_BY_HOP]
    headers = [
        (k, _rewrite_location(v, root) if k.lower() == "location" else v) for k, v in headers
    ]
    result = StreamingResponse(
        response.aiter_raw(),
        status_code=response.status_code,
        background=BackgroundTask(response.aclose),
    )
    result.raw_headers = [(k.lower().encode("latin-1"), v.encode("latin-1")) for k, v in headers]
    return result


@router.websocket("/grafana/{path:path}")
async def proxy_ws(ws: WebSocket, path: str):
    store: Store = ws.app.state.store
    found = _grafana(store)
    if auth.session_user(store, ws.cookies.get(auth.SESSION_COOKIE)) is None or found is None:
        await ws.close(code=4401)
        return
    config, secrets = found
    root = grafana.upstream_root(config)
    url = root.replace("http", "ws", 1) + "/" + path
    if ws.url.query:
        url += "?" + ws.url.query
    headers = grafana.auth_headers(config, secrets)
    cookie = _strip_panel_cookie(ws.headers.get("cookie"))
    if cookie:
        headers["cookie"] = cookie
    subprotocols = ws.scope.get("subprotocols") or None
    try:
        upstream = await websockets.connect(
            url, additional_headers=headers, subprotocols=subprotocols
        )
    except Exception as exc:  # noqa: BLE001
        log.warning("Grafana websocket proxy error: %s", exc)
        await ws.close(code=1011)
        return
    await ws.accept(subprotocol=upstream.subprotocol)

    async def client_to_upstream():
        while True:
            message = await ws.receive()
            if message["type"] == "websocket.disconnect":
                return
            await upstream.send(
                message.get("text") if message.get("text") is not None else message.get("bytes")
            )

    async def upstream_to_client():
        async for message in upstream:
            if isinstance(message, str):
                await ws.send_text(message)
            else:
                await ws.send_bytes(message)

    tasks = [asyncio.create_task(client_to_upstream()), asyncio.create_task(upstream_to_client())]
    try:
        await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
    finally:
        for t in tasks:
            t.cancel()
        await upstream.close()
        with contextlib.suppress(RuntimeError):
            await ws.close()
