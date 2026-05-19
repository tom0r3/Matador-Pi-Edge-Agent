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

## 2026-05-15 - Version 3.4.4

- Hardened true/magnetic direction handling so GoFree direction metrics without
  a confirmed source reference no longer fall back to static default units,
  avoiding accidental magnetic-variation conversion on unknown-reference TWD,
  heading, COG, or start-line bearing values.
- Changed browser mean-wind and trend caches to retain raw direction samples and
  convert them at render time, so TWD displays follow the current user true /
  magnetic preference without reusing stale converted samples.
- Cleaned up dashboard TWD handling so `TWD` remains one canonical wind
  direction value with a displayed reference (`degT` / `degM`), while
  `TWD_MAG` is used only as an ingestion compatibility fallback.
- Added an SQL Admin background action to delete all telemetry readings,
  snapshots, and collector events for a selected processor with explicit
  confirmation, progress polling, stale storage-stat cleanup, and audit logging.
- Updated the Windows Edge Agent to request GoFree `DataInfoReq` metadata and
  `SettingReq {"ids":[21]}` true/magnetic reference checks for direction
  metrics, matching the direct collector path.
- Added Edge Agent processor reconnection when refreshed Matador config changes
  the local subscription list, ensuring new server-requested metrics such as
  magnetic variation are subscribed without requiring an app restart.
- Updated Edge Agent and Edge ingest version reporting to `3.4.4`.

## 2026-05-13 - Version 3.4.3

- Added an optional Njord Player Format export checkbox to processor exports and the Data Calendar export modal.
- Added Njord ZIP exports containing `{processor}_{date}_wind_data.csv` and `{processor}_{date}_extra_data.csv`.
- Added Njord-compatible CSV headers for wind and start-line data while keeping normal CSV exports unchanged.
- Added a sailing-team-only `Njord` feature flag so the Njord export checkbox is only visible and callable when enabled.

## 2026-05-13 - Version 3.4.2

- Added GoFree `DataInfoReq` refreshes and `SettingReq {"ids":[21]}` checks for direction metrics so Matador can detect whether the processor is currently sending true or magnetic bearings.
- Switched live magnetic variation collection to GoFree metric `125` and keeps it subscribed even when custom metric JSON is configured.
- Added per-user dashboard and CSV direction preferences for source, true, or magnetic bearings through the new User Settings modal.
- Converted dashboard TWD, heading, forecast TWD, mean wind, trends, start square-line display, and CSV exports using the latest magnetic variation.
- Added direction mode details to data export audit logs and database/user schema migrations for the new preferences.

## 2026-05-13 - Version 3.4.1

- Matched the CSV GoFree Emulator discovery announcement more closely to the
  captured Hercules processor by advertising `IP_LinkLocal`, `navico-nav-http`,
  and captured-style `N2kNames` by default.
- Added `N2kCANoEServer` ISO request responses for PGNs `126996`, `126998`,
  and `130847`, based on the N9/Hercules hub capture.
- Changed GoFree discovery multicast to advertise on each local IPv4 interface
  so link-local N9/Hercules networks receive emulator announcements.
- Corrected the emulator's `126996` Product Information and `126998`
  Configuration Information response templates to better match the hub capture.
- Added N2K `130306` true-wind-direction output from CSV `TWD`/`TWS` values.
- Added N2K `128267` water-depth output from CSV `Depth` values.
- Added live manual N2K overrides in the CSV GoFree Emulator GUI for heading,
  boat speed, wind, rudder, depth, heel, position, SOG, and COG.

## 2026-05-08 - Version 3.4.0

- Added authenticated, team-scoped GRIB/GRIB2 forecast uploads and HTTPS URL imports through the new Forecast page.
- Added private GRIB storage metadata in PostgreSQL, active-file selection, 28-day retention settings, and a daily `gofree-grib-cleanup` systemd timer.
- Added ecCodes-backed GRIB parsing for current UTC TWD/TWS, using temporal interpolation between validity steps and spatial interpolation around each processor GPS position.
- Added GRIB forecast values to the existing processor Forecast pane and a Fleet Map `GRIB Overlay` button controlled by the existing `Forecast` feature flag.
- Tuned the GRIB map overlay so wide zoom levels request fewer points, close zoom levels request more, and each GRIB sample includes a TWS-coloured wind-speed patch under the wind barb.
- Added GRIB grid resolution detection from ecCodes metadata, displayed it on the Forecast page, and changed the GRIB map colour layer to draw resolution-sized cells instead of fixed circular point markers.
- Added browser-side GRIB grid-spacing inference so older active GRIB files or files without explicit resolution metadata still render as filled cells rather than sparse colour circles.
- Changed GRIB overlay downsampling to select a symmetrical latitude/longitude sample grid, keeping low-zoom barbs evenly spaced while the colour canvas stretches continuously across the shown points.
- Increased GRIB Overlay sample density and decoupled colour-field density from wind-barb density so the shaded forecast field remains smooth without overwhelming the map with barbs.
- Changed GRIB Overlay barb thinning to sample a balanced latitude/longitude grid, avoiding vertical “curtain” patterns on GRE/low-resolution GRIB displays.
- Changed GRIB Overlay barb placement to prefer viewport-cell sampling, improving visual spread when GRIB points are sparse or irregularly grouped.
- Clipped the GRIB colour canvas to the GRIB file boundary so low-zoom maps do not shade outside the forecast file coverage.
- Changed Forecast pane loading so GRIB forecasts can populate from server-side latest processor GPS even when the browser panel has not yet received live GPS rows; Open-Meteo cards still wait for browser GPS.
- Split Forecast pane loading so ECMWF/GFS Open-Meteo cards render as soon as their lightweight request returns, while the heavier GRIB card updates independently when extraction finishes.
- Added a long-term GRIB wind cache: uploads/imports now parse U/V fields into a private `.wind-cache.npz` sidecar so Forecast pane and GRIB Overlay requests no longer repeatedly scan the full GRIB file.
- Changed GRIB cache generation to stream ecCodes output and downsample very dense grids into a bounded cache, avoiding out-of-memory kills on high-resolution uploads.
- Hardened GRIB cache generation for high-resolution files whose advertised grid metadata does not exactly match ecCodes point coordinates, falling back to the actual point axes when needed.
- Hardened cached GRIB point lookup so Forecast cards can use the nearest valid cached grid value instead of failing when the immediate interpolation cells are empty.
- Hardened GRIB extraction for mixed GRIB1/GRIB2 files by trying both validity-time and data-time/step-range ecCodes filters when reading wind fields.
- Added `paramId`/field-name matching for OpenWRF-style GRIBs where ecCodes reports 10 m wind fields as `shortName=unknown`.
- Added ecCodes message-count selection and OpenWRF fallback pairing for files whose 10 m U/V wind messages are both reported as unknown `heightAboveGround=10` fields.
- Changed the GRIB cache backfill command to always re-parse source files, ensuring newer parser metadata such as message counts is used for older upload rows.
- Extended GRIB cache generation to support files that provide wind speed plus wind direction fields instead of U/V components.
- Hardened GRIB cache generation for OpenWRF/GRE files whose validity slices produce different point-axis shapes, keeping the cache on one stable grid shape instead of failing the upload.
- Added audit-log coverage for failed GRIB URL imports, alongside existing GRIB upload/import, activate, and delete audit entries.
- Added audit-log coverage for manual GRIB cache rebuild success/failure entries from `python -m gofree_collector.grib_cache`.
- Smoothed GRIB Overlay colour interpolation while preserving zoom-aware barb thinning so low-resolution forecasts show a continuous wind-speed field without overloading the map with markers.
- Changed GRIB Overlay smoothing to use typical on-screen grid spacing instead of the closest point pair, preventing clustered points from making the colour field collapse into isolated blobs.
- Changed the GRIB Overlay colour canvas to render a stronger full-field nearest-neighbour raster across the GRIB extent, making the TWS overlay visible even when source points are sparse.
- Added a dedicated high-contrast GRIB TWS colour scale and stronger overlay opacity so low wind-speed GRIBs remain visible over both sea and land map tiles.
- Hardened GRIB cache generation to reject mostly-empty metadata-projected grids and fall back to actual ecCodes point axes, preventing overlays with only one or two valid wind cells.
- Changed fallback GRIB cache downsampling to fill the actual point grid before thinning it, preserving valid cells instead of dropping most points during axis sampling.
- Added flattened cached GRIB wind points per validity time and changed GRIB Overlay reads to prefer those real points over reconstructed grids, avoiding sparse overlays when model grid metadata is unreliable.
- Restored the original direct ecCodes GRIB Overlay extraction as an automatic fallback whenever the cached overlay returns too few points, preventing sparse cache regressions from degrading the map.
- Changed GRIB Overlay canvas clipping to ignore degenerate GRIB metadata bounds and use the actual returned point extent, restoring colour shading for files whose metadata reports a one-point boundary.
- Softened GRIB Overlay opacity and expanded point-derived fallback padding so the colour field is less overpowering while covering more of each forecast cell.
- Aligned GRIB Overlay colours and opacity with the existing TWS/WX overlay visual scale for a consistent map presentation.
- Tuned GRIB Overlay smoothing to avoid browser freezes by using a moderate raster resolution, a light canvas blur, and cheaper nearest-point interpolation.
- Increased low-zoom GRIB Overlay colour-field point density while keeping barbs thinned, and scaled colour smoothing with on-screen GRIB spacing to reduce zoomed-out grid artifacts.
- Changed GRIB Overlay requests to use the full point limit at every zoom so colour interpolation remains stable while only wind barbs are zoom-thinned.
- Added GRIB cache metadata and cleanup handling so expired/deleted GRIB uploads remove both the original file and cached wind sidecar.
- Added `python -m gofree_collector.grib_cache` to backfill wind caches for existing ready GRIB uploads after deployment.
- Restricted GRIB uploads to `.grib`, `.grb`, `.gre`, `.grib2`, and `.grb2` file extensions, removing generic binary upload acceptance.
- Added client-side GRIB upload validation so browsers cannot submit `.com`, `.exe`, `.bin`, or other non-GRIB files even if their file picker ignores the accept list.
- Documented GRIB environment settings, `libeccodes-tools`/NumPy dependencies, and deployment steps.

## 2026-05-07 - Version 3.3.3

- Added `messaging_message_sent` audit log entries for Telegram and WhatsApp sends, including UTC timestamp via the audit row, channel, recipient, recipient user where known, purpose, provider, and message body.
- Added message-send audit logging for automatic processor notifications, Telegram bot link/help replies, admin messaging tests, Race Management position messages, and password reset delivery.

## 2026-05-06 - Version 3.3.2

- Reworked Data Calendar year queries to use indexed processor/day existence probes instead of grouping full-year telemetry scans, preventing nginx 504 timeouts on large historical imports.
- Documented the Data Calendar lookup path for per-partition processor/time indexes rather than creating a heavy parent-table index during service startup.
- Updated CSV exports to stream telemetry in raw timestamp order instead of ordering by a truncated timestamp expression, avoiding large pre-stream sorts on imported telemetry.
- Optimized CSV export forward-fill seeding to fetch the latest prior value per metric with indexed lateral lookups and removed unnecessary secondary sort keys from the export cursor.
- Changed CSV export streaming to read telemetry in 15-minute windows, reducing per-query sort work and preventing nginx from timing out after only the CSV header has been sent.

## 2026-05-05 - Version 3.3.1

