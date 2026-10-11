"""JSON API under /api."""

from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response
from pydantic import BaseModel

from . import auth
from .integrations import REGISTRY, TestResult
from .store import Conflict, Invalid, NotFound, Store

router = APIRouter(prefix="/api")


def get_store(request: Request) -> Store:
    return request.app.state.store


# setup and sign-in -------------------------------------------------------------


class PasswordBody(BaseModel):
    password: str


@router.get("/setup/state")
def setup_state(request: Request, store: Store = Depends(get_store)) -> dict[str, bool]:
    return {
        "admin_created": store.password_hash(auth.ADMIN) is not None,
        "setup_complete": store.setup_complete,
        "authenticated": auth.current_user(request) is not None,
    }


@router.post("/setup/admin", status_code=204)
def setup_admin(
    body: PasswordBody, request: Request, response: Response, store: Store = Depends(get_store)
):
    if store.password_hash(auth.ADMIN) is not None:
        raise HTTPException(status_code=409, detail="The admin password is already set")
    if len(body.password) < auth.MIN_PASSWORD_LENGTH:
        raise HTTPException(
            status_code=422, detail=f"Use at least {auth.MIN_PASSWORD_LENGTH} characters"
        )
    try:
        store.create_user(auth.ADMIN, auth.hash_password(body.password))
    except Conflict as exc:
        raise HTTPException(status_code=409, detail="The admin password is already set") from exc
    auth.set_session_cookie(response, request, auth.create_session(store, auth.ADMIN))


@router.post("/setup/complete", status_code=204, dependencies=[Depends(auth.require_user)])
def setup_complete(store: Store = Depends(get_store)):
    store.set_setting("setup_complete", "1")


@router.post("/auth/login", status_code=204)
def login(
    body: PasswordBody, request: Request, response: Response, store: Store = Depends(get_store)
):
    stored = store.password_hash(auth.ADMIN)
    if stored is None or not auth.verify_password(body.password, stored):
        raise HTTPException(status_code=401, detail="Wrong password")
    auth.set_session_cookie(response, request, auth.create_session(store, auth.ADMIN))


@router.post("/auth/logout", status_code=204)
def logout(request: Request, response: Response, store: Store = Depends(get_store)):
    token = request.cookies.get(auth.SESSION_COOKIE)
    if token:
        auth.delete_session(store, token)
    response.delete_cookie(auth.SESSION_COOKIE, path="/")


# integrations ------------------------------------------------------------------

signed_in = APIRouter(dependencies=[Depends(auth.require_user)])


class IntegrationCreate(BaseModel):
    kind: str
    name: str | None = None
    enabled: bool = True
    config: dict[str, Any] = {}
    secrets: dict[str, Any] = {}


class IntegrationUpdate(BaseModel):
    name: str | None = None
    enabled: bool | None = None
    config: dict[str, Any] | None = None
    secrets: dict[str, Any] = {}


class TestRequest(BaseModel):
    kind: str
    config: dict[str, Any] = {}
    secrets: dict[str, Any] = {}
    id: int | None = None


def _translate(exc: Exception) -> HTTPException:
    status = {NotFound: 404, Conflict: 409, Invalid: 422}[type(exc)]
    return HTTPException(status_code=status, detail=str(exc))


@signed_in.get("/integration-types")
def integration_types() -> list[dict[str, Any]]:
    return [t.public() for t in REGISTRY.values()]


@signed_in.get("/integrations")
def list_integrations(store: Store = Depends(get_store)):
    return store.list_integrations()


def _refresh_status(request: Request, tasks: BackgroundTasks, kind: str) -> None:
    """Re-check a sidebar service right after it changes, instead of on the next cycle."""
    if REGISTRY[kind].status_key:
        tasks.add_task(request.app.state.status.check, kind)


@signed_in.post("/integrations", status_code=201)
def create_integration(
    body: IntegrationCreate,
    request: Request,
    tasks: BackgroundTasks,
    store: Store = Depends(get_store),
):
    try:
        created = store.create_integration(
            body.kind, body.name, body.config, body.secrets, body.enabled
        )
    except (Conflict, Invalid) as exc:
        raise _translate(exc) from exc
    _refresh_status(request, tasks, created["kind"])
    return created


@signed_in.put("/integrations/{integration_id}")
def update_integration(
    integration_id: int,
    body: IntegrationUpdate,
    request: Request,
    tasks: BackgroundTasks,
    store: Store = Depends(get_store),
):
    try:
        updated = store.update_integration(
            integration_id, body.name, body.config, body.secrets, body.enabled
        )
    except (NotFound, Invalid) as exc:
        raise _translate(exc) from exc
    _refresh_status(request, tasks, updated["kind"])
    return updated


@signed_in.delete("/integrations/{integration_id}", status_code=204)
def delete_integration(integration_id: int, store: Store = Depends(get_store)):
    try:
        store.delete_integration(integration_id)
    except NotFound as exc:
        raise _translate(exc) from exc


async def _run_test(
    request: Request, kind: str, config, secrets, integration_id: int | None
) -> TestResult:
    t = REGISTRY.get(kind)
    if t is None:
        raise HTTPException(status_code=422, detail=f"Unknown integration type {kind!r}")
    result = await t.test(config, secrets)
    if integration_id is not None:
        request.app.state.store.record_test(integration_id, result)
        if t.status_key and request.app.state.store.first_of_kind(kind) == integration_id:
            request.app.state.status.note(kind, result)
    return result


@signed_in.post("/integrations/test")
async def test_unsaved(
    body: TestRequest, request: Request, store: Store = Depends(get_store)
) -> TestResult:
    if body.kind not in REGISTRY:
        raise HTTPException(status_code=422, detail=f"Unknown integration type {body.kind!r}")
    stored: dict[str, str] = {}
    if body.id is not None:
        try:
            stored_kind, _, stored = store.resolved(body.id)
        except NotFound as exc:
            raise _translate(exc) from exc
        if stored_kind != body.kind:
            raise HTTPException(status_code=422, detail="Integration type does not match")
    config = {**REGISTRY[body.kind].defaults(), **body.config}
    secrets = store.merge_secrets(body.kind, body.secrets, stored)
    # An unsaved form is not recorded, so a failed experiment never overwrites the last real result.
    return await _run_test(request, body.kind, config, secrets, None)


@signed_in.post("/integrations/{integration_id}/test")
async def test_saved(
    integration_id: int, request: Request, store: Store = Depends(get_store)
) -> TestResult:
    try:
        kind, config, secrets = store.resolved(integration_id)
    except NotFound as exc:
        raise _translate(exc) from exc
    return await _run_test(request, kind, config, secrets, integration_id)


@signed_in.get("/status")
def status(request: Request):
    return {"services": request.app.state.status.snapshot()}


router.include_router(signed_in)
