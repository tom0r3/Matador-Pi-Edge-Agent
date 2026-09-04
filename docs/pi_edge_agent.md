# Matador Pi Edge Agent

The Matador Pi Edge Agent is the headless Raspberry Pi companion to the
Windows Matador Edge Agent. Version 3.7.2 is the current production baseline:
unattended operation, discovery, durable offline spooling, remote commands,
health/storage telemetry, no-code admin claiming, golden-image preparation,
and remote diagnostics/maintenance from Matador Admin.

## Version 3.7.2 Mast Height Forwarding

Version `3.7.2` forwards valid GoFree Setting `31` (mast height above
waterline) as `processor_settings.mast_height_above_wl_m`. It processes both
`DataInfo` and `Setting` metadata sections when they share a GoFree websocket
frame, allowing Matador to apply its team-enabled 10 m wind correction without
a manual duplicate mast-height entry.

## Version 3.7.1 Remote Channels Reliability

Version `3.7.1` shortens the local Hercules receive interval to 200 ms while a
Remote Channels command is queued or active. Configuration, live values, and
fail-safe invalidation use separate bounded command lifetimes so Matador can
complete validation and receive cleanup evidence without weakening the expiry
guard on live routed data.

## Public Network Classification

Every five minutes the agent asks `https://ipinfo.io/org` for the public
network organisation. If it identifies AS14593 / Space Exploration
Technologies, it reports `starlink` in its health payload. Matador uses this to
show the Starlink status mark beside an active Pi Edge processor. The request
does not collect or report the public IP address. Any other provider, or a
failed lookup, is reported as `unknown` and shows no status mark.

## Three-Stage Appliance Roadmap

- Stage 1 - Headless proxy foundation: enrolment-code setup, GoFree discovery,
  server-configured subscriptions, and WSS streaming.
- Stage 2 - Reliable field appliance: durable offline spool, reconnect/retry,
  command polling, storage reporting, and processor identity persistence.
- Stage 3 - Managed appliance baseline: unattended `systemd` deployment,
  server-visible health payloads, remote start/stop/connect commands, and
  no-code admin claiming for pre-imaged appliances.

## Version 3.6.0 Capabilities

- Runs unattended as a Python module under `systemd`.
- Discovers B&G GoFree processors from UDP multicast `239.2.1.1` on ports
  `2052` and `2050`.
- Connects to the processor `navico-nav-ws` websocket.
- Keeps the local processor websocket alive with configurable ping heartbeat
  defaults of 30 seconds interval and 15 seconds timeout.
- Fetches Matador Edge config and subscribes to the server-provided metric list.
- Sends `DataReq` plus `DataInfoReq` metadata refreshes for direction metrics.
- Sends `SettingReq {"ids":[21,89]}` so Matador can identify true/magnetic
  heading reference and, on H5000/v1 processors, the barcode serial used for
  stable processor locking.
- Streams live processor data to Matador over WSS using the existing
  `/edge/stream` endpoint.
- Stores unsent payloads in a durable SQLite spool at
  `/var/lib/matador-pi-edge-agent/outbound-spool.sqlite3`.
- Samples the durable offline spool to 1 Hz by default for historical/export
  data, while live upstream payloads remain high-rate when the Pi is connected
  to Matador. Override with `MATADOR_PI_EDGE_STORAGE_SAMPLE_HZ=0` only for
  short diagnostic captures where every GoFree frame must be retained locally.
- Keeps the durable spool unlimited by default so offline data is not dropped
  at an arbitrary row cap. Set `MATADOR_PI_EDGE_SPOOL_MAX_PAYLOADS` only if a
  deliberate field cap is required.
- Uploads queued payloads in bounded batches so outage backlogs drain quickly
  after internet service returns.
- Keeps spooled payloads until Matador acknowledges the batch, then deletes
  the acknowledged rows.
- Reports Pi hostname, app version, load average, spool depth, spool size, and
  filesystem capacity in the upstream `pi_health` payload.
- Reports current app version, hostname, local processor host, queue state,
  disk guard state, and update-result telemetry during config check-ins, so
  Admin remains fresh even when upstream uploads are paused.
