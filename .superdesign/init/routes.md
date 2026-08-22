# Routes

Routing is implemented in `frontend/src/App.tsx` with the browser History API.

| URL | Rendered view | Layout |
| --- | --- | --- |
| `/` | `LandingPage` — product story, health summary, route entry cards | `app-shell`, `topbar`, `footer` |
| `/dashboard` | `DashboardPage` — product ledger, search/filter, signal and trust summaries | `app-shell`, `topbar` |
| `/signals` | `SignalsPage` — filterable price-drop/restock desk | `app-shell`, `topbar`, `footer` |
| `/trust` | `TrustPage` — self-healing timeline and incident register | `app-shell`, `topbar`, `footer` |
| `/network` | `NetworkPage` — collector health cards | `app-shell`, `topbar`, `footer` |

`useRoute()` maps `window.location.pathname` to these five routes and calls `history.pushState` for client-side navigation.
