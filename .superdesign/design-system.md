# SentinelScrape product design system

## Product and jobs

SentinelScrape is a price and inventory intelligence product powered by Bright Data Scraper Studio. Its differentiator is that scraper failures are detected, healed, approved, re-run, and narrated visibly. The product must make three jobs effortless: monitor competitor listings, act on price/restock changes, and trust the self-healing evidence.

The extended product includes a research desk (Bright Data Search), cited docs answers (Sitemap RAG), weekly competitor changelog intelligence, a parallel scraper battle, and a personal watchlist/profile.

## Visual direction

Use the supplied Zeus-and-horse artwork as an atmospheric full-bleed page background below a solid header. The design language is an old-world intelligence observatory: charcoal-black, parchment, bronze, dull umber, and rust. It must feel crafted and editorial, never sci-fi, neon, rounded SaaS, or AI-generic.

No gradients. Use only the following colors:

- Night `#090807`
- Header umber `#17120d`
- Elevated umber `#2a2015`
- Ink `#20160f`
- Parchment `#e9dfcc`
- Light parchment `#f4ecdc`
- Muted parchment `#c6b89e`
- Dusty olive `#8d7a5b`
- Brass `#d2a15a`
- Dark brass `#8d622d`
- Rust `#a95743`

## Typography

- Display, brand, key numbers, and primary navigation: Cormorant Garamond, medium/semibold, expressive but legible.
- Body: DM Sans.
- Metadata, labels, filters, time, and technical evidence: DM Mono.
- Never use all-caps for primary navigation; labels may use small uppercase mono with wide letter spacing.

## Layout

- Persistent solid header; no background artwork behind it.
- A scroll-story home view with anchors for Overview, Market Ledger, Signals, Trust, Intelligence, and Network. Desktop has generous negative space and editorial columns; mobile becomes one-column without clipped controls.
- Parchment data panels are sharply edged with thin dark-brass borders and isolated to preserve readable contrast over the art.
- Product interaction is a floating detail sheet rather than a navigation interruption. It contains price, stock, trend, full sparkline, seller/site, favorite, share, and an external open action.
- Profile/favorites are personal, quiet, useful areas—not avatar decoration.

## Motion

- Use Framer Motion only for intent-revealing motion: scroll-progress indicator, 160–260ms detail-sheet entrance, button press, card lift of 2–4px, and staggered list reveal.
- Respect `prefers-reduced-motion`.
- No looping decorative animation, no parallax that hurts text readability, no gradient animation.

## Icons and symbols

Use simple monochrome Unicode or hand-drawn-line symbols: `⌕` search, `⌘` command/research, `✦` recovery evidence, `♧` favorite, `⤢` open externally, `⧉` copy/share, `↓` price drop, `●` status. Avoid textual arrows in navigation or button labels.

## Functional UX requirements

- Current Bright Data collector health, product data, alerts, incidents, and raw self-heal proof stay first-class.
- The docs RAG and keyword research APIs must be visible in an Intelligence section with answer citations and research result cards.
- Personal favorites persist per authenticated Clerk user in Neon/Postgres; a local demo fallback is acceptable only when no Clerk configuration exists.
- Provide an explicit no-data/connection state with a direct retry action.
- Make the intended production stack clear: Neon `DATABASE_URL`, Clerk publishable key and JWT verification settings, Bright Data token, and Gemini key.
