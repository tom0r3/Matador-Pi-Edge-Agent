# Matador Pi Edge Agent

The Matador Pi Edge Agent is the headless Raspberry Pi companion to the
Windows Matador Edge Agent. Version 3.5.2 compresses the original appliance
roadmap into three larger stages and implements the Stage 3 client-side
foundation: unattended operation, discovery, durable offline spooling, remote
commands, health/storage telemetry, and no-code admin claiming.

## Three-Stage Appliance Roadmap

- Stage 1 - Headless proxy foundation: enrolment-code setup, GoFree discovery,
  server-configured subscriptions, and WSS streaming.
- Stage 2 - Reliable field appliance: durable offline spool, reconnect/retry,
  command polling, storage reporting, and processor identity persistence.
- Stage 3 - Managed appliance baseline: unattended `systemd` deployment,
  server-visible health payloads, remote start/stop/connect commands, and
  no-code admin claiming for pre-imaged appliances.

## Version 3.5.2 Capabilities

- Runs unattended as a Python module under `systemd`.
- Discovers B&G GoFree processors from UDP multicast `239.2.1.1` on ports
  `2052` and `2050`.
- Connects to the processor `navico-nav-ws` websocket.
- Keeps the local processor websocket alive with configurable ping heartbeat
  defaults of 30 seconds interval and 15 seconds timeout.
- Fetches Matador Edge config and subscribes to the server-provided metric list.
- Sends `DataReq` plus `DataInfoReq` metadata refreshes for direction metrics.
- Sends `SettingReq {"ids":[21]}` so Matador can identify true/magnetic
  heading and wind-direction reference when the processor provides it.
- Streams live processor data to Matador over WSS using the existing
  `/edge/stream` endpoint.
- Stores unsent payloads in a durable SQLite spool at
  `/var/lib/matador-pi-edge-agent/outbound-spool.sqlite3`.
- Uploads queued payloads in bounded batches so outage backlogs drain quickly
  after internet service returns.
- Keeps spooled payloads until Matador acknowledges the batch, then deletes
  the acknowledged rows.
- Reports Pi hostname, app version, load average, spool depth, spool size, and
  filesystem capacity in the upstream `pi_health` payload.
- Separates active queued payload bytes from SQLite spool file size, since the
  database file may remain large after a backlog has drained.
- Polls Matador config every 10 seconds for remote commands.
- Supports existing Edge remote command actions:
  `connect_processor`, `start_streaming`, and `stop_streaming`.
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
MATADOR_PI_EDGE_SPOOL_MAX_PAYLOADS=50000
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

- The dashboard exposes pending Pi claims and per-card health/status, but there
  is not yet a dedicated Pi appliance fleet-management page.
- Processor identity locking is available from Admin approval. It prefers
  serial number, then name/model, then name, so DHCP address changes are safe.
