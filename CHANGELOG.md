# Changelog

All notable project changes will be recorded here.

## Unreleased

## 2026-05-19 - Version 3.5.2

- Added an initial native SwiftUI iOS dashboard prototype under `ios/MatadorDashboard`, including login, role/team context, fleet summary, MapKit preview, forecast cards, and processor cards.
- Added the Stage 3 Pi Edge Agent no-code claiming path: unconfigured Pi agents can phone home with a stable claim code, appear in the Admin page, and be approved into a team/processor without typing an enrolment code on the device.
- Added a Pi Edge activity timeline to the Admin pending-claims panel so admins can see phone-home, waiting, approval, rejection, and config-pickup events without opening service logs.
- Added a Pi Edge Agent GoFree telemetry-silence watchdog so an established but silent processor websocket is reconnected automatically instead of leaving the dashboard stale.
- Hardened Pi Edge Agent state-file writes with unique temporary filenames to avoid concurrent `state.json.tmp` save races between config, claim, and processor loops.

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

