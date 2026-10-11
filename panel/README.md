# Clear Cloud Farm Panel

The panel is the one place an address or a credential is typed. It serves
the web app, stores integration settings in SQLite with secrets encrypted by
a key it generates on first run, runs the Test buttons, and reverse-proxies
Grafana at `/grafana/` so embedded panels are same-origin behind one login.

```
panel/
  backend/    FastAPI app (clearcloud_panel), tests
  frontend/   React + TypeScript + Vite app, built into the image
  Dockerfile  one image: built frontend served by the backend
```

## Run Locally

```sh
# backend, on :8080
cd panel/backend
python3 -m venv .venv && .venv/bin/pip install -e '.[dev]'
.venv/bin/uvicorn clearcloud_panel.main:app --reload --port 8080

# frontend, on :5173, proxying /api and /grafana to :8080
cd panel/frontend
npm ci && npm run dev
```

Open http://localhost:5173 and the setup wizard asks for the admin password,
then Home Assistant and Grafana. State lives in `panel/backend/data/`
(delete it to start over).

To serve the built frontend from the backend instead, run `npm run build`
and start uvicorn with `PANEL_STATIC_DIR=../frontend/dist`.

## Container

```sh
docker build -t clearcloud-panel panel
docker run -p 8080:8080 -v panel-data:/data clearcloud-panel
```

The only environment variables are internal: `PANEL_PORT` (listen port,
default 8080), `PANEL_DATA_DIR` (`/data` in the image), and
`PANEL_STATIC_DIR`. Nothing a person configures goes in them.

## Grafana

The panel proxies `/grafana/*` to the Grafana integration's address with
`/grafana` appended, and signs in for the user with Grafana's auth proxy
header (or a service account token, if chosen on the Integrations page).
The Grafana container needs:

```
GF_SERVER_ROOT_URL=%(protocol)s://%(domain)s/grafana/
GF_SERVER_SERVE_FROM_SUB_PATH=true
GF_AUTH_PROXY_ENABLED=true
GF_AUTH_PROXY_HEADER_NAME=X-WEBAUTH-USER
GF_AUTH_PROXY_HEADER_PROPERTY=username
GF_AUTH_PROXY_AUTO_SIGN_UP=true
GF_SECURITY_ALLOW_EMBEDDING=true
```

Grafana's port must not be published outside the Compose network, since the
auth proxy header is trusted from anyone who can reach it.

## Adding an Integration Type

Each type is a module in `backend/clearcloud_panel/integrations/` that
registers an `IntegrationType`: the fields the GUI renders (`text`, `url`,
`secret`, `number`, `bool`, `select`) and an async `test(config, secrets)`
returning a `TestResult`. Import it in `integrations/__init__.py` and the
Integrations page picks it up. Secret fields are encrypted at rest and
never returned by the API. Collectors will read their settings through
`Store.resolved(id)`.

Embedding a Grafana panel on a Monitor page is one line in
`frontend/src/monitorPages.ts`.
