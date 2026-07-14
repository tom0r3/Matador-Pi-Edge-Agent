# Changelog

All notable project changes will be recorded here.

## Unreleased

## 2026-07-13 - Version 3.6.2

- Moved Pi Edge GoFree setting subscriptions to the server-provided
  `gofree_setting_ids` configuration field, with a safe fallback for older
  Matador servers.
- Request mast height above waterline setting `31` alongside the existing
  true/magnetic reference and barcode settings when the server does not provide
  an explicit list.
- Reconnect the local GoFree websocket after a Matador configuration refresh
  changes the requested setting IDs, port, path, or metric list.

- Added a lightweight local Pi Edge health web page on port `8080` with
-  connectivity, queue, Pi health, processor lock, discovery, and subscribed
-  metric status, plus JSON endpoints at `/api/status` and `/health`.
- Hardened the local Pi Edge health page so transient snapshot/render failures
-  show as page warnings and normal service logs instead of returning a generic
-  `Local status error`.
- Changed the local Pi Edge health page request handler to ignore normal browser
-  disconnects, log full tracebacks for genuine page errors, and render an
-  explanatory local error page if an internal status-page failure still occurs.
- Fixed browser speculative/preload sockets timing out before sending a request
-  so they are closed quietly instead of being rendered as a visible
-  `TimeoutError` page.

## 2026-07-11 - Version 3.6.0

- Added five-minute public egress classification for Starlink. The Pi reports
  only the network organisation and classification to Matador; it never sends a
  public IP address. Matador can show the Starlink status mark when confirmed.

## 2026-07-10 - Version 3.5.9

- Accepted GoFree `DataInfo` and `Setting` replies delivered either as a list
  or as a single object.
- Accepted the `value`, `val`, and `current` setting fields when reading the
  GoFree true/magnetic compass reference.
- Preserved the source `degT` or `degM` reference alongside TWD, heading, and
  start-line bearing telemetry so Matador can convert user-selected true and
  magnetic dashboard views safely.
- Corrected the standalone Pi Agent development checks so they validate only
  files that are part of this repository.

## 2026-05-19 - Version 3.5.2

- Added the Stage 3 Pi Edge Agent no-code claiming path: unconfigured Pi agents can phone home with a stable claim code, appear in the Admin page, and be approved into a team/processor without typing an enrolment code on the device.
- Added a Pi Edge activity timeline to the Admin pending-claims panel so admins can see phone-home, waiting, approval, rejection, and config-pickup events without opening service logs.
- Added a Pi Edge Agent GoFree telemetry-silence watchdog so an established but silent processor websocket is reconnected automatically instead of leaving the dashboard stale.
- Hardened Pi Edge Agent state-file writes with unique temporary filenames to avoid concurrent `state.json.tmp` save races between config, claim, and processor loops.
- Added Pi Edge Agent install and update scripts for GitHub-based appliance deployment and one-command field updates.
- Added a root `VERSION` file and wired Pi Edge Agent plus Edge ingest version reporting to it so future release bumps are consistent.
- Added Pi health counters and discovered-processor reporting so Admin/support can see queue activity, processor candidates, and message-flow counters.
- Added Pi support/update tooling with `scripts/status.sh` plus optional `matador-pi-edge-update` systemd service/timer deployment files.
- Cleaned up the Pi Edge Agent remote restart command so admin-triggered restarts exit intentionally without noisy asyncio traceback logs.
- Changed Pi Edge Agent backlog uploads to drain the durable message queue in bounded batches instead of one SQLite payload per upstream acknowledgement.
- Fixed Admin Pi Edge message-queue sizing so it displays active queued payload bytes instead of the SQLite spool file allocation, which can stay large after a backlog drains.
- Added H5000/v1 Pi Edge processor identity handling by ignoring discovery serial `0`, reading barcode serial setting `89`, and backfilling the Edge processor lock when the real serial is available.
- Updated Pi Edge install/update scripts to provision a narrow sudoers rule for remote maintenance commands and removed service hardening that blocked those sudo-backed controls.
- Added Pi Edge self-test reporting, update timer state, update-available badges, and queue drain-rate/ETA telemetry to the Pi Edge Support page.
- Added `MATADOR_PI_EDGE_START_NOW=0` production-prep install mode so new Pis can be provisioned without phoning home until the customer first boots them.
- Added first-boot hostname uniquing for golden-image Pi clones, using a generic production-prep hostname that becomes `matador-pi-edge-xxxxxx` on first customer boot.
- Preserved pending Pi Edge approval form selections across live Admin refreshes so only claim statistics/activity update while admins are choosing teams, roles, names, and lock targets.
- Hardened Pi Edge golden-image hostname generation with a first-boot marker, hardware-first suffixes, and stale generated-hostname detection so cloned SD cards do not keep the source Pi hostname.
- Fixed the Pi Edge first-boot hostname path by importing the hashing library used to derive hardware-based hostname suffixes.
- Changed Pi Edge claim handling so a new pending claim from the same hostname supersedes older pending claim records, preventing duplicate approval cards after reset/golden-image preparation.
- Added local Pi Edge `factory-reset.sh` and `prepare-golden-image.sh` wrappers, and made production-prep installs update `/etc/hosts` alongside the reset hostname.
- Added a Pi Edge diagnostics maintenance control for remotely rebooting the Raspberry Pi, backed by a narrow sudoers rule for `systemctl reboot`.

## 2026-05-17 - Version 3.5.1

- Added first-pass Windows Edge Agent `Expedition TCP` source support. The
  agent can now connect as a TCP client to an Expedition-compatible server on a
  configurable port, parse line-delimited Expedition channel/value sentences,
  map common wind/heading/GPS channels into Matador telemetry metrics, and
  stream them through the existing Edge ingest websocket path.
- Updated Windows Edge Agent version reporting to `3.5.1`.

## 2026-05-16 - Version 3.5.0

- Added Stage 1 of the headless Matador Pi Edge Agent, including multicast
  GoFree processor discovery, existing Edge enrolment/config support, local
  GoFree websocket subscription, direction metadata requests, and WSS streaming
  to Matador.
- Collapsed the original Pi appliance roadmap into three larger stages and
  advanced the client directly to the Stage 3 baseline with durable SQLite
  outbound spooling, Matador command polling, remote start/stop/connect handling,
  and Pi health/storage telemetry in upstream payloads.
- Added Stage 2 dashboard visibility for Pi Edge clients by classifying Pi
  agents from stored upstream health payloads and surfacing hostname, version,
  spool depth, disk free space, load average, and live local processor IP to the
  dashboard.
- Added the Stage 3 no-code Pi claim workflow so a pre-imaged appliance can
  request admin approval, receive its config after approval, and continue using
  the existing encrypted Edge stream path.
- Added a `matador-pi-edge-agent.service` systemd unit template and Pi Edge
  Agent runbook for Raspberry Pi OS Lite installs.
- Updated Edge Agent and Edge ingest version reporting to `3.5.0`.

