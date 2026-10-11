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
    token = f"PVEAPIToken={config.get('token_id', '')}={secrets.get('token_secret', '')}"
    async with http_client(verify=bool(config.get("verify_tls"))) as client:
        version = await client.get(f"{url}/api2/json/version", headers={"Authorization": token})
        if version.status_code == 401:
            return TestResult.fail("Proxmox rejected the API token")
        if version.status_code != 200:
            return TestResult.fail(f"Unexpected response from Proxmox: HTTP {version.status_code}")
        nodes = await client.get(f"{url}/api2/json/nodes", headers={"Authorization": token})
    data = version.json().get("data", {})
    node_names = (
        [n.get("node", "") for n in nodes.json().get("data", [])]
        if nodes.status_code == 200
        else []
    )
    return TestResult(
        ok=True,
        message="Connected to Proxmox",
        details=[
            Detail(label="Version", value=str(data.get("version", ""))),
            Detail(label="Nodes", value=", ".join(node_names) or "none visible to this token"),
        ],
    )


TYPE = register(
    IntegrationType(
        kind="proxmox",
        label="Proxmox",
        description="Host and VM health for the Infrastructure page.",
        fields=[
            Field(
                key="url",
                label="Address",
                type="url",
                required=True,
                placeholder="https://pve.local:8006",
            ),
            Field(
                key="token_id",
                label="API Token ID",
                type="text",
                required=True,
                placeholder="monitor@pve!panel",
                help="Datacenter, Permissions, API Tokens. A read-only PVEAuditor role is enough.",
            ),
            Field(key="token_secret", label="API Token Secret", type="secret", required=True),
            VERIFY_TLS,
        ],
        test=test,
    )
)
