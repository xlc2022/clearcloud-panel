export interface NavItem {
  to: string;
  label: string;
}

export const MONITOR_NAV: NavItem[] = [
  { to: "/overview", label: "Overview" },
  { to: "/water", label: "Water" },
  { to: "/weather", label: "Weather and Fields" },
  { to: "/security", label: "Security" },
  { to: "/network", label: "Network" },
  { to: "/infrastructure", label: "Infrastructure" },
  { to: "/events", label: "Events" },
];

export const CONFIGURE_NAV: NavItem[] = [
  { to: "/settings/thresholds", label: "Thresholds and Alerts" },
  { to: "/settings/devices", label: "Devices" },
  { to: "/settings/glance-board", label: "Glance Board" },
  { to: "/settings/notifications", label: "Notifications" },
  { to: "/settings/integrations", label: "Integrations" },
];
