import { useEffect, useState } from "react";
import { api } from "../lib/api";

const GRAFANA  = "http://localhost:3001";
const UID      = "fraud-metrics";
const SLUG     = "fraud-metrics";
const PARAMS   = "orgId=1&theme=light&refresh=5s";

const clientPanels = [8, 9, 10];                 // API‑usage graphs
const healthPanels = [1, 2, 3, 4, 5, 6, 7];      // existing host graphs
const modelPanels  = [11, 13, 14];               // new model metrics graphs

interface Client {
  email: string;
  name: string;
  age?: number;
  gender?: string;
  country?: string;
}

export default function MetricsPage() {
  const [me, setMe] = useState<Client | null>(null);

  useEffect(() => {
    api.get<Client>("/clients/me").then(({ data }) => setMe(data));
  }, []);

  return (
    <div className="space-y-8 p-4">
      {/* -------- Client details + API usage ---------- */}
      <section>
        <h2 className="text-xl font-semibold mb-3">Client metrics</h2>

        {/* Profile card */}
        {me ? (
          <div className="ui-card max-w-md mb-4 space-y-1">
            <h3 className="font-semibold text-brand-blue">Your profile</h3>
            <p><strong>Email:</strong> {me.email}</p>
            <p><strong>Name:</strong> {me.name}</p>
            <p><strong>Age:</strong> {me.age ?? "-"}</p>
            <p><strong>Gender:</strong> {me.gender ?? "-"}</p>
            <p><strong>Country:</strong> {me.country ?? "-"}</p>
          </div>
        ) : (
          <p>Loading profile…</p>
        )}

        {/* API‑usage charts */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {clientPanels.map((id) => (
            <iframe
              key={id}
              src={`${GRAFANA}/d-solo/${UID}/${SLUG}?${PARAMS}&panelId=${id}`}
              className="w-full h-64 border-0"
              title={`Client Panel ${id}`}
              loading="lazy"
            />
          ))}
        </div>
      </section>

      {/* -------- Host / Health metrics -------- */}
      <section>
        <h2 className="text-xl font-semibold mb-2">Health metrics</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {healthPanels.map((id) => (
            <iframe
              key={id}
              src={`${GRAFANA}/d-solo/${UID}/${SLUG}?${PARAMS}&panelId=${id}`}
              className="w-full h-64 border-0"
              title={`Health Panel ${id}`}
              loading="lazy"
            />
          ))}
        </div>
      </section>

      {/* -------- Model metrics -------- */}
      <section>
        <h2 className="text-xl font-semibold mb-2">Model metrics</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {modelPanels.map((id) => (
            <iframe
              key={id}
              src={`${GRAFANA}/d-solo/${UID}/${SLUG}?${PARAMS}&panelId=${id}`}
              className="w-full h-64 border-0"
              title={`Model Panel ${id}`}
              loading="lazy"
            />
          ))}
        </div>
      </section>
    </div>
  );
}
