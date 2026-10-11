from fastapi.testclient import TestClient

from clearcloud_panel.main import create_app


def test_serves_index_for_client_routes(settings):
    (settings.static_dir / "assets").mkdir(parents=True)
    (settings.static_dir / "index.html").write_text("<div id=root></div>")
    (settings.static_dir / "assets" / "app.js").write_text("console.log(1)")
    with TestClient(create_app(settings, background=False)) as client:
        assert client.get("/settings/integrations").text == "<div id=root></div>"
        assert client.get("/assets/app.js").text == "console.log(1)"
        assert client.get("/%2e%2e/%2e%2e/etc/passwd").text == "<div id=root></div>"
        assert client.get("/healthz").json() == {"ok": True}
