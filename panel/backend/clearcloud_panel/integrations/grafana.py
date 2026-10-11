from .base import (
    Detail,
    Field,
    IntegrationType,
    Option,
    TestResult,
    base_url,
    guarded,
    http_client,
    register,
)

DEFAULT_URL = "http://grafana:3000"
SUB_PATH = "/grafana"


def upstream_root(config) -> str:
    """Grafana serves from /grafana so its links work through the panel proxy."""
    url = base_url(config) or DEFAULT_URL
    return url if url.endswith(SUB_PATH) else url + SUB_PATH


def auth_headers(config, secrets) -> dict[str, str]:
    if config.get("auth_mode", "proxy") == "token":
        return {"Authorization": f"Bearer {secrets.get('token', '')}"}
    return {"X-WEBAUTH-USER": str(config.get("proxy_user") or "admin")}


@guarded
async def test(config, secrets) -> TestResult:
    root = upstream_root(config)
    async with http_client() as client:
        health = await client.get(f"{root}/api/health")
        if health.status_code != 200:
            return TestResult.fail(f"Grafana health check returned HTTP {health.status_code}")
        version = health.json().get("version", "")
        user = await client.get(f"{root}/api/user", headers=auth_headers(config, secrets))
    if user.status_code in (401, 403):
        if config.get("auth_mode", "proxy") == "token":
            return TestResult.fail("Grafana rejected the service account token")
        return TestResult.fail(
            "Grafana is up but did not accept the sign-in header. "
            "Check that auth proxy is enabled in the Grafana container."
        )
    if user.status_code != 200:
        return TestResult.fail(f"Unexpected response from Grafana: HTTP {user.status_code}")
    login = user.json().get("login", "")
    return TestResult(
        ok=True,
        message="Connected to Grafana",
        details=[
            Detail(label="Version", value=str(version)),
            Detail(label="Signed in as", value=str(login)),
        ],
    )


TYPE = register(
    IntegrationType(
        kind="grafana",
        label="Grafana",
        description="Dashboards embedded in the Monitor pages, served through the panel.",
        status_key="grafana",
        fields=[
            Field(
                key="url",
                label="Address",
                type="url",
                required=True,
                default=DEFAULT_URL,
                help="Grafana as the panel reaches it. The default is the container in this stack.",
            ),
            Field(
                key="auth_mode",
                label="Sign-In Method",
                type="select",
                required=True,
                default="proxy",
                options=[
                    Option(value="proxy", label="Panel signs in for you (auth proxy)"),
                    Option(value="token", label="Service account token"),
                ],
                help="The stack's Grafana is set up for the panel to sign in for you.",
            ),
            Field(
                key="proxy_user",
                label="Grafana User",
                type="text",
                default="admin",
                help="Used with the auth proxy method.",
            ),
            Field(
                key="token",
                label="Service Account Token",
                type="secret",
                help="Used with the service account token method.",
            ),
        ],
        test=test,
    )
)
