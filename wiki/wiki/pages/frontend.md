---
title: Frontend (React UI)
tags: [frontend, react, typescript, charts]
sources: [frontend-src]
updated: 2026-06-14
---

# Frontend

## Stack

React 19, TypeScript, Vite, Tailwind CSS v4, Recharts, TanStack Query (data fetching), TanStack Table (sortable tables). Served as a static SPA from an Nginx container.

## Pages

| Route | File | Description |
|---|---|---|
| `/runs` | `RunsListPage.tsx` | Sortable table of all simulation runs with tags, terminal net worth, ruin status |
| `/runs/:id` | `RunDetailPage.tsx` | Full detail: net worth & debt, free cash flow, portfolio composition, income stack, tax analysis |
| `/mc` | `McListPage.tsx` | List of MC run sets with ruin probability and P50 terminal wealth |
| `/mc/:id` | `McDetailPage.tsx` | Fan chart (P10–P90), ruin probability gauge, terminal wealth distribution |
| `/compare?ids=1,2,3` | `ComparePage.tsx` | Side-by-side net worth comparison across up to three runs |
| `/config` | `ConfigPage.tsx` | Live editor for `config.json` and all asset JSON files |

## Chart Components (`frontend/src/components/charts/`)

| Component | Description |
|---|---|
| `NetWorthChart.tsx` | Net worth and debt over time |
| `FreeCashFlowChart.tsx` | Monthly free cash flow trajectory |
| `PortfolioChart.tsx` | Portfolio composition over time |
| `IncomeStackChart.tsx` | Income by source (stacked area) |
| `TaxAnalysisChart.tsx` | Taxes paid per period |
| `McFanChart.tsx` | Monte Carlo percentile bands (P10–P90) |
| `TerminalWealthDist.tsx` | Terminal wealth histogram |

## Layout

`AppShell.tsx` — top-level shell with navigation.

## API Client (`frontend/src/api/`)

| File | Covers |
|---|---|
| `client.ts` | Base Axios instance; reads `VITE_API_URL` |
| `runs.ts` | `/api/runs` endpoints — `useRuns`, `useRun`, `useRunAssets`, `useRunTax` |
| `mc.ts` | `/api/mc` endpoints |
| `configuration.ts` | `/api/configuration` endpoints — `useWorldConfig`, `useSaveWorldConfig`, `useAssets`, `useSaveAsset`, `useDeleteAsset` |

## Type Definitions (`frontend/src/types/`)

| File | Types |
|---|---|
| `runs.ts` | `RunSummary`, `RunDetail`, `AssetMetricRow`, `TaxRow` |
| `mc.ts` | `McRunSet`, `McDetail`, `PercentileBand` |
| `configuration.ts` | `WorldConfig`, `TaxClasses`, `EquityAsset`, `RealEstateAsset`, `SalaryAsset`, `Asset`, `AssetFile` |

## Configuration Page (`/config`)

`ConfigPage.tsx` is a single-page live editor for all model configuration files. It has two sections:

**World Configuration** — edits `configuration/config.json` in place. Fields are grouped into four sections:
- *Personal*: birth dates (owner + spouse), retirement age, RMD age, simulation start/end dates
- *Savings & Withdrawals*: savings rate, Roth savings rate, withdrawal rate, inflation rate
- *Portfolio Allocation*: stock and bond allocation with real-time validation (must sum to 1.0; Save is blocked if not)
- *Tax Rates*: income, capital gains, social security, roth (read-only, always 0.0)

Save triggers a `PUT /api/configuration` call; the button flashes a ✓ for 2 seconds on success.

**Assets** — reads all files from `configuration/assets/` via `GET /api/configuration/assets`. Displays a card grid:
- Each card shows the asset type badge (Equity / RealEstate / Salary), name, description, a summary stat line, and the filename.
- *Edit* opens a modal pre-filled with the asset's current values.
- *Delete* shows a confirmation dialog before calling `DELETE /api/configuration/assets/<filename>`.
- *New Asset* button: choose type (Equity / RealEstate / Salary), fill type-specific fields, filename auto-generated from name (slugified) or manually overridden.

Type-specific modal fields:
- **Equity**: initial value, expense ratio, appreciation rate + volatility, dividend rate, optional SP500 CSV path
- **RealEstate**: current value and debt, appreciation, property tax, insurance, management fee, rental income and expense rate, mortgage interest rate and monthly payment
- **Salary**: annual salary (optional), COLA rate, initial debt, and a dynamic age → monthly-benefit table editor (for Social Security age-based claiming amounts)

`start_date` and `end_date` on assets are always placeholder strings (`first_date`, `end_date`, `retirement`) — rendered as dropdowns, not date pickers.

## Dev Server

```bash
cd frontend
npm install
npm run dev    # http://localhost:5173
```

Vite proxies `/api` and `/health` to `localhost:8000` (the Flask dev server).

## Production Build

```bash
cd frontend
npm run build  # outputs to frontend/dist/
```

Built into `frontend/Dockerfile.frontend` and served by Nginx static file server.

## Related

- [[rest-api]] — API endpoints the frontend consumes
- [[deployment]] — how the frontend container is built and served

---
