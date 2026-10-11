import { NavLink, useNavigate } from "react-router-dom";
import { api } from "../api";
import { useSession } from "../session";
import { useStatus } from "../status";
import { CONFIGURE_NAV, MONITOR_NAV, type NavItem } from "../nav";

export function CloudIcon({ size = 28 }: { size?: number }) {
  return (
    <svg aria-hidden="true" width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="var(--accent)" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M7 18a4 4 0 0 1-.5-7.97A6 6 0 0 1 18 9a4.5 4.5 0 0 1-1 8.9H7z" />
    </svg>
  );
}

function Section({ title, items, onNavigate }: { title: string; items: NavItem[]; onNavigate: () => void }) {
  return (
    <div className="nav-section">
      <span className="nav-heading">{title}</span>
      {items.map((i) => (
        <NavLink key={i.to} to={i.to} className="nav-link" onClick={onNavigate}>
          {i.label}
        </NavLink>
      ))}
    </div>
  );
}

function Reachability() {
  const { services } = useStatus();
  return (
    <ul className="reach" aria-label="Service reachability">
      {(services ?? []).map((s) => (
        <li key={s.key} title={s.message ?? (s.state === "ok" ? "Reachable" : s.state === "unconfigured" ? "Not configured" : s.state === "unknown" ? "Checking" : "Unreachable")}>
          <span className={`dot dot-${s.state}`} aria-hidden="true" />
          <span>{s.label}</span>
          <span className="visually-hidden">: {s.state}</span>
        </li>
      ))}
    </ul>
  );
}

export function Sidebar({ open, onNavigate }: { open: boolean; onNavigate: () => void }) {
  const { refresh } = useSession();
  const navigate = useNavigate();
  const signOut = async () => {
    try {
      await api.logout();
    } finally {
      await refresh();
      navigate("/login");
    }
  };
  return (
    <nav id="sidebar" aria-label="Main" className={`sidebar${open ? " open" : ""}`}>
      <div className="brand">
        <CloudIcon />
        <span>Clear Cloud Farm</span>
      </div>
      <Section title="Monitor" items={MONITOR_NAV} onNavigate={onNavigate} />
      <Section title="Configure" items={CONFIGURE_NAV} onNavigate={onNavigate} />
      <div className="sidebar-footer">
        <Reachability />
        <button type="button" className="btn" onClick={signOut}>
          Sign Out
        </button>
      </div>
    </nav>
  );
}
