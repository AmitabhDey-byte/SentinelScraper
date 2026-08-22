import { AnimatePresence, motion } from "framer-motion";
import {
  useCallback,
  useEffect,
  useMemo,
  useState,
  type FormEvent,
  type ReactNode,
} from "react";
import { api } from "./api";
import { PixelSwap } from "./components/PixelSwap";
import { ProductGlance } from "./components/ProductGlance";
import {
  AlertCard,
  CollectorRail,
  ProductRow,
  TrustCard,
} from "./components/DashboardCards";
import type {
  Alert,
  AlertPage,
  CollectorStatus,
  IncidentPage,
  MarketInsight,
  Operation,
  Product,
  ProductPage,
  Profile,
} from "./types";
import "./styles.css";

type Route = "/" | "/dashboard" | "/signals" | "/trust" | "/network";

type DashboardState = {
  collectors: CollectorStatus[];
  products: ProductPage;
  alerts: AlertPage;
  incidents: IncidentPage;
};

const emptyPage = <T,>(): {
  items: T[];
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
} => ({ items: [], page: 1, page_size: 8, total: 0, total_pages: 1 });
const emptyState: DashboardState = {
  collectors: [],
  products: emptyPage(),
  alerts: emptyPage(),
  incidents: emptyPage(),
};
const pageTransition = {
  initial: { opacity: 0, y: 18 },
  animate: { opacity: 1, y: 0 },
  exit: { opacity: 0, y: -12 },
  transition: { duration: 0.3, ease: "easeOut" as const },
};

function routeFor(pathname: string): Route {
  if (
    pathname === "/dashboard" ||
    pathname === "/signals" ||
    pathname === "/trust" ||
    pathname === "/network"
  )
    return pathname;
  return "/";
}