- Added a command-line admin credential update utility that renames an existing admin, prompts for a new password, stores it with the platform Argon2 hashing helper, and clears existing sessions by default.
- Added an `Overlay` feature flag and moved the live TWS wind-field overlay controls from Experimental into the Fleet Map toolbar.
- Added a Fleet Map `WX Overlay` control for Weather Stations teams, using each station's latest TWS/TWD at the station location.
- Added a Windows CSV GoFree Emulator that replays processor CSV logs as a discoverable local GoFree websocket server with live UTC date/time replacement and row/offset seeking.
- Updated the CSV GoFree Emulator discovery announcement to match real Navico `navico-nav-ws` JSON more closely, with advanced controls for advertised app, device, platform, serial, model, name, and service version fields.
- Added an optional CSV-driven `N2kCANoEServer` TCP stream that advertises on discovery and emits generated 16-byte NMEA 2000 CAN records on port 8086.
- Made the CSV emulator's `N2kCANoEServer` bidirectional enough to read client 16-byte records and answer ISO Requests for address claim and the observed proprietary 65304 request.
- Added optional raw CAN text-log replay for `N2kCANoEServer`, using captured 29-bit CAN IDs, DLCs, payload bytes, and source timestamps instead of synthesized CSV-derived N2K frames.
- Moved the raw CAN/N2K log selector onto the CSV emulator's main window and tightened file validation so blank paths no longer produce a permission error.
- Kept `Time for Wind to Arrive` inside Experimental and left-aligned Fleet Map toolbar controls.
- Added Race Management settings for Race Areas and draw enabled areas as dashed, lightly shaded circles on the Fleet Map.
- Added Race Area colour selection and changed Fleet Map Race Areas to show a fixed centre label instead of hover text.
- Added optional Windows system-tray minimization to the Matador Edge Agent, with tray restore and exit actions.
- Updated the Edge Agent version to `3.3.1`.
- Added NOAA NDBC as a Weather Stations source type, accepting station IDs and converting NDBC realtime `WSPD` from m/s to knots while storing `WDIR` as TWD degrees true.
- Added WeatherLink as a Weather Stations source type, accepting public embed IDs and reading current wind speed/direction from WeatherLink's public summary data endpoint.

## 2026-05-04 - Version 3.3.0

- Added the `Fleet Observer` team role with `Fleet Administrator`, `Observer`, and `Viewer` users.
- Added fleet-safe Matador Edge Agent processor creation, Fleet Settings, and fleet-only alphanumeric `Sail Number` metadata.
- Added fleet event branding fields so enrolled Edge Agents can show the Event Authority, Regatta Name, and logo supplied by the server.
- Added Fleet Observer feature-flag grouping, a hideable Feature Flags section, and Fleet Administrator Data Calendar access.
- Added a SQL Admin all-processor data calendar backed by a date/processor telemetry index.
- Added a fixed totals row to the SQL Admin Processor Storage table for telemetry, snapshots, events, and approximate size.
- Changed SQL Admin archives to download CSV files instead of SQL insert archives.
- Added a WhatsApp Notifications toggle to Team Settings and changed notification repeat cooldown defaults to 600 seconds.
- Hardcoded the Edge Agent server address to the Matador production endpoint and protected stored device tokens on Windows using user-profile encryption where available.
- Added a Fleet Settings Edge Agent download control and removed the earlier DigitalOcean database health integration.
- Hardened telemetry storage so inactive or archived processors cannot store new readings even if an existing collector task is still running.
- Updated Edge Agent and Edge ingest version reporting to `3.3.0`.

## 2026-05-04 - Version 3.2.19

- Split the Windows Edge Agent's local processor connection from Matador upstream streaming.
- Changed `Connect to Processor` into a toggle that becomes `Disconnect from Processor` while the local B&G GoFree websocket is connected.
- Changed `Stop Streaming` so it stops only Edge Agent to Matador streaming and leaves the local processor connection/subscribed-data view active.
- Updated Edge Agent and Edge ingest version reporting to `3.2.19`.

## 2026-05-04 - Version 3.2.18

- Reordered the Windows Edge Agent status rows so `Edge Agent Connectivity` appears above `B&G GoFree Connection`, followed by `Data Streaming`.
- Hardened Edge ingest so an already-open Edge websocket re-checks processor/client authorization before accepting each payload, preventing data storage immediately after processor deactivation, retirement, archival, or Edge revocation.
- Updated the Windows Edge Agent to clear streaming indicators and require re-enrolment when Matador rejects config or stream data because the processor is no longer authorized.
- Updated Edge Agent and Edge ingest version reporting to `3.2.18`.

## 2026-05-04 - Version 3.2.17

- Simplified the Windows Edge Agent main layout by renaming `Manual Processor IP` to `Processor IP` and placing `Auto Discover` and `Connect to Processor` alongside the startup options.
- Removed the visible `Save` button; server, enrolment, processor IP, and startup settings now auto-save as they change.
- Moved `Raw Data` out of the main operator controls and into the `Diagnostics` window as a technical-user action.
- Updated Edge Agent and Edge ingest version reporting to `3.2.17`.

## 2026-05-04 - Version 3.2.16

- Added a Windows Edge Agent `Diagnostics` window with refresh and JSON export for config, status lights, subscription IDs, latest subscribed values, and recent raw samples.
- Added admin-side Edge command lifecycle states so remote commands show as `No command`, `Pending pickup`, or `Picked up`.
- Updated Edge Agent and Edge ingest version reporting to `3.2.16`.

## 2026-05-04 - Version 3.2.15

- Added a `View Subscribed Data` popup table to the Windows Edge Agent showing configured metric subscriptions and their latest extracted values.
- Added the `Wind Observer` processor role, matching Coach Boat behavior while excluding GoFree subscription IDs `230`, `340`, `341`, `352`, `353`, `354`, `380`, `420`, `423`, `538`, and `539`.
- Added clearer Edge Agent health states to the admin processor cards and dashboard Edge icon tooltip.
- Reduced Edge Agent remote-command/config polling from 10 seconds to 30 seconds to cut routine log and database noise.
- Updated the Edge Agent version to `3.2.15`.

## 2026-05-04 - Version 3.2.14

- Disabled websocket protocol pings on the Edge Agent local B&G GoFree processor connection to avoid one-minute reconnect cycles on processors that stream data but do not answer ping/pong keepalives reliably.
- Kept normal websocket keepalives enabled for the encrypted upstream Matador connection.
- Updated the Edge Agent version to `3.2.14`.

## 2026-05-04 - Version 3.2.13

- Reworked dashboard latest telemetry SQL to use indexed per-metric lookups instead of `DISTINCT ON` over all processor telemetry history.
- Raised the latest-query timeout slightly to 2 seconds while keeping bounded failure behavior.

## 2026-05-04 - Version 3.2.12

- Added bounded database pool waits for dashboard authentication, config, latest-data, and health checks so pool pressure degrades gracefully instead of hanging requests.
- Added a short timeout around latest telemetry lookups to prevent slow historical reads from blocking the dashboard.
- Increased the default asyncpg pool size to 16 connections, configurable with `DB_POOL_MAX_SIZE`.

## 2026-05-04 - Version 3.2.11

- Reduced dashboard `/api/latest` request pressure by changing normal live polling from 10 Hz to 1 Hz and low-power polling to 3 seconds.
- Added a dashboard in-flight guard so slow `/api/latest` responses cannot overlap and pile up into nginx 504 timeouts.
- Fixed Edge Agent remote-command acknowledgement timestamp parsing so ISO strings from the Windows app do not trigger asyncpg datetime errors.
- Updated the Edge ingest version to `3.2.11`.

## 2026-05-04 - Version 3.2.10

- Fixed dashboard latest-data source selection so Matador Edge Agent processors always use the Edge-ingested PostgreSQL latest rows instead of stale collector live payload entries.

## 2026-05-04 - Version 3.2.9

- Moved CloudConnexa status refreshes off the dashboard event loop so slow external OpenVPN API calls cannot block unrelated dashboard/admin requests.
- Reduced the CloudConnexa HTTP request timeout to 5 seconds to prevent admin/config responses from waiting on long external API stalls.

## 2026-05-04 - Version 3.2.8

- Reduced local Edge Agent raw-data window noise by sampling displayed raw payloads instead of appending every telemetry frame.
- Cleared stale streaming interruption text once live data is successfully streaming to Matador again.
- Updated the Edge Agent version to `3.2.8`.

## 2026-05-04 - Version 3.2.7

- Reduced Edge Agent server load by throttling Edge ingest proxy-client status/raw JSON database updates instead of writing diagnostic rows for every telemetry frame.
- Reduced Edge Agent upstream payload size by sending full raw diagnostic processor JSON only periodically while continuing to stream live telemetry every frame.
- Updated the Edge Agent and Edge ingest versions to `3.2.7`.

## 2026-05-04 - Version 3.2.6

- Fixed the Windows Edge Agent stop flow so stopping immediately resets the stream button and prevents late frame acknowledgements from repainting the streaming status green.
- Added admin-requested Edge Agent commands for connect-to-processor, start streaming, and stop streaming.
- Added Edge Agent raw-data viewing locally in the app and remotely from the admin processor card using the latest processor-to-agent and agent-to-Matador payloads.
- Updated the Edge Agent and Edge ingest versions to `3.2.6`.

## 2026-05-04 - Version 3.2.5

- Improved the Windows Edge Agent interface with larger colour-changing status icons, clearer status labels, and a taller default window so the bottom message is visible.
- Renamed the Edge Agent status rows to `B&G GoFree Connection`, `Edge Agent Connectivity`, and `Data Streaming`.
- Updated the Edge Agent version to `3.2.5`.

## 2026-05-04 - Version 3.2.4

- Updated the Windows Edge Agent controls to use `Connect to Processor` and a `Stream to Server` button that changes to `Stop Streaming` while active.
- Added dedicated processor, collection-service, and upstream-streaming status icons to the Edge Agent UI.
- Updated the Edge Agent version to `3.2.4`.

## 2026-05-04 - Version 3.2.3

- Refined the Windows Edge Agent status area to three red/yellow/green indicators for processor link/data, collection service/config reachability, and upstream Matador streaming.
- Updated the Edge Agent version to `3.2.3`.

## 2026-05-04 - Version 3.2.2

- Added a Windows Edge Agent discovery picker so multiple Navico UDP/Bonjour GoFree websocket devices are shown with name, model, IP, port, and discovery source instead of silently selecting the first device.
- Added the app-window icon asset for the Edge Agent executable and source-run window.
- Updated the Edge Agent version to `3.2.2`.

## 2026-05-04 - Version 3.2.1

- Made the SQL Admin default processor storage overview avoid telemetry `count(*)` scans so `/api/admin/sql/overview?include_metrics=0` stays responsive on large databases.
- Fixed the dashboard processor query to qualify processor columns after joining Edge Agent proxy client records, preventing ambiguous-column errors on the live dashboard/config endpoints.
- Updated SQL Admin storage display to show unloaded storage counts clearly instead of forcing expensive counts by default.
- Added a `processor_storage_stats` cache table for processor telemetry, snapshot, event, and approximate byte counts.
- Added an admin-triggered background refresh action for processor storage counts so expensive table scans no longer block SQL Admin page loads.
- Added SQL Admin refresh status text and a manual "Refresh Storage Counts" button for recalculating cached processor storage after deletes, copies, or imports.
- Fixed the SQL Admin Metric Storage panel so opening it during a Processor Storage load queues a metric-count fetch instead of rendering a false empty state.
- Fixed the admin overview processor query to qualify processor columns after joining Edge Agent proxy client records, preventing ambiguous-column 500 errors on the admin dashboard.
- Fixed Edge Agent enrolment and revocation notices so processor-specific codes appear persistently inside the administered processor card instead of the temporary global banner.
- Updated the Windows Edge Agent app to remember the entered enrolment code locally, disable that input once a device token is stored, keep status labels stable, and report local processor websocket failures separately from upstream Matador stream failures.
- Updated Edge Agent processor IP handling so the admin processor IP is sent as a fallback suggestion, while the locally configured Edge Agent IP wins and is written back to the admin processor record during streaming.
- Added UDP multicast GoFree discovery to the Windows Edge Agent using Navico discovery announcements on `239.2.1.1:2052`, with the older `2050` discovery port and Bonjour retained as fallbacks.
- Updated the admin create-team default language to English and widened the Create Processor source-type selector.
- Colour-coded the dashboard Matador Edge icon: grey for offline, yellow for Edge connected without valid GoFree streaming data, and green for valid data streaming.

## 2026-05-04 - Version 3.2.0

