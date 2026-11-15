type IconName =
  | "phone" | "shield" | "inbox" | "radar" | "sliders" | "chart" | "play" | "sun" | "moon"
  | "logo" | "check" | "x" | "alert" | "info" | "chevron-right" | "chevron-left" | "search"
  | "arrow-right" | "banknote" | "flag" | "user" | "clock" | "file" | "spark" | "circle-check"
  | "menu" | "download" | "external" | "mobile" | "signal" | "wifi" | "battery";

const PATHS: Record<IconName, JSX.Element> = {
  logo: <path d="M12 2 4 7v6c0 5 3.4 8.6 8 10 4.6-1.4 8-5 8-10V7l-8-5Z" />,
  phone: <path d="M8 3h8a1 1 0 0 1 1 1v16a1 1 0 0 1-1 1H8a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1Z" />,
  shield: <path d="M12 3 5 6v5c0 4.5 2.9 8.4 7 10 4.1-1.6 7-5.5 7-10V6l-7-3Z" />,
  inbox: <path d="M4 13v5a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-5M4 13l2.7-7.2A2 2 0 0 1 8.6 4h6.8a2 2 0 0 1 1.9 1.8L20 13M4 13h5l1.5 2h3L15 13h5" />,
  radar: <><circle cx="12" cy="12" r="2" /><path d="M12 12 18 6" /><path d="M12 5a7 7 0 0 1 7 7M12 2a10 10 0 0 1 10 10" /></>,
  sliders: <path d="M4 7h10M18 7h2M4 12h4M12 12h8M4 17h13M20 17h0" />,
  chart: <path d="M4 20V4M4 20h16M9 16v-5M13 16V8M17 16v-8" />,
  play: <path d="M8 5.5v13l11-6.5-11-6.5Z" />,
  sun: <><circle cx="12" cy="12" r="4" /><path d="M12 2v2m0 16v2M4.9 4.9l1.4 1.4m11.3 11.3 1.4 1.4M2 12h2m16 0h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" /></>,
  moon: <path d="M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5Z" />,
  check: <path d="M5 12.5l4.5 4.5L19 7.5" />,
  x: <path d="M6 6l12 12M18 6 6 18" />,
  alert: <path d="M12 4 3 20h18L12 4Zm0 6v5m0 3h.01" />,
  info: <><circle cx="12" cy="12" r="9" /><path d="M12 11v5m0-8h.01" /></>,
  "chevron-right": <path d="M9 6l6 6-6 6" />,
  "chevron-left": <path d="M15 6l-6 6 6 6" />,
  search: <><circle cx="11" cy="11" r="7" /><path d="m20 20-3.2-3.2" /></>,
  "arrow-right": <path d="M4 12h15M13 6l6 6-6 6" />,
  banknote: <><rect x="2.5" y="7" width="19" height="10" rx="2" /><circle cx="12" cy="12" r="2.5" /><path d="M6.5 10h.01M17.5 14h.01" /></>,
  flag: <path d="M6 21V4m0 1h11l-2.5 4L17 13H6" />,
  user: <><circle cx="12" cy="8" r="4" /><path d="M4 21c1.5-4 4.5-6 8-6s6.5 2 8 6" /></>,
  clock: <><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3.5 2" /></>,
  file: <path d="M7 3h7l5 5v13a1 1 0 0 1-1 1H7a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1Zm7 0v5h5M10 13h5m-5 4h5" />,
  spark: <path d="M12 2l2.1 5.6L20 9.5l-5.9 1.9L12 17l-2.1-5.6L4 9.5l5.9-1.9L12 2Z" />,
  "circle-check": <><circle cx="12" cy="12" r="9" /><path d="M8.5 12.5 11.5 15.5 15.5 9.5" /></>,
  menu: <path d="M4 7h16M4 12h16M4 17h16" />,
  download: <path d="M12 3v12m0 0 4-4m-4 4-4-4M4 21h16" />,
  external: <path d="M9 5h10v10M19 5 9 15M5 9v10a1 1 0 0 0 1 1h10" />,
  mobile: <><rect x="7" y="2" width="10" height="20" rx="2" /><path d="M11 18h2" /></>,
  signal: <path d="M5 17h3v3H5zM10 13h3v7h-3zM15 9h3v11h-3z" />,
  wifi: <path d="M2.5 10a15 15 0 0 1 19 0M6 13.5a10 10 0 0 1 12 0M9.5 17a5 5 0 0 1 5 0M12 20h.01" />,
  battery: <><rect x="3" y="8" width="16" height="8" rx="1.5" /><path d="M21 11v2M6.5 11v2M10 11v2M13.5 11v2" /></>,
};

export function Icon({ name, className = "w-5 h-5", strokeWidth = 1.7 }: { name: IconName; className?: string; strokeWidth?: number }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={strokeWidth}
         strokeLinecap="round" strokeLinejoin="round" className={className} aria-hidden="true">
      {PATHS[name]}
    </svg>
  );
}
