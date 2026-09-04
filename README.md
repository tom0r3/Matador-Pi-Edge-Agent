# Matador

Current release: `Version 3.7.3`

`Version 3.7.3` restores normal Pi GoFree telemetry after the `3.7.2` release.
It corrects the Remote Channels command-queue reference used by the receive
loop, so an idle Pi stays subscribed and continues to forward data.

`Version 3.7.2` forwards valid GoFree Setting `31` mast-height data to Matador
for the existing 10 m wind correction. It safely processes `DataInfo` and
`Setting` when they arrive in the same websocket frame, so the mast-height
setting cannot be skipped by metadata handling. No manual mast-height override
is required when the processor reports a valid value.

`Version 3.7.1` improves Remote Channels command reliability. While a command
is queued or active, the Pi shortens its local Hercules receive interval to
200 ms and applies separate bounded lifetimes for configuration, live values,
and fail-safe invalidation. Normal telemetry retains its one-second idle cycle.

`Version 3.7.0` adds the Remote Channels Edge transport for enrolled B&G
GoFree/Hercules targets. Commands arrive through the existing Matador stream,
are signed with the enrollment token and bound to the exact processor UUID,
profile revision, lease generation, and expiry, and can write only Linear
Channels `481-490`. The Pi performs writable Setting `91` preflight and exact
caption readback, reports an explicit acknowledgement, and fails an in-flight
command if its local GoFree connection restarts. This path remains inactive
unless the Matador team feature, validated target, active profile, target
lease, and server-wide write interlock all permit it.

`Version 3.6.2` receives its read-only GoFree setting subscriptions from the
Matador server. The server controls the requested setting IDs through
`EDGE_GOFREE_SETTING_IDS`; a configuration change reconnects the local GoFree
websocket automatically. Future approved setting subscriptions therefore do not
require a Pi Agent rebuild. The compatibility fallback requests settings `21`,
`31`, and `89` when connected to an older server.

`Version 3.6.0` checks the public network organisation every five minutes and
reports a confirmed Starlink connection to Matador without collecting or
sending the Pi's public IP address.

`Version 3.5.9` preserves the true or magnetic reference supplied by GoFree
for TWD, heading, and start-line bearing telemetry. It accepts both list and
single-object metadata replies, plus the observed `value`, `val`, and
`current` settings fields, so Matador dashboards can display and convert
directions without applying magnetic variation twice.

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
where it is not wanted. Browser refresh/preload disconnects and speculative
connections that send no request are ignored, and any genuine local-page
rendering error is logged with a traceback in
`journalctl -u matador-pi-edge-agent.service`.

Pi appliances now also advertise a Navico HTML5 app tile for compatible B&G,
Simrad, and Lowrance MFDs. By default the Pi sends the proven descriptor to
`239.2.1.1:2053` from `eth0` every 10 seconds, serves the compact TORO favicon
locally at `http://<pi-mfd-address>/icon.png?v=toro-favicon-1`, and opens
`https://matador.torodatasystems.eu/` directly when the `Matador` tile is
selected. The production profile deliberately does not send TORO UDP `2052`,
mDNS, or `navico-nav-ws` announcements.