- Added the Matador Edge Agent architecture for venues where OpenVPN / CloudConnexa cannot run on the boat network.
- Added `local_proxy` / `Matador Edge Agent` as a processor source type and `edge_agent` as a transport.
- Added `proxy_clients` device identity storage with one-time enrolment codes, hashed device tokens, authorization state, revocation state, and Edge Agent status timestamps.
- Added admin creation, enrolment-code regeneration, and revocation flows for Edge Agent processors.
- Added the independent `gofree_collector.edge_ingest` FastAPI service for encrypted Edge Agent enrolment, config delivery, and WSS telemetry ingest.
- Added both local `/health` and public `/edge/health` health checks for the Edge Agent ingest service.
- Added a deployable `gofree-edge-ingest.service` systemd unit and nginx `/edge/` proxy route.
- Added a first Windows-friendly `Matador Edge Agent` Tkinter app scaffold with enrolment, config refresh, optional startup behaviour, optional Bonjour discovery, manual IP fallback, WSS streaming, and local buffering during upstream outages.
- Updated the dashboard to display an app-window Edge Agent icon instead of an OpenVPN icon for `local_proxy` processors.
- Updated latest-data handling so processors missing from the main collector live cache can still be populated from PostgreSQL, allowing Edge Agent readings to appear on the dashboard.

## 2026-04-30 - Version 3.1.15

- Changed dashboard map fitting so weather station markers display as overlays but do not affect the default fleet bounds or initial zoom.

## 2026-04-30 - Version 3.1.14

- Added a per-station `Poll now` button on the Weather Stations admin page.
- Added an admin API endpoint that queues an immediate poll by marking an active weather station due for the independent collector service.

## 2026-04-30 - Version 3.1.13

- Added a known SOCIB platform-position fallback for Buoy Bahia de Palma (`143`) and rejected `0,0` as an invalid weather-station position.

## 2026-04-30 - Version 3.1.12

- Hardened SOCIB THREDDS position parsing so scalar `LAT` / `LON` values are read correctly and DataDiscovery coordinates remain the fallback.

## 2026-04-30 - Version 3.1.11

- Updated SOCIB Weather Station polling to prefer THREDDS numeric `WIN_DIR` / `WIN_SPE` data for known platforms such as Buoy Bahia de Palma (`143`).
- Kept SOCIB DataDiscovery as the admin-facing platform ID and fallback source when no THREDDS mapping exists.

## 2026-04-30 - Version 3.1.10

- Added SOCIB DataDiscovery as a Weather Stations source type.
- Added SOCIB platform ID support on the Weather Stations admin page, using platform `143` for Buoy Bahia de Palma.
- Added SOCIB collector parsing for `WIN_SPE` and `WIN_DIR`, including compass-sector to numeric-degree conversion when SOCIB returns average wind direction as text.

## 2026-04-30 - Version 3.1.9

- Made AEMET Weather Station polling tolerate non-UTF-8 JSON payloads by using the response charset and Latin-1 fallback decoding.

## 2026-04-30 - Version 3.1.8

- Fixed AEMET Weather Station creation so the create form sends the entered station code instead of looking up the wrong field id.

## 2026-04-30 - Version 3.1.7

- Changed AEMET Weather Stations to store a stable AEMET station code (`idema`) instead of temporary `/opendata/sh/...` data URLs.
- Updated the AEMET collector path to call `/api/observacion/convencional/datos/estacion/{idema}` and then follow the returned `datos` URL.
- Updated the Weather Stations admin UI to request an AEMET station code for AEMET sources.

## 2026-04-30 - Version 3.1.6

- Added AEMET OpenData as a third Weather Stations source type.
- Added `AEMET_API_KEY` environment configuration and AEMET URL support on the Weather Stations admin page.
- Added AEMET observation parsing for station name (`ubi`), latitude, longitude, wind speed (`vv`), and wind direction (`dv`), converting AEMET wind speed from m/s to knots for the map.

## 2026-04-30 - Version 3.1.5

- Made weather station map markers scale down as the user zooms out, matching the behaviour of other map overlays.

## 2026-04-30 - Version 3.1.4

- Restored the add-station fetch interval control to the original row.
- Gave configured station edit fields a roomier layout and moved each edit fetch interval onto a dedicated row.

## 2026-04-30 - Version 3.1.3

- Made weather station map markers smaller and neutral-coloured rather than TWS colour-coded.
- Updated the Weather Stations admin page wording to describe generic weather sources instead of only OceanDrivers.
- Moved the create-form fetch interval control onto a new row and renamed the station list eyebrow to `Station Status`.

## 2026-04-30 - Version 3.1.2

- Fixed METAR Weather Station creation by correcting the SQL insert placeholder count for `is_active` and `updated_by_user_id`.

## 2026-04-30 - Version 3.1.1

- Added METAR / CheckWX as a second Weather Stations source type alongside OceanDrivers.
- Added admin Weather Stations form support for ICAO airport codes, with METAR station positions populated from CheckWX decoded responses.
- Added `CHECKWX_API_KEY` environment configuration and server-side API-key use via the `X-API-Key` header.
- Updated WX map popups to distinguish OceanDrivers and METAR sources.

## 2026-04-30 - Version 3.1.0

- Added admin-managed OceanDrivers weather stations with global URL, latitude/longitude, active state, and configurable fetch interval settings.
- Added a separate `gofree_collector.weather_station_collector` service and systemd unit to scrape TWS/TWD independently of the main telemetry collector.
- Added a team feature flag for `Weather Stations` / `WX` so enabled teams can see global station markers on the dashboard map.
- Added Windycator-style WX map markers showing TWS in knots, an arrow rotated to TWD, and a popup with latest scrape status and station source details.
- Added the Playwright browser dependency required for rendered OceanDrivers SVG scraping.

## 2026-04-30 - Version 3.0.14

- Added a compact JSON output mode to the standalone OceanDrivers wind scraper for script-friendly `wind_speed` and `wind_direction` output.

## 2026-04-30 - Version 3.0.13

- Made the standalone OceanDrivers wind scraper tolerate SVG coordinate drift by falling back to nearby numeric rendered SVG candidates.

## 2026-04-30 - Version 3.0.12

- Added a standalone OceanDrivers CNArenal proof-of-concept scraper for rendered SVG wind speed and wind direction values.

## 2026-04-30 - Version 3.0.11

- Fixed a login 500 caused by a misplaced processor-restore snippet in the authentication handler.

## 2026-04-29 - Version 3.0.10

- Removed unnecessary Hide/Show controls from the Admin create Team/User/Processor cards so those creation panes stay visible.

## 2026-04-29 - Version 3.0.9

- Fixed the Admin create Team/User/Processor Hide/Show buttons so each button toggles its own form pane reliably.

## 2026-04-29 - Version 3.0.8

- Removed parenthetical true/magnetic wording from True Wind Direction labels, relying on `degT`/`degM` units instead.
- Added a safe remove action for retired processors that hides them from admin lists while preserving historical telemetry data and processor references, with automatic restoration if the same processor name is re-created later.
- Added friendlier service-operation errors when sudoers is missing passwordless systemctl access, and documented the `gofree-cloudconnexa.service` sudoers entries.

## 2026-04-29 - Version 3.0.7

- Made the live dashboard prefer magnetic wind direction and magnetic heading where NMEA0183 feeds provide both magnetic and true values.
- Added `TWD_MAG` to historical wind loading so magnetic direction can drive live trends, wind barbs, and Race Management course-axis calculations.
- Tidied the Admin Diagnostics source summary into grouped status cards, NMEA health counters, collapsible sentence details, and a separate last-message section.

## 2026-04-29 - Version 3.0.6

- Clarified dashboard and export-facing metric labels for NMEA direction values, distinguishing true, magnetic, and relative angles.
- Updated metric fallbacks and UI translations for NMEA-derived heading, wind direction, wind angle, and magnetic variation values.
- Documented that additional captured navigation/autopilot/depth/satellite sentence families remain diagnostics-only and are intentionally not stored as telemetry metrics.

## 2026-04-29 - Version 3.0.5

- Added `gofree_collector.nmea_replay`, a command-line NMEA0183 replay tool for testing Matador with captured NMEA text logs.
- Added TCP server replay mode so Matador can connect to a replayed NMEA source like a real instrument server.
- Added UDP send replay mode for testing datagram-style NMEA feeds.
- Added a systemd service template and runbook for repeatable NMEA replay testing on the server.

## 2026-04-29 - Version 3.0.4

- Added live NMEA health counters for parsed sentences, parsed metrics, unsupported sentences, checksum failures, invalid lines, empty lines, and seen sentence types.
- Added backend last-message age and quiet-feed classification for Diagnostics, distinguishing live, quiet, stale, and no-data sources without requiring database writes.
- Expanded Admin Diagnostics to show NMEA health counters and quiet-feed age beside each source.

## 2026-04-29 - Version 3.0.3

- Added live collector source health state to the in-memory diagnostics cache, including connecting, connected, receiving, reconnecting, and error states.
- Exposed per-source last message time, live message count, and last error details in Admin Diagnostics so quiet or disconnected NMEA0183 feeds are easier to distinguish from active feeds.
- Updated GoFree and NMEA collector paths to publish connection and message state without requiring any PostgreSQL schema changes.

## 2026-04-29 - Version 3.0.2

- Added NMEA0183 sentence-type tagging to live raw payloads so Diagnostics can identify sentence families such as `RMC`, `GGA`, `MWD`, and `VTG`.
- Expanded Admin Diagnostics summaries to show per-source NMEA sentence type counts, with fallback parsing for live sentences captured before the new tag is present.
- Hardened Admin processor editing so switching an existing source between GoFree and NMEA automatically normalizes transport and port values before saving.

## 2026-04-29 - Version 3.0.1

- Made Admin Diagnostics source-aware for mixed GoFree/NMEA0183 deployments, including source type, transport, port, live row counts, metric counts, validity counts, NMEA sentence counts, and the latest NMEA sentence seen.
- Updated diagnostics copy from GoFree-only raw JSON wording to generic live source/raw payload wording.
- Added an NMEA0183 setup and operations runbook covering source configuration, supported sentences, diagnostics, storage, and exports.

## 2026-04-29 - Version 3.0.0

- Started the Version 3 mixed-source telemetry architecture.
- Added processor `source_type` and `transport` fields so admins can configure either B&G GoFree websocket processors or NMEA0183 TCP/UDP telemetry feeds.
- Added NMEA0183 parsing for common GPS, wind, heading, speed, and UTC sentences including `RMC`, `GGA`, `GLL`, `MWD`, `MWV`, `VWR`, `HDG`, `HDM`, `HDT`, `VTG`, `VBW`, and `ZDA`.
- Routed active collector tasks by source type so GoFree websocket feeds and NMEA0183 feeds share the same live cache, notifications, diagnostics, exports, and telemetry storage tables.
- Added normalized NMEA-derived metric names for apparent wind, true wind angle, magnetic wind direction, magnetic/true heading, magnetic variation, boat speed through water, and source UTC context.
- Updated the admin processor creation and edit UI to expose source type, transport, and port settings while preserving GoFree defaults.

## 2026-04-29 - Version 2.0.103

- Tightened Mean Wind coverage checks so 10, 20, 30, and 60 minute averages only display when data spans the full selected window.

## 2026-04-29 - Version 2.0.102

- Added visible admin feedback and validation for processor creation failures.
- Normalized processor host inputs so pasted URLs like `http://192.168.33.109/` are stored as `192.168.33.109`.
- Made collector websocket ping interval and timeout configurable, with less aggressive 60 second defaults to reduce false disconnects from processors that miss websocket pongs.

## 2026-04-29 - Version 2.0.101

- Made initial dashboard trail loading non-blocking so slow `/api/trail/...` database queries can no longer prevent the main page from rendering and starting live polling.

## 2026-04-29 - Version 2.0.100

- Made the SQL Admin processor storage overview use lightweight row-count based size estimates instead of full-table row-size scans, preventing `/api/admin/sql/overview` from timing out on large telemetry tables.
- Split SQL Admin storage loading so the expensive metric breakdown only runs when the Metric Storage panel is opened.

## 2026-04-29 - Version 2.0.99