function useRoute() {
  const [route, setRoute] = useState<Route>(() =>
    routeFor(window.location.pathname),
  );
  useEffect(() => {
    const onPopState = () => setRoute(routeFor(window.location.pathname));
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []);
  const navigate = useCallback((nextRoute: Route) => {
    window.history.pushState({}, "", nextRoute);
    setRoute(nextRoute);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }, []);
  return { route, navigate };
}

function PanelHeading({
  eyebrow,
  title,
  trailing,
}: {
  eyebrow: string;
  title: string;
  trailing?: ReactNode;
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

function EmptyState({
  children,
  detail,
}: {
  children: ReactNode;
  detail?: string;
}) {
  return (
    <div className="empty-state">
      <span className="empty-glyph" aria-hidden="true">
        ⌁
      </span>
      <p>{children}</p>
      {detail && <small>{detail}</small>}
    </div>
  );
}

function ScrollNavLink({
  section,
  label,
  active,
  onJump,
}: {
  section: string;
  label: string;
  active: boolean;
  onJump: (section: string) => void;
}) {
  return (
    <a
      href={`#${section}`}
      className={`nav-link ${active ? "nav-link-active" : ""}`}
      onClick={(event) => {
        event.preventDefault();
        onJump(section);
      }}
    >
      {label}
    </a>
  );
}

function Pagination({
  page,
  totalPages,
  total,
  onChange,
}: {
  page: number;
  totalPages: number;
  total: number;
  onChange: (page: number) => void;
}) {
  if (totalPages <= 1) return null;
  const visiblePages = Array.from(
    { length: totalPages },
    (_, index) => index + 1,
  ).slice(Math.max(0, page - 2), Math.min(totalPages, page + 1));
  return (
    <div className="pagination" aria-label="Pagination">
      <span>
        {total} tracked · page {page} / {totalPages}
      </span>
      <div>
        <button
          type="button"
          onClick={() => onChange(page - 1)}
          disabled={page === 1}
          aria-label="Previous page"
        >
          ‹
        </button>
        {visiblePages.map((pageNumber) => (
          <button
            type="button"
            key={pageNumber}
            className={pageNumber === page ? "pagination-current" : ""}
            onClick={() => onChange(pageNumber)}
          >
            {String(pageNumber).padStart(2, "0")}
          </button>
        ))}
        <button
          type="button"
          onClick={() => onChange(page + 1)}
          disabled={page === totalPages}
          aria-label="Next page"
        >
          ›
        </button>
      </div>
    </div>
  );
}

function StatStrip({ data }: { data: DashboardState }) {
  const openIncidents = data.incidents.items.filter(
    (incident) => incident.status === "open",
  ).length;
  const drops = data.alerts.items.filter(
    (alert) => alert.type === "price_drop",
  ).length;
  const restocks = data.alerts.items.filter(
    (alert) => alert.type === "restock",
  ).length;
  return (
    <div className="stat-strip">
      <div>
        <span>Listings indexed</span>
        <strong>{data.products.total}</strong>
        <small>across the network</small>
      </div>
      <div>
        <span>Price movement</span>
        <strong>{drops}</strong>
        <small>drops in the last scan</small>
      </div>
      <div>
        <span>Supply returning</span>
        <strong>{restocks}</strong>
        <small>restock signals</small>
      </div>
      <div>
        <span>Open breaks</span>
        <strong className={openIncidents ? "stat-warn" : ""}>
          {openIncidents}
        </strong>
        <small>awaiting collector repair</small>
      </div>
    </div>
  );
}

function SignalSummary({
  alerts,
  incidents,
}: {
  alerts: Alert[];
  incidents: IncidentPage;
}) {
  const drops = alerts.filter((alert) => alert.type === "price_drop").length;
  const restocks = alerts.filter((alert) => alert.type === "restock").length;
  const open = incidents.items.filter(
    (incident) => incident.status === "open",
  ).length;
  return (
    <div className="signal-summary">
      <div className="signal-summary-card signal-summary-drop">
        <span>↓</span>
        <strong>{drops}</strong>
        <small>price drops</small>
      </div>
      <div className="signal-summary-card signal-summary-restock">
        <span>✦</span>
        <strong>{restocks}</strong>
        <small>back in stock</small>
      </div>
      <div className="signal-summary-card signal-summary-open">
        <span>!</span>
        <strong>{open}</strong>
        <small>open breaks</small>
      </div>
    </div>
  );
}

const manualOperationsEnabled = import.meta.env.VITE_MANUAL_OPERATIONS !== "false";
const hostedDemo = !manualOperationsEnabled;
const watchlistStorageKey = "sentinelscrape-watchlist";

function HealingConsole({
  operation,
  incidents,
  operatorUnlocked,
  onOpenOperator,
  onScan,
  onProposeHeal,
  onApprove,
}: {
  operation: Operation | null;
  incidents: IncidentPage;
  operatorUnlocked: boolean;
  onOpenOperator: () => void;
  onScan: () => void;
  onProposeHeal: (incidentId: number) => void;
  onApprove: (incidentId: number) => void;
}) {
  const busy = operation?.status === "queued" || operation?.status === "running";
  const openIncident = incidents.items.find((incident) => incident.status === "open");
  const stage = operation?.kind === "approve_and_verify" ? "approve + verify" : operation?.kind === "heal_proposal" ? "heal proposal" : operation?.kind === "scan" ? "scan network" : operation?.kind === "auto_heal" ? "automatic watch" : "ready";
  return (
    <section className="healing-console" aria-label="Self-healing operation console">
      <div className="healing-console-title">
        <p className="eyebrow">LIVE / SELF-HEALING PROTOCOL</p>
        <h2>Make the break prove itself.</h2>
        <p>Every command below calls your Bright Data collectors. The record is persisted and Gemini narrates a verified recovery.</p>
      </div>
      <div className="healing-steps" aria-label="Healing workflow stages">
        <span className={operation?.kind === "scan" ? "active" : ""}>01 Scan</span>
        <span className={operation?.kind === "heal_proposal" ? "active" : ""}>02 Detect</span>
        <span className={operation?.kind === "approve_and_verify" ? "active" : ""}>03 Heal</span>
        <span className={operation?.status === "completed" ? "active" : ""}>04 Prove</span>
      </div>
      <div className="healing-actions">
        {(manualOperationsEnabled || operatorUnlocked) ? <button type="button" className="operation-primary" onClick={onScan} disabled={busy}>
          {busy && operation?.kind === "scan" ? "Scanning collectors…" : "Run Bright Data scan"}
        </button> : <button type="button" className="operation-unlock" onClick={onOpenOperator}>Unlock live controls</button>}
        {!manualOperationsEnabled && !operatorUnlocked && <p className="automatic-note">GitHub Actions watch is active. Unlock only when you need a manual Bright Data run.</p>}
        {(manualOperationsEnabled || operatorUnlocked) && openIncident && (
          <>
            <button type="button" onClick={() => onProposeHeal(openIncident.id)} disabled={busy}>
              Propose AI heal
            </button>
            <button type="button" onClick={() => onApprove(openIncident.id)} disabled={busy}>
              Approve + verify
            </button>
          </>
        )}
      </div>
      <div className="operation-transcript">
        <div>
          <span>OPERATION</span>
          <strong>{stage}</strong>
        </div>
        <div>
          <span>STATUS</span>
          <strong className={`operation-${operation?.status ?? "ready"}`}>{operation?.status?.replace(/_/g, " ") ?? "waiting for command"}</strong>
        </div>
        <ol>
          {(operation?.events ?? [{ at: new Date().toISOString(), message: "Run a scan to create a live, inspectable Bright Data operation." }]).slice(-3).map((event) => (
            <li key={`${event.at}-${event.message}`}><time>{new Date(event.at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</time>{event.message}</li>
          ))}
        </ol>
      </div>
      {operation?.error && <p className="operation-error">{operation.error}</p>}
    </section>
  );
}

function OperatorConsole({
  unlocked,
  busy,
  error,
  keyValue,
  onKeyChange,
  onClose,
  onUnlock,
  onLock,
}: {
  unlocked: boolean;
  busy: boolean;
  error: string | null;
  keyValue: string;
  onKeyChange: (value: string) => void;
  onClose: () => void;
  onUnlock: (event: FormEvent<HTMLFormElement>) => void;
  onLock: () => void;
}) {
  return (
    <motion.aside
      className="operator-console"
      aria-label="Operator mode"
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      transition={{ duration: 0.18 }}
    >
      <div className="operator-console-head">
        <div><p className="eyebrow">PRIVATE / OPERATOR MODE</p><h2>Live controls</h2></div>
        <button type="button" onClick={onClose} aria-label="Close operator mode">×</button>
      </div>
      {unlocked ? (
        <div className="operator-unlocked">
          <strong>◉ Operator controls unlocked</strong>
          <p>Live scan, heal, and approve actions are enabled for this tab only.</p>
          <button type="button" onClick={onLock}>Lock controls</button>
        </div>
      ) : (
        <form onSubmit={onUnlock}>
          <label htmlFor="operator-key">Render operator key</label>
          <input
            id="operator-key"
            type="password"
            value={keyValue}
            onChange={(event) => onKeyChange(event.target.value)}
            autoComplete="off"
            placeholder="Paste OPERATIONS_API_TOKEN"
          />
          <p>Validated against the API and held only in this browser tab. It is never saved to this device.</p>
          {error && <p className="operator-error">{error}</p>}
          <div className="operator-console-actions">
            <button type="button" onClick={onClose}>Cancel</button>
            <button type="submit" disabled={busy}>{busy ? "Checking…" : "Unlock"}</button>
          </div>
        </form>
      )}
    </motion.aside>
  );
}

function DashboardPage({
  data,
  loading,
  error,
  siteFilter,
  siteOptions,
  queryDraft,
  onQueryDraft,
  onSearch,
  onSiteChange,
  onRefresh,
  onPageChange,
  navigate,
  onSelectProduct,
  operation,
  operatorUnlocked,
  onOpenOperator,
  onScan,
  onProposeHeal,
  onApprove,
}: {
  data: DashboardState;
  loading: boolean;
  error: string | null;
  siteFilter: string;
  siteOptions: string[];
  queryDraft: string;
  onQueryDraft: (value: string) => void;
  onSearch: (event: FormEvent<HTMLFormElement>) => void;
  onSiteChange: (value: string) => void;
  onRefresh: () => void;
  onPageChange: (page: number) => void;
  navigate: (route: Route) => void;
  onSelectProduct: (product: Product) => void;
  operation: Operation | null;
  operatorUnlocked: boolean;
  onOpenOperator: () => void;
  onScan: () => void;
  onProposeHeal: (incidentId: number) => void;
  onApprove: (incidentId: number) => void;
}) {
  const healedCount = data.incidents.items.filter(
    (incident) => incident.status === "healed",
  ).length;
  return (
    <motion.main className="dashboard" {...pageTransition}>
      <section className="hero hero-dashboard">
        <div>
          <p className="eyebrow">
            FIELD REPORT / 04 <span>—</span> THE WATCH HOUSE
          </p>
          <h1>
            A change in the field.
            <br />
            <em>Noted at once.</em>
          </h1>
          <p className="hero-copy">
            Five markets under observation. Every broken field is recorded,
            repaired, and signed off.
          </p>
        </div>
        <div className="hero-signal">
          <div className="signal-note">
            <span className="case-stamp">CASE 001</span>
            <strong>
              WATCH
              <br />
              THE BREAK.
            </strong>
          </div>
          <div className="signal-ring">
            <span>{data.collectors.length || "—"}</span>
            <small>
              nodes
              <br />
              online
            </small>
          </div>
          <div className="signal-legend">
            <span>
              <i className="dot-lime" /> {data.products.total} listings
            </span>
            <span>
              <i className="dot-violet" /> {healedCount} repairs
            </span>
          </div>
        </div>
      </section>
      <StatStrip data={data} />
      <CollectorRail collectors={data.collectors} />
      <HealingConsole operation={operation} incidents={data.incidents} operatorUnlocked={operatorUnlocked} onOpenOperator={onOpenOperator} onScan={onScan} onProposeHeal={onProposeHeal} onApprove={onApprove} />
      {error && (
        <div className="error-banner" role="alert">
          <span>Signal lost</span>
          <p>{error}. Start the API.</p>
          <button type="button" onClick={onRefresh}>
            retry
          </button>
        </div>
      )}
      <section className="content-grid">
        <section className="panel market-panel">
          <PanelHeading
            eyebrow="01 / THE LEDGER"
            title="Market ledger"
            trailing={
              <span className="panel-count">
                {data.products.total} products
              </span>
            }
          />
          <form className="market-toolbar" onSubmit={onSearch}>
            <label className="search-field">
              <span>⌕</span>
              <input
                value={queryDraft}
                onChange={(event) => onQueryDraft(event.target.value)}
                placeholder="Find a laptop listing"
              />
            </label>
            <select
              value={siteFilter}
              onChange={(event) => onSiteChange(event.target.value)}
              aria-label="Filter by site"
            >
              <option value="">All markets</option>
              {siteOptions.map((site) => (
                <option value={site} key={site}>
                  {site}
                </option>
              ))}
            </select>
            <button type="submit" className="toolbar-submit">
              scan
            </button>
          </form>
          <div className="table-head">
            <span>listing</span>
            <span>price</span>
            <span>status</span>
            <span>trend</span>
          </div>
          <div className="market-list">
            {loading && data.products.items.length === 0 ? (
              <div className="empty-state">
                <span className="loader" />
                <p>Reading collector snapshots…</p>
              </div>
            ) : data.products.items.length ? (
              data.products.items.map((product, index) => (
                <ProductRow product={product} key={product.id} index={index} onSelect={onSelectProduct} />
              ))
            ) : (
              <EmptyState detail="Run one collector cycle.">
                No scan data.
              </EmptyState>
            )}
          </div>
          <Pagination
            page={data.products.page}
            totalPages={data.products.total_pages}
            total={data.products.total}
            onChange={onPageChange}
          />
        </section>
        <aside className="side-column">
          <section className="panel alerts-panel">
            <PanelHeading
              eyebrow="02 / MARKET NOTICES"
              title="Notices"
              trailing={
                <button
                  className="panel-link"
                  type="button"
                  onClick={() => navigate("/signals")}
                >
                  open log ⧉
                </button>
              }
            />
            <SignalSummary
              alerts={data.alerts.items}
              incidents={data.incidents}
            />
            <div className="alerts-list">
              {data.alerts.items.length ? (
                data.alerts.items
                  .slice(0, 4)
                  .map((alert, index) => (
                    <AlertCard
                      alert={alert}
                      key={`${alert.product_id}-${alert.type}-${index}`}
                    />
                  ))
              ) : (
                <div className="small-empty">No impact yet.</div>
              )}
            </div>
          </section>
          <section className="panel trust-panel">
            <PanelHeading
              eyebrow="03 / REPAIR REGISTER"
              title="The register"
              trailing={
                <button
                  className="panel-link"
                  type="button"
                  onClick={() => navigate("/trust")}
                >
                  full trace ⧉
                </button>
              }
            />
            <div className="trust-list">
              {data.incidents.items.length ? (
                data.incidents.items
                  .slice(0, 3)
                  .map((incident) => (
                    <TrustCard incident={incident} key={incident.id} />
                  ))
              ) : (
                <div className="small-empty">No breaks logged.</div>
              )}
            </div>
          </section>
        </aside>
      </section>
    </motion.main>
  );
}

function LandingPage({
  data,
  navigate,
}: {
  data: DashboardState;
  navigate: (route: Route) => void;
}) {
  const healthy = data.collectors.filter(
    (collector) => collector.status === "healthy",
  ).length;
  return (
    <motion.main className="landing-page" {...pageTransition}>
      <section className="landing-hero">
        <div className="landing-copy">
          <p className="eyebrow">SENTINELSCRAPE / PRIVATE INTELLIGENCE</p>
          <h1>
            A ledger
            <br />
            <em>of the wild web.</em>
            <br />
            kept daily.
          </h1>
          <p className="landing-subtitle">
            A quiet watch house for competitor prices and stock. We note the
            movement, mark the break, and keep the repair in the record.
          </p>
          <div className="landing-actions">
            <button
              className="primary-button"
              type="button"
              onClick={() => navigate("/dashboard")}
            >
              Enter the control room <span>⌘</span>
            </button>
            <button
              className="text-button"
              type="button"
              onClick={() => navigate("/trust")}
            >
              See the repair trail
            </button>
          </div>
        </div>
        <div
          className="landing-void landing-plate"
          aria-label="Zeus horse field illustration"
        />
      </section>
      <section className="landing-strip">
        <span>THE LOOP</span>
        <div>
          <b>WATCH</b>
          <i>✦</i>
          <b>DETECT</b>
          <i>✦</i>
          <b>HEAL</b>
          <i>✦</i>
          <b>PROVE</b>
        </div>
        <span>04 / 04</span>
      </section>
      <section className="landing-cards">
        <motion.article
          className="landing-card landing-card-dark"
          whileHover={{ y: -6 }}
        >
          <span className="card-index">01</span>
          <h2>The ledger</h2>
          <p>
            {data.products.total || "—"} listings in the latest indexed view.
          </p>
          <button type="button" onClick={() => navigate("/dashboard")}>
            open the ledger ⧉
          </button>
        </motion.article>
        <motion.article
          className="landing-card landing-card-lime"
          whileHover={{ y: -6 }}
        >
          <span className="card-index">02</span>
          <h2>Market notices</h2>
          <p>
            {data.alerts.total} price and stock changes waiting for a decision.
          </p>
          <button type="button" onClick={() => navigate("/signals")}>
            read the notices ⧉
          </button>
        </motion.article>
        <motion.article
          className="landing-card landing-card-red"
          whileHover={{ y: -6 }}
        >
          <span className="card-index">03</span>
          <h2>Repair register</h2>
          <p>{healthy} collectors clear. Every recovery stays visible.</p>
          <button type="button" onClick={() => navigate("/trust")}>
            inspect the register ⧉
          </button>
        </motion.article>
      </section>
    </motion.main>
  );
}

function SignalsPage({
  data,
  navigate,
}: {
  data: DashboardState;
  navigate: (route: Route) => void;
}) {
  const [filter, setFilter] = useState<"all" | "price_drop" | "restock">("all");
  const alerts =
    filter === "all"
      ? data.alerts.items
      : data.alerts.items.filter((alert) => alert.type === filter);
  return (
    <motion.main className="page-shell" {...pageTransition}>
      <PageIntro
        eyebrow="02 / MARKET NOTICES"
        title="Notices from the watch house."
        copy="Price falls and returning stock, arranged as a quiet daily brief for the people making the next move."
        action={
          <button
            className="text-button"
            type="button"
            onClick={() => navigate("/dashboard")}
          >
            return to market
          </button>
        }
      />
      <SignalSummary alerts={data.alerts.items} incidents={data.incidents} />
      <div className="filter-row">
        <span>
          showing {alerts.length} of {data.alerts.total}
        </span>
        <div>
          {(["all", "price_drop", "restock"] as const).map((value) => (
            <button
              type="button"
              key={value}
              className={filter === value ? "filter-active" : ""}
              onClick={() => setFilter(value)}
            >
              {value === "all"
                ? "all signals"
                : value === "price_drop"
                  ? "price drops"
                  : "restocks"}
            </button>
          ))}
        </div>
      </div>
      <section className="wide-panel panel">
        <div className="wide-list">
          {alerts.length ? (
            alerts.map((alert, index) => (
              <AlertCard
                alert={alert}
                key={`${alert.product_id}-${alert.type}-${index}`}
              />
            ))
          ) : (
            <EmptyState>No matching signals.</EmptyState>
          )}
        </div>
      </section>
    </motion.main>
  );
}

function TrustPage({
  data,
  navigate,
}: {
  data: DashboardState;
  navigate: (route: Route) => void;
}) {
  return (
    <motion.main className="page-shell" {...pageTransition}>
      <PageIntro
        eyebrow="03 / REPAIR REGISTER"
        title="A repair leaves a paper trail."
        copy="The failure, the approved heal, the recovered fields, and the plain-English account all remain in the register."
        action={
          <button
            className="text-button"
            type="button"
            onClick={() => navigate("/dashboard")}
          >
            return to market
          </button>
        }
      />
      <section className="repair-steps">
        <div>
          <span>01</span>
          <strong>FIELD DROP</strong>
          <small>completeness falls below 20%</small>
        </div>
        <i>✦</i>
        <div>
          <span>02</span>
          <strong>AI HEAL</strong>
          <small>Bright Data proposes a repair</small>
        </div>
        <i>✦</i>
        <div>
          <span>03</span>
          <strong>PROOF</strong>
          <small>re-run recovers the field</small>
        </div>
      </section>
      <section className="wide-panel panel">
        <PanelHeading
          eyebrow="TRACE / REVERSE CHRONOLOGY"
          title="Repair register"
          trailing={
            <span className="panel-count">
              {data.incidents.total} incidents
            </span>
          }
        />
        <div className="wide-list trust-wide-list">
          {data.incidents.items.length ? (
            data.incidents.items.map((incident) => (
              <TrustCard incident={incident} key={incident.id} />
            ))
          ) : (
            <EmptyState>No breaks logged.</EmptyState>
          )}
        </div>
      </section>
    </motion.main>
  );
}

function NetworkPage({
  data,
  navigate,
}: {
  data: DashboardState;
  navigate: (route: Route) => void;
}) {
  return (
    <motion.main className="page-shell" {...pageTransition}>
      <PageIntro
        eyebrow="04 / THE OBSERVATORY"
        title="Five markets under watch."
        copy="Each collector keeps its own record. A quiet green mark means the latest observation passed inspection."
        action={
          <button
            className="text-button"
            type="button"
            onClick={() => navigate("/dashboard")}
          >
            return to market
          </button>
        }
      />
      <section className="network-grid">
        {data.collectors.length ? (
          data.collectors.map((collector, index) => (
            <motion.article
              className={`network-card network-${collector.status}`}
              key={collector.collector_id}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.05 }}
            >
              <div className="network-card-top">
                <span className="network-number">0{index + 1}</span>
                <span className="network-status">
                  <i />
                  {collector.status.replace("_", " ")}
                </span>
              </div>
              <h2>{collector.site_name}</h2>
              <p>{collector.category} collector</p>
              <div className="network-meta">
                <span>
                  rows <b>{collector.row_count ?? "—"}</b>
                </span>
                <span>
                  open breaks <b>{collector.open_incidents}</b>
                </span>
              </div>
              <button type="button" onClick={() => navigate("/dashboard")}>
                open market ⧉
              </button>
            </motion.article>
          ))
        ) : (
          <EmptyState>
            Register collectors to bring the network online.
          </EmptyState>
        )}
      </section>
    </motion.main>
  );
}

function PageIntro({
  eyebrow,
  title,
  copy,
  action,
}: {
  eyebrow: string;
  title: string;
  copy: string;
  action: ReactNode;
}) {
  return (
    <section className="page-intro">
      <div>
        <p className="eyebrow">{eyebrow}</p>
        <h1>{title}</h1>
        <p className="page-copy">{copy}</p>
      </div>
      <div>{action}</div>
    </section>
  );
}

function IntelligencePage({
  insight,
  loading,
  onRefresh,
}: {
  insight: MarketInsight | null;
  loading: boolean;
  onRefresh: () => void;
}) {
  return (
    <section className="intelligence-section" id="intelligence">
      <div className="intelligence-veil" />
      <div className="intelligence-copy">
        <p className="eyebrow">05 / THE CABINET OF REASON</p>
        <h1>
          Evidence first.
          <br />
          <em>Judgment second.</em>
        </h1>
        <p>
          Gemini turns only the latest verified movement and collector state into a brief. It does not fabricate a price forecast.
        </p>
      </div>
      <div className="intelligence-card">
        <PixelSwap
          firstContent={
            <div>
              <span className="pixel-kicker">MARKET BRIEF / TAP TO UNSEAL</span>
              <strong>{loading ? "Consulting the record…" : "A grounded note is waiting."}</strong>
              <small>Gemini speaks after the ledger is checked.</small>
            </div>
          }
          secondContent={
            <div>
              <span className="pixel-kicker">{insight?.source ?? "fallback"} / {insight?.confidence ?? "medium"} confidence</span>
              <strong>{insight?.headline ?? "The latest record is still being assembled."}</strong>
              <small>{insight?.recommendation ?? "Run a fresh scan to create an evidence-backed brief."}</small>
            </div>
          }
        />
        <button className="intelligence-refresh" type="button" onClick={onRefresh} disabled={loading}>
          {loading ? "Reading…" : "Refresh brief ⌘"}
        </button>
        {insight && <p className="intelligence-rationale">{insight.rationale}</p>}
      </div>
    </section>
  );
}

function ProfilePage({
  profile,
  favorites,
  onSelectProduct,
  onJump,
}: {
  profile: Profile | null;
  favorites: Product[];
  onSelectProduct: (product: Product) => void;
  onJump: (section: string) => void;
}) {
  return (
    <section className="profile-section" id="profile">
      <div className="profile-sheet">
        <p className="eyebrow">06 / YOUR WATCHLIST</p>
        <h2>The observer's cabinet</h2>
        <p>Saved listings stay in this SentinelScrape database and are ready for a local demo.</p>
        <div className="profile-stats">
          <span><b>{profile?.favorites_count ?? favorites.length}</b> saved</span>
          <span><b>{profile?.auth_mode === "operator" ? "operator" : "local"}</b> identity</span>
        </div>
        <button className="text-button" type="button" onClick={() => onJump("market")}>Browse the ledger</button>
      </div>
      <div className="favorites-shelf">
        <p className="eyebrow">FAVOURITES / AT A GLANCE</p>
        {favorites.length ? (
          favorites.slice(0, 4).map((product) => (
            <button type="button" className="favorite-card" key={product.id} onClick={() => onSelectProduct(product)}>
              <span>{product.site_name}</span>
              <strong>{product.name}</strong>
              <small>{product.price === null ? "Price pending" : `$${Math.round(product.price)}`}</small>
            </button>
          ))
        ) : (
          <div className="favorites-empty">Save a listing from the ledger and it will appear here.</div>
        )}
      </div>
    </section>
  );
}

function ScrollObservatory({
  data,
  loading,
  error,
  siteFilter,
  siteOptions,
  queryDraft,
  onQueryDraft,
  onSearch,
  onSiteChange,
  onRefresh,
  onPageChange,
  navigate,
  onSelectProduct,
  insight,
  insightLoading,
  onInsightRefresh,
  profile,
  favorites,
  onJump,
  operation,
  operatorUnlocked,
  onOpenOperator,
  onScan,
  onProposeHeal,
  onApprove,
}: {
  data: DashboardState;
  loading: boolean;
  error: string | null;
  siteFilter: string;
  siteOptions: string[];
  queryDraft: string;
  onQueryDraft: (value: string) => void;
  onSearch: (event: FormEvent<HTMLFormElement>) => void;
  onSiteChange: (value: string) => void;
  onRefresh: () => void;
  onPageChange: (page: number) => void;
  navigate: (route: Route) => void;
  onSelectProduct: (product: Product) => void;
  insight: MarketInsight | null;
  insightLoading: boolean;
  onInsightRefresh: () => void;
  profile: Profile | null;
  favorites: Product[];
  onJump: (section: string) => void;
  operation: Operation | null;
  operatorUnlocked: boolean;
  onOpenOperator: () => void;
  onScan: () => void;
  onProposeHeal: (incidentId: number) => void;
  onApprove: (incidentId: number) => void;
}) {
  const scrollNavigate = (route: Route) => onJump(route === "/signals" ? "signals" : route === "/trust" ? "trust" : route === "/network" ? "network" : "market");
  return (
    <div className="scroll-observatory">
      <div id="overview"><LandingPage data={data} navigate={scrollNavigate} /></div>
      <div id="market"><DashboardPage data={data} loading={loading} error={error} siteFilter={siteFilter} siteOptions={siteOptions} queryDraft={queryDraft} onQueryDraft={onQueryDraft} onSearch={onSearch} onSiteChange={onSiteChange} onRefresh={onRefresh} onPageChange={onPageChange} navigate={scrollNavigate} onSelectProduct={onSelectProduct} operation={operation} operatorUnlocked={operatorUnlocked} onOpenOperator={onOpenOperator} onScan={onScan} onProposeHeal={onProposeHeal} onApprove={onApprove} /></div>
      <div id="signals"><SignalsPage data={data} navigate={scrollNavigate} /></div>
      <div id="trust"><TrustPage data={data} navigate={scrollNavigate} /></div>
      <IntelligencePage insight={insight} loading={insightLoading} onRefresh={onInsightRefresh} />
      <div id="network"><NetworkPage data={data} navigate={scrollNavigate} /></div>
      <ProfilePage profile={profile} favorites={favorites} onSelectProduct={onSelectProduct} onJump={onJump} />
    </div>
  );
}

function Footer({ lastUpdated }: { lastUpdated: Date | null }) {
  return (
    <footer className="footer">
      <span>
        <i className="dot-lime" /> repair trace live
      </span>
      <span>
        {lastUpdated
          ? `last synced ${lastUpdated.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`
          : "Bright Data / Gemini / local store"}
      </span>
    </footer>
  );
}

function App() {
  const { route, navigate } = useRoute();
  const [data, setData] = useState<DashboardState>(emptyState);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [productPageNumber, setProductPageNumber] = useState(1);
  const [siteFilter, setSiteFilter] = useState("");
  const [query, setQuery] = useState("");
  const [queryDraft, setQueryDraft] = useState("");
  const [selectedProduct, setSelectedProduct] = useState<Product | null>(null);
  const [favorites, setFavorites] = useState<Product[]>([]);
  const [profile, setProfile] = useState<Profile | null>(null);
  const [insight, setInsight] = useState<MarketInsight | null>(null);
  const [insightLoading, setInsightLoading] = useState(false);
  const [operation, setOperation] = useState<Operation | null>(null);
  const [operatorPanelOpen, setOperatorPanelOpen] = useState(false);
  const [operatorKey, setOperatorKey] = useState("");
  const [operatorUnlocked, setOperatorUnlocked] = useState(false);
  const [operatorBusy, setOperatorBusy] = useState(false);
  const [operatorError, setOperatorError] = useState<string | null>(null);

  useEffect(() => () => api.lockOperations(), []);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const [collectors, products, alerts, incidents] = await Promise.all([
        api.collectors(),
        api.products({
          page: productPageNumber,
          pageSize: 8,
          site: siteFilter || undefined,
          q: query || undefined,
        }),
        api.alerts({ page: 1, pageSize: 50 }),
        api.incidents({ page: 1, pageSize: 50 }),
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
  }, [productPageNumber, query, siteFilter]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const refreshPersonal = useCallback(async () => {
    if (hostedDemo) {
      try {
        const saved = JSON.parse(window.localStorage.getItem(watchlistStorageKey) ?? "[]");
        setFavorites(Array.isArray(saved) ? saved as Product[] : []);
      } catch {
        setFavorites([]);
      }
      setProfile(null);
      return;
    }
    try {
      const [nextProfile, nextFavorites] = await Promise.all([api.profile(), api.favorites()]);
      setProfile(nextProfile);
      setFavorites(nextFavorites);
    } catch {
      // The market still works before a local migration has been applied.
    }
  }, []);

  useEffect(() => {
    void refreshPersonal();
  }, [refreshPersonal]);

  const refreshInsight = useCallback(async () => {
    setInsightLoading(true);
    try {
      setInsight(await api.marketInsight());
    } catch {
      setInsight(null);
    } finally {
      setInsightLoading(false);
    }
  }, []);

  useEffect(() => {
    void refreshInsight();
  }, [refreshInsight]);

  useEffect(() => {
    void api.latestOperation().then(setOperation).catch(() => setOperation(null));
  }, []);

  useEffect(() => {
    if (!operation || !["queued", "running"].includes(operation.status)) return;
    const timer = window.setInterval(() => {
      void api.operation(operation.id).then((nextOperation) => {
        setOperation(nextOperation);
        if (!["queued", "running"].includes(nextOperation.status)) {
          void refresh();
          void refreshInsight();
        }
      }).catch(() => undefined);
    }, 2500);
    return () => window.clearInterval(timer);
  }, [operation, refresh, refreshInsight]);

  const startOperation = useCallback(async (request: () => Promise<Operation>) => {
    try {
      setOperation(await request());
      setError(null);
    } catch (operationError) {
      setError(operationError instanceof Error ? operationError.message : "Operation could not be started");
    }
  }, []);

  const unlockOperator = useCallback(async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const candidate = operatorKey.trim();
    if (!candidate) {
      setOperatorError("Paste the Render operator key.");
      return;
    }
    setOperatorBusy(true);
    setOperatorError(null);
    try {
      await api.unlockOperations(candidate);
      setOperatorUnlocked(true);
      setOperatorKey("");
      setOperatorPanelOpen(false);
    } catch {
      setOperatorError("That operator key was not accepted.");
    } finally {
      setOperatorBusy(false);
    }
  }, [operatorKey]);

  const lockOperator = useCallback(() => {
    api.lockOperations();
    setOperatorUnlocked(false);
    setOperatorKey("");
    setOperatorError(null);
    setOperatorPanelOpen(false);
  }, []);

  const siteOptions = useMemo(
    () => data.collectors.map((collector) => collector.site_name).sort(),
    [data.collectors],
  );
  const favoriteIds = useMemo(() => new Set(favorites.map((product) => product.id)), [favorites]);
  const toggleFavorite = useCallback(async (product: Product) => {
    const wasFavorite = favoriteIds.has(product.id);
    if (hostedDemo) {
      const nextFavorites = wasFavorite
        ? favorites.filter((favorite) => favorite.id !== product.id)
        : [product, ...favorites];
      window.localStorage.setItem(watchlistStorageKey, JSON.stringify(nextFavorites));
      setFavorites(nextFavorites);
      return;
    }
    try {
      await (wasFavorite ? api.removeFavorite(product.id) : api.saveFavorite(product.id));
      await refreshPersonal();
    } catch {
      // A failed save is non-destructive; the current displayed list remains truthful.
    }
  }, [favoriteIds, favorites, refreshPersonal]);

  const jumpTo = useCallback((section: string) => {
    const scroll = () => document.getElementById(section)?.scrollIntoView({ behavior: "smooth", block: "start" });
    if (route !== "/") {
      navigate("/");
      window.setTimeout(scroll, 80);
      return;
    }
    scroll();
  }, [navigate, route]);

  const page =
    route === "/" ? (
      <ScrollObservatory
        data={data}
        loading={loading}
        error={error}
        siteFilter={siteFilter}
        siteOptions={siteOptions}
        queryDraft={queryDraft}
        onQueryDraft={setQueryDraft}
        onSearch={(event) => { event.preventDefault(); setProductPageNumber(1); setQuery(queryDraft.trim()); }}
        onSiteChange={(value) => { setSiteFilter(value); setProductPageNumber(1); }}
        onRefresh={() => void refresh()}
        onPageChange={setProductPageNumber}
        navigate={navigate}
        onSelectProduct={setSelectedProduct}
        operation={operation}
        operatorUnlocked={operatorUnlocked}
        onOpenOperator={() => setOperatorPanelOpen(true)}
        onScan={() => void startOperation(api.scan)}
        onProposeHeal={(incidentId) => void startOperation(() => api.proposeHeal(incidentId))}
        onApprove={(incidentId) => void startOperation(() => api.approveHeal(incidentId))}
        insight={insight}
        insightLoading={insightLoading}
        onInsightRefresh={() => void refreshInsight()}
        profile={profile}
        favorites={favorites}
        onJump={jumpTo}
      />
    ) : route === "/signals" ? (
      <SignalsPage data={data} navigate={navigate} />
    ) : route === "/trust" ? (
      <TrustPage data={data} navigate={navigate} />
    ) : route === "/network" ? (
      <NetworkPage data={data} navigate={navigate} />
    ) : (
      <DashboardPage
        data={data}
        loading={loading}
        error={error}
        siteFilter={siteFilter}
        siteOptions={siteOptions}
        queryDraft={queryDraft}
        onQueryDraft={setQueryDraft}
        onSearch={(event) => {
          event.preventDefault();
          setProductPageNumber(1);
          setQuery(queryDraft.trim());
        }}
        onSiteChange={(value) => {
          setSiteFilter(value);
          setProductPageNumber(1);
        }}
        onRefresh={() => void refresh()}
        onPageChange={setProductPageNumber}
        navigate={navigate}
        onSelectProduct={setSelectedProduct}
        operation={operation}
        operatorUnlocked={operatorUnlocked}
        onOpenOperator={() => setOperatorPanelOpen(true)}
        onScan={() => void startOperation(api.scan)}
        onProposeHeal={(incidentId) => void startOperation(() => api.proposeHeal(incidentId))}
        onApprove={(incidentId) => void startOperation(() => api.approveHeal(incidentId))}
      />
    );

  return (
    <div className={`app-shell ${route === "/" ? "app-shell-landing" : ""}`}>
      <header className="topbar">
        <a
          className="brand"
          href="/"
          onClick={(event) => {
            event.preventDefault();
            navigate("/");
          }}
        >
          <span className="brand-orbit" aria-hidden="true">
            <i />
          </span>
          <span>
            sentinel<span>scrape</span>
          </span>
        </a>
        <nav className="nav-links" aria-label="Primary navigation">
          <ScrollNavLink
            section="market"
            label="Control room"
            active={route === "/dashboard"}
            onJump={jumpTo}
          />
          <ScrollNavLink
            section="signals"
            label="Signals"
            active={route === "/signals"}
            onJump={jumpTo}
          />
          <ScrollNavLink
            section="trust"
            label="Trust layer"
            active={route === "/trust"}
            onJump={jumpTo}
          />
          <ScrollNavLink
            section="intelligence"
            label="Intelligence"
            active={false}
            onJump={jumpTo}
          />
          <ScrollNavLink
            section="network"
            label="Network"
            active={route === "/network"}
            onJump={jumpTo}
          />
        </nav>
        <div className="topbar-right">
          <span className="live-indicator">
            <i /> {error ? "signal paused" : "signal live"}
          </span>
          {(manualOperationsEnabled || operatorUnlocked) ? <button
            className="refresh-button"
            type="button"
            onClick={() => void startOperation(api.scan)}
            disabled={operation?.status === "queued" || operation?.status === "running"}
          >
            {operation?.status === "queued" || operation?.status === "running" ? "scan running…" : "run live scan"} <span>⌘</span>
          </button> : <button className="operator-mode-button" type="button" onClick={() => setOperatorPanelOpen(true)}>⌾ operator mode</button>}
          {operatorUnlocked && !manualOperationsEnabled && <button className="operator-lock-button" type="button" onClick={lockOperator}>◉ operator on</button>}
        </div>
      </header>
      <AnimatePresence>
        {operatorPanelOpen && <OperatorConsole
          unlocked={operatorUnlocked}
          busy={operatorBusy}
          error={operatorError}
          keyValue={operatorKey}
          onKeyChange={setOperatorKey}
          onClose={() => { setOperatorPanelOpen(false); setOperatorError(null); }}
          onUnlock={(event) => void unlockOperator(event)}
          onLock={lockOperator}
        />}
      </AnimatePresence>
      <AnimatePresence mode="wait">
        <div key={route}>{page}</div>
      </AnimatePresence>
      {route !== "/dashboard" && (
        <div className="page-footer-wrap">
          <Footer lastUpdated={lastUpdated} />
        </div>
      )}
      <ProductGlance
        product={selectedProduct}
        favorite={selectedProduct ? favoriteIds.has(selectedProduct.id) : false}
        onClose={() => setSelectedProduct(null)}
        onFavorite={(product) => void toggleFavorite(product)}
      />
    </div>
  );
}

export default App;
