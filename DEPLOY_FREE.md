# ASTRA OS — free demo deployment (Render + DNSExit + Neon)

This deployment uses one Python web service. FastAPI serves both the API and the static frontend from the same origin, so a separate frontend host is not needed.

> Free-tier deployment is suitable for a public demo or early testing, not a production SLA. Render's free web service sleeps after 15 minutes without inbound traffic, can take about a minute to wake, and has an ephemeral filesystem. ASTRA therefore uses an external PostgreSQL database rather than SQLite.

## 1. Push the project to GitHub

1. Create a GitHub repository, preferably private.
2. From the ASTRA OS project root, run:

   ```bash
   git init
   git add .
   git status --short
   ```

3. Confirm that `.env`, `backend/.env`, `*.db`, virtual environments and `backend/data/ephemeris/*.bsp` are not staged. The repository `.gitignore` is set to exclude them.
4. Commit and push the source, including `render.yaml`, to the default branch.

Do not commit database credentials, Stripe secrets, Mapbox tokens or generated user data.

## 2. Create the free PostgreSQL database on Neon

1. Create a Neon account and a PostgreSQL project on its Free plan.
2. Create/open the project and copy its **pooled** connection string from the Connect panel.
3. The ASTRA backend uses Psycopg 3. Change the URL scheme from `postgresql://` to `postgresql+psycopg://` and keep the supplied host, database, username, password and SSL query parameters.

Example shape (not a real credential):

```text
postgresql+psycopg://USER:PASSWORD@HOST-pooler.REGION.aws.neon.tech/DBNAME?sslmode=require
```

Keep this connection string private. You will enter it as `ASTRA_DATABASE_URL` in Render.

Neon's Free plan currently lists 1 GB storage per project, 100 compute-unit hours per project/month, and 5 GB public network transfer per project/month. Compute scales to zero after inactivity, so the first database query after idle may be slower.

## 3. Deploy the Render Blueprint

1. Create/sign in to Render.
2. Choose **New → Blueprint**.
3. Connect the GitHub repository containing `render.yaml`.
4. Render should detect the `astra-os` Python web service and its Free plan.
5. When prompted, set `ASTRA_DATABASE_URL` to the Neon connection string from step 2.
6. Apply the Blueprint and open the service's deploy logs.

The Blueprint does the following:

- installs `backend/requirements.txt`;
- downloads the JPL DE440s ephemeris during the build;
- starts Uvicorn on Render's `$PORT`;
- sets `ASTRA_ENV=production` and a generated secret;
- sets the geocoder provider to Mapbox so production startup does not use the public Nominatim service.

The app can start without a Mapbox token, but **place-name search will return unavailable until you add a Mapbox geocoding token**. Users can still enter latitude, longitude and timezone manually. Add a token later in Render → service → Environment as `ASTRA_GEOCODER_API_KEY`.

Stripe billing is not configured by this Blueprint. Add the Stripe environment variables only after creating and testing your Stripe products/webhook.

## 4. Attach `astraos.run.place` to Render

1. In Render, open the ASTRA OS web service.
2. Open **Settings → Custom Domains → Add Custom Domain**.
3. Enter exactly:

   ```text
   astraos.run.place
   ```

4. Save it. Keep the Render custom-domain screen open; it will show verification status.

Render supports custom domains and automatically provisions/renews TLS certificates for them.

## 5. Point DNSExit DNS to Render

1. Sign in to DNSExit and open DNS management for the `astraos.run.place` zone.
2. Open its DNS records / advanced DNS editor.
3. Add or update this **A record** for the zone root:

   | Field | Value |
   |---|---|
   | Type | `A` |
   | Host / Name | `@` (or blank if DNSExit uses a blank field for the root) |
   | Address / Content | `216.24.57.1` |
   | TTL | Default / Auto |

4. Remove conflicting old `A` records for the root and remove any `AAAA` records for this hostname. Render's current custom-domain instructions say to remove `AAAA` records and use the IPv4 A-record target above for a root domain.
5. Save the record. Do **not** point it at your Kali machine, router or home public IP; Render hosts the app.
6. Wait for DNS propagation, then return to Render and click **Verify**.

Optional `www` hostname: add `www.astraos.run.place` as another custom domain in Render, then create a DNSExit CNAME with Host `www` and Target equal to the exact `*.onrender.com` hostname shown for your ASTRA service. Do this only if you want the `www` address too.

## 6. Verify the live deployment

From Kali/Linux:

```bash
# DNS should resolve the root A record to Render's IP.
dig +short astraos.run.place A

# There should be no stale AAAA answer for the root hostname.
dig +short astraos.run.place AAAA

# App health endpoint should return HTTP 200 and JSON.
curl -i https://astraos.run.place/api/health

# Readiness should return HTTP 200 with all checks true.
curl -i https://astraos.run.place/api/ready
```

Expected health response shape:

```json
{"status":"ok","service":"astra-os","version":"0.1.1"}
```

Then open `https://astraos.run.place`, register a test account, create a chart and save it. Restart/redeploy the service and confirm that the test account and saved chart remain; this verifies the Neon database is actually being used.

## 7. Free-tier limitations and launch checklist

- Render free web services sleep after 15 minutes idle and may take about a minute to wake.
- Render free services have ephemeral filesystems. Do not use local SQLite for hosted user data.
- Render's free Postgres expires after 30 days; this guide uses Neon instead.
- Neon Free currently has monthly compute and transfer quotas. Monitor them in the Neon console.
- The app's public place search needs a configured Mapbox token. Until then, enter coordinates and timezone manually.
- No Stripe billing is active until Stripe keys, a Price ID and the webhook have been configured.
- Before taking payments or storing real customer birth data, add backups/restore tests, email verification and account recovery, rate limiting, security headers, migrations, privacy/retention controls, monitoring and independent security testing.

## 8. Troubleshooting

**Render build fails while downloading DE440s**

Check the build log and retry. The build requires outbound HTTPS access to the JPL ephemeris source. Do not put the `.bsp` file in Git; the build command downloads it into the image/runtime build filesystem.

**Service exits with “Use PostgreSQL” or a SQLite error**

`ASTRA_DATABASE_URL` is missing or not set to Neon. It must start with `postgresql+psycopg://` and must include `?sslmode=require` as provided by Neon.

**Service exits because of secret key**

Confirm `ASTRA_ENV=production` and that Render generated `ASTRA_SECRET_KEY` (at least 32 characters). Do not use the development default.

**Place search returns 503**

Add `ASTRA_GEOCODER_API_KEY` in Render's Environment settings with a valid Mapbox token, then redeploy/restart.

**Custom domain is not verified**

Check that the apex/root A record is `216.24.57.1`, remove stale AAAA records and conflicting root records, then click Verify again in Render.
