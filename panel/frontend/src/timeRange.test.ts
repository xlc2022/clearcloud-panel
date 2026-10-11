import { describe, expect, it } from "vitest";
import { grafanaPanelUrl, parseRange } from "./timeRange";

describe("time range helpers", () => {
  it("falls back to 24h for unknown values", () => {
    expect(parseRange("bogus")).toBe("24h");
    expect(parseRange(null)).toBe("24h");
    expect(parseRange("7d")).toBe("7d");
  });
  it("builds a d-solo url", () => {
    const u = grafanaPanelUrl({ uid: "abc", slug: "water", panelId: 3 }, "6h");
    expect(u).toBe("/grafana/d-solo/abc/water?orgId=1&panelId=3&from=now-6h&to=now&theme=dark");
  });
});
