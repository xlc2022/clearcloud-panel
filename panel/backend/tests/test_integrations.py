import httpx
import respx

HA = {
    "kind": "home_assistant",
    "config": {"url": "http://ha.test:8123/"},
    "secrets": {"token": "ha-token-123"},
}


def test_types_are_listed(signed_in):
    kinds = {t["kind"]: t for t in signed_in.get("/api/integration-types").json()}
    assert {"home_assistant", "grafana", "mqtt", "proxmox", "truenas", "omada"} <= set(kinds)
    grafana = {f["key"]: f for f in kinds["grafana"]["fields"]}
    assert grafana["url"]["default"] == "http://grafana:3000"


def test_mqtt_is_seeded_with_stack_defaults(signed_in):
    [mqtt] = [i for i in signed_in.get("/api/integrations").json() if i["kind"] == "mqtt"]
    assert mqtt["config"]["host"] == "mosquitto"
    assert mqtt["config"]["port"] == 1883


def test_secrets_never_leave_the_server(signed_in, app):
    created = signed_in.post("/api/integrations", json=HA)
    assert created.status_code == 201
    body = created.json()
    assert body["name"] == "Home Assistant"
    assert body["secrets_set"] == {"token": True}
    assert "ha-token-123" not in created.text
    assert "ha-token-123" not in signed_in.get("/api/integrations").text

    raw = app.state.store.db.execute("SELECT config, secrets FROM integrations").fetchall()
    assert all(b"ha-token-123" not in bytes(r["secrets"] or b"") for r in raw)
    assert all("ha-token-123" not in r["config"] for r in raw)


def test_blank_secret_keeps_stored_value(signed_in, app):
    integration_id = signed_in.post("/api/integrations", json=HA).json()["id"]
    updated = signed_in.put(
        f"/api/integrations/{integration_id}",
        json={"config": {"url": "http://ha2.test:8123"}, "secrets": {"token": ""}},
    )
    assert updated.status_code == 200
    assert updated.json()["config"]["url"] == "http://ha2.test:8123"
    _, _, secrets = app.state.store.resolved(integration_id)
    assert secrets == {"token": "ha-token-123"}


def test_single_instance_kinds_conflict(signed_in):
    assert signed_in.post("/api/integrations", json=HA).status_code == 201
    assert signed_in.post("/api/integrations", json=HA).status_code == 409


def test_required_fields_are_enforced(signed_in):
    response = signed_in.post(
        "/api/integrations", json={"kind": "home_assistant", "config": {"url": "http://x"}}
    )
    assert response.status_code == 422
    assert "Long-Lived Access Token" in response.json()["detail"]


def test_unknown_config_keys_are_dropped(signed_in):
    body = {**HA, "config": {**HA["config"], "evil": 1, "token": "plaintext"}}
    created = signed_in.post("/api/integrations", json=body).json()
    assert "evil" not in created["config"] and "token" not in created["config"]


def test_delete(signed_in):
    integration_id = signed_in.post("/api/integrations", json=HA).json()["id"]
    assert signed_in.delete(f"/api/integrations/{integration_id}").status_code == 204
    assert signed_in.delete(f"/api/integrations/{integration_id}").status_code == 404


@respx.mock(assert_all_mocked=False)
def test_home_assistant_test_button(signed_in, respx_mock):
    route = respx_mock.get("http://ha.test:8123/api/config").mock(
        return_value=httpx.Response(
            200, json={"location_name": "Clear Cloud Farm", "version": "2026.10.1"}
        )
    )
    result = signed_in.post("/api/integrations/test", json=HA).json()
    assert result["ok"] is True
    assert {"label": "Location", "value": "Clear Cloud Farm"} in result["details"]
    assert route.calls.last.request.headers["authorization"] == "Bearer ha-token-123"


@respx.mock(assert_all_mocked=False)
def test_unsaved_test_falls_back_to_stored_secret(signed_in, respx_mock):
    integration_id = signed_in.post("/api/integrations", json=HA).json()["id"]
    route = respx_mock.get("http://ha.test:8123/api/config").mock(return_value=httpx.Response(401))
    result = signed_in.post(
        "/api/integrations/test",
        json={**HA, "secrets": {"token": ""}, "id": integration_id},
    ).json()
    assert result == {
        "ok": False,
        "message": "Home Assistant rejected the access token",
        "details": [],
    }
    assert route.calls.last.request.headers["authorization"] == "Bearer ha-token-123"


@respx.mock(assert_all_mocked=False)
def test_saved_test_records_result_and_status(signed_in, respx_mock):
    integration_id = signed_in.post("/api/integrations", json=HA).json()["id"]
    respx_mock.get("http://ha.test:8123/api/config").mock(return_value=httpx.Response(200, json={}))
    assert signed_in.post(f"/api/integrations/{integration_id}/test").json()["ok"] is True
    stored = signed_in.get("/api/integrations").json()
    [ha] = [i for i in stored if i["id"] == integration_id]
    assert ha["last_test"]["ok"] is True and ha["last_test"]["at"]
    services = {s["key"]: s for s in signed_in.get("/api/status").json()["services"]}
    assert services["home_assistant"]["state"] == "ok"
    assert services["grafana"]["state"] == "unconfigured"
    assert services["tailscale"]["state"] == "unconfigured"


def test_unreachable_host_is_a_failed_result(signed_in):
    body = {**HA, "config": {"url": "http://127.0.0.1:9"}}
    result = signed_in.post("/api/integrations/test", json=body).json()
    assert result["ok"] is False
    assert result["message"].startswith("Could not connect")


@respx.mock(assert_all_mocked=False)
def test_grafana_test_uses_sub_path_and_proxy_header(signed_in, respx_mock):
    respx_mock.get("http://grafana:3000/grafana/api/health").mock(
        return_value=httpx.Response(200, json={"version": "12.2.0"})
    )
    user = respx_mock.get("http://grafana:3000/grafana/api/user").mock(
        return_value=httpx.Response(200, json={"login": "admin"})
    )
    result = signed_in.post("/api/integrations/test", json={"kind": "grafana"}).json()
    assert result["ok"] is True, result
    assert user.calls.last.request.headers["x-webauth-user"] == "admin"


@respx.mock(assert_all_mocked=False)
def test_proxmox_token_header(signed_in, respx_mock):
    version = respx_mock.get("https://pve.test:8006/api2/json/version").mock(
        return_value=httpx.Response(200, json={"data": {"version": "9.0.3"}})
    )
    respx_mock.get("https://pve.test:8006/api2/json/nodes").mock(
        return_value=httpx.Response(200, json={"data": [{"node": "pve"}]})
    )
    result = signed_in.post(
        "/api/integrations/test",
        json={
            "kind": "proxmox",
            "config": {"url": "https://pve.test:8006", "token_id": "monitor@pve!panel"},
            "secrets": {"token_secret": "uuid"},
        },
    ).json()
    assert result["ok"] is True
    assert version.calls.last.request.headers["authorization"] == (
        "PVEAPIToken=monitor@pve!panel=uuid"
    )