- Hardened the collector database writer so a failed telemetry insert batch is logged and dropped without stopping future database writes.
- Added collector background-task logging so writer, sampler, live cache, Telegram, and notification task failures are visible in journald.

## 2026-04-29 - Version 2.0.98

- Made Trend waterfalls use the same historical wind buffer as Mean Wind when the dedicated trend buffer only has the live samples collected since page open.
- Opening Trends now also refreshes the broader historical wind buffer, so previous wind data is available even when Mean Wind is collapsed.

## 2026-04-29 - Version 2.0.97

- Added an optional `end` timestamp to the history API and made trend backfills request history ending at the latest live TWS/TWD sample, so trends load pre-existing history instead of only samples collected since the page opened.

## 2026-04-29 - Version 2.0.96

- Anchored trend waterfall windows to the newest available sample timestamp instead of browser time, preventing blank tails and apparent resets when telemetry timestamps lag slightly.

## 2026-04-29 - Version 2.0.95

- Changed trend history refreshes to merge sampled API history with dense live samples instead of replacing the chart buffer, preventing waterfall charts from repeatedly resetting with large blank sections.

## 2026-04-29 - Version 2.0.94

- Relaxed Mean Wind checks further so downsampled historical API rows can populate averages when Trends has usable history.

## 2026-04-29 - Version 2.0.93

- Relaxed Mean Wind window coverage checks so averages populate from current continuous samples after page load instead of requiring full-window historical coverage from the exact window start.

## 2026-04-29 - Version 2.0.92

- Shortened Admin Feature Flag table labels while keeping the full labels available as hover tooltips.
- Ensured the Race Committee Race Timer remains centred below the wind averages and above live GPS position.
- Made the websocket simulator add `RACE_TIMER` metric `230` as a rolling five minute countdown before subscription filtering, so simulator streams include the timer even when the dump lacks it.

## 2026-04-29 - Version 2.0.91

- Added OpenVPN client service status and start, stop, and restart controls to the Admin Service Operations panel.
- Added `OPENVPN_CLIENT_SYSTEMD_SERVICE` for deployments where the OpenVPN client systemd unit has a custom name.
- Added audit log entries for OpenVPN client start, stop, and restart requests.

## 2026-04-29 - Version 2.0.90

- Preserved the open admin team/create panel state across user actions like reset password, Telegram linking, and user updates, so those commands no longer collapse the team windows.
- Made the per-user and per-processor admin action buttons explicit `type="button"` controls to avoid browser form-submit style refreshes in the admin panel.

## 2026-04-29 - Version 2.0.89

- Ordered the admin utility page links alphabetically as Audit, Diagnostics, Messaging, and SQL.
- Reordered Feature Flag table columns alphabetically for both Sailing Team and Race Management matrices.
- Reduced the Diagnostics per-processor `Export 10s` button footprint and separated it from the live row count.

## 2026-04-29 - Version 2.0.88

- Changed the SQL Admin page to load a lightweight processor list by default and only run the heavier storage overview query when the collapsed storage panels are opened.
- Stopped SQL delete/copy completion from immediately forcing a storage overview reload, avoiding misleading `/api/admin/sql/overview returned 504` banners after successful commands.
- Added per-processor 10 second live raw JSON exports on the Diagnostics page, saved client-side as `.txt` files from the collector live cache.

## 2026-04-29 - Version 2.0.87

- Added automatic rolling monthly `telemetry_readings` partition creation on service startup for already-partitioned databases.
- Added `DB_PARTITION_MONTHS_AHEAD` to control how many future monthly partitions are maintained.
- Added `DB_STORE_RAW_JSONB`, defaulting to `false`, so new telemetry rows keep the compatibility `raw` column but store `{}` instead of full historical payloads.
- Added an admin-only Diagnostics page and API for inspecting the live collector raw JSON cache without reading historical raw JSON from PostgreSQL.

## 2026-04-29 - Version 2.0.86

- Ensured replay loading explicitly hydrates and renders Mean Wind averages from replay preamble/frame data.
- Moved SQL Admin storage tables below the archive/copy/delete controls and made Processor Storage and Metric Storage collapsed by default.

## 2026-04-29 - Version 2.0.85

- Added `DB_SNAPSHOT_INTERVAL_SECONDS`, defaulting to `0`, so telemetry snapshots are disabled unless explicitly re-enabled at a configured interval.
- Expanded change-only storage to slow-changing start-line, bias, line-length, and UTC date metrics while keeping CSV exports forward-filled.
- Added metric-level storage reporting to the SQL Admin page to identify high-volume telemetry data types.
- Added a controlled PostgreSQL migration script for converting `telemetry_readings` to monthly date partitions during a maintenance window.
- Added a metric/processor/time index to support metric-level storage analysis and historical lookups.
- Serialized schema bootstrap with a PostgreSQL advisory lock so simultaneous service restarts cannot race while creating indexes.
- Limited change-only startup seeding to active processor/metric lookups so the collector live-cache server is not delayed by a broad historical scan.
- Fixed the telemetry partition migration so the metric/processor/time index is renamed on the backup table before creating the replacement partitioned index.

## 2026-04-29 - Version 2.0.84

- Made the SQL Processor Storage table sortable by every column and drag-reorderable, with the chosen column order saved in the browser.
- Optimized start-line and ping-time telemetry storage so unchanged values are not duplicated in `telemetry_readings`.
- Seeded CSV exports with the latest stored start-line and ping-time values before the export window so those columns remain populated on every exported row.

## 2026-04-29 - Version 2.0.83

- Stopped storing `PITCH_RATE` and `ROLL_RATE` in telemetry history while keeping them subscribed and available in the live cache for motion-sensor detection.
- Removed live-only motion-sensor metrics from snapshot completeness checks.

## 2026-04-29 - Version 2.0.82

- Simplified the Messaging admin page to one send button that follows the selected channel.
- Shortened Telegram and WhatsApp provider request timeouts and return clearer admin test-message errors when a provider times out or rejects a send.

## 2026-04-29 - Version 2.0.81

- Added admin-only SQL operations for processor storage estimates, SQL archive downloads, confirmed day deletion, and copying a day's telemetry between processors.
- Added an admin-only Messaging page for sending dummy Telegram and WhatsApp examples of every programmed system notification type.

## 2026-04-29 - Version 2.0.80

- Forecast API calls are now one-shot per processor per page session and only fire when the Forecast pane is opened or already open while waiting for GPS.

## 2026-04-28 - Version 2.0.79

- Local dashboard timestamp displays now use a 24-hour clock while still respecting the user's local timezone.

## 2026-04-28 - Version 2.0.78

- Removed the orange overlay styling from connected OpenVPN status icons so the supplied icon displays normally, with only disconnected states greyed out.

## 2026-04-28 - Version 2.0.77

- Updated the OpenVPN dashboard status asset to the requested orange-and-blue CloudConnexa icon and stopped the VPN CSS from flattening it to a single colour.

## 2026-04-28 - Version 2.0.76

- Replaced the dashboard OpenVPN status image with a dedicated SVG asset so CloudConnexa status uses the correct OpenVPN icon instead of the motion sensor artwork.

## 2026-04-28 - Version 2.0.75

- CloudConnexa API calls now include a CURL-style user agent so Cloudflare does not reject Python's default HTTP client before OAuth reaches OpenVPN.

## 2026-04-28 - Version 2.0.74

- CloudConnexa OAuth credentials are now sent in a form-encoded POST body instead of the URL query string to avoid Cloudflare blocking the token request.

## 2026-04-28 - Version 2.0.73

- CloudConnexa requests now use Swagger-style `Accept: */*` headers and preserve exact failing endpoint/status/body details in the admin debug response.

## 2026-04-28 - Version 2.0.72

- Added an admin-only CloudConnexa debug API that reports fetched networks, CIDRs, processor matches, and match methods for diagnosing OpenVPN icon visibility.

## 2026-04-28 - Version 2.0.71

- CloudConnexa processor matching now normalizes processor/network names and reports the match method in the OpenVPN tooltip.
- CloudConnexa status refresh now treats embedded network connectors as a status source and uses safer page sizes for documented list endpoints.

## 2026-04-28 - Version 2.0.70

- Aligned CloudConnexa network, IP service, and connector reads with the Swagger-documented paginated endpoints, including beta fallbacks.
- CloudConnexa matching now also uses CIDRs present directly on Network route/subnet payloads and treats `ONLINE_WITH_ISSUES` connectors as connected.

## 2026-04-28 - Version 2.0.69

- OpenVPN icons now remain visible with a clean unavailable/permissions tooltip when the primary CloudConnexa status refresh fails.

## 2026-04-28 - Version 2.0.68

- CloudConnexa optional endpoint permission failures no longer abort the whole OpenVPN status refresh.
- Processor OpenVPN tooltips no longer show raw global API errors such as `HTTP Error 403: Forbidden`.

## 2026-04-28 - Version 2.0.67

- Disabled `Start` map layers are now fully excluded from Fleet Map auto-fit bounds, so hidden start ping positions no longer affect the initial map view.
- Added processor-level CloudConnexa match detail so unmatched or offline OpenVPN network status is visible in the dashboard tooltip instead of failing silently.

## 2026-04-28 - Version 2.0.66

- Removed the processor GPS position text from the Forecast pane footer.
- Forecast timestamps now parse Open-Meteo forecast times explicitly as UTC, honour the user's UTC/local time-display setting, and update immediately when the dropdown changes.
- Replay transport controls are now hidden until replay data has been loaded.
- Start Lines and Start Marks map controls are now hidden whenever the team's `Start` feature flag is disabled.
- OpenVPN CloudConnexa processor icons now show an offline/grey state when a matching network is found but disconnected, instead of only appearing when online.
- Hardened CloudConnexa IP-service matching to support additional API response shapes, related IP service IDs, nested network references, service-name matching, and recursively discovered CIDR strings.
- Admin team user role dropdowns now preserve each user's actual role instead of defaulting every user to Viewer.
- Team Settings WhatsApp save and verification feedback now stays inside the relevant user card.
- Race Management WhatsApp position delivery was restored to two messages: full text/Google Maps link first, followed by a native WhatsApp location pin.
- Race Management send buttons now only appear after a Mark Layer recipient is selected and only for channels the selected recipient has linked or verified.
- Added spacing between Telegram and WhatsApp send buttons in ODM and Mark Management panes.
- Replay visibility now follows the team `Replay` feature flag without requiring `?replay=1`.

## 2026-04-28 - Version 2.0.65

- Added a team feature flag for Forecast panes.
- Added Open-Meteo GFS and ECMWF 10 m wind forecasts per processor using the processor's current GPS position.
- Renamed Historical Wind to Mean Wind across the dashboard and feature flags.
- Added replay pre-roll data so Mean Wind averages are populated immediately at replay start.
- Fixed the replay modal close button rendering as mojibake.

## 2026-04-28 - Version 2.0.64

- Added a team-level `WhatsApp Notifications` feature flag and removed the old per-user WhatsApp enable checkbox.
- WhatsApp reset links, processor notifications, and Race Management position sends now require the team feature flag as well as a verified user phone number.
- User save feedback now appears in the modified user card instead of the global status banner.
- Fixed the simulator start/stop control so the button text changes immediately with the colour.
- Added HTTP response logging for failed Wasender sends to make WhatsApp delivery failures visible in service logs.

## 2026-04-28 - Version 2.0.63

- Added optional WasenderAPI WhatsApp delivery alongside Telegram.
- Added WhatsApp phone, enablement, and verification fields for users in Admin and Team Settings.
- Password reset links and processor notifications can now be delivered by WhatsApp when a user has WhatsApp enabled.
- Race Management position sends now offer separate Telegram and WhatsApp buttons, using `#0088CC` and `#128c7e`; WhatsApp sends include both the existing Google Maps link text and a native WhatsApp location pin.

## 2026-04-28 - Version 2.0.62

- Replaced the admin `Delete Team` primary action with `Deactivate Team` for active teams.
- Deactivated teams now show `Reactivate Team` plus `Delete Team`, and hard deletion is only allowed after deactivation.
- Team cards now show the team active/deactivated state directly in the summary pills.

## 2026-04-28 - Version 2.0.61

