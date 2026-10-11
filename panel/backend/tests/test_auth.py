from clearcloud_panel.auth import hash_password, verify_password

from .conftest import PASSWORD


def test_password_hash_verifies():
    stored = hash_password("abcdefghijk")
    assert verify_password("abcdefghijk", stored)
    assert not verify_password("abcdefghijx", stored)
    assert not verify_password("abcdefghijk", "garbage")


def test_first_run_flow(client):
    state = client.get("/api/setup/state").json()
    assert state == {"admin_created": False, "setup_complete": False, "authenticated": False}

    assert client.post("/api/setup/admin", json={"password": "short"}).status_code == 422
    assert client.post("/api/setup/admin", json={"password": PASSWORD}).status_code == 204
    assert client.get("/api/setup/state").json()["authenticated"] is True
    assert client.post("/api/setup/admin", json={"password": PASSWORD}).status_code == 409

    assert client.post("/api/setup/complete").status_code == 204
    assert client.get("/api/setup/state").json()["setup_complete"] is True


def test_login_and_logout(signed_in):
    client = signed_in
    assert client.post("/api/auth/logout").status_code == 204
    assert client.get("/api/integrations").status_code == 401
    assert client.post("/api/auth/login", json={"password": "wrong password"}).status_code == 401
    assert client.post("/api/auth/login", json={"password": PASSWORD}).status_code == 204
    assert client.get("/api/integrations").status_code == 200


def test_session_cookie_flags(client):
    response = client.post("/api/setup/admin", json={"password": PASSWORD})
    cookie = response.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=lax" in cookie


def test_api_requires_sign_in(client):
    for method, path in [
        ("get", "/api/integrations"),
        ("get", "/api/integration-types"),
        ("get", "/api/status"),
        ("post", "/api/setup/complete"),
    ]:
        assert getattr(client, method)(path).status_code == 401, path
    assert client.get("/api/nope").status_code == 404
