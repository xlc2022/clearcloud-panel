# Clear Cloud Farm panel

Monitoring, dashboards, and automation for a 26 acre farm in Bloomington, IN.
This repo is the infrastructure-as-code home: Docker Compose stack, exporter
configs, provisioned Grafana dashboards, and Home Assistant config exports.

## Working conventions

- The main Claude thread is reserved for overarching design and architecture.
- Specific features are delegated to subagents on cheaper models. Default to
  Sonnet for well-scoped implementation and config work, Opus for work that
  needs judgment across several files or an unfamiliar API.
- Subagent briefs state the goal, the files in play, what is already decided
  (see below), and what is out of scope. Decisions are not made in subagents;
  they report back and the main thread decides.

## Architecture decisions (so far)

- Home Assistant OS runs as a VM on the existing Proxmox host. It owns device
  integrations and automation logic.
- A separate Debian VM or LXC runs Docker Compose with four services: the
  panel, VictoriaMetrics (time series), Grafana (dashboards), and Mosquitto
  (MQTT). Addresses between them are fixed container names. Grafana
  dashboards and its VictoriaMetrics datasource are provisioned from this
  repo. Grafana reads from VictoriaMetrics only.
- Everything the user would configure is configured in the panel's GUI.
  No address or credential lives in a file, flag, or environment variable
  a person has to edit. The only exceptions are the panel's own listen port
  and the Docker VM's IP. Home Assistant's own integrations are configured
  in Home Assistant's GUI, which satisfies the rule.
- Consequence: the panel backend runs the collectors. No standalone
  exporters. It streams Home Assistant entity state over the websocket API
  into VictoriaMetrics, polls the Omada, Proxmox, and TrueNAS APIs, polls
  the Pharos bridges over SNMP, and subscribes to Mosquitto for Blue Iris
  events. Targets and credentials come from the Integrations page, stored
  encrypted in the panel's SQLite database with a key generated on first
  run.
- First run shows a setup wizard: admin password, Home Assistant
  connection, Grafana connection. Every integration has a Test button.
- The panel reverse-proxies Grafana so embedded panels are same-origin and
  there is one login.
- Backend is Python (FastAPI) serving a built static frontend. Frontend
  framework is a subagent-level choice.

## Device inventory and integration paths

| Device | Path |
|---|---|
| YoLink FlowSmart All-in-One (YS5008) on YoLink Hub YS1603 | Native HA YoLink integration, cloud push. Needs outbound TCP 8003. Local Hub (YS1606) is an optional later upgrade. |
| Morton M45C026 softener, iQua 2 app | Community HA iQua integration (EcoWater cloud). Slow polling; API has a daily call limit and lockout risk. iQua 2 login unverified. |
| Blue Iris (VM on Proxmox) | Native MQTT publishing to Mosquitto. |
| Omada controller (VM on Proxmox) | Native HA integration plus Prometheus omada exporter. |
| TP-Link Pharos bridges | SNMP via snmp_exporter. |
| Proxmox, TrueNAS (virtualized) | Prometheus exporters. |

## First milestone

Home Assistant VM up with the YoLink and iQua integrations. Confirming the
iQua 2 login works is the one open unknown.

## UX decisions

- Two surfaces: a glance board on a photo-frame sized display, and a
  comprehensive view for phones and computers.
- Glance board is a Home Assistant dashboard in kiosk mode, not Grafana.
  Preferred hardware is an existing iPad locked with Guided Access; an
  Amazon Fire tablet with Fully Kiosk Browser or a Nest Hub via Home
  Assistant Cast are alternatives. One home page with an
  alert takeover, touch to drill in, auto-return to home after a minute.
  Seasonal profiles are separate dashboard views. Anyone in the household
  can edit it through the Home Assistant UI editor.
- Comprehensive view splits into looking and acting. Grafana holds the deep
  dashboards (overview, water, network, security, weather and fields,
  infrastructure) and is used from computers and iPads. Grafana is not
  replaced by Home Assistant; it is the comprehensive web view. The Home Assistant
  companion app is the phone surface: push alerts with actions, controls
  such as the well valve and softener regeneration, and the same dashboards.
- Grafana panels may be embedded in Home Assistant pages where history is
  wanted on the glance board.
- The comprehensive view is a custom web app, the "panel", with its own
  sidebar. It embeds Grafana panels by URL and adds configuration screens
  that Grafana cannot host. Wireframe (approved as a starting point):
  https://claude.ai/artifact/BZ6E4Xq8eszJCYZLKTBtAn
  - Sidebar sections: Monitor (Overview, Water, Weather and Fields,
    Security, Network, Infrastructure, Events) and Configure (Thresholds
    and Alerts, Devices, Glance Board, Notifications, Integrations).
    Footer shows reachability of Home Assistant, Grafana, MQTT, Tailscale.
  - The global time range picker drives embedded Grafana charts. Summary
    tiles may carry their own Today / 7 days / 30 days toggle.
  - Thresholds are Home Assistant helpers. The settings screens are forms
    over those helpers, so automations read changes live and the glance
    board and phone app see the same values. No separate config store
    for thresholds.
  - The Devices settings page is the one registry mapping MAC or IP to a
    friendly name, location, and category. Every other page uses it. The
    network has 30+ devices, so lists need search, filters, and show-more.
  - Brand name in the UI is "Clear Cloud Farm". Page and panel titles use
    Title Case. Dark theme, amber accent, blue reserved for water.
  - The app is one container next to Grafana on the Docker VM. Its
    backend hosts the collectors, the settings API, and Grafana proxying.
- Access is local network plus Tailscale. Tailscale add-on on Home Assistant,
  Tailscale on the Docker VM advertising the farm LAN as a subnet route, and
  Tailscale HTTPS certificates for clean URLs. No ports opened on the WAN.
