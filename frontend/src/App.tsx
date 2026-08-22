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
  ProductPage,
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

function NavLink({
  href,
  label,
  active,
  onNavigate,
}: {
  href: Route;
  label: string;
  active: boolean;
  onNavigate: (route: Route) => void;
}) {
  return (
    <a
      href={href}
      className={`nav-link ${active ? "nav-link-active" : ""}`}
      onClick={(event) => {
        event.preventDefault();
        onNavigate(href);
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
          ←
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
          →
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
        <span>↗</span>
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
                <ProductRow product={product} key={product.id} index={index} />
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
                  open log →
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
                  full trace →
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
              Enter the control room <span>↗</span>
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
          <i>→</i>
          <b>DETECT</b>
          <i>→</i>
          <b>HEAL</b>
          <i>→</i>
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
            open the ledger →
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
            read the notices →
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
            inspect the register →
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
            ← back to market
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
            ← back to market
          </button>
        }
      />
      <section className="repair-steps">
        <div>
          <span>01</span>
          <strong>FIELD DROP</strong>
          <small>completeness falls below 20%</small>
        </div>
        <i>→</i>
        <div>
          <span>02</span>
          <strong>AI HEAL</strong>
          <small>Bright Data proposes a repair</small>
        </div>
        <i>→</i>
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
            ← back to market
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
                open market →
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

function Footer({ lastUpdated }: { lastUpdated: Date | null }) {
  return (
    <footer className="footer">
      <span>
        <i className="dot-lime" /> repair trace live
      </span>
      <span>
        {lastUpdated
          ? `last synced ${lastUpdated.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`
          : "Bright Data / Gemini / SQLite"}
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

  const siteOptions = useMemo(
    () => data.collectors.map((collector) => collector.site_name).sort(),
    [data.collectors],
  );
  const page =
    route === "/" ? (
      <LandingPage data={data} navigate={navigate} />
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
          <NavLink
            href="/dashboard"
            label="Control room"
            active={route === "/dashboard"}
            onNavigate={navigate}
          />
          <NavLink
            href="/signals"
            label="Signals"
            active={route === "/signals"}
            onNavigate={navigate}
          />
          <NavLink
            href="/trust"
            label="Trust layer"
            active={route === "/trust"}
            onNavigate={navigate}
          />
          <NavLink
            href="/network"
            label="Network"
            active={route === "/network"}
            onNavigate={navigate}
          />
        </nav>
        <div className="topbar-right">
          <span className="live-indicator">
            <i /> {error ? "signal paused" : "signal live"}
          </span>
          <button
            className="refresh-button"
            type="button"
            onClick={() => void refresh()}
            disabled={loading}
          >
            {loading ? "scanning…" : "scan again"} <span>↗</span>
          </button>
        </div>
      </header>
      <AnimatePresence mode="wait">
        <div key={route}>{page}</div>
      </AnimatePresence>
      {route !== "/dashboard" && (
        <div className="page-footer-wrap">
          <Footer lastUpdated={lastUpdated} />
        </div>
      )}
    </div>
  );
}

export default App;