- Reports the configured historical storage sample rate in Pi health payloads
  so support can confirm whether a Pi is using the production 1 Hz queue policy
  or a temporary full-rate diagnostic mode.
- Separates active queued payload bytes from SQLite spool file size, since the
  database file may remain large after a backlog has drained.
- Keeps `/etc/hosts` in sync when first-boot hostname uniquing or remote
  hostname changes update the system hostname.
- Polls Matador config every 10 seconds for remote commands.
- Supports existing Edge remote command actions:
  `connect_processor`, `start_streaming`, and `stop_streaming`.
- Supports Pi maintenance commands from the diagnostics page, including
  `self_test`, `update_agent`, `reboot_system`, auto-update timer enable/disable,
  support-bundle capture, queue clearing, hostname update, reset/re-enrol, and
  GoFree rediscovery/reconnect.
- Queue clearing removes the durable SQLite spool and the in-memory live/sample
  buffers, then records `last_queue_cleared_at` in local state. The spool uses
  serialized SQLite access and a longer busy timeout so clear/ack/enqueue
  operations do not trip over each other during heavy backlog maintenance.
- Lets support download the latest captured support bundle from the Pi Support
  page after a bundle has been collected and reported by the agent.
- Shows server-queued command state in Pi diagnostics so admins can see whether
  `update_agent` and other commands are waiting for pickup or acknowledged by
  the Pi.
- Shows token age and last token use in Pi Support so fleet support can see
  whether a device token is current without querying the database manually.
- Captures update output in `/var/lib/matador-pi-edge-agent/update.log`; the
  status script and Pi diagnostics page show the log tail and last result.
- Reports disk pressure as `ok`, `warn`, or `critical` so support can spot a
  growing backlog before the Pi runs out of space.
- Reports local network diagnostics in health payloads, including Pi IP
  addresses, default route, interface addresses, DNS servers, active `wlan0`
  SSID, and hostname.
- Serves a lightweight local health page on port `8080` by default, showing
  Pi health, Matador/GoFree connectivity, queue state, processor lock,
  discovered processors, and latest subscribed metric values. The same data is
  available as JSON from `/api/status`. Snapshot failures are shown as page
  warnings and service log warnings rather than taking the whole page down.
  Normal browser/preload disconnects and speculative sockets that send no
  request are ignored, while genuine local-page failures are logged with a
  traceback and shown as an explanatory error page.
- Advertises a Navico HTML5 `Matador` tile to compatible B&G, Simrad, and
  Lowrance MFDs by sending the capture-derived descriptor to
  `239.2.1.1:2053` every 10 seconds from the configured MFD-facing interface,
  normally `eth0`. The tile opens `https://matador.torodatasystems.eu/`
  directly and uses the local versioned TORO favicon served from port `80`.
  The production profile intentionally does not send TORO UDP `2052`, mDNS, or
  `navico-nav-ws` compatibility announcements.
- Self-test probes Matador `/edge/health` reachability so support can
  distinguish local processor issues from internet/server reachability issues.
- Source Diagnostics shows latest Pi-backed telemetry rows, metric freshness,
  source counts, and valid/invalid readings. Pi Support intentionally avoids a
  duplicate received-data panel and focuses on agent health and maintenance.
- Source Diagnostics flags duplicate Pi Edge source locks when two or more
  agents appear to be locked to the same GoFree processor identity.
- Pi diagnostics show stale-reason guidance so support can distinguish Pi
  offline, GoFree silence, paused uploads, queue backlog, and disk pressure.
- This runbook includes a production acceptance checklist for final appliance
  sign-off before handover.
- If no enrolment code is configured, phones home with a stable device ID and
  claim code so a Matador admin can approve the Pi from the Admin page.

## Supported Hardware

The agent targets Raspberry Pi OS Lite 64-bit on:

- Raspberry Pi Zero 2 W / WH
- Raspberry Pi 4
- Raspberry Pi 5

The expected network layout for the first build is Ethernet connected to the
B&G/processor network with internet access available from the same Pi network
stack.

## Install On A Pi

