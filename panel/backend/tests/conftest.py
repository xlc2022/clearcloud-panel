import pytest
from fastapi.testclient import TestClient

from clearcloud_panel.config import Settings
from clearcloud_panel.main import create_app

PASSWORD = "correct horse battery"


@pytest.fixture
def settings(tmp_path):
    return Settings(data_dir=tmp_path / "data", static_dir=tmp_path / "static", port=8080)


@pytest.fixture
def app(settings):
    return create_app(settings, background=False)


@pytest.fixture
def client(app):
    with TestClient(app) as c:
        yield c


@pytest.fixture
def signed_in(client):
    assert client.post("/api/setup/admin", json={"password": PASSWORD}).status_code == 204
    return client
