# Clear Cloud Farm panel

Monitoring, dashboards, and automation for Clear Cloud Farm. See `CLAUDE.md`
for the architecture.

## Running the stack

On the Docker VM:

```sh
docker compose up -d --build
```

Then open `http://<docker-vm-ip>:8080` and finish the setup wizard. To use a
different port, put `PANEL_PORT=9000` in a `.env` file next to `compose.yaml`.
Nothing else is configured in files.

| Service | Internal address | Published |
|---|---|---|
| panel | `http://panel:8000` | `PANEL_PORT` (8080) |
| victoriametrics | `http://victoriametrics:8428` | no |
| grafana | `http://grafana:3000/grafana/` | no, proxied by the panel |
| mosquitto | `mqtt://mosquitto:1883` | 1883, for Blue Iris |

Data lives in named volumes (`panel-data`, `vm-data`, `grafana-data`,
`mosquitto-data`, `mosquitto-auth`), so `docker compose down` keeps it and
`docker compose down -v` erases it.

Grafana's VictoriaMetrics datasource (uid `victoriametrics`) and the
dashboards in `grafana/dashboards/` are provisioned from this repo.
