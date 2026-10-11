import { useTimeRange } from "../TimeRangeContext";
import { grafanaPanelUrl } from "../timeRange";

interface Props {
  uid: string;
  slug: string;
  panelId: number;
  title: string;
  height?: number;
}

export function GrafanaPanel({ uid, slug, panelId, title, height = 260 }: Props) {
  const { range } = useTimeRange();
  return (
    <section className="card panel-card" aria-label={title}>
      <h2 className="card-title">{title}</h2>
      <iframe
        title={title}
        src={grafanaPanelUrl({ uid, slug, panelId }, range)}
        loading="lazy"
        style={{ border: 0, width: "100%", height }}
      />
    </section>
  );
}
