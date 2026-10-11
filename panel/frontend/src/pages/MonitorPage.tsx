import { Link } from "react-router-dom";
import { GrafanaPanel } from "../components/GrafanaPanel";
import { TimeRangePicker } from "../components/TimeRangePicker";
import { MONITOR_PAGES } from "../monitorPages";
import { useStatus } from "../status";

export function MonitorPage({ pageKey }: { pageKey: string }) {
  const cfg = MONITOR_PAGES[pageKey];
  const { services } = useStatus();
  const grafana = services?.find((s) => s.key === "grafana");
  const unconfigured = grafana?.state === "unconfigured";
  return (
    <>
      <div className="page-head">
        <h1>{cfg.title}</h1>
        <div className="page-actions">
          <TimeRangePicker />
          <a className="btn" href="/grafana/" target="_blank" rel="noreferrer">
            Open in Grafana
          </a>
        </div>
      </div>
      {cfg.panels.length === 0 ? (
        <div className="card empty">
          {unconfigured ? (
            <p>
              Grafana is not connected yet. <Link to="/settings/integrations">Set it up on the Integrations page.</Link>
            </p>
          ) : (
            <p>No dashboards yet. They arrive with the Grafana dashboards step.</p>
          )}
        </div>
      ) : (
        <div className="panel-grid">
          {cfg.panels.map((p) => (
            <div key={`${p.uid}-${p.panelId}`} className={p.span === 2 ? "span-2" : undefined}>
              <GrafanaPanel {...p} />
            </div>
          ))}
        </div>
      )}
    </>
  );
}
