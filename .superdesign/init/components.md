# Shared components

## `frontend/src/components/DashboardCards.tsx`

Reusable data-display primitives: product rows, stock status, alert cards, incident cards, and collector health rail.

```tsx
export function StockPill({ value }: { value: string | null }) {
  const normalized = value?.toLowerCase() ?? "unknown";
  const unavailable = /out|unavailable|sold/.test(normalized);
  const state = unavailable ? "stock-out" : value ? "stock-in" : "stock-unknown";
  return <span className={`stock-pill ${state}`}><i />{value ?? "No signal"}</span>;
}

export function ProductRow({ product, index = 0 }: { product: Product; index?: number }) {
  return (
    <motion.a className="market-row" href={product.listing_url || "#"} target="_blank" rel="noreferrer"
      initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }}
      transition={{ delay: Math.min(index, 7) * 0.035, duration: 0.24 }} whileHover={{ x: 5 }}>
      <div className="product-cell">
        {product.image_url ? <img src={product.image_url} alt="" loading="lazy" /> : <div className="image-placeholder">▦</div>}
        <div><span className={siteClass(product.site_name)}>{product.site_name}</span><strong>{product.name}</strong></div>
      </div>
      <span className="price-cell">{formatPrice(product.price)}</span>
      <StockPill value={product.stock_status} />
      <Sparkline values={product.price_history.map((point) => point.price)} />
    </motion.a>
  );
}

export function AlertCard({ alert }: { alert: Alert }) {
  const isDrop = alert.type === "price_drop";
  const detail = isDrop ? `${formatPrice(alert.previous_value)} → ${formatPrice(alert.current_value)}` : alert.stock_status;
  return <motion.article className={`alert-card ${isDrop ? "alert-drop" : "alert-restock"}`} whileHover={{ x: 4 }}><div className="alert-icon">{isDrop ? "↓" : "↗"}</div><div className="alert-copy"><div className="alert-topline"><span>{isDrop ? "DROP" : "BACK IN"}</span><time>{relativeTime(alert.observed_at)}</time></div><strong>{alert.product_name}</strong><small>{alert.site_name} · {detail}</small></div></motion.article>;
}

export function TrustCard({ incident }: { incident: Incident }) {
  const statusClass = incident.status === "healed" ? "status-healed" : "status-open";
  const source = incident.narration_source ?? "pending";
  return <motion.article className="trust-card" whileHover={{ x: 4 }}><div className="trust-card-head"><div className="trust-mark">✦</div><div><span className={siteClass(incident.site_name)}>{incident.site_name}</span><time>{relativeTime(incident.detected_at)}</time></div><span className={`status-badge ${statusClass}`}>{incident.status}</span></div><p>{incident.narration_text ?? "Field breach detected. Awaiting repair."}</p><div className="trust-meta"><span><b>broken</b>{incident.dropped_fields.join(", ") || "—"}</span><span><b>healed</b>{incident.recovered_fields.join(", ") || "pending"}</span></div><div className="trust-footer"><span>{incident.rows_prev} rows → {incident.rows_curr} rows</span><span className={`source-badge source-${source}`}>{incident.narration_source ?? "awaiting narration"}</span></div></motion.article>;
}
```

## `frontend/src/components/Sparkline.tsx`

```tsx
export function Sparkline({ values, positive = false }: { values: (number | null)[]; positive?: boolean }) {
  const clean = values.filter((value): value is number => value !== null);
  if (clean.length < 2) return <span className="sparkline-empty">—</span>;
  const min = Math.min(...clean), max = Math.max(...clean), range = max - min || 1;
  const points = clean.map((value, index) => `${((index / (clean.length - 1)) * 72).toFixed(1)},${(22 - ((value - min) / range) * 18).toFixed(1)}`).join(" ");
  return <svg className={`sparkline ${positive ? "sparkline-positive" : ""}`} viewBox="0 0 72 24" role="img" aria-label="Price history sparkline"><polyline points={points} fill="none" vectorEffect="non-scaling-stroke" /></svg>;
}
```
