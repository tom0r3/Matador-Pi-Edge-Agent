# Matador Pi Edge Agent

The Matador Pi Edge Agent is the headless Raspberry Pi companion to the
Windows Matador Edge Agent. Version 3.5.8 is the current production baseline:
unattended operation, discovery, durable offline spooling, remote commands,
health/storage telemetry, no-code admin claiming, golden-image preparation,
and remote diagnostics/maintenance from Matador Admin.

## Three-Stage Appliance Roadmap

- Stage 1 - Headless proxy foundation: enrolment-code setup, GoFree discovery,
  server-configured subscriptions, and WSS streaming.
- Stage 2 - Reliable field appliance: durable offline spool, reconnect/retry,
  command polling, storage reporting, and processor identity persistence.
- Stage 3 - Managed appliance baseline: unattended `systemd` deployment,
  server-visible health payloads, remote start/stop/connect commands, and
  no-code admin claiming for pre-imaged appliances.

## Version 3.5.8 Capabilities

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
