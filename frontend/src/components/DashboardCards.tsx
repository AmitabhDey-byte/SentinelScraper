import type { Alert, CollectorStatus, Incident, Product } from "../types";
import { Sparkline } from "./Sparkline";

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
  const slug = site.toLowerCase().replace(/[^a-z]+/g, "-");
  return `site-tag site-${slug}`;
}

export function StockPill({ value }: { value: string | null }) {
  const normalized = value?.toLowerCase() ?? "unknown";
  const unavailable = /out|unavailable|sold/.test(normalized);
  const state = unavailable ? "stock-out" : value ? "stock-in" : "stock-unknown";

  return <span className={`stock-pill ${state}`}><i />{value ?? "No signal"}</span>;
}

export function ProductRow({ product }: { product: Product }) {
  return (
    <a className="market-row" href={product.listing_url || "#"} target="_blank" rel="noreferrer">
      <div className="product-cell">
        {product.image_url ? (
          <img src={product.image_url} alt="" loading="lazy" />
        ) : (
          <div className="image-placeholder" aria-hidden="true">▦</div>
        )}
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

export function AlertCard({ alert }: { alert: Alert }) {
  const isDrop = alert.type === "price_drop";
  const detail = isDrop
    ? `${formatPrice(alert.previous_value)} → ${formatPrice(alert.current_value)}`
    : alert.stock_status;

  return (
    <article className={`alert-card ${isDrop ? "alert-drop" : "alert-restock"}`}>
      <div className="alert-icon" aria-hidden="true">{isDrop ? "↓" : "↗"}</div>
      <div className="alert-copy">
        <div className="alert-topline">
          <span>{isDrop ? "Price drop" : "Restocked"}</span>
          <time>{relativeTime(alert.observed_at)}</time>
        </div>
        <strong>{alert.product_name}</strong>
        <small>{alert.site_name} · {detail}</small>
      </div>
    </article>
  );
}

export function TrustCard({ incident }: { incident: Incident }) {
  const statusClass = incident.status === "healed" ? "status-healed" : "status-open";
  const source = incident.narration_source ?? "pending";

  return (
    <article className="trust-card">
      <div className="trust-card-head">
        <div className="trust-mark" aria-hidden="true">✦</div>
        <div>
          <span className={siteClass(incident.site_name)}>{incident.site_name}</span>
          <time>{relativeTime(incident.detected_at)}</time>
        </div>
        <span className={`status-badge ${statusClass}`}>{incident.status}</span>
      </div>
      <p>{incident.narration_text ?? "Extraction drift detected. Waiting for an approved Bright Data heal."}</p>
      <div className="trust-meta">
        <span><b>broken</b>{incident.dropped_fields.join(", ") || "—"}</span>
        <span><b>healed</b>{incident.recovered_fields.join(", ") || "pending"}</span>
      </div>
      <div className="trust-footer">
        <span>{incident.rows_prev} rows → {incident.rows_curr} rows</span>
        <span className={`source-badge source-${source}`}>
          {incident.narration_source ?? "awaiting narration"}
        </span>
      </div>
    </article>
  );
}

export function CollectorRail({ collectors }: { collectors: CollectorStatus[] }) {
  if (!collectors.length) {
    return (
      <div className="collector-rail collector-rail-empty">
        <span className="rail-label">collector health</span>
        <span>Register the five Scraper Studio collectors to start the network.</span>
      </div>
    );
  }

  return (
    <div className="collector-rail">
      <span className="rail-label">collector health</span>
      <div className="collector-list">
        {collectors.map((collector) => {
          const label = collector.status === "healthy"
            ? "green"
            : collector.status.replace("_", " ");

          return (
            <span className={`collector-chip collector-${collector.status}`} key={collector.collector_id}>
              <i />
              {collector.site_name}
              <small>{label}</small>
            </span>
          );
        })}
      </div>
    </div>
  );
}
