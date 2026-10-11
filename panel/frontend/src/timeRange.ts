export const TIME_RANGES = [
  { value: "1h", label: "Last 1 hour" },
  { value: "6h", label: "Last 6 hours" },
  { value: "24h", label: "Last 24 hours" },
  { value: "7d", label: "Last 7 days" },
  { value: "30d", label: "Last 30 days" },
] as const;

export type RangeValue = (typeof TIME_RANGES)[number]["value"];
export const DEFAULT_RANGE: RangeValue = "24h";

export function parseRange(v: string | null | undefined): RangeValue {
  return TIME_RANGES.some((r) => r.value === v) ? (v as RangeValue) : DEFAULT_RANGE;
}

export function rangeLabel(v: RangeValue): string {
  return TIME_RANGES.find((r) => r.value === v)!.label;
}

export function grafanaPanelUrl(p: { uid: string; slug: string; panelId: number }, range: RangeValue): string {
  const q = new URLSearchParams({
    orgId: "1",
    panelId: String(p.panelId),
    from: `now-${range}`,
    to: "now",
    theme: "dark",
  });
  return `/grafana/d-solo/${encodeURIComponent(p.uid)}/${encodeURIComponent(p.slug)}?${q.toString()}`;
}
