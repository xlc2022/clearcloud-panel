from ._common import VERIFY_TLS
from .base import (
    Detail,
    Field,
    IntegrationType,
    TestResult,
    base_url,
    guarded,
    http_client,
    register,
)


@guarded
async def test(config, secrets) -> TestResult:
    url = base_url(config)
    async with http_client(verify=bool(config.get("verify_tls"))) as client:
        info = await client.get(f"{url}/api/info")
        if info.status_code != 200:
            return TestResult.fail(f"No Omada controller answered: HTTP {info.status_code}")
        result = info.json().get("result", {})
        controller_id = result.get("omadacId")
        if not controller_id:
            return TestResult.fail(
                "That address answered, but it does not look like an Omada controller"
            )
        login = await client.post(
            f"{url}/{controller_id}/api/v2/login",
            json={"username": config.get("username", ""), "password": secrets.get("password", "")},
        )
    body = login.json() if login.status_code == 200 else {}
    if body.get("errorCode") != 0:
        return TestResult.fail(body.get("msg") or f"Omada login failed: HTTP {login.status_code}")
    return TestResult(
        ok=True,
        message="Signed in to the Omada controller",
        details=[Detail(label="Controller version", value=str(result.get("controllerVer", "")))],
    )


TYPE = register(
    IntegrationType(
        kind="omada",
        label="Omada Controller",
        description="Access points, switches, clients, and the WAN for the Network page.",
        fields=[
            Field(
                key="url",
                label="Address",
                type="url",
                required=True,
                placeholder="https://omada.local:8043",
            ),
            Field(
                key="username",
                label="Username",
                type="text",
                required=True,
                help="A local controller account. A Viewer role is enough.",
            ),
            Field(key="password", label="Password", type="secret", required=True),
            VERIFY_TLS,
        ],
        test=test,
    )
)
