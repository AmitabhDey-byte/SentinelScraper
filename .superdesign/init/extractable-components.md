# Extractable components

## AppShell
- Source: `frontend/src/App.tsx`
- Category: layout
- Description: Global background, persistent header, route transition, and optional footer.
- Extractable props: `activeRoute`, `collectorSignal`, `onRefresh`.
- Hardcoded: SentinelScrape mark, global navigation labels, Zeus image background.

## TopBar
- Source: `frontend/src/App.tsx`
- Category: layout
- Description: Brand, primary navigation, live system status, and scan action.
- Extractable props: `activeRoute`, `isLoading`, `isSignalPaused`.
- Hardcoded: navigation labels, Cormorant + DM Mono typography system, brass/rust status colors.

## ProductRow
- Source: `frontend/src/components/DashboardCards.tsx`
- Category: basic
- Description: Listing identity, price, availability, and historical price sparkline.
- Extractable props: `product`, `index`.
- Hardcoded: image/placeholder treatment, site tag, stock treatment.

## AlertCard
- Source: `frontend/src/components/DashboardCards.tsx`
- Category: basic
- Description: Compact price-drop or restock notice.
- Extractable props: `alert`.
- Hardcoded: drop/restock symbols and colors.

## TrustCard
- Source: `frontend/src/components/DashboardCards.tsx`
- Category: basic
- Description: Reliability incident record with narration provenance.
- Extractable props: `incident`.
- Hardcoded: repair glyph and incident metadata treatment.
