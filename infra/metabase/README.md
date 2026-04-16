# Metabase: Self-Hosted BI Stack

Self-hosted Metabase (Open Source edition) deployed via Docker Compose with a
dedicated Postgres metadata store. Connects to Snowflake as a data source for
portfolio analytics dashboards.

## Architecture

```
Browser (localhost:3000)
        ↓
┌───────────────────────────┐
│  metabase container       │ ──→ Snowflake (external, via native driver)
│  (Metabase OSS)           │
└───────────────────────────┘
        ↓
┌───────────────────────────┐
│  metabase-postgres        │  (internal only, no host port exposure)
│  (application database:   │
│   users, dashboards,      │
│   connection settings)    │
└───────────────────────────┘
```

Two containers on a private Docker network. Only Metabase's web UI is exposed
to the host (port 3000). The metadata Postgres is reachable only from within
the Docker network, following least-privilege production patterns.

## Prerequisites

- Docker Engine 20.10+ and Docker Compose v2
- Active Snowflake account with credentials available
- Port 3000 free on host machine

Verify Docker is running:

```bash
docker --version
docker ps
```

## Starting the Stack

From this directory:

```bash
docker compose up -d
```

First startup takes 30–60 seconds while Postgres initializes and Metabase
applies its schema migrations. Watch logs:

```bash
docker compose logs -f metabase
```

Metabase is ready when logs show:
```
Metabase Initialization COMPLETE
```

Open http://localhost:3000 in your browser.

## First-Time Setup (One-Time, ~3 Minutes)

Metabase Open Source edition does not support declarative database
provisioning via config file (that's a Pro feature). Initial setup is done
through the web UI on first launch.

> **Container user note:** The Metabase container runs as root. This means
> key pair files volume-mounted into the container are readable without
> permission adjustments, which is why key auth works out of the box.

> **After container recreation:** If you run `docker compose down -v` and
> restart, all Metabase state (admin account, Snowflake connection, dashboards)
> is wiped. Repeat Steps 1 and 2 below to restore. Your actual health data
> in Snowflake is unaffected.

### Step 1: Admin account

Metabase's welcome screen asks for:
- Preferred language
- Your name, email, and a password
- Company name (enter anything, e.g. "Personal")

This creates the local admin user. Credentials are stored in the metadata
Postgres. Only you have access.

### Step 2: Add Snowflake as a data source

When prompted to "Add your data," select **Snowflake**.

> **Auth method note:** This project uses RSA key pair authentication, not
> password auth. Snowflake is deprecating password-only connections
> (enforcement August–October 2026). All Python scripts and dbt already use
> key pair auth; Metabase must match.

Fill in the connection form using values from your repo-level `.env`:

| Metabase field | Value |
|---|---|
| Display name | `Snowflake - Health Analytics` |
| Account name | value of `SNOWFLAKE_ACCOUNT` in `.env` |
| Warehouse | value of `SNOWFLAKE_WAREHOUSE` in `.env` |
| Database name | value of `SNOWFLAKE_DATABASE` in `.env` |
| Username | value of `SNOWFLAKE_USER` in `.env` |
| Authentication | select **RSA key pair** (not Password) |
| RSA private key | paste the contents of `/home/hemu/.config/snowflake/keys/snowflake_key.p8` |
| Schema (optional) | `MART_HEALTH` |
| Role (optional) | Leave blank unless you've set a specific role |

To get the key contents for the paste field:
```bash
cat /home/hemu/.config/snowflake/keys/snowflake_key.p8
```

Click **Connect database**. Metabase will run a sync to discover tables in
`MART_HEALTH`. Once sync completes, `MART_REGIME_LABELS` and
`DAILY_HEALTH_SUMMARY` will be visible in the data browser.

### Step 3: Skip usage stats opt-in

Your choice. Neither option affects functionality.

## Daily Use

```bash
docker compose up -d          # start
docker compose stop           # pause (preserves state)
docker compose start          # resume
docker compose down           # stop and remove containers (volumes persist)
docker compose down -v        # stop and WIPE all data (nuclear option)
docker compose logs -f        # tail logs
docker compose ps             # check container health
```

## Persistence

All Metabase state (user accounts, dashboards, questions, Snowflake connection
config) lives in the `metabase_postgres_data` Docker volume.
Stopping and restarting containers (even after a machine reboot) preserves
everything. Only `docker compose down -v` wipes state.

If the metadata volume ever gets wiped, re-running Step 2 above restores the
Snowflake connection in ~2 minutes. No permanent data loss: your actual
health data is in Snowflake, untouched.

## Backup (Optional)

To snapshot the metadata Postgres:

```bash
docker exec metabase-postgres pg_dump -U metabase metabase > metabase-backup.sql
```

Restore:

```bash
cat metabase-backup.sql | docker exec -i metabase-postgres psql -U metabase metabase
```

## Troubleshooting

**Metabase logs show "Connection refused" to Postgres on startup**
The healthcheck should prevent this, but if it happens, restart the stack:
```bash
docker compose down && docker compose up -d
```

**Port 3000 already in use**
Check what's bound:
```bash
lsof -i :3000
```
Either stop the conflicting process or edit `docker-compose.yml` to map to a
different host port (e.g. `"3001:3000"`).

**Snowflake connection fails in Metabase**
- Verify credentials work independently: `python -c "import snowflake.connector; ..."` or via dbt
- Check the `Account name` field format: Snowflake account identifiers look like `abc12345.us-east-1` (no `.snowflakecomputing.com` suffix)
- Confirm the warehouse is not suspended in Snowflake UI

**Can't reach Metabase from browser**
```bash
docker compose ps        # verify both containers are "healthy"
docker compose logs metabase | tail -50
```

## Future Enhancements

- [ ] Automate Snowflake connection provisioning via Metabase REST API on first boot (removes manual UI step; makes the stack fully declarative)
- [ ] Pin Metabase image to a specific version (currently `latest`)
- [ ] Add backup cron job for metadata Postgres

## Why This Stack

- **Metabase OSS**: free, self-hostable, Snowflake-native with a drag-and-drop BI paradigm that transfers directly to Power BI for stack portability
- **Postgres for metadata**: production pattern (H2 default is not recommended for persistent work)
- **Docker Compose**: single-command reproducibility; anyone cloning this repo can run the stack identically
- **Internal-only metadata exposure**: least-privilege pattern; no reason to expose an application's internal database to the host network