Create a service user:

```bash
sudo useradd --system --create-home --home-dir /var/lib/matador-pi-edge-agent --shell /usr/sbin/nologin matador-edge
```

Install the application in `/opt/gofree-collector` and create a virtualenv:

```bash
cd /opt/gofree-collector
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Create `/etc/matador-pi-edge-agent.env`:

```bash
MATADOR_EDGE_SERVER=https://matador.torodatasystems.eu
# Optional. Omit this for no-code admin claiming.
MATADOR_EDGE_ENROLLMENT_CODE=PASTE-ONE-TIME-EDGE-CODE-HERE
MATADOR_PI_EDGE_STATE_DIR=/var/lib/matador-pi-edge-agent
MATADOR_DISCOVERY_TIMEOUT=8
# 0 means unlimited retention. Use a positive value only for a deliberate cap.
MATADOR_PI_EDGE_SPOOL_MAX_PAYLOADS=0
MATADOR_PI_EDGE_PROCESSOR_PING_INTERVAL_SECONDS=30
MATADOR_PI_EDGE_PROCESSOR_PING_TIMEOUT_SECONDS=15
MATADOR_PI_EDGE_DATA_SILENCE_RECONNECT_SECONDS=90
MATADOR_PI_EDGE_UPLOAD_BATCH_MAX_READINGS=250
MATADOR_PI_EDGE_UPLOAD_BATCH_MAX_PAYLOADS=50
MATADOR_PI_EDGE_LOCAL_STATUS_HOST=0.0.0.0
MATADOR_PI_EDGE_LOCAL_STATUS_PORT=8080
MATADOR_PI_EDGE_NAVICO_ADVERTISER_ENABLED=true
MATADOR_PI_EDGE_NAVICO_ADVERTISER_INTERFACE=eth0
MATADOR_PI_EDGE_NAVICO_ADVERTISER_INTERVAL_MS=10000
MATADOR_PI_EDGE_NAVICO_ADVERTISER_APP_NAME=Matador
MATADOR_PI_EDGE_NAVICO_ADVERTISER_SOURCE=TORO
MATADOR_PI_EDGE_NAVICO_ADVERTISER_FEATURE_NAME=TORO HTML5 App
MATADOR_PI_EDGE_NAVICO_ADVERTISER_APP_URL=https://matador.torodatasystems.eu/
MATADOR_PI_EDGE_NAVICO_ADVERTISER_ICON_PATH=/icon.png
MATADOR_PI_EDGE_NAVICO_ADVERTISER_ICON_REVISION=toro-favicon-1
MATADOR_PI_EDGE_NAVICO_ADVERTISER_ICON_HTTP_PORT=80
MATADOR_PI_EDGE_NAVICO_ADVERTISER_ONLY_SHOW_ON_CLIENT_IP=true
MATADOR_PI_EDGE_LOG_LEVEL=INFO
```

`MATADOR_EDGE_ENROLLMENT_CODE` is optional. If it is present, the Pi uses the
classic one-time Edge enrolment flow. If it is omitted, the Pi phones home and
shows a claim code in its logs; a global admin can approve the pending device
from the Admin page and bind it to a team/processor. After successful enrolment
or claim approval, the device token is stored in the state directory.

Install and start the service:

```bash
sudo cp deploy/matador-pi-edge-agent.service /etc/systemd/system/matador-pi-edge-agent.service
sudo systemctl daemon-reload
sudo systemctl enable --now matador-pi-edge-agent.service
```

View logs:

```bash
sudo journalctl -u matador-pi-edge-agent.service -f
```

Check local status:

```bash
sudo /opt/matador-pi-edge-agent/scripts/status.sh
```

Open the local Pi health page from a browser on the same network:

```text
http://<pi-ip>:8080/
```

Useful local status endpoints:

- `/` shows the human-readable status page.
- `/api/status` returns the same operational snapshot as JSON.
- `/health` returns a compact JSON health response.

If the page shows a local status error, inspect the traceback with:

```bash
sudo journalctl -u matador-pi-edge-agent.service --since "10 minutes ago" --no-pager | grep -i "local status\\|traceback\\|error\\|warning"
```

Set `MATADOR_PI_EDGE_LOCAL_STATUS_PORT=0` in
`/etc/matador-pi-edge-agent.env` and restart the service if a local web page is
not wanted on a particular installation.

## Navico HTML5 MFD Advertisement

The Pi advertises a `Matador` HTML5 tile for compatible Navico-family MFDs
using the Zeus S 7 hardware-tested production profile:

- Multicast destination: `239.2.1.1`.
- UDP destination port: `2053`.
- First send: immediately after the MFD-facing interface has an IPv4 address.
- Repeat interval: `10000` ms.
- Default MFD-facing interface: `eth0`.
- Icon URL: `http://<pi-mfd-address>/icon.png?v=toro-favicon-1`.
- App URL: `https://matador.torodatasystems.eu/`.
- Disabled by design: TORO UDP `2052`, mDNS `5353`, and `navico-nav-ws`.