- Fixed admin team default-language persistence by returning `default_locale` in the admin overview payload, so saved team language choices now reload correctly instead of always appearing as Spanish.
- Password reset Telegram notifications now use the target user/team language (`en`, `es`, `fr`, or `it`) when the reset link is sent to a linked Telegram chat.

## 2026-04-28 - Version 2.0.60

- Password reset links are now sent automatically via Telegram when the target user has a linked Telegram chat.
- Reset-link notices in Admin and Team Settings now indicate when the link was also delivered to Telegram.

## 2026-04-28 - Version 2.0.59

- Added a logged-in self-service Change Password flow from the main dashboard.
- Moved generated password reset links into the bottom of the relevant user cards in Admin and Team Settings instead of showing them only in the page-wide status banner.

## 2026-04-28 - Version 2.0.58

- Removed the dashboard Start Polling and Stop Polling buttons. Live polling still starts automatically, and replay retains its own dedicated controls.

## 2026-04-28 - Version 2.0.57

- Standardized all language dropdown options to always display in native form: `English`, `Español`, `Français`, and `Italiano`, regardless of the currently active UI language.

## 2026-04-28 - Version 2.0.56

- Fixed map Trails and Wind Barbs buttons so they no longer appear active when those overlays are disabled by default.
- Added the missing French and Italian translations for Race Committee live wind and GPS labels.

## 2026-04-28 - Version 2.0.55

- Race Management Telegram position sends now use the sender's current dashboard language for each send, so switching between Italian, French, English, or Spanish takes effect immediately.

## 2026-04-28 - Version 2.0.54

- Disabled map trails and wind barbs by default on dashboard load. Both overlays can still be enabled manually from the map controls.

## 2026-04-28 - Version 2.0.53

- Fixed Race Committee live panel headings so `Live True Wind Direction`, `Live True Wind Speed`, `GPS Latitude`, and `GPS Longitude` now stay translated when admins switch dashboard language.

## 2026-04-28 - Version 2.0.52

- Restricted team-scoped user roles by team role. Sailing Teams now allow `Performance Director`, `Coach`, `Data Analyst`, and `Viewer`; Race Management teams now allow `Race Officer`, `Mark Layer`, and `Viewer`.
- Enforced those role restrictions in both admin user management and Team Settings user creation, and updated the UI dropdowns so only valid role choices are offered for each team type.

## 2026-04-28 - Version 2.0.51

- Added the `Race Officer` user role with the same team settings permissions as `Performance Director`.
- Added team-scoped user creation from the Team Settings page for Performance Directors and Race Officers.
- Added a `Telegram Notifications` feature flag that controls whether the Team Settings Telegram and alert threshold panel is shown.
- Added Race Officer role documentation and updated team-role guides for the new permissions.

## 2026-04-27 - Version 2.0.50

- Added server-side Telegram localization for English, Spanish, French, and Italian.
- Changed processor online/offline alerts, daily summaries, Telegram link/help responses, chat ID replies, and Race Management position sends to use the recipient team default language when available.
- Added structured Race Management send-position metadata so Telegram messages no longer inherit the sender browser language.

## 2026-04-27 - Version 2.0.49

- Completed a hard-coded UI string audit across Dashboard, Admin, Team Settings, Audit Log, Data Calendar, Login, and Reset Password pages.
- Routed newly generated Admin, Team Settings, Audit Log, dashboard export/status, replay, and reset-password text through the shared i18n dictionaries.
- Added team default language controls in Admin and widened database locale constraints so English, Spanish, French, and Italian can all be saved.
- Applied locale-aware month and weekday rendering to the Data Calendar and localized login error display for known authentication failures.

## 2026-04-27 - Version 2.0.48

- Added French and Italian as supported platform UI languages alongside English and Spanish.
- Added French and Italian locale dictionaries for the login, dashboard shell, Data Calendar, Admin, Team Settings, and Race Management controls while keeping sailing-specific metric terminology and CSV headings unchanged.
- Updated the frontend and backend locale allow-lists so `fr` and `it` can be selected, saved, and loaded from user preferences.

## 2026-04-27 - Version 2.0.47

- Restricted live dashboard language switching to admins only. Non-admin users now choose language on the login page and keep it for the session until they sign out and back in.

## 2026-04-27 - Version 2.0.46

- Added audit logging for CSV export requests so both direct processor exports and Data Calendar-driven downloads are recorded in the admin audit page.

## 2026-04-27 - Version 2.0.45

- Added an admin-only audit page and API for browsing recent platform audit entries, including actor, team, action, entity, and stored details.

## 2026-04-27 - Version 2.0.44

- Simplified the Admin simulator controls to a single status-aware start/stop button that turns green for `Start Simulator` when inactive and red for `Stop Simulator` when active.

## 2026-04-27 - Version 2.0.43

- Fixed Admin user activation controls so the deactivate action visibly updates the card state, toggles to `Reactivate`, and only shows permanent delete once the account is inactive.

## 2026-04-27 - Version 2.0.42

- Added GoFree simulator service controls to the Admin Operations panel, including status plus start, stop, and restart actions.

## 2026-04-27 - Version 2.0.41

- Combined the Race Management `ODM Management` and `Mark Management` feature flags into a single `Course Management` flag across the backend, admin feature matrix, and dashboard gating.

## 2026-04-27 - Version 2.0.40

- Updated Course Axis mode switching so changing from `Automatic` to `Manual` pre-populates the manual axis input from the current live TWD, falling back to the current automatic axis when live TWD is unavailable.

## 2026-04-27 - Version 2.0.39

- Fixed dashboard language switching so generated processor panels, Race Management panes, metric labels, and live panel text redraw immediately when the user changes language.
- Preserved panel UI state during language redraws, including open/collapsed sections, export dates, trend-window choices, and Race Management input values.

## 2026-04-27 - Version 2.0.38

- Fixed processor reordering so Race Committee cards are included in the saved processor order payload, preventing `/api/team/processor-order` from returning `400` for Race Management teams.

## 2026-04-27 - Version 2.0.37

- Translated Race Management feature panes, including `Trends`, `Course Axis`, `ODM Management`, `Mark Management`, line/beat length controls, Mark Layer recipient selectors, and send buttons.
- Localized generated Course Axis, ODM, and Windward Mark status/context text so calculated position messages follow the active UI language.

## 2026-04-27 - Version 2.0.36

- Added translated metric-name keys for core telemetry values, including TWS, TWD, GPS, start-line values, pitch/roll rates, and related dashboard labels.
- Updated the dashboard metric rendering path to prefer locale-specific metric names before falling back to backend long names.
- Continued the Admin and Team Settings translation pass by covering additional visible generated labels and common operation text.

## 2026-04-27 - Version 2.0.35

- Extended the multilingual UI pass into the Admin and Team Settings pages, including translated page headers, creation cards, operations panels, notification settings, and common show/hide/loading labels.
- Expanded the English and Spanish locale dictionaries with administration, operations, feature access, and team-settings terminology.

## 2026-04-27 - Version 2.0.34

- Added the first multilingual platform foundation with English and Spanish locale dictionaries, Spanish as the preferred default, and a shared frontend translation helper.
- Added user and team locale fields to the database schema, exposed user locale through `/api/config`, and allowed users to persist language changes through `/api/me/preferences`.
- Added language selectors and Spanish translations for the login page, dashboard shell, map controls, replay shell, and Data Calendar shell.

## 2026-04-27 - Version 2.0.33

- Added 5-second damping to Race Management ODM and Windward Mark generated positions so displayed coordinates and map overlays move more smoothly.

## 2026-04-27 - Version 2.0.32

- Added a shared `Course Axis` section to Race Committee cards between `Trends` and `ODM Management` whenever `ODM Management` or `Mark Management` is enabled.
- Added automatic/manual course-axis controls, including configurable TWD averaging minutes in automatic mode and `+` / `-` one-degree manual stepping.
- Updated ODM and Windward Mark calculations to use the shared course axis instead of directly reading TWD.

## 2026-04-27 - Version 2.0.31

- Fixed Race Management ODM and Windward Mark position generation by reading the computed Leaflet destination coordinates correctly from `lat`/`lng` instead of treating them like array indexes.

## 2026-04-27 - Version 2.0.30

- Switched Race Committee GPS, ODM, and Windward Mark coordinate displays to Degrees and Decimal Minutes (DMM).
- Fixed race-management degree-symbol rendering so Line Bearing and related values no longer show mojibake like `Â°`.
- Updated ODM and Windward Mark calculations to use a rolling 3-minute average Race Committee GPS position as the base for generated coordinates.

## 2026-04-27 - Version 2.0.29

- Added an `Export` team feature flag and wired it into both Sailing Team and Race Management feature access tables.
- Made the Export flag control the per-processor Export pane and Data Calendar visibility/access for the team.
- Added live GPS latitude and longitude display to Race Committee processors below the wind averages and above Trends.

## 2026-04-27 - Version 2.0.28

- Made the websocket simulator path handling more forgiving, including support for accepting any path with `--path '*'`.
- Added simulator connection diagnostics so logs show when a client connects and when the first replay frame is sent.
- Expanded the simulator runbook with troubleshooting commands for listener, simulator, and collector checks.

## 2026-04-27 - Version 2.0.27

- Added admin-side processor host editing so processor IP addresses can be updated directly from the Admin page.
- Added safe processor retirement and reactivation in Admin. Retiring a processor stops future live use by setting it inactive while preserving all historical database data.
- Updated the Admin team overview to show both active and retired processors so they can still be reviewed and reactivated later.

## 2026-04-27 - Version 2.0.26

- Added a B&G GoFree websocket simulator that replays newline-delimited websocket dumps and accepts the collector's normal `DataReq` subscriptions.
- Added a `gofree-simulator.service` systemd template for running the simulator on the Ubuntu host.
- Added simulator deployment and dummy processor instructions in `docs/websocket_simulator.md`.

## 2026-04-26 - Version 2.0.25

- Preserved the admin page create-panel and team-panel open/closed state across refreshes so generating a Telegram link code no longer collapses the users pane.

## 2026-04-26 - Version 2.0.24

- Moved the Race Committee `Trends` section above `ODM Management` and centered the five Race Committee average tiles on the page.
- Updated Team Settings user cards so inline Telegram link codes sit as a full-width block at the bottom of each card.
- Updated the admin user cards so generated Telegram link codes also render inline at the bottom of the relevant user card instead of only appearing in the page banner.

## 2026-04-26 - Version 2.0.23

- Made `ODM Management` and `Mark Management` collapsible Race Management panes so they behave like the existing `Trends` sections.
- Restored the `Export` section for `Race Committee` processors in the Race Management dashboard layout.
- Tightened the admin Feature Access table layout with wrapped headers and removed the greyed-out `Start` column from `Race Management` feature flags.
- Aligned the `Temporary Password` field toward the top of the Create User card so it lines up better with the adjacent notes block.

## 2026-04-26 - Version 2.0.22

- Added optional OpenVPN CloudConnexa API integration driven by `.env` credentials so the admin health summary can show connected VPN networks as `Active Connections`.
- Added processor-to-CloudConnexa network matching using LAN IP subnets so dashboard processors can surface an OpenVPN status icon when their corresponding network is online.
- Added CloudConnexa configuration keys to `.env.example`.

## 2026-04-26 - Version 2.0.21

- Added the `Mark Layer` user role for Telegram-first Race Management position delivery and exposed it across the admin/team user management flows.
- Added admin-managed global dashboard notice controls with red/yellow/green styling, backed by new singleton `app_settings`.
- Added Race Management ODM and Mark Management tools to the dashboard, including calculated positions, DDM coordinate display, map overlays, and Telegram send actions to linked `Mark Layer` users.
- Allowed Race Management teams to fetch the TWS/TWD history needed for ODM and mark calculations even when ordinary historical wind panels are not enabled.

## 2026-04-26 - Version 2.0.20

- Added extra spacing between the `Team Role` selector and the `Create Team` action on the admin page.
- Updated the Race Management dashboard so Race Committee cards span the full page width, letting the average TWD/TWS row breathe across the layout.
- Made the Race Management Trends pane collapsible like the other dashboard sections.

