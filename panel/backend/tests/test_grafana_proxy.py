import httpx
import respx

from clearcloud_panel.auth import SESSION_COOKIE


def _add_grafana(client, **config):
    response = client.post("/api/integrations", json={"kind": "grafana", "config": config})
    assert response.status_code == 201, response.text


def test_proxy_requires_sign_in(client):
    assert client.get("/grafana/api/health").status_code == 401


def test_proxy_unconfigured(signed_in):
    assert signed_in.get("/grafana/").status_code == 503


@respx.mock(assert_all_mocked=False)
def test_proxy_forwards_with_panel_identity(signed_in, respx_mock):
    _add_grafana(signed_in)
    route = respx_mock.get("http://grafana:3000/grafana/d-solo/water/water").mock(
        return_value=httpx.Response(200, text="<html>panel</html>", headers={"x-up": "1"})
    )
    signed_in.cookies.set("grafana_session", "g1")
    response = signed_in.get(
        "/grafana/d-solo/water/water?panelId=2&from=now-24h",
        headers={"X-WEBAUTH-USER": "intruder", "Authorization": "Bearer nope"},
    )
    assert response.status_code == 200
    assert response.text == "<html>panel</html>"
    assert response.headers["x-up"] == "1"
    upstream = route.calls.last.request
    assert upstream.url.params["panelId"] == "2"
    assert upstream.headers["x-webauth-user"] == "admin"
    assert "authorization" not in upstream.headers
    assert "grafana_session=g1" in upstream.headers["cookie"]
    assert SESSION_COOKIE not in upstream.headers["cookie"]


@respx.mock(assert_all_mocked=False)
def test_proxy_rewrites_absolute_redirects(signed_in, respx_mock):
    _add_grafana(signed_in)
    respx_mock.get("http://grafana:3000/grafana/").mock(
        return_value=httpx.Response(302, headers={"location": "http://grafana:3000/grafana/login"})
    )
    response = signed_in.get("/grafana/", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["location"] == "/grafana/login"


@respx.mock(assert_all_mocked=False)
def test_proxy_token_mode(signed_in, respx_mock):
    signed_in.post(
        "/api/integrations",
        json={
            "kind": "grafana",
            "config": {"auth_mode": "token"},
            "secrets": {"token": "glsa_x"},
        },
    )
    route = respx_mock.post("http://grafana:3000/grafana/api/ds/query").mock(
        return_value=httpx.Response(200, json={"results": {}})
    )
    response = signed_in.post("/grafana/api/ds/query", json={"queries": []})
    assert response.json() == {"results": {}}
    upstream = route.calls.last.request
    assert upstream.headers["authorization"] == "Bearer glsa_x"
    assert "x-webauth-user" not in upstream.headers
    assert upstream.content == b'{"queries":[]}'


@respx.mock(assert_all_mocked=False)
def test_proxy_upstream_down(signed_in, respx_mock):
    _add_grafana(signed_in)
    respx_mock.get("http://grafana:3000/grafana/").mock(side_effect=httpx.ConnectError("down"))
    assert signed_in.get("/grafana/").status_code == 502
