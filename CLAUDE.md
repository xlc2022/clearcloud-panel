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