## 2026-04-26 - Version 2.0.19

- Aligned the `Create Team`, `Create User`, and `Create Processor` action buttons horizontally on the admin page by making the create cards equal-height and anchoring their action rows to the bottom.

## 2026-04-26 - Version 2.0.18

- Split the admin feature-flag matrix by team role so `Sailing Team` and `Race Management` teams now have separate tables and role-appropriate flags.
- Added `ODM Management` and `Mark Management` feature flags for `Race Management` teams and fixed `Start` off for that role.
- Kept the existing Sailing Team dashboard intact while adding a dedicated Race Management layout with horizontal `Race Committee` cards, race-management map copy, and start features removed.

## 2026-04-26 - Version 2.0.17

- Restricted replay mode so it is admin-only by default and added a per-team `Replay` feature flag that admins can enable for selected teams.
- Enforced the replay permission server-side on `/api/replay/{processor}` and exposed the new flag in the admin feature-flag matrix.

## 2026-04-26 - Version 2.0.16

- Fixed replay button visibility by forwarding the current dashboard query string to `/api/config`, so `?replay=1` now correctly enables the replay launcher and toolbar.

## 2026-04-26 - Version 2.0.15

- Renamed the dashboard and login experience to `Live Telemetry`, updated the login subtitle, and made the main top banner scroll with the page instead of sticking to the viewport.
- Added admin-managed team banner messaging with red/yellow/green styling, plus new editable team roles (`Sailing Team`, `Race Management`) and processor roles (`Coach Boat`, `Race Committee`, `Mark Boat`, `Land Station`).
- Reworked replay mode so `?replay=1` shows a dedicated replay launcher beside `Data Calendar`, moves replay start/step/stop controls into the main toolbar, and loads replay settings from an in-page modal.
- Hid the `Last data` text once a processor has been unseen for one hour or more.
- Rebuilt wind barbs to use weather-barb speed notation based on rounded 50/10/5-knot feathers and pennants, and fed the map wind-field barbs from blended `TWS` as well as `TWD`.

## 2026-04-25 - Version 2.0.14

- Removed the Team Settings shortcut from the dedicated Data Calendar page so the calendar view stays focused on exports.

## 2026-04-25 - Version 2.0.13

- Moved the yearly Data Calendar out of Team Settings into its own dedicated page linked from the main dashboard header.
- Broadened Data Calendar access to `Coach`, `Performance Director`, and `Data Analyst` users while keeping coach exports limited to the assigned boat only.
- Added a dedicated calendar context API so the page can present only the processors each role is allowed to export.

## 2026-04-25 - Version 2.0.12

- Added `gofree_collector.migrate_cronos`, a reusable importer for moving legacy Cronos per-processor telemetry tables into Matador `telemetry_readings`.
- Made the importer conservative by default so it backfills only rows older than the earliest existing Matador reading per processor unless overlap is explicitly allowed.
- Added Cronos migration documentation and command examples under `docs/migrating_from_cronos.md`.

## 2026-04-24 - Version 2.0.11

- Removed dashboard and collector service state from the admin health summary so it stays focused on plain numeric fleet metrics.
- Added dashboard service status and restart controls to the admin Operations panel alongside the existing collector controls.
- Changed admin health-summary value styling so all count values render in white instead of using status colors.
- Added `DASHBOARD_SYSTEMD_SERVICE` to the environment example for deployments that enable web-based service control.

## 2026-04-24 - Version 2.0.10

- Added an admin health summary card showing total systems, live/stale/offline counts, active connections, and dashboard/collector service state.
- Added Telegram chat ID display to admin user cards for linked accounts.

## 2026-04-24 - Version 2.0.9

- Updated the offline Telegram notification text to include a direct call to visit Matador and export the current day's data for analysis.

## 2026-04-24 - Version 2.0.8

- Changed the Team Settings deactivate action into a true deactivate/reactivate toggle, with inactive users showing a red role chip and a follow-up delete action.
- Updated the dashboard motion-sensor icon so it sits in a right-aligned header slot and greys out whenever the processor is not live.
- Replaced the Team Settings calendar export browser prompt with an in-page processor-selection modal.

## 2026-04-24 - Version 2.0.7

- Added Team Settings feedback for inactive accounts, including an inactive role-chip state, a green deactivated button state, and a follow-up delete action for manageable users once they are inactive.
- Added team-scoped permanent user deletion from Team Settings for `Coach`, `Data Analyst`, and `Viewer` accounts after deactivation.
- Added `Pitch Rate` and `Roll Rate` metric support and a motion-sensor indicator on the main dashboard using the provided accelerometer icon.
- Added a yearly `Data Calendar` to Team Settings that highlights UTC dates with logged data and lets the user export CSVs for the relevant processor.
- Added an HTTPS nginx deployment template for `matador.torodatasystems.eu`.
- Kept team deletion non-destructive by allowing it only when no historical telemetry or event data exists for that team.

## 2026-04-24 - Version 2.0.6

- Added admin-only permanent user deletion alongside the existing deactivate action, with backend cleanup of linked references before the user row is removed.
- Added admin-only team deletion for empty teams with no users, processors, or historical telemetry/events.
- Updated the admin UI to show `Delete User` and `Delete Team` actions with confirmation prompts.

## 2026-04-24 - Version 2.0.5

- Strengthened ping-time rendering so UTC/local switching now falls back through numeric timestamp sources when string parsing is unavailable.
- Improved Admin create-user validation and error reporting so failed user creation now shows a visible status message instead of silently failing in the browser.
- Changed the Create Processor notes block to span the full width of the form card.

## 2026-04-24 - Version 2.0.4

- Fixed ping timestamp formatting so `Port End Ping Time` and `Starboard End Ping Time` re-render reliably when switching between `UTC` and local time display.
- Added the new `Viewer` role as a team-scoped read-only user type with no exports and no Telegram workflow access.
- Hid processor export controls for `Viewer` users in the dashboard and blocked export requests server-side for that role.
- Updated Admin and Team Settings role handling so `Viewer` appears in the correct places while Telegram linking remains limited to coaches and data analysts.
- Changed Admin team panels to load collapsed by default for a tidier overview.
- Added role-by-role help documentation under `docs/roles/` for `Admin`, `Performance Director`, `Data Analyst`, `Coach`, and `Viewer`.

## 2026-04-24 - Version 2.0.3

- Added an admin-only collector control panel with live service status and a web-triggered restart action for `gofree-collector.service`.
- Added configuration flags for collector control so the restart button is only active when explicitly enabled on the server.
- Documented the dedicated Linux service-user and sudoers setup needed to run the dashboard/collector without `root` while still allowing collector restarts from the web UI.

## 2026-04-24 - Version 2.0.2

- Changed Team Settings Telegram link-code feedback so the generated code appears inside the relevant user card instead of the global page banner.
- Made the inline Team Settings Telegram code display persistent for the current page session instead of auto-hiding after a few seconds.

## 2026-04-24 - Version 2.0.1

- Updated the admin UI so `Create Team` uses one field per row and explains the purpose of the team slug.
- Simplified processor creation by removing user-editable websocket port/path fields and fixing them to `2053` and `/`.
- Fixed existing-user team selectors on the admin page so the currently assigned team is shown as the default selection.
- Removed the unnecessary `Assigned processor: -` display for `Performance Director` and `Data Analyst` users.
- Rebuilt Team Settings to match the newer admin UI style and added team-scoped password reset, deactivation, Telegram linking, and coach processor assignment actions for `Coach` and `Data Analyst` users.
- Updated ping-time displays so `Port End Ping Time` and `Starboard End Ping Time` follow the UTC/local display toggle.

## 2026-04-24 - Version 2

- Re-architected the project from the old single-team deployment into a multi-team hosted platform now defined as `Version 2`.
- Replaced the shared dashboard password with per-user login, server-side sessions, password reset tokens, and role-based access.
- Added PostgreSQL-backed platform tables for teams, users, processors, coach assignments, feature flags, notification settings, Telegram contacts/link requests, sessions, and audit logging.
- Replaced the old per-processor-table model with shared telemetry tables keyed by team and processor.
- Updated the collector to load active processors from PostgreSQL, write shared telemetry rows, and keep the local live cache endpoint for the dashboard.
- Added admin team switching so global admins can monitor any team from the main dashboard.
- Added per-user UTC/local time display preference support.
- Added team-scoped and role-aware dashboard permissions, including coach export restriction to the assigned processor.
- Added Telegram `/link CODE` linking support with the new contact/link-request tables.
- Added admin and team-settings pages for team management, notification settings, Telegram linking, feature flags, coach assignment, and account deactivation.
- Updated the admin UI with collapsible horizontal creation panels, grouped team sections, a feature-flag matrix, and cleaner role labels.
- Refined the admin page forms into labeled card-based layouts with cleaner team, user, and processor management blocks.
- Added drag-and-drop processor panel ordering on the main dashboard, persisted per team through `processors.sort_order`.
- Updated team settings to match the admin UI language and added team-scoped password reset, deactivation, Telegram linking, and coach assignment actions for coaches and data analysts.
- Simplified processor creation by fixing websocket port/path to the platform defaults and clarified team slug usage in the admin form.
- Updated the main dashboard header so Team Settings and Admin match the existing button styling and the team/time dropdowns are readable.
- Added `gofree_collector.bootstrap` for initial admin creation.
- Added `argon2-cffi` for password hashing.
- Rewrote the README around the `Version 2` architecture and current Ubuntu/nginx/systemd deployment flow.

## 2026-04-23 - Revision 85

- Animated the TWS overlay wind barbs so they drift through the enabled wind-field circles in the wind-travel direction, similar to Windy-style flow overlays.
- Kept overlay barb direction blended from contributing TWD values in overlap areas while animating the barb positions.
- Updated the Telegram test documentation to use the deployed virtual-environment Python interpreter so required packages such as `asyncpg` are available.

## 2026-04-23 - Revision 84

- Changed the `TWS Overlay` Experimental control from a global fleet toggle to a boat-specific toggle.
- Kept the TWS overlay radius shared across all enabled boat overlays, with every Experimental radius input staying in sync.
- Kept overlap interpolation between whichever boat-specific overlays are currently enabled.

## 2026-04-23 - Revision 83

- Changed the Experimental `Time for Wind to Arrive` calculation from fixed boat pairs to dynamic selection across any other configured boat.
- Used the quickest valid wind-arrival candidate when one of the other boats is windward within 30 degrees of that source boat's TWD.
- Updated the wind-arrival card caption to `Time for Wind to Arrive` and named the selected source boat in the panel metadata.

## 2026-04-23 - Revision 82

- Fixed the TWS overlay canvas sizing inside its Leaflet pane by applying explicit pixel dimensions on every render instead of relying on percentage sizing.
- Raised the dedicated TWS pane to just below Leaflet's normal overlay pane so the wind field stays visible above tiles while tracks, start lines, marks, and boats remain on top.

## 2026-04-23 - Revision 81

- Moved the TWS overlay canvas into a dedicated Leaflet pane between the tile pane and the normal overlay pane so it stays above map tiles but below tracks, start lines, marks, and boats.
- Positioned the TWS overlay canvas using Leaflet layer coordinates so it remains aligned through pan and zoom redraws.

## 2026-04-23 - Revision 80

- Moved the TWS overlay canvas below fleet-map tracks, start lines, start marks, and boat markers while keeping it above the base map tiles.
- Kept the overlay non-interactive so map clicks, popups, and marker interaction continue to target the visible fleet objects.

## 2026-04-23 - Revision 79

- Changed Historical Wind 10, 20, 30, and 60 minute TWS/TWD averages to require data coverage across the full selected window before displaying a value.
- Left Historical Wind averages blank when only a shorter partial period is available, while allowing small start/end timing tolerance and short internal gaps.
- Updated README documentation for the Historical Wind full-window coverage rule.

## 2026-04-23 - Revision 78

- Added wind barbs inside the live TWS overlay circles, spaced on a 0.25 nautical mile grid.
- Used each live system's TWD for overlay barb direction and blended TWD direction in overlapping overlay areas.
- Skipped overlay barbs when the map is too zoomed out for 0.25 nautical mile spacing to remain legible.

