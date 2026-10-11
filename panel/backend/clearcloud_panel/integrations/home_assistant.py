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
    headers = {"Authorization": f"Bearer {secrets.get('token', '')}"}
    async with http_client() as client:
        r = await client.get(f"{url}/api/config", headers=headers)
    if r.status_code == 401:
        return TestResult.fail("Home Assistant rejected the access token")
    if r.status_code != 200:
        return TestResult.fail(f"Unexpected response from Home Assistant: HTTP {r.status_code}")
    body = r.json()
    return TestResult(
        ok=True,
        message="Connected to Home Assistant",
        details=[
            Detail(label="Location", value=str(body.get("location_name", ""))),
            Detail(label="Version", value=str(body.get("version", ""))),
            Detail(label="Time zone", value=str(body.get("time_zone", ""))),
        ],
    )


TYPE = register(
    IntegrationType(
        kind="home_assistant",
        label="Home Assistant",
        description="Device integrations, automations, and the helpers that hold thresholds.",
        status_key="home_assistant",
        fields=[
            Field(
                key="url",
                label="Address",
                type="url",
                required=True,
                placeholder="http://homeassistant.local:8123",
                help="The address you use to open Home Assistant on the farm network.",
            ),
            Field(
                key="token",
                label="Long-Lived Access Token",
                type="secret",
                required=True,
                help="In Home Assistant, open your profile, then Security, "
                "then Create Token under Long-Lived Access Tokens.",
            ),
        ],
        test=test,
    )
)
