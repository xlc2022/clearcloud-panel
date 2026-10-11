import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { api, setUnauthorizedHandler } from "./api";
import type { SetupState } from "./types";

interface Ctx {
  state: SetupState | null;
  error: string | null;
  refresh: () => Promise<SetupState | null>;
}
const SessionCtx = createContext<Ctx>({ state: null, error: null, refresh: async () => null });

export function SessionProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<SetupState | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const s = await api.setupState();
      setState(s);
      setError(null);
      return s;
    } catch (e) {
      setError(e instanceof Error ? e.message : "Cannot reach the panel backend.");
      return null;
    }
  }, []);

  useEffect(() => {
    void refresh();
    // Any API 401 marks the session as signed out; route guards redirect to /login.
    setUnauthorizedHandler(() => setState((s) => (s ? { ...s, authenticated: false } : s)));
  }, [refresh]);

  const value = useMemo(() => ({ state, error, refresh }), [state, error, refresh]);
  return <SessionCtx.Provider value={value}>{children}</SessionCtx.Provider>;
}

export const useSession = () => useContext(SessionCtx);