## 2026-04-23 - Revision 77

- Added a one-decimal nautical mile radius input to each `Experimental` panel for the live TWS wind-field overlay.
- Replaced the fixed 1.0 nautical mile overlay radius with the shared configurable radius value.
- Extended the TWS overlay colour scale, clamping, and map legend from 0-21 knots to 0-25 knots.

## 2026-04-23 - Revision 76

- Changed TWS wind-field overlap blending to use linear radius weighting so intersecting 1 nautical mile circles fade directly from one boat's live TWS colour into the other's.
- Clarified README overlay notes with the 1.5 nautical mile / 2 kn / 20 kn example: the 0.5 nautical mile overlap now transitions from 2 kn through the midpoint blend to 20 kn.

## 2026-04-23 - Revision 75

- Raised the live TWS wind-field canvas above Leaflet map tiles and overlay panes so the overlay stays visible during normal map rendering and zoom animation.
- Kept the TWS overlay below boat markers, tooltips, and popups so map interaction remains readable.

## 2026-04-23 - Revision 74

- Added a live TWS wind-field overlay for the fleet map.
- Added a `TWS Overlay` toggle button to each system's collapsed-by-default `Experimental` panel.
- Drew a 1 nautical mile colour-scaled circle around each live boat using the same blue-to-red TWS palette shown in the reference image.
- Blended overlapping 1 nautical mile circles by interpolating the contributing boats' live TWS values in real time.
- Added a fleet-map TWS legend and updated the overlay automatically during live movement, replay movement, and map pan/zoom changes.

## 2026-04-22 - Revision 73

- Removed the remaining live wind barb from boat markers.
- Kept wind barbs only on sampled track/replay positions.
- Updated README wind-barb notes to describe track-only barbs.

## 2026-04-22 - Revision 72

- Removed wind barbs from start-line markers while keeping boat and track barbs.
- Changed all wind barbs to black instead of processor-coloured.
- Reduced wind barb sizes by roughly half while preserving zoom-scaled behaviour.
- Added UTC timestamps to track wind-barb hover tooltips.
- Updated README wind-barb documentation.

## 2026-04-22 - Revision 71

- Anchored wind barb tails to the underlying boat, track, or start-pin position instead of centering the icon.
- Made wind barb icon size scale with map zoom so wide views are less cluttered and close views remain readable.
- Refreshed wind barb icons on map zoom changes without changing the stored barb data.
- Documented zoom-scaled and tail-anchored barb behaviour in the README.

## 2026-04-22 - Revision 70

- Rotated wind barb icons 180 degrees so they indicate where the wind is coming from.
- Increased wind barb icon size for better visibility on the map.
- Removed hover tooltips from live boat/start-pin wind barbs while keeping start-pin click popups intact.
- Increased track wind-barb sampling to every 1 minute.
- Added hover tooltips to track wind barbs showing TWD and TWS.

## 2026-04-22 - Revision 69

- Added map wind barbs based on each processor's TWD.
- Added live wind barbs at each boat marker and both start-line pins.
- Added sparse track wind barbs sampled every two minutes from live trails or replay paths.
- Added a Wind Barbs map-layer toggle.
- Documented wind barb behaviour in the README.

## 2026-04-22 - Revision 68

- Removed the dashboard Compact mode control and related compact layout logic.
- Updated replay mode so Trends and Historical Wind use the replay clock and populate from replay frames.
- Added a collapsed-by-default Experimental panel to each system column.
- Added paired wind-arrival estimates for ILCA6/ILCA7 and FX/49er using paired GPS positions, windward-boat TWD, and a recent TWS average.
- Greyed out the wind-arrival estimate when the paired boat is not within 30 degrees of the windward TWD line.

## 2026-04-22 - Revision 67

- Added all/single-system selection to hidden replay mode.
- Added a replay Step button for frame-by-frame inspection.
- Added replay GPS trails so historical boat movement is drawn as replay progresses.
- Cleared replay state cleanly when loading or stopping replay.
- Updated replay documentation to describe system selection, stepping, speed control, and replay trails.

## 2026-04-22 - Revision 66

- Added a hidden dashboard replay mode, enabled with `?replay=1`.
- Added replay controls for UTC start time, duration, speed, play, pause, and stop.
- Added `/api/replay/{processor}` to read logged PostgreSQL rows in capped replay windows.
- Reused the existing live dashboard panels and map during replay while marking systems as `Replay`.
- Documented the hidden replay endpoint and access flag in the README.

## 2026-04-22 - Revision 65

- Added a commented `GOFREE_FORMATS_JSON` example to `.env` with an explanation of when to use it.

## 2026-04-22 - Revision 64

- Added a 60 minute wind trend window button.
- Renamed the live wind section from `Wind` to `Live Wind`.
- Added a collapsed-by-default `Historical Wind` panel under live wind.
- Added 10, 20, 30, and 60 minute historical averages for TWS and TWD.
- Kept historical wind loading lazy so it only refreshes when the panel is open and visible.

## 2026-04-22 - Revision 63

- Added a shared metric formatting layer for storage, dashboard display, CSV export, units, and fallback long names.
- Added `GOFREE_FORMATS_JSON` support so individual metric precision, units, and names can be overridden from `.env`.
- Updated live-cache and PostgreSQL API rows to include `display_value` and configured display units.
- Kept Bias Advantage displaying at 0 decimals while retaining 1-decimal storage/export precision.
- Documented the new formatting override options in the README and `.env.example`.

## 2026-04-22 - Revision 62

- Added `/api/status` with per-processor state, latest data age, and recent data-quality counts.
- Made dashboard stale/offline thresholds configurable through `DASHBOARD_STALE_AFTER_SECONDS` and `DASHBOARD_OFFLINE_AFTER_SECONDS`.
- Added last-data age text to each processor panel.
- Added a dashboard Compact mode toggle.
- Added fleet-map layer toggles for trails, start lines, and start marks.
- Added separated raw/damped/display/unit/name metadata columns for readings when database permissions allow column maintenance.
- Added per-processor 1 Hz snapshot tables with JSON values and quality counters.
- Added Telegram repeat cooldowns, optional daily summaries, and a `python -m gofree_collector.telegram_test` helper.
- Added pre-start setup checks to the systemd service templates.
- Updated README and environment examples for the new operational settings.

## 2026-04-22 - Revision 61

- Made the Start and Trends sections collapsed by default on all devices.
- Added a 3-minute offline timeout for dashboard panels.
- Changed panels to return to the waiting-style hidden data state when their system is offline.
- Kept the existing stale state before offline so brief data gaps are visible without hiding the panel.

## 2026-04-22 - Revision 60

- Added mobile/iOS dashboard optimisations.
- Slowed polling while the page is hidden and added a Low Power toggle for 1 Hz live polling.
- Changed trend rendering to use `requestAnimationFrame` with frame-rate caps.
- Skipped trend rendering and history refreshes when trend panels are collapsed, hidden, or off-screen.
- Added DOM text caching to avoid unnecessary text rewrites during high-frequency polling.
- Throttled boat marker and start-line map updates to reduce Leaflet work on mobile devices.
- Capped canvas pixel ratio to reduce Retina canvas drawing cost.
- Deferred Leaflet tile loading until the map has live data to show.
- Added CSS containment to reduce layout and paint cost inside panels and cards.

## 2026-04-22 - Revision 59

- Added a Useful Bash Commands section to the README covering service control, logs, environment loading, PostgreSQL checks, API checks, exports, Telegram, firewall, and browser access.
- Added `PROJECT_CHAT_REFERENCE.md` as a readable saved reference of the project conversation, architecture, troubleshooting, deployment notes, and feature history.

## 2026-04-22 - Revision 58

- Added per-boat map follow buttons next to Follow Fleet.
- Made each boat follow button pan the fleet map with that boat's latest GPS position.
- Hid boat follow buttons when the related system has no live GPS data or is stale/offline.
- Cleared boat-follow mode when the user manually moves or zooms the map.

## 2026-04-22 - Revision 57

- Added Start Line Length to the Port and Starboard start marker map popups.

## 2026-04-22 - Revision 56

- Added `UTC` after the time in Telegram online and offline notification messages.
- Updated Telegram notification examples in the README.

## 2026-04-22 - Revision 55

- Allowed `TELEGRAM_CHAT_ID` to contain multiple comma-separated chat IDs.
- Updated Telegram delivery to send each notification to every configured chat.
- Added documentation and `.env.example` guidance for multiple Telegram recipients.

## 2026-04-22 - Revision 54

- Added optional Telegram notifications to the collector.
- Added per-processor state tracking for online notifications after 15 seconds of valid data and offline notifications after 30 seconds without valid data.
- Included latest damped `TWS` and `TWD` values in online messages.
- Added Telegram environment variables to `.env.example`, `.env`, and setup documentation.
- Kept Telegram disabled by default until bot token and chat ID are configured.

## 2026-04-22 - Revision 53

- Changed wind waterfall rendering to use the current browser clock so samples visibly age down the selected trend window in real time.
- Added low-rate live TWS/TWD samples from `/api/latest` into the trend buffers between database history refreshes.
- Added a periodic background history refresh for trend data, with duplicate request protection.
- Kept the trend history API at 200 sampled points while allowing the browser view to move continuously.

## 2026-04-22 - Revision 52

- Changed CSV export rows to carry forward the latest valid metric value when a metric does not publish inside that exact one-second bucket.
- Kept explicitly invalid metric readings blank in exports by clearing the carried value until a new valid reading arrives.
- Documented why CSV rows can otherwise contain blank cells and how export fill-forward now behaves.

## 2026-04-22 - Revision 51

- Reduced wind trend history responses to 200 sampled points per selected window.
- Stacked TWS and TWD trend cards vertically so each graph has the full panel width.
- Increased the default collector live cache refresh rate to 10 Hz and dashboard polling to 10 Hz for more responsive live wind values.
- Changed collector readings to prefer GoFree `dampedVal` whenever it is available, so live display and 1 Hz database writes use damped values.
- Updated setup documentation and `.env.example` for the 10 Hz live cache default.

## 2026-04-22 - Revision 50

- Separated live dashboard display formatting from database storage rounding.
- Preserved original GoFree `valStr` for live dashboard display instead of regenerating it from raw values.
- Used GoFree `dampedVal` for live numeric values when the payload marks data as damped.
- Added per-metric live cache rate limiting through `COLLECTOR_LIVE_CACHE_MAX_HZ`, defaulting to 2 Hz.

## 2026-04-22 - Revision 49

- Added a local-only in-memory latest-value cache endpoint to the collector for more responsive live dashboard values.
- Updated dashboard `/api/latest` to read the collector live cache first and fall back to PostgreSQL when unavailable.
- Documented `COLLECTOR_LIVE_HOST`, `COLLECTOR_LIVE_PORT`, and `DASHBOARD_LIVE_LATEST_URL`.

## 2026-04-22 - Revision 48

- Increased dashboard latest-value polling from every 2 seconds to every 1 second for more responsive live wind values.

## 2026-04-22 - Revision 47

- Allowed collector startup to continue when the database user can insert into existing tables but does not own them.
- Changed optional schema/index maintenance privilege failures into warnings instead of fatal startup errors.

## 2026-04-22 - Revision 46

- Added popups to port and starboard start-line markers on the fleet map.
- Included relevant marker ping time, Square Line to Wind, and Bias Advantage in meters in each popup.

## 2026-04-22 - Revision 45

- Added storage-layer metric precision rounding so new inserts are rounded even if collector-side rounding is bypassed.
- Added export-side metric rounding so older unrounded rows still export at the requested precision.
- Added `sql/round_existing_metric_precision.sql` for one-time cleanup of existing PostgreSQL rows.
- Documented how to run the existing-row precision cleanup script.

## 2026-04-22 - Revision 44

- Aligned metric card values horizontally by reserving a consistent header area above each value.
- Kept Race Timer and Start Line Bias values on the same visual baseline even when labels wrap.

## 2026-04-22 - Revision 43

