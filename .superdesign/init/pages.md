# Page dependency trees

## `/` — landing

Entry: `frontend/src/App.tsx` → `LandingPage`

- `frontend/src/App.tsx`
  - `frontend/src/api.ts`
  - `frontend/src/types.ts`
  - `frontend/src/styles.css`
  - `framer-motion`

## `/dashboard` — control room

Entry: `frontend/src/App.tsx` → `DashboardPage`

- `frontend/src/App.tsx`
  - `frontend/src/components/DashboardCards.tsx`
    - `frontend/src/components/Sparkline.tsx`
    - `frontend/src/types.ts`
  - `frontend/src/api.ts`
  - `frontend/src/types.ts`
  - `frontend/src/styles.css`

## `/signals` — notices

Entry: `frontend/src/App.tsx` → `SignalsPage`

- `frontend/src/App.tsx`
  - `frontend/src/components/DashboardCards.tsx`
  - `frontend/src/types.ts`
  - `frontend/src/styles.css`

## `/trust` — repair register

Entry: `frontend/src/App.tsx` → `TrustPage`

- `frontend/src/App.tsx`
  - `frontend/src/components/DashboardCards.tsx`
  - `frontend/src/types.ts`
  - `frontend/src/styles.css`

## `/network` — observatory

Entry: `frontend/src/App.tsx` → `NetworkPage`

- `frontend/src/App.tsx`
  - `frontend/src/types.ts`
  - `frontend/src/styles.css`
