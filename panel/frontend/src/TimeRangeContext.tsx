import { createContext, useContext, useMemo, type ReactNode } from "react";
import { useSearchParams } from "react-router-dom";
import { parseRange, type RangeValue } from "./timeRange";

interface Ctx {
  range: RangeValue;
  setRange: (r: RangeValue) => void;
}
const TimeRangeCtx = createContext<Ctx>({ range: "24h", setRange: () => {} });

/** Global time range, kept in the URL query (?range=24h) so links are shareable. */
export function TimeRangeProvider({ children }: { children: ReactNode }) {
  const [params, setParams] = useSearchParams();
  const range = parseRange(params.get("range"));
  const value = useMemo<Ctx>(
    () => ({
      range,
      setRange: (r) =>
        setParams(
          (prev) => {
            const n = new URLSearchParams(prev);
            n.set("range", r);
            return n;
          },
          { replace: true },
        ),
    }),
    [range, setParams],
  );
  return <TimeRangeCtx.Provider value={value}>{children}</TimeRangeCtx.Provider>;
}

export const useTimeRange = () => useContext(TimeRangeCtx);
