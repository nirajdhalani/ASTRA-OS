# ASTRA OS — Astrology Intelligence Web App

ASTRA OS is a web-first commercial SaaS foundation for Vedic Jyotish, Western tropical astrology, KP and Jaimini. It is implemented as a FastAPI backend plus a responsive vanilla-JavaScript frontend. The frontend is served by the API server; no Node build step is required.

## v0.1.1 patch notes

- Fixed DE440s Mars lookup: this kernel exposes `MARS BARYCENTER` (target 4), not a direct `MARS` target. The provider now resolves planet targets from the names actually available in the loaded kernel and validates them once at startup.
- Added regression tests for the DE440s target set, alternate kernels that expose a direct Mars target, missing-target errors and the complete planetary-position iteration.

## What is implemented in v0.1.1

- Account registration, sign-in, signed bearer tokens, per-user chart storage and a configurable free-plan quota (3 saved charts by default).
- Birth input with coordinates and IANA timezone; historical timezone conversion; explicit rejection of daylight-saving gaps and a required `fold` choice for repeated local times.
- Skyfield + JPL DE440s apparent geocentric planetary positions for Sun through Pluto, plus mean lunar nodes.
- Tropical Western chart support and sidereal Vedic/KP/Jaimini chart conventions.
- Lahiri, KP, Raman, Fagan–Bradley and tropical offset choices (see calculation caveats below).
- Ascendant, Midheaven, 12 house cusps, Whole Sign, Equal and a first-pass Placidus implementation.
- 16 divisional chart outputs: D1, D2, D3, D4, D7, D9, D10, D12, D16, D20, D24, D27, D30, D40, D45 and D60.
- Nakshatra/pada, basic Panchang, Vimshottari Mahadasha and Antardasha timeline, recalculated against the analysis timestamp (including when reopening a saved report).
- Western major aspects; Parashari graha drishti; KP nakshatra sub-lords; Jaimini Chara Karakas and Rashi Drishti.
- Rule-based structural matches for selected yogas/doshas, with evidence and caveats.
- 18 life-domain evidence reports, including career, money, fame, love, marriage, health, legal/disputes, family, children, education, property, foreign travel, spirituality, competition and business.
- Stripe Checkout/subscription webhook integration, activated by environment variables.
- English, Hindi and Gujarati UI translations.

## Not included in this initial release

- AI chat / hosted LLM narrative generation; the current life reports are deterministic chart-factor evidence cards, not free-form predictions.
- Transit-based daily/monthly/yearly or 5-/10-year forecasting, Sade Sati analysis and event-date probability scores.
- Full Shadbala, Ashtakavarga, Bhava Chalit, full classical yoga/dosha catalogue, remedies catalogue, marriage compatibility and multi-chart synastry.
- PDF report export, password reset, email verification, admin moderation, customer portal, tax handling, database migrations and distributed abuse/rate-limit controls.

These are planned extension areas, not secretly stubbed endpoints. The code does not advertise them as shipped features.

## Important calculation boundaries

