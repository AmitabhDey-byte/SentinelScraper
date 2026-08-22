# SentinelScrape

SentinelScrape is a Bright Data Scraper Studio hackathon project for laptop price and inventory intelligence. It makes scraper reliability visible: when a competitor page changes and an extraction field collapses, the dashboard shows the failure, the proposed Bright Data heal, the human approval, the recovery, and the plain-English narration.

## What is tracked

Five laptop listing collectors are supported:

- eBay — `https://www.ebay.com/sch/i.html?_nkw=laptop`
- Newegg — `https://www.newegg.com/p/pl?d=laptop`
- AliExpress — `https://www.aliexpress.com/w/wholesale-laptop.html`
- Target — `https://www.target.com/c/laptops-computers/-/N-5xtdh`
- Flipkart — `https://www.flipkart.com/search?q=laptop`

Each Bright Data collector is asked for product title, price, availability, seller or brand, rating, image URL, and listing URL. Etsy is intentionally not included because it is not a relevant laptop source.

## Self-healing story

The demo is a visible reliability loop:

1. **Site changes.** A listing page changes markup, causing one or more collector fields to become empty.
2. **Detection.** The scheduler runs every collector and compares the new snapshot with the last successful snapshot. A field is marked dropped only when completeness moves from strictly above 80% to strictly below 20%.
3. **Trust Layer incident.** The failed run, row counts, dropped fields, and collector are written to the configured database. The incident appears as open in the `/incidents` API and the dashboard feed.
4. **Heal / approve.** An operator runs the Bright Data AI healing command. The proposed output can be inspected first. `bdata scraper approve` is only called with the explicit `--approve` flag, preserving the human-in-the-loop default.
5. **Recovery.** The healed snapshot is compared to the broken snapshot. Approval is recorded only when at least one dropped field recovers above 80% completeness.
6. **Narration.** Gemini `gemini-2.5-flash-lite` receives a structured JSON schema. Its site, fields, and current row count are validated against the real diff before trust. Any mismatch, malformed response, missing key, or API failure becomes a deterministic report with `narration_source: "fallback"`.

## Repository layout

```text
backend/
  app/api/             FastAPI routes and response models
  app/db/              SQLAlchemy models, session, and metadata
  app/orchestration/   bdata adapter, polling loop, healing workflow
  app/services/        diffing, narration, RAG, search, and intel services
  alembic/              database migrations
  tests/                fake snapshot and narration tests
frontend/              React/Vite dashboard
scripts/                collector bootstrap, scheduler, RAG, search, and battle helpers
.github/workflows/      scheduled run/heal/re-run and weekly intel workflows
```

## Setup

### 1. Install Bright Data CLI and Python dependencies

```bash
npm install -g @brightdata/cli
python -m venv .venv
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

The frontend dependencies are installed separately:

```bash
cd frontend
npm install
cd ..
```

### 2. Configure secrets

Copy `.env.example` to `.env` and set:

```dotenv
BRIGHTDATA_API_TOKEN=your_bright_data_token
# If your CLI installation expects the alternate name, use the same value:
BRIGHTDATA_API_KEY=your_bright_data_token
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini-2.5-flash-lite
# Local demo
DATABASE_URL=sqlite:///./backend/sentinelscrape.db
# Production / Neon
# DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST/DB?sslmode=require
OPERATIONS_API_TOKEN=
```

For the dashboard, copy `frontend/.env.example` to `frontend/.env.local`. It runs as a local observer by default. In production, protect `OPERATIONS_API_TOKEN` at a server-side gateway before exposing collector mutation controls.

Authenticate the `bdata` CLI according to your Bright Data account setup. The application never stores the API token in the database.

### 3. Create the database

Run from the repository root:

```bash
python -m alembic -c backend/alembic.ini upgrade head
```

The migrations create `collectors`, `runs`, `products`, `price_history`, `incidents`, and per-user `favorites`.

### 4. Create the five Scraper Studio collectors

Run from the repository root:

```bash
python scripts/bootstrap_collectors.py
```

This calls `bdata scraper create` once per site and stores each returned `collector_id` in SQLite. Existing site registrations are left unchanged.

## Run the demo

Start the API from `backend/`:

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

In another terminal, run one polling cycle:

```bash
cd backend
python -m app.orchestration.scheduler --once
```

Or keep polling on the configured interval:

```bash
python -m app.orchestration.scheduler
```

Start the dashboard in a third terminal:

```bash
cd frontend
npm run dev
```

Open `http://127.0.0.1:5173`. It is now one responsive, scroll-driven observatory rather than a static dashboard:

- **Landing:** the self-healing loop as the product story.
- **Control room:** paginated market listings with search, market filters, price sparklines, signals, and the Trust Layer.
- **Signals:** a larger impact desk for filtering price drops and restocks.
- **Trust layer / Network:** the full incident trace and per-collector health views.
- **Intelligence:** a Gemini brief that is explicitly grounded in verified price/restock counts and open incidents, plus the existing Search and Docs-RAG APIs for deeper research.
- **Your watchlist:** local saved favorites. Selecting a product opens a quick-glance sheet with price trace, save, share, and retailer controls.

The control room has three core panels:

- **Live listings:** product, latest price, availability, listing link, and price-history sparkline.
- **Alerts:** latest price drops and restocks derived from adjacent observations.
- **Trust Layer:** reverse-chronological incidents with broken fields, recovered fields, row counts, narration, and Gemini/fallback provenance.

### Run the self-healing loop from the UI

The header **Run live scan** and the in-page **Self-healing protocol** both create a persisted Bright Data operation—this is not a browser refresh. The UI polls its transcript while each collector runs. When the detector finds a completeness collapse, it exposes two deliberate controls:

1. **Propose AI heal** calls `bdata scraper heal` with the incident's actual dropped fields and saves the proposal for review.
2. **Approve + verify** calls the Bright Data approval flow, re-runs the repaired collector, writes recovered fields and product observations, then asks Gemini for the guardrailed narration.

For safety, these controls are available to the built-in local observer only in development. Production must set `APP_ENV=production` and protect requests with a server-side `OPERATIONS_API_TOKEN`; do not expose that token in the browser.

The collector-health rail above the panels is intentionally factual: each site is green only when its latest persisted run succeeded and it has no open incident. That gives the demo a compact “wall of checks” without inventing live data.

### Prove detection and recovery locally

Use this safe, no-network proof first. It deliberately removes a field from a fixture, applies the exact `>80% → <20%` detector, then restores it:

```bash
python scripts/demo_self_heal.py --field rating
```

Expected output is `rating` in both `detected` and `recovered`. For a live proof, press **Run Bright Data scan** in local development. The operation panel records the scan; if a field collapses, it offers **Propose AI heal** and then **Approve + verify**. The verification re-runs the repaired collector and only marks the incident healed after the measured recovery.

## Deploy: Render + Neon + Vercel

The repository includes a `Dockerfile` and a free-tier `render.yaml`. Render serves the API, while the included GitHub Actions workflow runs the automatic scan → detect → heal → approve → verify cycle every 30 minutes. Both use Neon, so the public dashboard can display persistent Trust Layer evidence without a paid Render cron service.

1. Create a Neon database and copy its pooled connection string into `DATABASE_URL` using `postgresql+psycopg://...`.
2. In Render, create a Blueprint from this repository. The API uses the Free instance. Fill `DATABASE_URL`, `BRIGHTDATA_API_TOKEN`, `BRIGHTDATA_API_KEY`, `GEMINI_API_KEY`, and a long random `OPERATIONS_API_TOKEN`.
3. After Vercel creates the frontend deployment, set the web service `CORS_ORIGINS` to `https://YOUR-VERCEL-DOMAIN`. Redeploy the API.
4. In Vercel, set the project root directory to `frontend`. Add `VITE_API_BASE_URL=https://YOUR-RENDER-API.onrender.com` and `VITE_MANUAL_OPERATIONS=false`, then deploy.

4. In GitHub Actions, add `DATABASE_URL`, `BRIGHTDATA_API_TOKEN`, and `GEMINI_API_KEY` as repository secrets. The `sentinel-self-heal` workflow is the production scheduler and writes its results to Neon.

Production intentionally makes operation reads public but hides write controls. Visitors can inspect the latest automatic operation and its timestamped transcript, while GitHub Actions owns expensive Bright Data mutations. `OPERATIONS_API_TOKEN` never goes into Vercel or browser code.

## GitHub Actions: scrapers in CI

`.github/workflows/sentinel-self-heal.yml` runs every 30 minutes and can also be started manually. Add `BRIGHTDATA_API_TOKEN`, `GEMINI_API_KEY`, and Neon `DATABASE_URL` as repository secrets, then enable the workflow. Each run:

