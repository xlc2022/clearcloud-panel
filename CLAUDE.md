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
- A separate Debian VM or LXC runs Docker Compose with Mosquitto (MQTT),
  VictoriaMetrics (time series), Grafana (dashboards), and Prometheus-style
  exporters. Grafana dashboards are provisioned from JSON in this repo.
- Home Assistant writes sensor history to VictoriaMetrics; Grafana reads from
  VictoriaMetrics only.

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
- A custom web panel is held in reserve and only built if the Home Assistant
  kiosk falls short in practice.
- Access is local network plus Tailscale. Tailscale add-on on Home Assistant,
  Tailscale on the Docker VM advertising the farm LAN as a subnet route, and
  Tailscale HTTPS certificates for clean URLs. No ports opened on the WAN.