1. **No 100% life-event accuracy claim.** Planetary positions can be calculated reproducibly under a specified ephemeris and convention. Astrology does not have established empirical validity as a method for determining court outcomes, health diagnoses, wealth, marriage dates or other future events. ASTRA reports chart factors and rule matches rather than presenting them as guaranteed facts.
2. **Ephemeris date coverage.** DE440s covers approximately 1849–2150. Birth dates outside that range are rejected. The JPL kernel is downloaded on first setup and is about 32 MB. See [Skyfield's JPL ephemeris guide](https://rhodesmill.org/skyfield/planets).
3. **Ayanamsa models.** The included Lahiri, KP and Raman implementations are transparent polynomial/offset approximations, not yet parity-certified against a named commercial ephemeris build. Fagan–Bradley is a fixed-difference approximation. Do not market cross-software arcsecond agreement until the models are independently fixture-tested and versioned.
4. **House systems.** Whole Sign and Equal are deterministic. Placidus is a first-pass numerical solver and rejects high latitudes; it must pass a larger reference-fixture comparison before being treated as release-grade KP house-cusp parity.
5. **Varga and yoga doctrines differ by school.** Each configured formula is a named convention, not a universal verdict. The current D30 and some higher varga implementations need comparison against authoritative reference charts before public launch.
6. **Mean lunar node only.** Ketu is calculated exactly opposite the mean Rahu node. A true-node model is not included in this release.
7. **Place search.** Development defaults to public Nominatim with caching and a one-request-per-second limiter. The public Nominatim service has strict limits, requires clear OpenStreetMap attribution and is not an appropriate scaling dependency for a commercial SaaS. Its limiter is shared by the app process; do not use the public endpoint as a multi-instance production service. The code supports `ASTRA_GEOCODER_PROVIDER=mapbox` plus `ASTRA_GEOCODER_API_KEY` for Mapbox, or `nominatim` for development. Use a contractually suitable commercial plan or self-hosted service before public launch.
8. **Timezone polygon data.** `timezonefinder` is MIT-licensed, while its separately distributed timezone boundary dataset is ODbL. Review attribution/share-alike obligations for your deployment.

## Stack

- Python 3.12+ (tested design target; Python 3.13 is supported by the selected dependencies)
- FastAPI + Pydantic
- SQLAlchemy + SQLite for local development; PostgreSQL + psycopg driver for production
- Skyfield + NASA/JPL DE440s
- `timezonefinder` + Python `zoneinfo`/`tzdata`
- Vanilla JavaScript, HTML and CSS
- Stripe Python SDK for paid subscriptions

## Quick start (clean machine)

### 1. Install Python

Install Python 3.12 or 3.13. On Windows, use PowerShell; on macOS/Linux, use a shell.

### 2. Create an environment and install dependencies

```bash
cd astra-os/backend
python -m venv .venv
```

Activate it:

```bash
# macOS / Linux
source .venv/bin/activate

# Windows PowerShell
.venv\\Scripts\\Activate.ps1
```

Install:

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Configure environment

```bash
# macOS / Linux
cp .env.example .env

# Windows PowerShell
Copy-Item .env.example .env
```

Set `ASTRA_SECRET_KEY` to a random value before exposing the service. For example:

```bash
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

Copy the result into `.env`.

### 4. Download JPL DE440s

```bash
python scripts/download_ephemeris.py
```

This step needs network access once. The kernel is cached under `backend/data/ephemeris/` afterwards.

### 5. Start the app

Run from `backend/`:

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Open <http://127.0.0.1:8000>. API documentation is at <http://127.0.0.1:8000/docs>.

### 6. Smoke test (under one minute)

```bash
curl http://127.0.0.1:8000/api/health
```

Expected response:

```json
{"status":"ok","service":"astra-os","version":"0.1.1"}
```

Create an account in the UI, then enter a birth date/time/place. For Junagadh, Gujarat, India, a reasonable city-centre coordinate is latitude `21.5222`, longitude `70.4579`, timezone `Asia/Kolkata`; verify the actual birthplace pin for a production chart.

## Tests

Run from `backend/`:

```bash
python -m pytest -q
```

The tests exercise Julian-day conversion, sign/nakshatra boundaries, timezone/DST handling, house geometry safeguards, Vimshottari structure, chart-service output contracts, account/auth APIs and the free chart quota. Ephemeris-provider integration against the downloaded DE440s kernel is a separate live-data check and must be run after the kernel has been downloaded. `/api/health` checks process liveness; `/api/ready` reports whether Skyfield, timezonefinder and the ephemeris file are present.

## API overview

- `POST /api/auth/register`
- `POST /api/auth/login`
- `GET /api/auth/me`
- `GET /api/geocode?query=...`
- `GET /api/timezone?latitude=...&longitude=...`
- `POST /api/charts/preview`
- `POST /api/charts`
- `GET /api/charts`
- `GET /api/charts/{id}`
- `DELETE /api/charts/{id}`
- `POST /api/billing/checkout`
- `POST /api/billing/webhook`
- `GET /api/health` (liveness)
- `GET /api/ready` (calculation dependency readiness)
- `GET /api/meta`

All chart endpoints require a bearer token. The preview endpoint does not save the chart; the create endpoint recalculates and stores it. In production, add email verification, account recovery, distributed login/geocoding rate limits, database migrations, audit logging, encrypted backups, data-retention controls, privacy disclosures, tax/VAT handling, CSP/secure session design and an independent security review before accepting paying customers. Production startup refuses the default secret, SQLite and public Nominatim.

## Stripe setup

Create a recurring monthly Price in Stripe and set:

- `STRIPE_SECRET_KEY`
- `STRIPE_PRICE_ID_PRO_MONTHLY`
- `STRIPE_WEBHOOK_SECRET`
- `STRIPE_SUCCESS_URL`
- `STRIPE_CANCEL_URL`

Register the webhook endpoint `/api/billing/webhook` for checkout completion, subscription updates and subscription deletion. Checkout metadata is also propagated to the Stripe Subscription so later status updates can locate the ASTRA account. Use Stripe test mode first. The app intentionally returns `503` while billing is not configured. Free accounts can save three charts by default; set `ASTRA_FREE_CHART_LIMIT` to change the quota. Pro accounts bypass this saved-chart limit.

## Commercial deployment checklist

- Replace the development geocoder with a commercial provider (for example Mapbox/Google) or a self-hosted service; configure `ASTRA_GEOCODER_PROVIDER=mapbox` and `ASTRA_GEOCODER_API_KEY`, or a self-hosted service.
- Review Skyfield's MIT license, the JPL kernel provenance, and the ODbL timezone data notices.
- Run against a curated independent fixture set for known planetary longitudes, ascendants, house cusps, divisional placements, ayanamsa, nodes and dasha boundaries.
- Version every doctrinal rule and expose its reference, formula, exceptions and cancellation rules in the report.
- Add PostgreSQL, migrations, rate limiting, CSRF policy if cookie auth is added, CSP, secure cookies if used, TLS, observability and backup/restore tests.
- Do not claim "0% false positives" for interpretations. The app can guarantee deterministic rule matching only for the implemented rules and declared input/model version.

## Sources and dependency notices

- Skyfield documentation and JPL ephemeris selection: <https://rhodesmill.org/skyfield/planets>
- Skyfield source license (MIT): <https://github.com/skyfielders/python-skyfield/blob/master/LICENSE>
- Python `zoneinfo`: <https://docs.python.org/3/library/zoneinfo.html>
- `timezonefinder` code/data licenses: <https://timezonefinder.readthedocs.io/en/latest/3_about.html>
- Nominatim usage policy: <https://operations.osmfoundation.org/policies/nominatim/>
- Stripe Checkout: <https://docs.stripe.com/payments/checkout>

## Project status

This is an executable v0.1.1 foundation, not a production-certified astrology product. The backend and frontend are implemented; the local environment used to assemble this bundle had no outbound network access, so external dependencies and the DE440s kernel could not be downloaded or live-verified here. The source tests can be run after installing `requirements.txt`; chart generation additionally requires the kernel download step.
