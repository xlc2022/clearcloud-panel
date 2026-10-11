export interface PanelSpec {
  uid: string;
  slug: string;
  panelId: number;
  title: string;
  height?: number;
  /** Grid columns out of 2; default 1. Use 2 for a full-width panel. */
  span?: 1 | 2;
}

export interface MonitorPageConfig {
  title: string;
  panels: PanelSpec[];
}

/**
 * Adding a panel later is a one-line change: push an entry into the page's
 * `panels` array, e.g.
 *   { uid: "water", slug: "water", panelId: 2, title: "Well Flow" }
 */
export const MONITOR_PAGES: Record<string, MonitorPageConfig> = {
  overview: { title: "Overview", panels: [] },
  water: { title: "Water", panels: [] },
  weather: { title: "Weather and Fields", panels: [] },
  security: { title: "Security", panels: [] },
  network: { title: "Network", panels: [] },
  infrastructure: { title: "Infrastructure", panels: [] },
  events: { title: "Events", panels: [] },
};
