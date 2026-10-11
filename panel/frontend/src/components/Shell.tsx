import { useEffect, useState } from "react";
import { Outlet, useLocation } from "react-router-dom";
import { Sidebar, CloudIcon } from "./Sidebar";
import { StatusProvider } from "../status";
import { TimeRangeProvider } from "../TimeRangeContext";

export function Shell() {
  const [open, setOpen] = useState(false);
  const loc = useLocation();
  useEffect(() => setOpen(false), [loc.pathname]);
  return (
    <StatusProvider>
      <TimeRangeProvider>
        <div className="shell">
          <header className="topbar">
            <CloudIcon size={24} />
            <span className="topbar-title">Clear Cloud Farm</span>
            <button type="button" className="btn" aria-expanded={open} aria-controls="sidebar" onClick={() => setOpen((o) => !o)}>
              {open ? "Close" : "Menu"}
            </button>
          </header>
          <Sidebar open={open} onNavigate={() => setOpen(false)} />
          <main className="main">
            <Outlet />
          </main>
        </div>
      </TimeRangeProvider>
    </StatusProvider>
  );
}
