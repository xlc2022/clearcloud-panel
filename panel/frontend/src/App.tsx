import type { ReactNode } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { Shell } from "./components/Shell";
import { Integrations } from "./pages/Integrations";
import { Login } from "./pages/Login";
import { MonitorPage } from "./pages/MonitorPage";
import { Placeholder } from "./pages/Placeholder";
import { Setup } from "./pages/Setup";
import { SessionProvider, useSession } from "./session";

const PLACEHOLDERS: { path: string; title: string; description: string }[] = [
  { path: "thresholds", title: "Thresholds and Alerts", description: "Forms over Home Assistant helpers. Automations read the changes live, and the glance board and phone app see the same values." },
  { path: "devices", title: "Devices", description: "The one registry that maps a MAC or IP address to a friendly name, location, and category. Every other page uses it." },
  { path: "glance-board", title: "Glance Board", description: "Settings for the photo-frame display: seasonal profiles and what shows on the home page." },
  { path: "notifications", title: "Notifications", description: "Who gets push alerts, and which alerts reach which phones." },
];

function Gate({ need, children }: { need: "app" | "login" | "setup"; children: ReactNode }) {
  const { state, error, refresh } = useSession();
  if (!state) {
    return error ? (
      <div className="center-screen">
        <div className="card auth-card">
          <p role="alert" className="msg-error">{error}</p>
          <button type="button" className="btn" onClick={() => void refresh()}>Retry</button>
        </div>
      </div>
    ) : (
      <div className="center-screen"><p className="muted">Loading...</p></div>
    );
  }
  const setupDone = state.admin_created && state.setup_complete;
  if (need === "setup") return setupDone ? <Navigate to="/overview" replace /> : <>{children}</>;
  if (!setupDone) return <Navigate to="/setup" replace />;
  if (need === "login") return state.authenticated ? <Navigate to="/overview" replace /> : <>{children}</>;
  return state.authenticated ? <>{children}</> : <Navigate to="/login" replace />;
}

export function App() {
  return (
    <SessionProvider>
      <Routes>
        <Route path="/" element={<Navigate to="/overview" replace />} />
        <Route path="/login" element={<Gate need="login"><Login /></Gate>} />
        <Route path="/setup" element={<Gate need="setup"><Setup /></Gate>} />
        <Route element={<Gate need="app"><Shell /></Gate>}>
          {["overview", "water", "weather", "security", "network", "infrastructure", "events"].map((k) => (
            <Route key={k} path={k} element={<MonitorPage pageKey={k} />} />
          ))}
          {PLACEHOLDERS.map((p) => (
            <Route key={p.path} path={`settings/${p.path}`} element={<Placeholder title={p.title} description={p.description} />} />
          ))}
          <Route path="settings/integrations" element={<Integrations />} />
        </Route>
        <Route path="*" element={<Navigate to="/overview" replace />} />
      </Routes>
    </SessionProvider>
  );
}
