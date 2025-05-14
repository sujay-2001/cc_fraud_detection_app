import { Tab } from "@headlessui/react";
import { useNavigate, Outlet, useLocation } from "react-router-dom";

function classNames(...cls: string[]) {
  return cls.filter(Boolean).join(" ");
}

export default function AppShell() {
  const nav = useNavigate();
  const loc = useLocation();

  function handleLogout() {
    if (confirm("Log out?")) {
      localStorage.removeItem("fraud_token");
      nav("/login", { replace: true });
    }
  }
  const tabs = [
    { label: "Predict", href: "predict" },
    { label: "Metrics", href: "metrics" },
    { label: "Explain", href: "explain" },
  ];

  // find current tab index from URL
  const activeIdx = Math.max(
    0,
    tabs.findIndex((t) => loc.pathname.includes(t.href))
  );

  return (
    <Tab.Group selectedIndex={activeIdx} onChange={(i) => nav(`/app/${tabs[i].href}`)} as="div" className="flex flex-col h-full">
      <Tab.List className="flex items-center gap-2 bg-brand-gray-100 p-2">
        {tabs.map((t) => (
          <Tab
            key={t.href}
            className={({ selected }) =>
              classNames(
                "px-4 py-2 rounded focus:outline-none",
                selected ? "bg-brand-blue text-white" : "bg-white"
              )
            }
          >
            {t.label}
          </Tab>
        ))}
        {/* ---- Sign‑out button ---- */}
        <button
          onClick={handleLogout}
          className="ml-auto px-3 py-2 rounded bg-risk-high text-white hover:bg-red-600"
        >
          Sign out
        </button>  
      </Tab.List>

      {/* page content */}
      <div className="flex-1 overflow-auto p-4">
        <Outlet />
      </div>
    </Tab.Group>
  );
}
