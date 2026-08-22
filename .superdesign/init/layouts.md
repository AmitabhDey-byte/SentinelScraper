# Layouts

## `frontend/src/App.tsx` — app shell

The app uses a single React shell with a persistent `topbar`, a manual History API route switch, `AnimatePresence` page transitions, and a footer for non-dashboard routes.

```tsx
return <div className={`app-shell ${route === "/" ? "app-shell-landing" : ""}`}><header className="topbar"><a className="brand" href="/" onClick={(event) => { event.preventDefault(); navigate("/"); }}><span className="brand-orbit"><i /></span><span>sentinel<span>scrape</span></span></a><nav className="nav-links"><NavLink href="/dashboard" label="Control room" active={route === "/dashboard"} onNavigate={navigate} /><NavLink href="/signals" label="Signals" active={route === "/signals"} onNavigate={navigate} /><NavLink href="/trust" label="Trust layer" active={route === "/trust"} onNavigate={navigate} /><NavLink href="/network" label="Network" active={route === "/network"} onNavigate={navigate} /></nav><div className="topbar-right"><span className="live-indicator"><i /> {error ? "signal paused" : "signal live"}</span><button className="refresh-button" type="button" onClick={() => void refresh()} disabled={loading}>{loading ? "scanning…" : "scan again"}</button></div></header><AnimatePresence mode="wait"><div key={route}>{page}</div></AnimatePresence>{route !== "/dashboard" && <div className="page-footer-wrap"><Footer lastUpdated={lastUpdated} /></div>}</div>;
```

The real application source is `frontend/src/App.tsx`; it also contains page implementations for the landing, dashboard, signals, trust register, and network.
