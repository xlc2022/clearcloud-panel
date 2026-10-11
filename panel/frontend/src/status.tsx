import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { api } from "./api";
import type { ServiceStatus } from "./types";

interface Ctx {
  services: ServiceStatus[] | null;
}
const StatusCtx = createContext<Ctx>({ services: null });

/** Polls /api/status every 30 seconds. */
export function StatusProvider({ children }: { children: ReactNode }) {
  const [services, setServices] = useState<ServiceStatus[] | null>(null);
  useEffect(() => {
    let alive = true;
    const load = () =>
      api
        .status()
        .then((r) => alive && setServices(r.services))
        .catch(() => {});
    void load();
    const t = window.setInterval(load, 30_000);
    return () => {
      alive = false;
      window.clearInterval(t);
    };
  }, []);
  return <StatusCtx.Provider value={{ services }}>{children}</StatusCtx.Provider>;
}

export const useStatus = () => useContext(StatusCtx);
