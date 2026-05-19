# Matador

Current release: `Version 3.5.0`

`Version 3` introduces mixed telemetry-source collection. Matador can now model
both B&G GoFree websocket processors and NMEA0183 feeds as active telemetry
sources while preserving the same team, role, export, notification, diagnostics,
and historical storage model.

`Version 3.2.0` adds the Matador Edge Agent architecture for sites where the
boat network cannot run OpenVPN / CloudConnexa. Admins can create a
`Matador Edge Agent` processor source, issue a one-time enrolment code, and have
a Windows app stream local GoFree websocket data to Matador over encrypted WSS
through the independent edge ingest service.

`Version 3.2.1` makes the SQL Admin processor storage page safe for large
telemetry databases by reading cached `processor_storage_stats` values and
refreshing those counts in a background admin action instead of during page
load. It also keeps Edge Agent enrolment and revocation notices beside the
processor being administered so those one-time codes do not disappear from the
global status banner. The Windows Edge Agent app now also remembers the entered
enrolment code locally and reports local processor websocket failures separately
from upstream Matador stream failures. Edge Agent processor IP handling now uses
the admin processor IP as a fallback suggestion, while the locally configured
Windows app IP wins and is written back to the admin processor record while
streaming. Edge Agent discovery now prefers Navico UDP multicast discovery and
uses Bonjour only as a fallback, while dashboard Edge icons show grey, yellow,
or green status for offline, connected/no-data, and streaming states.

`Version 3.2.2` adds an Edge Agent discovery picker so operators can choose the
correct GoFree websocket source when a Navico network advertises multiple CPUs
or MFDs. The Edge Agent build now also uses the app-window icon.

`Version 3.2.3` refines the Edge Agent UI into three traffic-light status
indicators covering processor data, collection service/config health, and
upstream Matador streaming.

`Version 3.2.4` updates the Edge Agent controls so processor connection testing
and server streaming are separate actions. It also adds dedicated status icons
for processor data, Matador config/health, and upstream streaming.

`Version 3.2.5` improves the Edge Agent interface with larger colour-changing
status icons, renamed connection labels, and a taller default window so status
messages are visible without resizing.

`Version 3.2.6` adds remote Edge Agent commands from the admin page, fixes the
stop-streaming UI state, and adds raw processor/upstream payload visibility for
Edge Agent diagnostics.

`Version 3.2.7` reduces Edge Agent server load by throttling diagnostic raw JSON
and proxy-client status writes while preserving full live telemetry streaming.

`Version 3.2.8` tidies Edge Agent diagnostics by sampling the local raw-data
window and clearing stale interruption text after streaming resumes.

`Version 3.2.9` prevents slow CloudConnexa API calls from blocking dashboard
and admin responses by running those checks off the dashboard event loop with a
shorter external request timeout.

`Version 3.2.10` fixes Edge Agent dashboard freshness by making Edge-backed
processors read their latest values from Edge-ingested PostgreSQL rows rather
than the collector live payload.

`Version 3.2.11` reduces dashboard live polling pressure by limiting latest
requests to a sane live rate and preventing overlapping `/api/latest` calls. It
also fixes Edge Agent remote-command acknowledgement timestamp parsing.

`Version 3.2.12` hardens dashboard database access with bounded pool waits,
short latest-query timeouts, and a larger configurable asyncpg pool so slow
telemetry lookups cannot freeze health checks, config, or page loads.

`Version 3.2.13` makes dashboard latest telemetry reads use indexed per-metric
lookups instead of scanning a processor's full telemetry history, which keeps
Edge Agent processors fresh even when they stream high-frequency data.

`Version 3.2.14` disables websocket protocol pings on the local B&G GoFree
processor connection because some embedded processors stream data normally but
do not reliably respond to ping/pong keepalives, causing one-minute Edge Agent
reconnect cycles.

`Version 3.2.15` adds a Windows Edge Agent `View Subscribed Data` table so the
local operator can see each configured GoFree subscription and its latest
extracted value without reading raw JSON. It also adds clearer Edge health
states to the admin and dashboard UIs and reduces Edge Agent remote-command
polling noise to 30 seconds.

`Version 3.2.16` adds a Windows Edge Agent diagnostics window/export and clearer
admin-side remote command lifecycle states: no command, pending pickup, and
picked up.

`Version 3.2.17` simplifies the Windows Edge Agent operator layout by renaming
`Manual Processor IP` to `Processor IP`, placing discovery and processor-connect
actions beside the startup options, auto-saving settings, and moving raw JSON
access into Diagnostics.

`Version 3.2.18` hardens Edge stream authorization after processor retirement or
revocation and reorders the Edge Agent status rows to show Edge Agent
Connectivity before B&G GoFree Connection and Data Streaming.

`Version 3.2.19` separates the Windows Edge Agent's local processor connection
from Matador upstream streaming. `Connect to Processor` now toggles to
`Disconnect from Processor`, and `Stop Streaming` stops only the Matador data
stream while keeping the local B&G GoFree connection alive.