The advertised descriptor is visible to every host on the MFD LAN and contains
no credentials, cookies, or device tokens. The MFD itself must have DNS,
gateway, internet access, a valid clock, compatible TLS support, and trusted
certificate authorities to open Matador.

Production should set the MFD-facing adapter explicitly with:

```bash
MATADOR_PI_EDGE_NAVICO_ADVERTISER_INTERFACE=eth0
```

If that interface does not exist, the agent fails fast instead of silently
advertising on Wi-Fi, VPN, Docker, loopback, or a management-only interface. If
the interface exists but has no IPv4 address yet, the advertiser waits and
retries. IPv4 link-local addresses such as `169.254.x.x` are valid.

The systemd service grants only `CAP_NET_BIND_SERVICE` so the unprivileged
`matador-edge` service user can serve `/icon.png` on port `80`. If another
service owns port `80`, either serve `public/icon.png` from that existing web
server or change `MATADOR_PI_EDGE_NAVICO_ADVERTISER_ICON_HTTP_PORT` and repeat
the Zeus acceptance test.

Useful local checks:

```bash
sudo /opt/matador-pi-edge-agent/scripts/status.sh
curl -I "http://PI_MFD_ADDRESS/icon.png?v=toro-favicon-1"
sudo tcpdump -ni eth0 -A 'udp dst host 239.2.1.1 and dst port 2053'
```

Hardware acceptance sequence:

1. Confirm the Pi and MFD share the MFD LAN.
2. Confirm the MFD has DNS, gateway, internet access, and correct time.
3. Start or update the Pi agent and inspect the local status Navico card.
4. Capture at least 30 seconds on the MFD-facing interface.
5. Verify packets go only to `239.2.1.1:2053` every 10 seconds.
6. Verify no TORO packets are sent to UDP `2052` or `224.0.0.251:5353`.
7. Fully reboot the MFD to avoid relying on cached tiles.
8. Confirm one `Matador` tile appears with the compact TORO favicon.
9. Open the tile and confirm `https://matador.torodatasystems.eu/` loads.
10. Test login, cookies, logout, session recovery, and the on-screen keyboard.
11. Test internet loss/recovery while the local tile remains advertised.
12. Restart the Pi agent and confirm the tile recovers.
13. Disconnect/reconnect the MFD-facing Ethernet cable.
14. Run a 30 to 60 minute soak test with stable counters and no error growth.

Update from GitHub:

```bash
cd /opt/matador-pi-edge-agent
sudo ./scripts/update.sh
```

The update command writes its console output to:

```bash
/var/lib/matador-pi-edge-agent/update.log
```

The log is owned/readable by the Pi agent service user after the update so
Matador Admin can show the recent update tail in diagnostics.

The updater treats the Pi checkout as an appliance release tree: it fetches the
configured branch, defaults to `main`, and hard-resets the local files before
reinstalling dependencies and restarting the service. This prevents chmod drift,
root-owned edits, or interrupted manual support changes from blocking future
remote updates. Git safety is passed per command with `safe.directory`, so the
systemd update service does not depend on `$HOME` or global Git config.

