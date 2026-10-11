"""The shared shape every integration kind follows.

A kind declares the fields the GUI renders and a ``test`` coroutine behind
the Test button. Collectors added later hang off the same registry.
"""

import socket
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any, Literal

import httpx
from pydantic import BaseModel

FieldType = Literal["text", "url", "secret", "number", "bool", "select"]


class Option(BaseModel):
    value: str
    label: str


class Field(BaseModel):
    key: str
    label: str
    type: FieldType
    required: bool = False
    default: Any = None
    help: str | None = None
    placeholder: str | None = None
    options: list[Option] | None = None


class Detail(BaseModel):
    label: str
    value: str


class TestResult(BaseModel):
    ok: bool
    message: str
    details: list[Detail] = []

    @classmethod
    def fail(cls, message: str) -> "TestResult":
        return cls(ok=False, message=message)


TestFn = Callable[[dict[str, Any], dict[str, str]], Awaitable[TestResult]]


@dataclass
class IntegrationType:
    kind: str
    label: str
    description: str
    fields: list[Field]
    test: TestFn
    multiple: bool = False
    status_key: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def secret_keys(self) -> set[str]:
        return {f.key for f in self.fields if f.type == "secret"}

    def defaults(self) -> dict[str, Any]:
        return {f.key: f.default for f in self.fields if f.default is not None}

    def public(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "label": self.label,
            "description": self.description,
            "multiple": self.multiple,
            "fields": [f.model_dump() for f in self.fields],
        }


REGISTRY: dict[str, IntegrationType] = {}


def register(t: IntegrationType) -> IntegrationType:
    REGISTRY[t.kind] = t
    return t


TIMEOUT = httpx.Timeout(10.0, connect=5.0)


def http_client(verify: bool = True) -> httpx.AsyncClient:
    return httpx.AsyncClient(timeout=TIMEOUT, verify=verify, follow_redirects=False)


def base_url(config: dict[str, Any], key: str = "url") -> str:
    return str(config.get(key) or "").strip().rstrip("/")


def describe_error(exc: Exception) -> str:
    if isinstance(exc, socket.gaierror):
        return "Could not find that host name on the network"
    if isinstance(exc, ConnectionRefusedError):
        return "Nothing is listening at that address and port"
    if isinstance(exc, TimeoutError | httpx.ConnectTimeout | httpx.ReadTimeout):
        return "Timed out waiting for a response"
    if isinstance(exc, httpx.ConnectError):
        return f"Could not connect: {exc}"
    if isinstance(exc, httpx.InvalidURL | httpx.UnsupportedProtocol):
        return "That address is not a valid http(s) URL"
    return f"{type(exc).__name__}: {exc}"


def guarded(fn: TestFn) -> TestFn:
    """Turn any exception inside a test into a failed result."""

    async def wrapper(config: dict[str, Any], secrets: dict[str, str]) -> TestResult:
        try:
            return await fn(config, secrets)
        except Exception as exc:  # noqa: BLE001 - shown to the user
            return TestResult.fail(describe_error(exc))

    return wrapper
