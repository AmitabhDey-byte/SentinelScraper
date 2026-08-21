import { useCallback, useEffect, useState } from "react";
import { api } from "./api";
import { Sparkline } from "./components/Sparkline";
import type { Alert, CollectorStatus, Incident, Product } from "./types";
import "./styles.css";

const money = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  maximumFractionDigits: 0,
});

function formatPrice(value: number | null) {
  return value === null ? "—" : money.format(value);
}

function relativeTime(value: string) {
  const elapsed = Date.now() - new Date(value).getTime();
  const minutes = Math.max(0, Math.floor(elapsed / 60000));
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

function siteClass(site: string) {
  return `site-tag site-${site.toLowerCase().replace(/[^a-z]+/g, "-")}`;
}

function StockPill({ value }: { value: string | null }) {
  const normalized = value?.toLowerCase() ?? "unknown";
  const unavailable = /out|unavailable|sold/.test(normalized);
  return <span className={`stock-pill ${unavailable ? "stock-out" : value ? "stock-in" : "stock-unknown"}`}><i />{value ?? "No signal"}</span>;
}

function ProductRow({ product }: { product: Product }) {
  return (
    <a className="market-row" href={product.listing_url || "#"} target="_blank" rel="noreferrer">
      <div className="product-cell">
        {product.image_url ? <img src={product.image_url} alt="" loading="lazy" /> : <div className="image-placeholder">▦</div>}
        <div>
          <span className={siteClass(product.site_name)}>{product.site_name}</span>
          <strong>{product.name}</strong>
        </div>
      </div>
      <span className="price-cell">{formatPrice(product.price)}</span>
      <StockPill value={product.stock_status} />
      <Sparkline values={product.price_history.map((point) => point.price)} />
    </a>
  );
}

function AlertCard({ alert }: { alert: Alert }) {
  const isDrop = alert.type === "price_drop";
  return (
    <article className={`alert-card ${isDrop ? "alert-drop" : "alert-restock"}`}>
      <div className="alert-icon">{isDrop ? "↓" : "↗"}</div>
      <div className="alert-copy">
        <div className="alert-topline"><span>{isDrop ? "Price drop" : "Restocked"}</span><time>{relativeTime(alert.observed_at)}</time></div>
        <strong>{alert.product_name}</strong>
        <small>{alert.site_name} · {isDrop ? `${formatPrice(alert.previous_value)} → ${formatPrice(alert.current_value)}` : alert.stock_status}</small>
      </div>
    </article>
  );
}

function TrustCard({ incident }: { incident: Incident }) {
  return (
    <article className="trust-card">
      <div className="trust-card-head">
        <div className="trust-mark">✦</div>
        <div><span className={siteClass(incident.site_name)}>{incident.site_name}</span><time>{relativeTime(incident.detected_at)}</time></div>
        <span className={`status-badge ${incident.status === "healed" ? "status-healed" : "status-open"}`}>{incident.status}</span>
      </div>
      <p>{incident.narration_text ?? "Extraction drift detected. Waiting for an approved Bright Data heal."}</p>
      <div className="trust-meta">
        <span><b>broken</b> {incident.dropped_fields.join(", ") || "—"}</span>
        <span><b>healed</b> {incident.recovered_fields.join(", ") || "pending"}</span>
      </div>
      <div className="trust-footer"><span>{incident.rows_prev} rows → {incident.rows_curr} rows</span><span className={`source-badge source-${incident.narration_source ?? "pending"}`}>{incident.narration_source ?? "awaiting narration"}</span></div>
    </article>
  );
}

function CollectorRail({ collectors }: { collectors: CollectorStatus[] }) {
  if (!collectors.length) {
    return <div className="collector-rail collector-rail-empty"><span className="rail-label">collector health</span><span>Register the five Scraper Studio collectors to start the network.</span></div>;
  }
  return (
    <div className="collector-rail">
      <span className="rail-label">collector health</span>
      <div className="collector-list">
        {collectors.map((collector) => (
          <span className={`collector-chip collector-${collector.status}`} key={collector.collector_id}>
            <i /> {collector.site_name}
            <small>{collector.status === "healthy" ? "green" : collector.status.replace("_", " ")}</small>
          </span>
        ))}
      </div>
    </div>
  );
}

function App() {
  const [collectors, setCollectors] = useState<CollectorStatus[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const [nextCollectors, nextProducts, nextAlerts, nextIncidents] = await Promise.all([api.collectors(), api.products(), api.alerts(), api.incidents()]);
      setCollectors(nextCollectors);
      setProducts(nextProducts);
      setAlerts(nextAlerts);
      setIncidents(nextIncidents);
      setLastUpdated(new Date());
      setError(null);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "The API could not be reached");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void refresh(); }, [refresh]);

  const sites = collectors.length;
  const healed = incidents.filter((incident) => incident.status === "healed").length;

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand"><span className="brand-orbit"><i /></span><span>sentinel<span>scrape</span></span></div>
        <div className="topbar-right"><span className="live-indicator"><i /> collector network live</span><button className="refresh-button" onClick={() => void refresh()} disabled={loading}>{loading ? "syncing…" : "refresh data"} <span>↗</span></button></div>
      </header>

      <main className="dashboard">
        <section className="hero">
          <div><p className="eyebrow">LAPTOP MARKET INTELLIGENCE <span>·</span> TRUST LAYER</p><h1>Watch the market.<br /><em>See the repair.</em></h1><p className="hero-copy">A live view of competitor inventory with every extraction failure, recovery, and AI narration left visible.</p></div>
          <div className="hero-signal"><div className="signal-ring"><span>{sites || "—"}</span><small>sites<br />watched</small></div><div className="signal-legend"><span><i className="dot-lime" /> {products.length || "—"} listings tracked</span><span><i className="dot-violet" /> {healed || "—"} incidents healed</span></div></div>
        </section>

        <CollectorRail collectors={collectors} />

        {error && <div className="error-banner"><span>Connection paused</span><p>{error}. Start the FastAPI server to populate live data.</p><button onClick={() => void refresh()}>retry</button></div>}

        <section className="content-grid">
          <section className="panel market-panel">
            <div className="panel-heading"><div><p className="eyebrow">01 / MARKET PULSE</p><h2>Live listings</h2></div><span className="panel-count">{products.length} products</span></div>
            <div className="table-head"><span>product</span><span>current price</span><span>availability</span><span>30d movement</span></div>
            <div className="market-list">
              {loading && products.length === 0 ? <div className="empty-state"><span className="loader" /><p>Reading collector snapshots…</p></div> : products.length ? products.map((product) => <ProductRow product={product} key={product.id} />) : <div className="empty-state"><span className="empty-glyph">⌁</span><p>No successful snapshots yet.</p><small>Run the scheduler after registering your collectors.</small></div>}
            </div>
          </section>

          <aside className="side-column">
            <section className="panel alerts-panel"><div className="panel-heading"><div><p className="eyebrow">02 / SIGNALS</p><h2>Alerts</h2></div><span className="panel-count accent-count">{alerts.length}</span></div><div className="alerts-list">{alerts.length ? alerts.slice(0, 5).map((alert, index) => <AlertCard key={`${alert.product_id}-${alert.type}-${index}`} alert={alert} />) : <div className="small-empty">Price drops and restocks will appear here.</div>}</div></section>
            <section className="panel trust-panel"><div className="panel-heading"><div><p className="eyebrow">03 / TRUST LAYER</p><h2>What changed</h2></div><span className="pulse-badge"><i /> live feed</span></div><div className="trust-list">{incidents.length ? incidents.slice(0, 5).map((incident) => <TrustCard key={incident.id} incident={incident} />) : <div className="small-empty">No collector incidents yet. The feed stays quiet until a field drops below the 20% threshold.</div>}</div></section>
          </aside>
        </section>

        <footer className="footer"><span><i className="dot-lime" /> self-healing visibility on</span><span>{lastUpdated ? `last synced ${lastUpdated.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}` : "waiting for sync"}</span></footer>
      </main>
    </div>
  );
}

export default App;