`Version 3.3.0` introduces Fleet Observer operations with Fleet Administrator
and Observer user roles, fleet-scoped Matador Edge Agent processor creation,
fleet-only sail number metadata, a Fleet Settings page with event branding for
enrolled Edge Agents, a global SQL admin data calendar, CSV archive downloads,
WhatsApp notification toggles, a Fleet Settings Edge Agent download control,
processor-storage totals, retired-processor storage hardening, and a hardcoded
production server endpoint in the Edge Agent.

`Version 3.3.2` makes the Data Calendar scale safely after large historical
imports by using indexed processor/day existence checks instead of grouping a
full year of telemetry rows on every calendar load.

`Version 3.3.3` adds outbound Telegram and WhatsApp message auditing so admins
can review when messages were sent, which API/channel was used, who received
them, and the message body from the Audit Log.

`Version 3.4.0` adds team-scoped GRIB forecast support. Authorized users can
upload or import a GRIB/GRIB2 file, Matador stores it privately, interpolates
the current UTC forecast time between GRIB validity steps, and shows forecast
TWD/TWS in the existing Forecast panes and as an optional Fleet Map `GRIB
Overlay`. Uploaded GRIB files are retained for 28 days by default and cleaned
by a daily systemd timer.

`Version 3.4.2` adds user-selectable true/magnetic direction display and CSV
export preferences. Matador now collects GoFree magnetic variation metric `125`,
refreshes GoFree direction unit metadata and setting `21` while connected, and
labels/converts TWD, heading, forecast, mean-wind, trend, and start-line
direction displays according to each user's preference.

`Version 3.4.3` adds optional Njord Player Format exports. Processor exports
and the Data Calendar can now download a ZIP containing separate `wind_data`
and `extra_data` CSV files with Njord-compatible metric headers. The option is
controlled by the sailing-team-only `Njord` feature flag.

`Version 3.4.4` aligns the Windows Edge Agent with the direct collector's
true/magnetic direction handling. Edge Agent processor connections now request
GoFree direction metadata plus the processor true/magnetic setting, reconnect
when refreshed Matador config changes the subscription list, and dynamically
pick up server-requested metrics such as magnetic variation.

`Version 3.5.1` adds first-pass Expedition TCP source support to the Windows
Edge Agent. Operators can select `Expedition TCP`, enter an Expedition/ATP1
server IP and configurable port, defaulting to `5010`, and stream common
Expedition wind, heading, GPS, and magnetic-variation channels through the
existing Edge ingest path.

`Version 3.5.0` adds the headless Matador Pi Edge Agent and compresses the
original Pi appliance roadmap into three larger stages. The Pi agent runs under
`systemd`, discovers GoFree processors via multicast, subscribes using
Matador-provided Edge config, requests direction metadata and true/magnetic
reference settings, durably spools unsent payloads in SQLite, accepts existing
Edge remote commands, reports Pi health/storage telemetry, and streams live
telemetry upstream over the existing Edge ingest websocket.

The Pi Edge Agent also supports no-code appliance claiming. If an imaged Pi is
started without `MATADOR_EDGE_ENROLLMENT_CODE`, it phones home with a stable
device ID and claim code. A global admin can approve the pending Pi from the
Admin page, choose the destination team, processor name, and processor role, and
the Pi will pick up its authorized config on the next poll.

`Version 2` is the multi-team hosted architecture introduced on 2026-04-24.
It replaces the old single-team, shared-password setup with:

- per-user login
- teams and team-scoped dashboards
- role-based access
- admin team switching
- admin-managed feature flags
- team notification settings
- Telegram `/link CODE` account linking
- persisted processor panel ordering per team
- motion-sensor availability indicator
- admin-managed global team banner messages
- admin-managed global dashboard notice messaging
- an admin-only audit page for reviewing recent platform actions
- optional CloudConnexa-backed VPN network status in the dashboard and admin health summary
- multilingual UI support for English, Spanish, French, and Italian
- localized Telegram notifications for team default languages
- optional WasenderAPI WhatsApp delivery for reset links, notifications, and Race Management positions
- admin-managed team default language for new users
- team roles and processor roles
- dedicated yearly data calendar and export launcher
- optional Open-Meteo GFS/ECMWF forecast panes for live 10 m wind at each processor GPS position
- optional team GRIB forecasts for current TWD/TWS at each processor GPS position and map overlay barbs
- admin-only SQL archive, data maintenance, and messaging test pages
- metric-level SQL storage reporting and configurable snapshot retention
- admin-only live raw JSON diagnostics without historical raw payload storage by default
- shared Race Management course-axis controls for ODM and mark placement
- user language preferences with English and Spanish UI translation support
- shared telemetry tables in one PostgreSQL database
- a local websocket simulator for dummy processor testing
- admin-managed OceanDrivers weather station scraping with optional WX map markers