1. creates or reuses the five collectors;
2. runs the snapshots and checks completeness drift;
3. heals an open incident from the detected field description;
4. explicitly approves the fix in CI mode;
5. re-runs the collectors and fails if an incident remains open;
6. uploads `backend/output/` and writes a run summary to the Actions page.

Local operation remains human-in-the-loop by default. Only the workflow sets `AUTO_APPROVE_HEALS=true`, making the “scrapers in CI, no humans” policy explicit and reviewable.

## Resource track coverage

The project now covers the relevant functionality from resources 04–09:

- **04 — Self-healing scraper:** `scripts/demo_self_heal.py` creates a deterministic field break/recovery proof; the live path uses the detected incident description with `bdata scraper heal`, verifies recovery, approves, and re-runs.
- **05 — Scrapers in CI:** `.github/workflows/sentinel-self-heal.yml` runs the complete loop on a cron and leaves a summary plus collector JSON artifacts.
- **06 — Docs to RAG:** `scripts/build_docs_rag.py` uses Bright Data to fetch a sitemap and pages, chunks them, embeds them with `gemini-embedding-001` when configured, and stores a cited index. `scripts/query_docs.py` and `POST /rag/query` answer with source URLs.
- **07 — Competitive intel:** `scripts/competitive_intel.py` diffs three to five configured competitor pages weekly and can deliver a short update to Slack or Discord. The Monday workflow restores the prior observation baseline from Actions cache before creating the next diff.
- **08 — Keyword-powered agent:** `scripts/keyword_agent.py` and `POST /research` use Bright Data Search with a plain-English keyword, optional country, and search type.
- **09 — Parallel scraper battle:** `scripts/parallel_scraper_battle.py` fans out independent site agents concurrently, scores extraction coverage, and writes a deterministic judge result to `battle.json`.

Set `COMPETITOR_SOURCES_JSON` to a JSON array such as:

```json
[{"name":"Apify","url":"https://apify.com/changelog"},{"name":"Zyte","url":"https://www.zyte.com/changelog/"},{"name":"ScrapingBee","url":"https://www.scrapingbee.com/changelog/"}]
```

## Demonstrate a heal

When an incident is open, inspect it through `GET /incidents` or the Trust Layer. First propose a heal without approval:

```bash
cd backend
python -m app.orchestration.scheduler --heal INCIDENT_ID
```

The healed JSON is written under `backend/output/`, but the incident stays open. Review the output, then run:

```bash
python -m app.orchestration.scheduler --heal INCIDENT_ID --approve
```

The second command runs `bdata scraper heal`, verifies the recovered fields, calls `bdata scraper approve`, upserts the healed products/prices, and narrates the incident. The same workflow is available through `scripts/run_scheduler.ps1`.

## API

- `GET /health`
- `GET /collectors`
- `GET /products?site=eBay&page=1&page_size=8&q=laptop`
- `GET /incidents?page=1&page_size=50`
- `GET /alerts?page=1&page_size=50`
- `GET /me/profile`, `GET /me/favorites`, `PUT|DELETE /me/favorites/{product_id}`
- `GET /insights/market`
- `POST /operations/scan` — authenticated/local-dev live Bright Data collector run
- `POST /operations/incidents/{id}/heal` — create a Bright Data AI heal proposal
- `POST /operations/incidents/{id}/approve` — approve, re-run, verify, and narrate
- `GET /operations/latest`, `GET /operations/{id}` — persisted operational transcript

The paginated endpoints return `{items, page, page_size, total, total_pages}` so the UI can move through the full dataset without loading every listing into the first screen.
- `POST /research`
- `POST /rag/query`

Build a documentation index and query it:

```bash
python scripts/build_docs_rag.py https://docs.example.com/sitemap.xml
python scripts/query_docs.py "How do I authenticate?"
```

Run keyword research or the parallel battle:

```bash
python scripts/keyword_agent.py "best laptop under $800" --country us
python scripts/parallel_scraper_battle.py --sites ebay,newegg,target
```

## Verification

```bash
cd backend
python -m pytest -q
```

The test suite covers the exact 80%/20% threshold behavior, empty-value semantics, wrapped fake snapshots, Gemini schema validation, and deterministic fallback behavior. The frontend production build is checked with:

```bash
cd frontend
npm run build
```
