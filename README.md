# GB Wind Forecast Decision Support Portal

A quantitative decision-support system for Great Britain (GB) day-ahead power trading. It answers one question for a trading desk: **given the wind forecast we could legally see at 09:00 on D-1, what should we buy for tomorrow, and how wrong might we be?**

The project is split across two repositories, and this README describes both:

| Repository | Role | Stack |
|---|---|---|
| [`analysis-tool-backend`](https://github.com/iyin141/analysis-tool-backend) | Data ingestion, forecast selection, error metrics, REST API | Python 3.13, FastAPI, pandas, NumPy, Parquet |
| [`analysis-tool-frontend`](https://github.com/iyin141/analysis-tool-frontend) | Four-page analyst portal (charts, KPI cards, methodology) | React 19, TypeScript, Vite, Tailwind, Recharts, TanStack Query, Zod |

```
 Elexon BMRS (WINDFOR, FUELHH)
          │  scripts/ingest.py  or  POST /admin/refresh
          ▼
 Parquet files (committed)  ──►  FastAPI backend (:2847)  ──►  React frontend (:5173)
 22,776 forecasts                services + metrics            4 pages, Zod-validated
  1,493 actuals                  /api/v1/*                      responses
```

---

## 1. What problem does this solve?

### The market
UK electricity suppliers must match their customers' demand in each of the 48 half-hour settlement periods of tomorrow (delivery day **D**). Power can't be stored cheaply, so suppliers buy ahead on wholesale day-ahead auctions (EPEX SPOT and Nord Pool).

### The wind problem
Wind often supplies 10–18 GW, which can be over half of GB demand. National Grid ESO publishes rolling half-hourly wind forecasts (Elexon dataset `WINDFOR`), but wind is volatile. If the forecast is wrong:

- **Over-forecast (wind falls short).** You forecast 12,000 MW and got 10,000 MW. You're 2,000 MW short, and the Balancing Mechanism covers the gap at the System Buy Price. In tight winter periods that can reach £1,000–£4,000/MWh.
- **Under-forecast (wind overshoots).** You over-bought thermal power and sell the surplus back at distressed or negative prices.

### The gate-closure constraint
The EPEX SPOT GB day-ahead order book closes at **09:20 UK time** on D-1, so desks freeze their generation assumptions at about **09:00 D-1**. The portal evaluates only what was knowable at that moment.

### What the portal does
Built on audited January 2026 Elexon BMRS data (22,776 forecast records, 1,493 actual-generation outturns), it:

1. **Guarantees zero look-ahead bias.** Only forecasts with `publishTime <= cutoff` are used.
2. **Shows honest uncertainty bands (P10–P90)** derived from *prior* delivery days only.
3. **Quantifies asymmetric risk.** It measures bias, diurnal weak spots, and the probability of large shortfalls (> 1,000 MW).
4. **Quantifies the value of waiting.** It models error decay from 0 to 72 hours of lead time, to show what committing early at D-1 09:00 costs in accuracy.

> **A note on numbers.** Figures such as "11,609.6 MW", "+214 MW bias" or "68.4% error reduction" in the tables below are illustrative examples used to explain each KPI. The live values come from the API and depend on the data and filters selected.

---

## 2. Sign convention

Everything follows one definition:

```
error = forecast − actual
```

- **Positive error** → wind under-generated vs forecast → the desk was **short** (cash-out exposure).
- **Negative error** → wind over-generated vs forecast → the desk was **long**.

---

## 3. The four pages

### Page 1 — Day-Ahead Decision View (`/`)
*Trading desk goal: "It's 09:00 on D-1. What's tomorrow's baseline wind profile, how risky is it, and how much non-wind power must we buy?"*

**Filters:** Delivery Date (YYYY-MM-DD) and Decision Cutoff (HH:MM, default 09:00 London time; the UI offers 07:00–12:00).

| KPI | Definition | Commercial meaning |
|---|---|---|
| **Day Avg Wind Forecast** (with peak) | `(1/48) Σ ŷᵢ` over the frozen forecast | Low-wind day (tight, expensive) vs gale day (saturated, cheap) |
| **Total Expected Generation** (with actual) | `Σ ŷᵢ × 0.5 h` in MWh | Procurement target: demand minus expected wind = non-wind volume to buy |
| **Decision Cutoff (D-1)** | The local time the data was frozen | Auditability: proves only eligible information was used before gate closure |
| **Forecast Vintage Used** | Publish time of the latest forecast used | Data freshness; a stale vintage means weather-front changes may have been missed |
| **Uncertainty Interval (80%)** | `ŷᵢ − P90 ≤ yᵢ ≤ ŷᵢ − P10` using prior-day errors | Sizing standby reserve (peakers, batteries) |

**Chart and table (48 settlement periods):** the blue line is the frozen forecast, the green line is metered actuals, and the shaded area is the P10–P90 band. The table lists per-period error. If the green line stays inside the band, the hedge worked without overpaying for reserve.

### Page 2 — Quantitative Accuracy Dashboard (`/accuracy`)
*Risk manager goal: "How reliable is the forecast over time? Is there systematic bias, a diurnal blind spot, or tail risk to protect against?"*

**Filters:** date range, overshoot threshold (default 1,000 MW), histogram bin width (default 250 MW).

| KPI | Definition | Commercial meaning |
|---|---|---|
| **MAE** (with RMSE) | `(1/n) Σ│eᵢ│` | Typical volume miss per half-hour; sizes the intra-day balancing buffer |
| **Forecast Bias** | `(1/n) Σ eᵢ` | Systematic tendency. A positive bias means over-forecasting, so shave the raw forecast before bidding |
| **nMAE** (with guarded MAPE) | `MAE / mean(actual) × 100` | Season- and portfolio-independent quality benchmark |
| **Under-Procurement Risk (> X MW)** | `count(e > X) / n` | Tail-risk probability of hitting extreme cash-out prices |
| **Error Spread (P10 / P50 / P90)** | Empirical percentiles of `e` | Shows asymmetry; a fatter P90 than P10 means skew toward dangerous shortfalls |

**Charts:**
- **Daily error trend:** MAE and bias per delivery day.
- **Error distribution:** histogram with mean, standard deviation and skewness. It shows fat tails rather than a Gaussian assumption.
- **Accuracy by hour of day (00–23):** shows where ramp-period errors cluster.
- **Error by wind-generation tier:** 0–3, 3–7, 7–11, 11–15 and 15+ GW. Error is not uniform. High-wind regimes (e.g. turbine high-wind cut-off) are harder to predict.

### Page 3 — Horizon Explorer (`/horizon`)
*Desk lead goal: "What does committing at D-1 09:00 cost in accuracy, and what would waiting for intra-day gain us?"*

Unlike the other pages, this one evaluates **all forecast vintages** (not just the as-of-cutoff one), binned by **lead time** = `startTime − publishTime`, from 0 to 72 hours.

| KPI | Meaning |
|---|---|
| **Ultra Short-Term MAE (0–3 h)** | Best-case, near-real-time accuracy ceiling |
| **Day-Ahead Horizon MAE (24–27 h)** | The accuracy the desk accepts by committing on D-1 morning |
| **Value of Waiting** | `(MAE₄₈ₕ − MAE₃ₕ) / MAE₄₈ₕ × 100`, the relative error reduction from waiting |
| **Analyzed Forecast Vintages** | Sample size behind the curve |

**Reading the decay chart:** errors are large at 48–72 h, fall steeply through the day-ahead window, and are smallest at 0–6 h. The D-1 09:00 decision sits near the "elbow": most of the weather-model improvement is captured while still trading in the deepest, most liquid auction.

### Page 4 — Methodology & Guide (`/methodology`)
*Auditor / compliance goal: "What are the rules, formulas and governance behind these numbers?"*

Covers the GB day-ahead market and gate closure, the as-of-cutoff (zero look-ahead) selection logic, each metric's formula, the guarded-MAPE rule (actuals < 50 MW excluded), the out-of-sample band construction (`bandIsInSample` flag), and the Elexon Insights API sources.

---

## 4. Backend — `analysis-tool-backend`

FastAPI service that loads two Parquet files into memory at startup and serves all analytics.

### Layout
```
app/
  main.py                 App factory, CORS, router registration, lifespan (loads data)
  core/                   config.py (pydantic-settings), exceptions.py, error_handlers.py, logging.py
  api/
    deps.py               Dependency providers for services and the Elexon client
    routers/              health, delivery_days, forecast, accuracy, horizon, admin
  clients/elexon_client.py  Async httpx client for Elexon with retry/backoff
  services/
    cutoff.py             As-of-cutoff forecast selection (the zero look-ahead core)
    forecast_selection.py Decision view assembly + out-of-sample P10/P90 band
    metrics.py            Accuracy summary, by-hour, distribution, by-wind-level
    horizon.py            Lead-time error decay across all vintages
    data_repository.py    Parquet load/save + schema standardisation (in-memory pandas)
  utils/                  time.py (London↔UTC, slots), stats.py (metrics, histogram)
  schemas/                Pydantic response models (camelCase over the wire)
  models/domain.py        Canonical DataFrame column names (`Col`)
  data/                   fuelhh_wind_jan2026.parquet, windfor_jan2026.parquet
scripts/ingest.py         One-off Elexon ingestion to Parquet
tests/                    pytest: API endpoints, cutoff, metrics, schemas, timezone
```

### How the key logic works

**As-of-cutoff selection (`services/cutoff.py`).** For delivery day D:
1. Compute the cutoff as D-1 at the chosen local time in `Europe/London`, converted to UTC (DST-aware).
2. Build the full list of half-hour slots for D (48 normally; 46/50 on clock-change days).
3. Keep only forecasts with `publish_time <= cutoff`.
4. For each slot take the **latest** such vintage, and left-join onto the slots so missing periods stay `NaN` instead of being dropped.

**Uncertainty band (`services/forecast_selection.py`).** Errors are collected from delivery days strictly *before* D, and their P10/P90 give the band `[forecast − P90, forecast − P10]`, clamped at 0 MW. If fewer than 3 prior days exist, it falls back to all available days and sets `bandIsInSample: true` so the UI can say so honestly.

**Metrics (`utils/stats.py`).** Bias, MAE, RMSE, nMAE, guarded MAPE (actuals > 50 MW only), P10/P50/P90 of error, overshoot probability `P(e > threshold)`, plus histogram binning and skewness.

**Horizon analysis (`services/horizon.py`).** Joins every forecast vintage to actuals, keeps lead times in [0, 72] h, bins by `horizonBinHours` (default 3), and computes bias/MAE/RMSE per bin.

### API
Served at the root (`/health`) and under `/api/v1`. Interactive docs are at `/docs`.

| Method & path | Purpose | Key params |
|---|---|---|
| `GET /api/v1/health` | Status, version, data last-updated | — |
| `GET /api/v1/delivery-days` | Available days, default cutoff, timezone | — |
| `GET /api/v1/forecast/decision-view` | 48-point frozen forecast, actuals, band, summary | `deliveryDate`, `cutoffTime` |
| `GET /api/v1/accuracy/summary` | Aggregate metrics + per-day breakdown | `from`, `to`, `cutoffTime`, `overshootThresholdMw` |
| `GET /api/v1/accuracy/by-hour` | 24-hour diurnal profile | `from`, `to`, `cutoffTime` |
| `GET /api/v1/accuracy/distribution` | Error histogram + stats | `from`, `to`, `cutoffTime`, `binWidthMw` |
| `GET /api/v1/accuracy/by-wind-level` | Accuracy by generation tier | `from`, `to`, `cutoffTime` |
| `GET /api/v1/horizon/analysis` | Error vs lead time | `from`, `to`, `horizonBinHours` |
| `POST /api/v1/admin/refresh` | Re-pull FUELHH/WINDFOR from Elexon and overwrite Parquet | — |

Errors use one envelope: `{"error": {"code", "message", "details"}}` with codes `INVALID_PARAMETER` (400), `NOT_FOUND` (404), `UPSTREAM_ERROR` (502), `DATA_UNAVAILABLE` (503) and `INTERNAL_ERROR` (500).

### Data sources
- **Actuals:** Elexon `FUELHH` stream filtered to `fuelType == "WIND"`.
- **Forecasts:** Elexon `WINDFOR` stream (all published vintages). Ingestion starts from 2025-12-25 so that D-1 cutoffs for 1 January are covered.

### Run it
```bash
cd analysis-tool-backend
cp .env.example .env
pip install -r requirements.txt
uvicorn app.main:app --reload --port 2847   # docs at http://localhost:2847/docs

# or with Docker
docker compose up --build                   # serves on :2847

# tests
pytest

# optional: re-ingest data from Elexon
python scripts/ingest.py
```

**Configuration (`.env`):** `TIMEZONE`, `DEFAULT_CUTOFF_LOCAL_TIME`, `ELEXON_BASE_URL`, `ELEXON_TIMEOUT_SECONDS`, `ELEXON_MAX_RETRIES`, `DELIVERY_FROM`, `DELIVERY_TO`, `CORS_ORIGINS`. The January 2026 Parquet files are committed, so the API works offline.

---

## 5. Frontend — `analysis-tool-frontend`

Single-page React app. Each page lives in `src/features/*`, fetches through typed hooks, and validates every API response with Zod before rendering.

### Layout
```
src/
  main.tsx, App.tsx          Entry; QueryClientProvider + RouterProvider
  routes/AppRoutes.tsx       / and /decision-view, /accuracy, /horizon, /methodology
  features/
    decision-view/           Page 1
    accuracy/                Page 2
    horizon/                 Page 3
    methodology/             Page 4
  api/                       axios client + per-resource functions + typed error classes
  schemas/                   Zod schemas mirroring backend response models
  hooks/                     TanStack Query hooks (useDecisionView, useAccuracy, useHorizon, …)
  components/
    layout/                  AppLayout, Sidebar (slide-over nav), TopNavbar
    shared/                  Card, KpiCard, DatePicker, CutoffSelect, States, ChartContainer
  config/                    env.ts (Zod-validated env), constants.ts, color.ts
  lib/format.ts              MW / MWh / % / date / time formatters (Europe/London)
  types/index.ts             Types inferred from the Zod schemas
```

### Design notes
- **Runtime-validated contracts.** `parseOrThrow` runs each response through its Zod schema, so backend drift fails loudly instead of rendering wrong numbers.
- **Normalised errors.** The axios interceptor converts failures into `NetworkError`, `HttpError` (with the backend's `code`/`message`/`details`) or `ValidationError`, and pages show a retryable `ErrorState`.
- **Caching.** TanStack Query with a 60 s stale time per query (5 min for delivery days), no refetch on window focus, one retry.
- **Charts.** Recharts: composed/area charts for the 48-period profile with the P10–P90 band, histograms, and bar/line charts for hour, tier and horizon views.
- **Styling.** Tailwind with a navy/green palette defined in `config/color.ts`.

### Run it
```bash
cd analysis-tool-frontend
cp .env.example .env
npm install
npm run dev        # http://localhost:5173
npm run build      # type-check + production build
```

**Configuration (`.env`):** `VITE_API_BASE_URL`, `VITE_DEFAULT_FROM_DATE`, `VITE_DEFAULT_TO_DATE`, `VITE_DEFAULT_CUTOFF_TIME`, `VITE_DEFAULT_DELIVERY_DATE`, `VITE_TIMEZONE`, `VITE_APP_NAME`.

> **Port alignment.** The backend Dockerfile and compose file serve on **2847**, but `frontend/.env.example` and the Vite dev proxy point to **localhost:8000**. When running both locally, either start the backend with `--port 8000` or set `VITE_API_BASE_URL=http://localhost:2847/api/v1` (and update the proxy target in `vite.config.ts`).

---

## 6. Key takeaways for presentations

1. **Market reality.** Binding D-1 09:00 decisions on EPEX SPOT carry £1,000+/MWh imbalance exposure.
2. **Zero look-ahead integrity.** Every metric is strictly as-of-cutoff. No future data leaks into past decisions.
3. **Honest uncertainty bands.** Empirical, out-of-sample P10–P90 corridors from prior delivery days, not idealised bell curves.
4. **Asymmetric risk discovery.** Bias, ramp-hour weakness and high-wind-tier vulnerability point to where defensive bidding is needed.
5. **Optimal timing.** The Horizon Explorer shows how much of the forecast-error decay D-1 09:00 captures while keeping access to day-ahead auction liquidity.

---

## 7. Scope and limitations

- Data scope is **January 2026** only. Several code paths (delivery-day listing, the historical band) are hard-wired to `2026-01*`.
- Data is served from in-memory pandas frames loaded from Parquet; there is no database.
- `POST /admin/refresh` has no authentication and overwrites the Parquet files, so it should be protected or disabled in any shared deployment.
- Metrics describe historical forecast quality. They are decision *support*, not a guarantee of future performance or trading advice.

---

*This project was built with AI.*
