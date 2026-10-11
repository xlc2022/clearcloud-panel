import { useTimeRange } from "../TimeRangeContext";
import { TIME_RANGES, parseRange } from "../timeRange";

export function TimeRangePicker() {
  const { range, setRange } = useTimeRange();
  return (
    <label className="range-picker">
      <span className="visually-hidden">Time range</span>
      <select value={range} onChange={(e) => setRange(parseRange(e.target.value))}>
        {TIME_RANGES.map((r) => (
          <option key={r.value} value={r.value}>
            {r.label}
          </option>
        ))}
      </select>
    </label>
  );
}