Admin-triggered updates start the dedicated
`matador-pi-edge-update.service` with `systemctl --no-block` so the update runs
outside the agent service cgroup. That lets the updater restart
`matador-pi-edge-agent.service` without killing its own update process.

## Production And Golden Images

Fresh install on a Pi that should phone home immediately for Admin approval:

```bash
cd /opt
sudo git clone https://github.com/tom0r3/Matador-Pi-Edge-Agent.git matador-pi-edge-agent
sudo chown -R "$USER:$USER" /opt/matador-pi-edge-agent
cd /opt/matador-pi-edge-agent
sudo ./scripts/install.sh
```

Production-prep install for a Pi or SD-card image that should be enabled for
the customer's first boot, but must not phone home during preparation:

```bash
cd /opt
sudo git clone https://github.com/tom0r3/Matador-Pi-Edge-Agent.git matador-pi-edge-agent
sudo chown -R "$USER:$USER" /opt/matador-pi-edge-agent
cd /opt/matador-pi-edge-agent
sudo MATADOR_PI_EDGE_START_NOW=0 ./scripts/install.sh
```

Prepare an already configured Pi as a cloneable golden image:

```bash
cd /opt/matador-pi-edge-agent
sudo ./scripts/prepare-golden-image.sh
```

That clears local claim/config/queue state, resets the hostname seed to
`matador-pi-edge`, leaves first-boot hostname uniquing pending, disables active
phone-home during preparation, and shuts down ready for SD-card imaging. On
the customer's first boot the service starts, derives a stable hardware-based
hostname suffix, updates `/etc/hostname` and `/etc/hosts`, and then phones home
for approval.

Factory reset an installed Pi so it reboots and appears as a fresh pending
claim:

```bash
sudo /opt/matador-pi-edge-agent/scripts/factory-reset.sh
```

## Production Acceptance Checklist

Use this checklist while viewing the Pi diagnostics page for final appliance
sign-off. For each new or updated Pi, confirm:

- The Pi is approved to the correct team, has the expected processor name, and
  shows the correct processor role.
- The processor lock matches the intended GoFree processor and survives
  refresh/reconnect without falling back to a DHCP-only identity.
- Live Health shows the expected Wi-Fi SSID, Pi IP address, default route, DNS
  servers, queue state, and Matador check-in freshness.
- Source Diagnostics shows current metrics for the expected source, especially
  wind, heading, GPS, COG, and SOG where those values are available on the
  vessel.
- Queue depth stays small when online, grows while uploads are paused/offline,
  and drains after uploads resume.
- Remote commands are acknowledged and visible: Run Self-Test, Update Now,
  Restart Agent, Reboot Pi, Capture Bundle, and Pause/Resume Uploads.
- Fresh production units start unclaimed, generate a unique hostname on first
  boot, and do not carry previous device tokens, queue rows, or customer state.

## Manual Testing

Run discovery only:

```bash
cd /opt/gofree-collector
.venv/bin/python -m edge_agent.pi_edge_agent --discover-once
```

Run the agent in the foreground:

```bash
cd /opt/gofree-collector
.venv/bin/python -m edge_agent.pi_edge_agent \
  --enrollment-code PASTE-ONE-TIME-EDGE-CODE-HERE \
  --log-level DEBUG
```

Use a fixed processor IP if multicast discovery is unavailable:

```bash
.venv/bin/python -m edge_agent.pi_edge_agent \
  --processor-host 192.168.33.109 \
  --enrollment-code PASTE-ONE-TIME-EDGE-CODE-HERE
```

## Remaining Gaps

- The Pi diagnostics page now provides appliance support controls, but a wider
  fleet-management workflow for rollout batches, staged releases, and hardware
  inventory is still a future production-polish item.
- Processor identity locking is available from Admin approval. It prefers
  serial number, then name/model, then name, so DHCP address changes are safe.
  Hercules/v2 processors normally advertise the serial in discovery. H5000/v1
  processors may advertise `0`, so the Pi reads setting `89` after connection
  and backfills the barcode serial. Zeus/MFD discovery does not expose a serial,
  so those locks intentionally fall back to name/model.
