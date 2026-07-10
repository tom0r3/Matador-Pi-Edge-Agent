# Matador

Current release: `Version 3.5.2`

`Version 3` introduces mixed telemetry-source collection. Matador can now model
both B&G GoFree websocket processors and NMEA0183 feeds as active telemetry
sources while preserving the same team, role, export, notification, diagnostics,
and historical storage model.



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

Pi appliances also expose a local health page at `http://<pi-ip>:8080/` by
default. It shows Matador/GoFree connectivity, queue state, Pi network/storage
health, processor lock, discovered processors, and latest subscribed metric
values. `/api/status` returns the same snapshot as JSON and `/health` returns a
compact health response. If a live diagnostic section cannot be read, the page
stays available and shows a warning instead of failing completely. Set
`MATADOR_PI_EDGE_LOCAL_STATUS_PORT=0` to disable the local page on installations
where it is not wanted.

