import { useCallback, useEffect, useState, type ReactNode } from "react";
import { api } from "./api";
import {
  AlertCard,
  CollectorRail,
  ProductRow,
  TrustCard,
} from "./components/DashboardCards";
import type { Alert, CollectorStatus, Incident, Product } from "./types";
import "./styles.css";

type DashboardState = {
  collectors: CollectorStatus[];
  products: Product[];
  alerts: Alert[];
  incidents: Incident[];
};

const emptyState: DashboardState = {
  collectors: [],
  products: [],
  alerts: [],
  incidents: [],
};

function PanelHeading({
  eyebrow,
  title,
  trailing,
}: {
  eyebrow: string;
  title: string;
  trailing: ReactNode;
}) {
  return (
    <div className="panel-heading">
      <div>
        <p className="eyebrow">{eyebrow}</p>
        <h2>{title}</h2>
      </div>
      {trailing}
    </div>
  );
}

function EmptyState({ children, detail }: { children: ReactNode; detail?: string }) {
  return (
    <div className="empty-state">
      <span className="empty-glyph" aria-hidden="true">⌁</span>
      <p>{children}</p>
      {detail && <small>{detail}</small>}
    </div>
  );
}

function App() {
  const [data, setData] = useState<DashboardState>(emptyState);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);

    try {
      const [collectors, products, alerts, incidents] = await Promise.all([
        api.collectors(),
        api.products(),
        api.alerts(),
        api.incidents(),
      ]);

      setData({ collectors, products, alerts, incidents });
      setLastUpdated(new Date());
      setError(null);
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "The API could not be reached",
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const healedCount = data.incidents.filter(
    (incident) => incident.status === "healed",
  ).length;
  const networkLabel = error ? "collector network paused" : "collector network live";

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand">
          <span className="brand-orbit" aria-hidden="true"><i /></span>
          <span>sentinel<span>scrape</span></span>
        </div>
        <div className="topbar-right">
          <span className="live-indicator"><i /> {networkLabel}</span>
          <button className="refresh-button" onClick={() => void refresh()} disabled={loading}>
            {loading ? "syncing…" : "refresh data"} <span>↗</span>
          </button>
        </div>
      </header>

      <main className="dashboard">
        <section className="hero">
          <div>
            <p className="eyebrow">
              LAPTOP MARKET INTELLIGENCE <span>·</span> TRUST LAYER
            </p>
            <h1>Watch the market.<br /><em>See the repair.</em></h1>
            <p className="hero-copy">
              A live view of competitor inventory with every extraction failure,
              recovery, and AI narration left visible.
            </p>
          </div>

          <div className="hero-signal">
            <div className="signal-ring">
              <span>{data.collectors.length || "—"}</span>
              <small>sites<br />watched</small>
            </div>
            <div className="signal-legend">
              <span><i className="dot-lime" /> {data.products.length} listings tracked</span>
              <span><i className="dot-violet" /> {healedCount} incidents healed</span>
            </div>
          </div>
        </section>

        <CollectorRail collectors={data.collectors} />

        {error && (
          <div className="error-banner" role="alert">
            <span>Connection paused</span>
            <p>{error}. Start the FastAPI server to populate live data.</p>
            <button onClick={() => void refresh()}>retry</button>
          </div>
        )}

        <section className="content-grid">
          <section className="panel market-panel">
            <PanelHeading
              eyebrow="01 / MARKET PULSE"
              title="Live listings"
              trailing={<span className="panel-count">{data.products.length} products</span>}
            />
            <div className="table-head">
              <span>product</span>
              <span>current price</span>
              <span>availability</span>
              <span>30d movement</span>
            </div>
            <div className="market-list">
              {loading && data.products.length === 0 ? (
                <div className="empty-state">
                  <span className="loader" />
                  <p>Reading collector snapshots…</p>
                </div>
              ) : data.products.length ? (
                data.products.map((product) => (
                  <ProductRow product={product} key={product.id} />
                ))
              ) : (
                <EmptyState detail="Run the scheduler after registering your collectors.">
                  No successful snapshots yet.
                </EmptyState>
              )}
            </div>
          </section>

          <aside className="side-column">
            <section className="panel alerts-panel">
              <PanelHeading
                eyebrow="02 / SIGNALS"
                title="Alerts"
                trailing={<span className="panel-count accent-count">{data.alerts.length}</span>}
              />
              <div className="alerts-list">
                {data.alerts.length ? (
                  data.alerts.slice(0, 5).map((alert, index) => (
                    <AlertCard
                      alert={alert}
                      key={`${alert.product_id}-${alert.type}-${index}`}
                    />
                  ))
                ) : (
                  <div className="small-empty">Price drops and restocks will appear here.</div>
                )}
              </div>
            </section>

            <section className="panel trust-panel">
              <PanelHeading
                eyebrow="03 / TRUST LAYER"
                title="What changed"
                trailing={<span className="pulse-badge"><i /> live feed</span>}
              />
              <div className="trust-list">
                {data.incidents.length ? (
                  data.incidents.slice(0, 5).map((incident) => (
                    <TrustCard incident={incident} key={incident.id} />
                  ))
                ) : (
                  <div className="small-empty">
                    No collector incidents yet. The feed stays quiet until a field
                    drops below the 20% threshold.
                  </div>
                )}
              </div>
            </section>
          </aside>
        </section>

        <footer className="footer">
          <span><i className="dot-lime" /> self-healing visibility on</span>
          <span>
            {lastUpdated
              ? `last synced ${lastUpdated.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`
              : "waiting for sync"}
          </span>
        </footer>
      </main>
    </div>
  );
}

export default App;