- Repositioned metric units to the top-right of metric cards while keeping them below the title line.

## 2026-04-22 - Revision 42

- Restored dashboard Bias Advantage display to 0 decimal places while leaving collector storage precision unchanged.

## 2026-04-22 - Revision 41

- Rounded stored collector values for `COG`, `HEADING`, `TWD`, `START_LINE_BEARING`, and `START_LINE_BIAS` to 0 decimal places.
- Rounded stored collector values for `SOG`, `TWS`, and `BIAS_ADVANTAGE` to 1 decimal place.
- Applied the same precision to stored `value_text` and raw display fields for those metrics.
- Updated the dashboard Bias Advantage value to display 1 decimal place.

## 2026-04-22 - Revision 40

- Moved metric units to their own line directly below each metric label.
- Restored a unit line for `Square Line to Wind Direction` while keeping its value numeric-only.
- Standardized metric value sizing and centered alignment, including Race Timer.

## 2026-04-22 - Revision 39

- Moved metric units into the top-right of metric cards below the label.
- Removed the degree symbol from the derived `Square Line to Wind Direction` value.
- Removed the square-line calculation text from the derived metric card.

## 2026-04-22 - Revision 38

- Updated the fleet map subtitle to describe coach boat positions and start line pings.

## 2026-04-22 - Revision 37

- Kept ping time values white instead of applying freshness colours.
- Kept invalid metric values white instead of applying amber or red stale colouring.

## 2026-04-22 - Revision 36

- Removed per-value age/status text from dashboard metric cards.
- Added freshness colouring to metric and ping values: amber after 10 seconds and red after 30 seconds.
- Applied the same freshness colouring to the derived square-line value based on its source bearing age.

## 2026-04-22 - Revision 35

- Removed the `newest at top` and sampled-point count helper text from trend footers.
- Kept the selected trend window and stale-data age text visible.

## 2026-04-22 - Revision 34

- Restyled the Start section bottom area so `Square Line to Wind Direction` appears as a wide card.
- Changed port and starboard end ping times from large metric cards to compact list rows below the square-line card.
- Simplified square-line metadata to show the source bearing calculation and unit.

## 2026-04-22 - Revision 33

- Kept the Export panel visible while a boat is waiting for live data.
- Continued hiding only live-data panels such as Wind, Start, and Trends during the waiting state.

## 2026-04-22 - Revision 32

- Hid the fleet map panel while all boat panels are still waiting for data.
- Restored the fleet map automatically once at least one boat has received database data.

## 2026-04-22 - Revision 31

- Changed login route return annotations to generic `Response` objects for FastAPI compatibility.
- Kept the same login and redirect behavior while avoiding startup-time response model parsing issues.

## 2026-04-22 - Revision 30

- Hid Wind, Start, Trends, and Export sections while a boat panel is still waiting for its first database row.
- Kept waiting boat panels compact with only boat name, IP address, and waiting status visible.

## 2026-04-22 - Revision 29

- Added a server-side password login page before the dashboard loads.
- Protected dashboard API and CSV export endpoints with a signed HTTP-only session cookie.
- Added `/login` and `/logout` routes for dashboard session handling.
- Added `DASHBOARD_PASSWORD` and `DASHBOARD_SESSION_SECRET` configuration documentation.

## 2026-04-22 - Revision 28

- Split CSV export timestamps into `date`, `time_utc`, and `offset` columns.
- Kept CSV exports in the existing one-row-per-second, metric-columns format.

## 2026-04-22 - Revision 27

- Changed CSV exports from row-per-metric output to row-per-second output.
- Added one CSV column per configured metric, excluding `UTC_DATE` and `UTC_TIME` because the row already has a UTC timestamp.
- Kept the existing normalized database structure and pivoted the data during export instead of requiring a migration.
- Updated the dashboard Export panel text to describe the new output shape.

## 2026-04-22 - Revision 26

- Reduced trend history sampling to match 1 Hz dashboard use.
- Limited 10, 20, and 30 minute trend calls to 600, 1200, and 1800 points respectively.
- Added a hard 1800-point ceiling for trend history API responses to reduce database and network load.

## 2026-04-22 - Revision 25

- Reduced GPS trail sampling to 900 points, matching 15 minutes at 1 Hz.
- Added `/api/export/{processor}?date=YYYY-MM-DD` for per-system CSV downloads from PostgreSQL.
- Streamed CSV exports row-by-row to avoid holding a full day's export in memory.
- Added a collapsible Export panel under Trends with a date picker and Export button.
- Documented the dashboard export endpoint and UTC date behavior.

## 2026-04-22 - Revision 24

- Added `/api/trail/{processor}` endpoint for 15-minute GPS trail data.
- Rendered boat trails from historical GPS position rows instead of only page-session points.
- Matched each trail color to its boat color.
- Limited trail data to 5000 sampled points per boat.

## 2026-04-22 - Revision 23

- Updated dashboard display-name mapping so `HEADING` is presented as `Heading`.

## 2026-04-21 - Revision 22

- Added Heading and SOG to the boat marker popup on the fleet map.

## 2026-04-21 - Revision 21

- Added derived `Square Line to Wind Direction` value at the bottom of each Start panel.
- Calculated the derived value as `(START_LINE_BEARING + 90) mod 360`.
- Added stale/age metadata for the derived value based on the source Start Line Bearing row.

## 2026-04-21 - Revision 20

- Added history window start/end metadata to the dashboard API.
- Changed waterfall rendering to position samples by timestamp age within the selected window.
- Made stale trend data visually age downward, leaving empty space at the top when no recent data has arrived.
- Added latest-sample age text to trend footers when data is stale.

## 2026-04-21 - Revision 19

- Added configurable database write rate limiting with `DB_WRITE_RATE_LIMIT_HZ`.
- Defaulted database writes to 1 Hz per processor/metric/instance.
- Added a latest-sample buffer so fast websocket updates are received but only the newest pending value is written each interval.
- Documented how to disable write rate limiting by setting `DB_WRITE_RATE_LIMIT_HZ=0`.

## 2026-04-21 - Revision 18

- Changed dashboard history sampling to spread up to 5000 points across the full selected timeframe.
- Preserved oldest-to-newest history ordering for waterfall rendering.
- Fixed 10, 20, and 30 minute trend windows showing the same newest 5000-point slice when data density is high.

## 2026-04-21 - Revision 17

- Made the fleet map pannable by disabling automatic re-centering after manual pan or zoom.
- Added a `Follow Fleet` button to re-enable automatic map fitting.

## 2026-04-21 - Revision 16

- Limited dashboard history API responses to 5000 points per selected metric and timeframe.
- Kept returned history rows ordered oldest-to-newest for graph rendering.
- Updated dashboard display-name preference so key Start metrics use the long configured names.

## 2026-04-21 - Revision 15

- Changed dashboard section titles to title case: `Wind`, `Start`, and `Trends`.
- Restyled trend controls and waterfall cards to more closely match the provided reference.
- Moved min, average, and max labels into the top of each waterfall graph.
- Added trend footers showing window, newest-at-top note, sample count, and average.

## 2026-04-21 - Revision 14

- Displayed Bias Advantage with zero decimal places on the dashboard.
- Made the Start section collapsible per boat.
- Made the Wind Trends section collapsible per boat.

## 2026-04-21 - Revision 13

- Removed the dashboard navigation metric panel for heading, COG, and GPS position.
- Added GoFree long-name metadata to dashboard API responses from raw payload fields.
- Updated metric labels to use GoFree long names when available.
- Reworked wind trends into separate TWS and TWD waterfall graphs.
- Added 10, 20, and 30 minute trend window controls per boat.
- Added min, max, and average stats with the average centered in each waterfall graph.
- Added circular averaging and wraparound handling for TWD angles.
- Updated the fleet map to use GPS positions, red port start mark, green starboard start mark, and boat-colored start lines.

## 2026-04-21 - Revision 12

- Changed the dashboard root route to return an explicit HTML response.
- Added `/health` endpoint for quick dashboard service checks.
- Added troubleshooting steps for cases where `/api/latest` works but the browser page does not load.

## 2026-04-21 - Revision 11

- Changed the PostgreSQL dashboard service from port `8080` to `8081` to avoid collisions with the old websocket proxy.
- Added troubleshooting notes for the `Upgrade required` message shown by websocket-only services.

## 2026-04-21 - Revision 10

- Added a PostgreSQL-backed dashboard API using FastAPI.
- Added `web/index.html`, a browser dashboard that polls `/api/latest` instead of connecting to the old websocket proxy.
- Added `/api/config`, `/api/latest`, and `/api/history/{processor}/{metric_name}` endpoints.
- Added `deploy/gofree-dashboard.service` for running the dashboard with systemd.
- Added FastAPI and Uvicorn dependencies.
- Documented dashboard deployment and API test commands.

## 2026-04-21 - Revision 9

- Added `sql/admin_grant_gofree_permissions.sql` as a one-time handoff script for the database admin.
- Documented deployment options when the operator does not have admin access to the DigitalOcean database.
- Clarified that the collector needs table-creation rights at first startup and insert rights afterward.

## 2026-04-21 - Revision 8

- Added friendlier setup-check errors for DNS, login, and schema privilege failures.
- Updated DigitalOcean setup guidance to use port `25060`.
- Added PostgreSQL grants needed when the `gofree` user cannot create tables in `public`.
- Added DNS troubleshooting for temporary hostname resolution failures.

## 2026-04-21 - Revision 7

- Updated database test and schema setup instructions to explicitly load `.env` before running `psql`.
- Added troubleshooting guidance for the local socket error that appears when `DATABASE_URL` is empty.

## 2026-04-21 - Revision 6

- Added a local `.env` file with the provided DigitalOcean PostgreSQL connection string.
- Updated `.env.example` to use the DigitalOcean host, port `25060`, database `gofree-collection`, and `sslmode=require`.
- Kept the real database password out of template documentation.

## 2026-04-21 - Revision 5

- Added dynamic GoFree metric ID configuration through `GOFREE_METRICS_JSON`.
- Updated subscriptions so configured future IDs are requested from every processor.
- Updated metric-name mapping so new IDs are stored under their configured names.
- Documented how adding `UTC_TIME` with ID `35` is stored without schema changes.

## 2026-04-21 - Revision 4

- Added this changelog file.
- Established the convention that future project changes should be recorded here.

## 2026-04-21 - Revision 3

- Changed the database name to `gofree-collection`.
- Reworked storage from one shared `telemetry_readings` table to one table per processor.
- Added automatic table creation for every configured processor at collector startup.
- Added support for dynamic processors through `GOFREE_PROCESSORS_JSON`.
- Updated setup checks to create and verify each configured processor table.
- Updated PostgreSQL examples for quoted table names such as `"49er"`.
- Updated Grafana and commissioning queries for the per-processor table layout.

## 2026-04-21 - Revision 2

- Removed the local PostgreSQL hosting assumption.
- Removed `docker-compose.yml`.
- Updated setup instructions to use a remote PostgreSQL server.
- Updated `.env.example` to point at a remote database host.
- Added instructions for removing a locally installed PostgreSQL server from the collector box.
- Added remote PostgreSQL connection testing guidance.
- Added SSL connection string guidance using `sslmode=require`.

## 2026-04-21 - Revision 1

- Removed CSV export requirements from the project scope.
- Deleted the CSV export module.
- Focused the project on real-time GoFree websocket collection into PostgreSQL.
- Added `gofree_collector/check_setup.py` to validate configuration, database connection, and schema.
- Rewrote the README as beginner-friendly Ubuntu setup instructions.
- Added `.gitignore`.

## 2026-04-21 - Initial Scaffold

- Created an async Python collector for B&G Hercules GoFree websocket data.
- Added default processors:
  - `ILCA6` at `192.168.6.10`
  - `ILCA7` at `192.168.7.10`
  - `FX` at `192.168.8.10`
  - `49er` at `192.168.9.10`
- Added subscriptions for the requested GoFree data IDs.
- Added PostgreSQL storage using batched async writes.
- Added environment-based configuration.
- Added systemd service template.
- Added initial PostgreSQL schema.
- Added README setup and Grafana query examples.
