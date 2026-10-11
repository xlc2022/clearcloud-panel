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
    headers = {"Authorization": f"Bearer {secrets.get('api_key', '')}"}
    async with http_client(verify=bool(config.get("verify_tls"))) as client:
        r = await client.get(f"{url}/api/v2.0/system/info", headers=headers)
    if r.status_code == 401:
        return TestResult.fail("TrueNAS rejected the API key")
    if r.status_code != 200:
        return TestResult.fail(f"Unexpected response from TrueNAS: HTTP {r.status_code}")
    body = r.json()
    return TestResult(
        ok=True,
        message="Connected to TrueNAS",
        details=[
            Detail(label="Host", value=str(body.get("hostname", ""))),
            Detail(label="Version", value=str(body.get("version", ""))),
        ],
    )


TYPE = register(
    IntegrationType(
        kind="truenas",
        label="TrueNAS",
        description="Pool, disk, and service health for the Infrastructure page.",
        fields=[
            Field(
                key="url",
                label="Address",
                type="url",
                required=True,
                placeholder="https://truenas.local",
            ),
            Field(
                key="api_key",
                label="API Key",
                type="secret",
                required=True,
                help="In TrueNAS, open the user menu, then API Keys, then Add.",
            ),
            VERIFY_TLS,
        ],
        test=test,
    )
)