The intended production URL is:

- [https://matador.torodatasystems.eu](https://matador.torodatasystems.eu)

Version history is tracked in [CHANGELOG.md](CHANGELOG.md), and each change from this point onward should be recorded under a new incremented version entry.

## Version 3 Architecture

The platform has five runtime parts:

- `dashboard` service
- `collector` service
- `edge ingest` service
- optional `weather station collector` service
- PostgreSQL database

The collector connects to active Hercules processors over the VPN, subscribes to
the configured GoFree IDs, writes telemetry into shared PostgreSQL tables, and
serves a local live-value cache on `127.0.0.1:8091`.
From Version 3.0.0, active sources can be either GoFree websocket processors or
NMEA0183 TCP/UDP feeds. The collector routes each source by
`processors.source_type` and writes normalized readings into the same telemetry
tables so dashboards and exports do not need a separate NMEA data path.

Matador Edge Agent processors use a separate ingest service on `127.0.0.1:8092`.
The Windows Edge Agent enrols with a one-time code, stores its device token in
the local user profile using Windows data protection where available, connects
to a local B&G GoFree websocket processor, and streams normalized telemetry to
Matador over HTTPS/WSS. The Edge Agent server URL is hardcoded to the production
Matador endpoint in the application build rather than being user-editable.

From Version 3.1.0, weather station sources can be configured from the
admin-only `/weather-stations` page. These sources are global rather than
team-owned. OceanDrivers stations store a URL and latitude/longitude; METAR
stations store an ICAO airport code and use CheckWX decoded METAR data to fetch
live wind and airport position; AEMET stations store an OpenData station code;
and SOCIB stations store a DataDiscovery platform ID such as `143` for Buoy
Bahia de Palma, preferring THREDDS numeric wind values when configured. A
separate `gofree-weather-stations.service` stores the latest
values in PostgreSQL. Teams with the `WX` / `Weather Stations` feature flag
enabled see those station markers on the dashboard map with speed in knots and
direction arrows.

The dashboard is a FastAPI app served behind nginx. nginx listens on port `80`
and proxies to the dashboard on `127.0.0.1:8081`.

The admin page uses grouped, collapsible team sections plus a feature-flag matrix.
It now also includes an admin health summary with processor counts, shows
Telegram chat IDs for linked users, exposes restart/status controls for both
the dashboard and collector in the Operations panel, and lets admins maintain
team-wide banner messages, a global dashboard notice, and the new
team/processor/user role classifications.
When CloudConnexa API credentials are configured, the admin health summary uses
the number of connected VPN networks for `Active Connections`, and the main
dashboard shows an OpenVPN icon beside processors whose matching LAN network is
currently online.
The main dashboard supports drag-and-drop processor panel ordering for users who
can manage team settings; the chosen order is saved back to PostgreSQL
`processors.sort_order`.
When the dashboard is opened with `?replay=1`, replay controls are exposed
through a dedicated modal launcher and toolbar actions instead of the old inline
panel.
Team Settings now mirrors the same UI style and lets an `Admin`,
`Performance Director`, or `Race Officer` reset passwords, deactivate
team-managed users, generate Telegram link codes, and manage coach processor
assignments.
Fleet Settings is available to global admins and `Fleet Administrator` users.
It lets fleet teams manage fleet users, create Matador Edge Agent processors,
set fleet-only sail numbers, and configure event branding shown in enrolled
Edge Agents.
User-role availability is now constrained by each team's role:
- `Sailing Team`: `Performance Director`, `Coach`, `Data Analyst`, `Viewer`
- `Race Management`: `Race Officer`, `Mark Layer`, `Viewer`
- `Fleet Observer`: `Fleet Administrator`, `Observer`, `Viewer`
The Data Calendar now lives on its own page and is available to `Coach`,
`Performance Director`, and `Data Analyst` users, with coach exports limited to
their assigned boat. Fleet Administrators can access the Data Calendar for all
processors in their fleet team.
Admins can also permanently delete users, and can delete empty teams that have
no users, processors, or historical telemetry/event data.

Role-specific user guides live in [docs/roles/README.md](docs/roles/README.md).
The Cronos-to-Matador historical import runbook lives in [docs/migrating_from_cronos.md](docs/migrating_from_cronos.md).
The NMEA0183 source setup runbook lives in [docs/nmea0183_sources.md](docs/nmea0183_sources.md).
The NMEA0183 replay/test tool runbook lives in [docs/nmea0183_replay.md](docs/nmea0183_replay.md).
The Matador Edge Agent runbook lives in [docs/edge_agent.md](docs/edge_agent.md).
The Matador Pi Edge Agent runbook lives in [docs/pi_edge_agent.md](docs/pi_edge_agent.md).
The Windows CSV GoFree Emulator runbook lives in
[docs/csv_gofree_emulator.md](docs/csv_gofree_emulator.md).
The OceanDrivers weather station setup runbook lives in [docs/weather_stations.md](docs/weather_stations.md).
The local dummy processor simulator runbook lives in [docs/websocket_simulator.md](docs/websocket_simulator.md).

### GRIB Forecasts

Teams with the `Forecast` feature flag enabled can use the `/forecast` page to
upload a `.grib`, `.grb`, `.gre`, `.grib2`, or `.grb2` file, or import an
approved HTTPS GRIB URL. Files are stored under `GRIB_STORAGE_DIR` and are never
served directly; the dashboard only exposes authenticated, team-scoped forecast
APIs. The default allowed import host is
`metsystem-datafront-1.s3-eu-west-1.amazonaws.com`.

GRIB parsing uses the system `ecCodes` command-line tools and NumPy:

```bash
sudo apt update
sudo apt install -y libeccodes-tools
cd /opt/gofree-collector
. .venv/bin/activate
pip install -r requirements.txt
```

When a GRIB is uploaded or imported, Matador streams the wind fields once and
writes a private `.wind-cache.npz` sidecar next to the GRIB file. U/V component
fields are preferred; files that provide wind speed plus wind direction are
converted into the same internal U/V cache. Very dense GRIBs are downsampled
into a bounded cache so the server does not need to hold the full model grid in
memory. At display time Matador reads this compact cache, finds the validity
times that bracket current UTC, linearly interpolates U/V wind components in
time, spatially interpolates the grid around each processor GPS position, and
then derives TWD/TWS for the existing Forecast pane and GRIB Overlay. If current
UTC falls outside the GRIB validity window, the GRIB forecast is shown as
unavailable. Older uploads without a cache still fall back to direct ecCodes
extraction, but new uploads should use the cached path for fast dashboard reads.
GRIB upload, URL import, failed URL import, activation, and deletion actions are
recorded in the Audit Log with the acting user, team, filename/source details,
and status where applicable. Manual cache rebuilds from
`python -m gofree_collector.grib_cache` are also audited with a system actor.

After deploying the cache schema, build caches for existing ready GRIB uploads:

```bash
cd /opt/gofree-collector
set -a
source .env
set +a
. .venv/bin/activate
python -m gofree_collector.grib_cache
sudo systemctl restart gofree-dashboard.service
```

Useful environment settings:

```bash
GRIB_STORAGE_DIR=/opt/gofree-collector/data/grib
GRIB_RETENTION_DAYS=28
GRIB_MAX_UPLOAD_MB=250
GRIB_IMPORT_ALLOWED_DOMAINS=metsystem-datafront-1.s3-eu-west-1.amazonaws.com
GRIB_OVERLAY_MAX_POINTS=2500
GRIB_TOOLS_TIMEOUT_SECONDS=20
```

Create the storage directory for the service user:

```bash
sudo mkdir -p /opt/gofree-collector/data/grib
sudo chown -R gofree:gofree /opt/gofree-collector/data
```

nginx must also allow GRIB upload bodies large enough to reach the dashboard
app. Set this in the Matador `server` block or relevant `location /` block:

```nginx
client_max_body_size 250M;
```

Then validate and reload nginx:

```bash
sudo nginx -t
sudo systemctl reload nginx
```

### Core data model

Platform tables:

- `teams`
- `users`
- `processors`
- `coach_processor_assignments`
- `proxy_clients`
- `team_feature_flags`
- `team_notification_settings`
- `weather_stations`
- `grib_uploads`
- `app_settings`
- `password_reset_tokens`
- `user_sessions`
- `telegram_contacts`
- `telegram_link_requests`
- `audit_log`

Telemetry tables:

- `telemetry_readings`
- `telemetry_snapshots`
- `collector_events`
- `processor_storage_stats`

### Team and Processor Roles

Teams now carry a lightweight classification:

- `Sailing Team`
- `Race Management`
- `Fleet Observer`

Processors also carry an operational role:

- `Coach Boat`
- `Wind Observer`
- `Race Committee`
- `Mark Boat`
- `Land Station`

These roles are editable from the admin page and are intended to help keep
multi-team and mixed-fleet deployments organised without changing export or
permission boundaries by themselves.
`Wind Observer` uses the Coach Boat behavior but skips GoFree subscription IDs
`230`, `340`, `341`, `352`, `353`, `354`, `380`, `420`, `423`, `538`, and
`539`.

Processors also carry a telemetry source type:

- `B&G GoFree Websocket`
- `Matador Edge Agent`
- `NMEA0183`

GoFree sources use websocket transport with the normal port `2053` and path
`/`. NMEA0183 sources can use `TCP` or `UDP` with an admin-configured host/IP
and port. One NMEA0183 source should represent one boat or station feed.
Fleet Administrators can create only `Matador Edge Agent` processors; processor
IP, port, source type, and sort-order controls are intentionally hidden in Fleet
Settings because the local operator links the real boat processor through the
Edge Agent enrolment flow.

Supported NMEA0183 sentences in Version 3 include:

- `RMC`, `GGA`, `GLL` for GPS position and source UTC context
- `MWD` for true wind direction/speed
- `MWV`, `VWR` for true/apparent wind angle/speed where supplied
- `HDG`, `HDM`, `HDT` for magnetic/true heading where supplied
- `VTG`, `VBW` for course/speed values
- `ZDA` for UTC date/time context

Matador does not derive true wind from apparent wind in this path. It stores the
values supplied by the NMEA0183 source and trusts upstream instrument systems for
wind calculations.

Where both true and magnetic direction values are supplied, the live dashboard
prefers magnetic wind direction and magnetic heading for operator-facing display
and course-management calculations while still storing true values for
diagnostics and export.

Captured navigation/autopilot/depth sentences such as `BOD`, `RMB`, `XTE`,
`AAM`, `APB`, `DBT`, `MTW`, `VLW`, `VHW`, `XDR`, `GLC`, `GSA`, and `GSV` are
currently counted in Diagnostics as unsupported sentence families rather than
stored as telemetry metrics.

## Roles

- `Admin`
  - global access
  - can switch dashboard team context
  - manages teams, users, processors, feature flags, password resets, delete actions, and team-wide settings
- `Performance Director`
  - team-scoped access
  - can manage team notification settings
  - can generate Telegram link codes for coaches and data analysts in their own team
- `Race Officer`
  - team-scoped access
  - has the same team-management rights as a Performance Director
  - can create team users from Team Settings
- `Data Analyst`
  - team-scoped read/export access
  - receives notifications for all processors in their team
- `Coach`
  - team-scoped read access
  - export limited to assigned processor
  - notifications limited to assigned processor
- `Viewer`
  - team-scoped read-only access
  - cannot export data
  - cannot use Telegram linking or notifications
- `Fleet Administrator`
  - team-scoped fleet management role for `Fleet Observer` teams
  - can manage fleet users and create Matador Edge Agent processors for their own team
  - can set sail numbers, event authority, regatta name, and event logo branding
  - can access the Data Calendar for all processors in their fleet team
  - cannot delete, retire, remotely connect, start, or stop Edge Agent processors
- `Observer`
  - team-scoped read access for `Fleet Observer` teams
  - is not linked to an individual processor
- `Mark Layer`
  - team-scoped Telegram recipient role intended for Race Management position sends
  - does not need dashboard access for the workflow to function
  - can receive calculated ODM and mark positions by Telegram when linked

## Feature Flags

Feature flags are stored per team in `team_feature_flags`.

Replay is admin-only by default. Admins can also enable the `Replay` feature flag
for specific teams to expose replay mode to users in those teams.

Current flags are split by team role.

`Sailing Team` flags:

- `Mean Wind`
- `Export`
- `Start`
- `Trends`
- `Experimental`
- `Map`
- `Replay`
- `Forecast`
- `Telegram Notifications`
- `WhatsApp Notifications`

`Race Management` flags:

- `Mean Wind`
- `Export`
- `Trends`
- `Experimental`
- `Map`
- `Replay`
- `Forecast`
- `Course Management`
- `Telegram Notifications`
- `WhatsApp Notifications`

`Fleet Observer` starts with the same feature selections as `Race Management`
and is managed from the admin feature-flag matrix. The Feature Flags section can
be collapsed when the page is being used for routine team/user maintenance.

For `Race Management` teams, `Start` is intentionally fixed off in the admin UI
and start-related boat/map features are removed from the dashboard layout.

Feature flags are `Admin` only. They are enforced in both the UI and backend.

## SQL Admin

The SQL Admin page is for global administrators and covers database maintenance
tasks that should stay bounded on large telemetry tables:

- `Download CSV Archive` exports telemetry readings, snapshots, and collector events for a selected processor/date range.
- `Administrator Data Calendar` shows all processors with telemetry by UTC day, including inactive processors whose historical records are still retained.
- `Processor Storage` reads cached `processor_storage_stats` values rather than recounting large telemetry tables during page load.
- `Refresh Storage Counts` recalculates cached processor row counts in the background.
- The Processor Storage table has a fixed totals row for telemetry rows, snapshots, events, and approximate size.
- `Metric Storage` is loaded only when opened and highlights high-volume processor/metric combinations.
- Delete/copy day tools invalidate cached storage views so an administrator can refresh counts after maintenance.

## Historical Migration From Cronos

Cronos stored telemetry in one PostgreSQL table per processor. Matador stores
telemetry in shared tables keyed by `team_id` and `processor_id`.

Use:

```bash
python -m gofree_collector.migrate_cronos \
  --source-database-url "$CRONOS_DATABASE_URL" \
  --team TEAM_SLUG \
  --dry-run
```

Then run the real import without `--dry-run` once the table-to-processor mapping
looks correct. Full instructions are in
[docs/migrating_from_cronos.md](C:\Users\TomRobinson\OneDrive - Toro Data Systems SL\Documents\Codex\Matador\docs\migrating_from_cronos.md).

## Time Zones

All timestamps are stored in UTC.

Users can toggle dashboard display between:

- `UTC`
- browser-local time

This preference is stored in `users.time_display_mode`.

## Telegram Linking

Telegram linking uses a one-time code flow.

1. User opens the Telegram bot and sends `/start`
2. An authorised user generates a link code in the web app
3. The user sends `/link CODE` to the bot
4. The bot links the Telegram `chat_id` to that platform user

Permissions:

- `Admin` can link any user
- `Performance Director` and `Race Officer` can link `Coach` and `Data Analyst` users in their own team
- only `Admin` can link a `Performance Director`

## Environment

Create `.env` from `.env.example`.

Important values:

```text
DATABASE_URL=postgresql://USER:PASSWORD@HOST:25060/defaultdb?sslmode=require
DASHBOARD_SESSION_SECRET=long-random-secret
GOFREE_WS_DEFAULT_PORT=2053
GOFREE_WS_DEFAULT_PATH=/
COLLECTOR_LIVE_HOST=127.0.0.1
COLLECTOR_LIVE_PORT=8091
DASHBOARD_LIVE_LATEST_URL=http://127.0.0.1:8091/latest
EDGE_AGENT_EXE_PATH="/opt/gofree-collector/downloads/Matador Edge Agent.exe"
DB_SNAPSHOT_INTERVAL_SECONDS=0
DB_STORE_RAW_JSONB=false
DB_PARTITION_MONTHS_AHEAD=6
TELEGRAM_BOT_TOKEN=
TELEGRAM_POLL_TIMEOUT_SECONDS=20
TELEGRAM_LINK_CODE_TTL_MINUTES=15
WASENDER_ENABLED=false
WASENDER_API_KEY=
WASENDER_API_BASE_URL=https://www.wasenderapi.com/api
COLLECTOR_CONTROL_ENABLED=false
COLLECTOR_SYSTEMD_SERVICE=gofree-collector.service
DASHBOARD_SYSTEMD_SERVICE=gofree-dashboard.service
SIMULATOR_SYSTEMD_SERVICE=gofree-simulator.service
OPENVPN_CLIENT_SYSTEMD_SERVICE=openvpn-client.service
```

Place the current Windows Edge Agent build at `EDGE_AGENT_EXE_PATH` so Fleet
Administrators can download it from the Event Branding pane in Fleet Settings.
Event branding is not compiled into a unique executable; enrolled Edge Agents
pull the current event authority name, regatta name, and logo from Matador
during enrolment/config refresh.

## Ubuntu Setup

### 1. Install packages

```bash
sudo apt update
sudo apt install -y python3.12 python3.12-venv python3-pip postgresql-client nginx
```

### 2. Copy the project

```bash
sudo mkdir -p /opt/gofree-collector
sudo chown "$USER":"$USER" /opt/gofree-collector
cd /opt/gofree-collector
```

### 3. Create the virtual environment

```bash
python3.12 -m venv .venv
. .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
python -m playwright install chromium
```

On Ubuntu servers, Playwright may also need browser system libraries:

```bash
python -m playwright install-deps chromium
```

### 4. Configure the environment

```bash
cp .env.example .env
nano .env
```

### 5. Load the environment into the shell

```bash
set -a
source .env
set +a
```

### 6. Initialise the schema

You can let the app create the schema automatically, or run:

```bash
psql "$DATABASE_URL" -f sql/001_init.sql
```

### 7. Bootstrap the first admin

```bash
. .venv/bin/activate
python -m gofree_collector.bootstrap \
  --admin-username admin \
  --admin-full-name "Platform Administrator" \
  --admin-email admin@example.com
```

To update an existing admin username and password later:

```bash
. .venv/bin/activate
python -m gofree_collector.update_admin_credentials \
  --current-username admin \
  --new-username new-admin
```

The command prompts for the new password, stores it as an Argon2 hash, and signs
out existing sessions for that admin. Omit `--new-username` to keep the current
username and update only the password.

### 8. Verify setup

```bash
python -m gofree_collector.check_setup
```

### 9. Start the dashboard manually

```bash
nohup uvicorn gofree_collector.dashboard:app --host 127.0.0.1 --port 8081 > dashboard.log 2>&1 &
```

Health check:

```bash
curl http://127.0.0.1:8081/health
```

### 10. Configure nginx for port 80

Create `/etc/nginx/sites-available/matador`:

```nginx
server {
    listen 80;
    server_name matador.torodatasystems.eu;

    location / {
        proxy_pass http://127.0.0.1:8081;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /edge/ {
        proxy_pass http://127.0.0.1:8092;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## Dedicated Service User

The recommended production setup is to run Matador services as a dedicated Linux
user instead of `root`.

### 1. Create the service account

```bash
sudo useradd --system --home /opt/gofree-collector --shell /usr/sbin/nologin gofree
sudo chown -R gofree:gofree /opt/gofree-collector
```

### 2. Update the systemd unit files

Set each Matador systemd service to:

```ini
User=gofree
Group=gofree
```

### 3. Allow only service control through sudo

Create `/etc/sudoers.d/gofree-collector-control`:

```sudoers
gofree ALL=(root) NOPASSWD: /bin/systemctl restart gofree-collector.service, /bin/systemctl is-active gofree-collector.service, /bin/systemctl restart gofree-dashboard.service, /bin/systemctl is-active gofree-dashboard.service, /bin/systemctl start gofree-simulator.service, /bin/systemctl stop gofree-simulator.service, /bin/systemctl restart gofree-simulator.service, /bin/systemctl is-active gofree-simulator.service, /bin/systemctl start openvpn-client.service, /bin/systemctl stop openvpn-client.service, /bin/systemctl restart openvpn-client.service, /bin/systemctl is-active openvpn-client.service, /bin/systemctl start gofree-cloudconnexa.service, /bin/systemctl stop gofree-cloudconnexa.service, /bin/systemctl restart gofree-cloudconnexa.service, /bin/systemctl is-active gofree-cloudconnexa.service
```

Validate:

```bash
sudo visudo -cf /etc/sudoers.d/gofree-collector-control
```

### 4. Enable web-based collector control

Set in `.env`:

```text
COLLECTOR_CONTROL_ENABLED=true
COLLECTOR_SYSTEMD_SERVICE=gofree-collector.service
DASHBOARD_SYSTEMD_SERVICE=gofree-dashboard.service
SIMULATOR_SYSTEMD_SERVICE=gofree-simulator.service
OPENVPN_CLIENT_SYSTEMD_SERVICE=gofree-cloudconnexa.service
```

Then reload:

```bash
sudo systemctl daemon-reload
sudo systemctl restart gofree-dashboard.service
sudo systemctl restart gofree-collector.service
```

With that in place, the admin page can show collector status and request a
restart without giving the dashboard broad root privileges.

If the Operations panel shows `sudo: a password is required`, the service name
in `.env` does not yet have a matching `NOPASSWD` entry. For example, if
`OPENVPN_CLIENT_SYSTEMD_SERVICE=gofree-cloudconnexa.service`, the sudoers file
must include the `start`, `stop`, `restart`, and `is-active` commands for
`gofree-cloudconnexa.service`.

Enable it:

```bash
sudo ln -sf /etc/nginx/sites-available/matador /etc/nginx/sites-enabled/matador
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx
sudo systemctl enable nginx
```

### 11. Enable HTTPS with Let's Encrypt

Install certbot:

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo mkdir -p /var/www/certbot
```

Use the HTTPS-ready nginx template from
[deploy/matador.nginx.https.conf](C:\Users\TomRobinson\OneDrive - Toro Data Systems SL\Documents\Codex\Matador\deploy\matador.nginx.https.conf)
as `/etc/nginx/sites-available/matador`, then request the certificate:

```bash
sudo certbot certonly --webroot -w /var/www/certbot -d matador.torodatasystems.eu
sudo nginx -t
sudo systemctl reload nginx
```

After that, users should access the platform at:

- [https://matador.torodatasystems.eu](https://matador.torodatasystems.eu)

### 11. Create teams, users, and processors

Open the site in a browser:

- [http://matador.torodatasystems.eu](http://matador.torodatasystems.eu)

Then:

1. log in as the bootstrap admin
2. create teams
3. create users
4. create processors
5. assign coach processors where needed
6. set feature flags
7. set notification thresholds

### 12. Start the collector

Only after processors exist:

```bash
nohup python -m gofree_collector.collector > collector.log 2>&1 &
```

Health check:

```bash
curl http://127.0.0.1:8091/health
```

## systemd

Recommended service files:

`/etc/systemd/system/gofree-dashboard.service`

```ini
[Unit]
Description=GoFree multi-team dashboard
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=root
Group=root
WorkingDirectory=/opt/gofree-collector
EnvironmentFile=/opt/gofree-collector/.env
ExecStartPre=/opt/gofree-collector/.venv/bin/python -m gofree_collector.check_setup
ExecStart=/opt/gofree-collector/.venv/bin/uvicorn gofree_collector.dashboard:app --host 127.0.0.1 --port 8081
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

`/etc/systemd/system/gofree-collector.service`

```ini
[Unit]
Description=GoFree multi-team collector
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=root
Group=root
WorkingDirectory=/opt/gofree-collector
EnvironmentFile=/opt/gofree-collector/.env
ExecStartPre=/opt/gofree-collector/.venv/bin/python -m gofree_collector.check_setup
ExecStart=/opt/gofree-collector/.venv/bin/python -m gofree_collector.collector
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

`/etc/systemd/system/gofree-edge-ingest.service`

```ini
[Unit]
Description=Matador Edge Agent ingest service
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=root
Group=root
WorkingDirectory=/opt/gofree-collector
EnvironmentFile=/opt/gofree-collector/.env
ExecStartPre=/opt/gofree-collector/.venv/bin/python -m gofree_collector.check_setup
ExecStart=/opt/gofree-collector/.venv/bin/uvicorn gofree_collector.edge_ingest:app --host 127.0.0.1 --port 8092
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

`/etc/systemd/system/gofree-weather-stations.service`

```ini
[Unit]
Description=Matador OceanDrivers weather station collector
After=network-online.target postgresql.service
Wants=network-online.target

[Service]
Type=simple
User=gofree
Group=gofree
WorkingDirectory=/opt/gofree-collector
EnvironmentFile=/opt/gofree-collector/.env
ExecStartPre=/opt/gofree-collector/.venv/bin/python -m gofree_collector.check_setup
ExecStart=/opt/gofree-collector/.venv/bin/python -m gofree_collector.weather_station_collector
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

`/etc/systemd/system/gofree-grib-cleanup.service`

```ini
[Unit]
Description=Matador GRIB retention cleanup
After=network-online.target

[Service]
Type=oneshot
User=gofree
Group=gofree
WorkingDirectory=/opt/gofree-collector
EnvironmentFile=/opt/gofree-collector/.env
ExecStart=/opt/gofree-collector/.venv/bin/python -m gofree_collector.grib_cleanup
```

`/etc/systemd/system/gofree-grib-cleanup.timer`

```ini
[Unit]
Description=Run Matador GRIB retention cleanup daily

[Timer]
OnCalendar=daily
Persistent=true

[Install]
WantedBy=timers.target
```

Enable them:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now gofree-dashboard.service
sudo systemctl enable --now gofree-collector.service
sudo systemctl enable --now gofree-edge-ingest.service
sudo systemctl enable --now gofree-weather-stations.service
sudo systemctl enable --now gofree-grib-cleanup.timer
```

## Operations

Restart dashboard:

```bash
sudo systemctl restart gofree-dashboard.service
```

Restart collector:

```bash
sudo systemctl restart gofree-collector.service
```

Restart Edge Agent ingest:

```bash
sudo systemctl restart gofree-edge-ingest.service
```

Restart weather station scraper:

```bash
sudo systemctl restart gofree-weather-stations.service
```

Control simulator:

```bash
sudo systemctl start gofree-simulator.service
sudo systemctl stop gofree-simulator.service
sudo systemctl restart gofree-simulator.service
```

Control OpenVPN client:

```bash
sudo systemctl start openvpn-client.service
sudo systemctl stop openvpn-client.service
sudo systemctl restart openvpn-client.service
```

Follow logs:

```bash
journalctl -u gofree-dashboard.service -f
journalctl -u gofree-collector.service -f
journalctl -u gofree-edge-ingest.service -f
```

Checks:

```bash
curl http://127.0.0.1:8081/health
curl http://127.0.0.1:8091/health
curl http://127.0.0.1:8092/edge/health
python -m gofree_collector.check_setup
```

After schema, dashboard, Edge ingest, or collector changes, the usual production
refresh command set is:

```bash
psql "$DATABASE_URL" -f sql/001_init.sql
sudo systemctl restart gofree-dashboard.service
sudo systemctl restart gofree-edge-ingest.service
sudo systemctl restart gofree-collector.service
```

## Current Caveats

- The collector loads processors from PostgreSQL on startup. If you add or edit
  direct GoFree/NMEA processors in the admin UI, restart the collector. Edge
  Agent processors do not require the direct collector, but Edge ingest should
  be restarted after deploying Edge API changes.
- Telemetry writes are guarded so inactive or archived processors cannot store
  new rows, even if an old collector or Edge stream task is still running.
- Telegram long polling will return `409 Conflict` if another process is already
  using the same bot token with `getUpdates`.
- The simple example service files use `root`; the recommended production setup
  is the dedicated `gofree` service user described above.
- HTTPS is required for production Edge Agent enrolment and WSS streaming.

## Versioning

- `Version 1`
  - single-team
  - shared dashboard password
  - env-defined processors
  - per-processor tables
- `Version 2`
  - multi-team hosted platform
  - per-user authentication
  - role-based access
  - admin team switching
  - team feature flags
  - team notification settings
  - Telegram `/link CODE`
  - shared telemetry tables

## Related Files

- [SETUP_MULTI_TEAM.md](C:/Users/TomRobinson/OneDrive%20-%20Toro%20Data%20Systems%20SL/Documents/Codex/Matador/SETUP_MULTI_TEAM.md)
- [sql/001_init.sql](C:/Users/TomRobinson/OneDrive%20-%20Toro%20Data%20Systems%20SL/Documents/Codex/Matador/sql/001_init.sql)
- [.env.example](C:/Users/TomRobinson/OneDrive%20-%20Toro%20Data%20Systems%20SL/Documents/Codex/Matador/.env.example)
