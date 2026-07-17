from __future__ import annotations

import asyncio
import ipaddress
import json
import logging
import socket
import subprocess
import time
from contextlib import suppress
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlsplit


LOGGER = logging.getLogger("matador_pi_edge_agent.navico_advertiser")

NAVICO_GROUP = "239.2.1.1"
NAVICO_APP_PORT = 2053
NAVICO_DEVICE_PORT = 2052
MDNS_GROUP = "224.0.0.251"
MDNS_PORT = 5353
DEFAULT_ICON_REVISION = "toro-favicon-1"
DEFAULT_ICON_PATH = "/icon.png"
DEFAULT_ICON_HTTP_PORT = 80
DEFAULT_INTERVAL_MS = 10000


class NavicoAdvertiserConfigError(ValueError):
    """Raised when the Navico HTML5 advertiser configuration is unsafe."""


class NavicoAdvertiserInterfaceError(RuntimeError):
    """Raised when the configured MFD-facing interface is not present."""


def default_icon_file() -> Path:
    return Path(__file__).resolve().parents[1] / "public" / "icon.png"


@dataclass(frozen=True)
class NavicoAdvertiserSettings:
    enabled: bool = True
    interface: str = "eth0"
    interval_ms: int = DEFAULT_INTERVAL_MS
    app_name: str = "Matador"
    source: str = "TORO"
    feature_name: str = "TORO HTML5 App"
    description: str = "HTML5 app advertised to Navico, B&G, Simrad, and Lowrance MFDs."
    app_url: str = "https://matador.torodatasystems.eu/"
    icon_path: str = DEFAULT_ICON_PATH
    icon_revision: str = DEFAULT_ICON_REVISION
    icon_file: Path = field(default_factory=default_icon_file)
    icon_http_port: int = DEFAULT_ICON_HTTP_PORT
    only_show_on_client_ip: bool = True
    multicast_group: str = NAVICO_GROUP
    multicast_port: int = NAVICO_APP_PORT
    device_broadcast_enabled: bool = False
    mdns_enabled: bool = False
    navico_nav_ws_enabled: bool = False


def parse_bool(value: Any, *, name: str) -> bool:
    if isinstance(value, bool):
        return value
    normalized = str(value).strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise NavicoAdvertiserConfigError(f"{name} must be true or false.")


def validate_absolute_http_url(value: str, *, name: str) -> str:
    text = str(value or "").strip()
    parsed = urlsplit(text)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise NavicoAdvertiserConfigError(f"{name} must be an absolute HTTP or HTTPS URL.")
    if parsed.username or parsed.password:
        raise NavicoAdvertiserConfigError(f"{name} must not contain embedded credentials.")
    return text


def validate_navico_settings(settings: NavicoAdvertiserSettings) -> NavicoAdvertiserSettings:
    if not settings.enabled:
        return settings
    if not settings.interface.strip():
        raise NavicoAdvertiserConfigError("Navico advertiser interface must not be empty.")
    for name, value in (
        ("app name", settings.app_name),
        ("source", settings.source),
        ("feature name", settings.feature_name),
        ("icon revision", settings.icon_revision),
    ):
        if not str(value or "").strip():
            raise NavicoAdvertiserConfigError(f"Navico advertiser {name} must not be empty.")
    if not 1000 <= int(settings.interval_ms) <= 86400000:
        raise NavicoAdvertiserConfigError("Navico advertiser interval must be between 1000 and 86400000 ms.")
    if not 1 <= int(settings.icon_http_port) <= 65535:
        raise NavicoAdvertiserConfigError("Navico icon HTTP port must be between 1 and 65535.")
    if settings.multicast_group != NAVICO_GROUP or int(settings.multicast_port) != NAVICO_APP_PORT:
        raise NavicoAdvertiserConfigError("Production Navico advertiser must send only to UDP 239.2.1.1:2053.")
    if settings.device_broadcast_enabled:
        raise NavicoAdvertiserConfigError("UDP 2052 TORO device announcements are disabled in the production profile.")
    if settings.mdns_enabled:
        raise NavicoAdvertiserConfigError("TORO mDNS announcements are disabled in the production profile.")
    if settings.navico_nav_ws_enabled:
        raise NavicoAdvertiserConfigError("navico-nav-ws is not implemented by the Matador Pi Edge Agent.")
    if not settings.icon_path.startswith("/"):
        raise NavicoAdvertiserConfigError("Navico icon path must start with '/'.")
    validate_absolute_http_url(settings.app_url, name="Navico advertiser app URL")
    if not settings.icon_file.exists():
        raise NavicoAdvertiserConfigError(f"Navico icon file does not exist: {settings.icon_file}")
    return settings


def icon_url_for_address(address: str, settings: NavicoAdvertiserSettings) -> str:
    port = "" if int(settings.icon_http_port) == 80 else f":{int(settings.icon_http_port)}"
    return f"http://{address}{port}{settings.icon_path}?v={settings.icon_revision}"


def build_navico_descriptor(address: str, settings: NavicoAdvertiserSettings) -> dict[str, Any]:
    ipaddress.ip_address(address)
    return {
        "Version": "1",
        "Source": settings.source,
        "IP": address,
        "FeatureName": settings.feature_name,
        "Text": [
            {
                "Language": "en",
                "Name": settings.app_name,
                "Description": settings.description,
            }
        ],
        "Icon": icon_url_for_address(address, settings),
        "URL": settings.app_url,
        "OnlyShowOnClientIP": "true" if settings.only_show_on_client_ip else "false",
        "BrowserPanel": {
            "Enable": True,
            "ProgressBarEnable": True,
            "MenuText": [{"Language": "en", "Name": "Home"}],
        },
    }


def serialize_navico_descriptor(address: str, settings: NavicoAdvertiserSettings) -> bytes:
    return json.dumps(build_navico_descriptor(address, settings), separators=(",", ":")).encode("utf-8")


def interface_exists(interface: str) -> bool:
    try:
        socket.if_nametoindex(interface)
        return True
    except OSError:
        return (Path("/sys/class/net") / interface).exists()


def resolve_interface_ipv4(interface: str) -> str | None:
    if not interface_exists(interface):
        raise NavicoAdvertiserInterfaceError(f"Configured MFD interface '{interface}' was not found.")
    try:
        result = subprocess.run(
            ["ip", "-o", "-4", "addr", "show", "dev", interface],
            text=True,
            capture_output=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        LOGGER.debug("Unable to inspect IPv4 address for %s: %s", interface, exc)
        return None
    if result.returncode != 0:
        return None
    for line in result.stdout.splitlines():
        parts = line.split()
        if "inet" not in parts:
            continue
        value = parts[parts.index("inet") + 1].split("/", 1)[0]
        try:
            address = ipaddress.ip_address(value)
        except ValueError:
            continue
        if address.version == 4 and not address.is_loopback and not address.is_multicast:
            return str(address)
    return None


def send_navico_udp_advertisement(address: str, payload: bytes, settings: NavicoAdvertiserSettings) -> None:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    try:
        sock.bind((address, 0))
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_IF, socket.inet_aton(address))
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 1)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_LOOP, 0)
        sock.sendto(payload, (settings.multicast_group, int(settings.multicast_port)))
    finally:
        sock.close()


class NavicoHtml5Advertiser:
    def __init__(
        self,
        settings: NavicoAdvertiserSettings,
        *,
        address_resolver: Callable[[str], str | None] = resolve_interface_ipv4,
        interface_checker: Callable[[str], bool] = interface_exists,
        sender: Callable[[str, bytes, NavicoAdvertiserSettings], None] = send_navico_udp_advertisement,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        self.settings = settings
        self.address_resolver = address_resolver
        self.interface_checker = interface_checker
        self.sender = sender
        self.monotonic = monotonic
        self.started_at_monotonic: float | None = None
        self.selected_address: str | None = None
        self.payload: dict[str, Any] | None = None
        self.payload_bytes: bytes | None = None
        self.send_count = 0
        self.error_count = 0
        self.last_send_at: str | None = None
        self.last_error: str | None = None
        self.last_error_at: str | None = None
        self.last_address_change_at: str | None = None
        self.running = False
        self.icon_server_running = False
        self._last_send_monotonic: float | None = None
        self._icon_server: asyncio.AbstractServer | None = None
        self._icon_server_address: str | None = None
        self._first_success_logged = False

    def status(self) -> dict[str, Any]:
        uptime = None
        if self.started_at_monotonic is not None:
            uptime = max(0.0, self.monotonic() - self.started_at_monotonic)
        return {
            "enabled": self.settings.enabled,
            "running": self.running,
            "interface": self.settings.interface,
            "selected_address": self.selected_address,
            "interval_ms": self.settings.interval_ms,
            "multicast_group": self.settings.multicast_group,
            "multicast_port": self.settings.multicast_port,
            "udp_2052_enabled": self.settings.device_broadcast_enabled,
            "mdns_enabled": self.settings.mdns_enabled,
            "navico_nav_ws_enabled": self.settings.navico_nav_ws_enabled,
            "app_name": self.settings.app_name,
            "source": self.settings.source,
            "feature_name": self.settings.feature_name,
            "app_url": self.settings.app_url,
            "icon_url": icon_url_for_address(self.selected_address, self.settings) if self.selected_address else None,
            "icon_http_port": self.settings.icon_http_port,
            "icon_server_running": self.icon_server_running,
            "send_count": self.send_count,
            "error_count": self.error_count,
            "last_send_at": self.last_send_at,
            "last_error": self.last_error,
            "last_error_at": self.last_error_at,
            "last_address_change_at": self.last_address_change_at,
            "uptime_seconds": uptime,
            "payload": self.payload,
        }

    def set_selected_address(self, address: str) -> bool:
        if address == self.selected_address:
            return False
        self.selected_address = address
        self.payload = build_navico_descriptor(address, self.settings)
        self.payload_bytes = serialize_navico_descriptor(address, self.settings)
        self._last_send_monotonic = None
        self.last_address_change_at = utc_timestamp()
        return True

    def send_due(self, now: float) -> bool:
        return self._last_send_monotonic is None or (now - self._last_send_monotonic) >= (self.settings.interval_ms / 1000.0)

    async def run(self, stop_event: asyncio.Event) -> None:
        if not self.settings.enabled:
            LOGGER.info("Navico HTML5 advertiser disabled")
            return
        validate_navico_settings(self.settings)
        if not self.interface_checker(self.settings.interface):
            message = f"Configured MFD interface '{self.settings.interface}' was not found."
            self.record_error(message)
            raise NavicoAdvertiserInterfaceError(message)
        self.started_at_monotonic = self.monotonic()
        self.running = True
        retry_seconds = 1.0
        try:
            while not stop_event.is_set():
                try:
                    address = self.address_resolver(self.settings.interface)
                    if not address:
                        self.record_error(f"Interface {self.settings.interface} has no IPv4 address yet.")
                        await self.close_icon_server()
                        retry_seconds = min(10.0, retry_seconds * 1.5)
                        await sleep_until_stopped(stop_event, retry_seconds)
                        continue
                    changed = self.set_selected_address(address)
                    if changed:
                        LOGGER.info("Navico HTML5 advertiser selected %s on %s", address, self.settings.interface)
                    await self.ensure_icon_server(address)
                    retry_seconds = 1.0
                    now = self.monotonic()
                    if self.payload_bytes and self.send_due(now):
                        await asyncio.to_thread(self.sender, address, self.payload_bytes, self.settings)
                        self._last_send_monotonic = now
                        self.send_count += 1
                        self.last_send_at = utc_timestamp()
                        self.last_error = None
                        if not self._first_success_logged:
                            LOGGER.info(
                                "Navico HTML5 advertiser sending %s tile to %s:%s from %s",
                                self.settings.app_name,
                                self.settings.multicast_group,
                                self.settings.multicast_port,
                                address,
                            )
                            self._first_success_logged = True
                    await sleep_until_stopped(stop_event, min(1.0, self.settings.interval_ms / 1000.0))
                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    self.record_error(str(exc) or type(exc).__name__)
                    LOGGER.warning("Navico HTML5 advertiser error: %s", exc)
                    await sleep_until_stopped(stop_event, min(10.0, retry_seconds))
                    retry_seconds = min(10.0, retry_seconds * 1.5)
        finally:
            self.running = False
            await self.close_icon_server()

    def record_error(self, message: str) -> None:
        self.error_count += 1
        self.last_error = message
        self.last_error_at = utc_timestamp()

    async def ensure_icon_server(self, address: str) -> None:
        if self._icon_server and self._icon_server_address == address:
            return
        await self.close_icon_server()
        self._icon_server = await asyncio.start_server(
            self.handle_icon_client,
            host=address,
            port=int(self.settings.icon_http_port),
            reuse_address=True,
        )
        self._icon_server_address = address
        self.icon_server_running = True
        LOGGER.info("Navico icon endpoint available at %s", icon_url_for_address(address, self.settings))

    async def close_icon_server(self) -> None:
        if self._icon_server:
            self._icon_server.close()
            await self._icon_server.wait_closed()
        self._icon_server = None
        self._icon_server_address = None
        self.icon_server_running = False

    async def handle_icon_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        try:
            request = await asyncio.wait_for(reader.read(8192), timeout=3.0)
            request_line = request.decode("iso-8859-1", errors="ignore").splitlines()[0] if request else ""
            parts = request_line.split(" ", 2)
            if len(parts) < 2:
                await write_http_response(writer, "400 Bad Request", "text/plain", b"Bad request")
                return
            method, target = parts[0].upper(), parts[1]
            path = target.split("?", 1)[0] or "/"
            if method not in {"GET", "HEAD"}:
                await write_http_response(writer, "405 Method Not Allowed", "text/plain", b"Method not allowed")
                return
            if path != self.settings.icon_path:
                await write_http_response(writer, "404 Not Found", "text/plain", b"Not found")
                return
            icon = self.settings.icon_file.read_bytes()
            await write_http_response(writer, "200 OK", "image/png", b"" if method == "HEAD" else icon, content_length=len(icon))
        except (asyncio.TimeoutError, BrokenPipeError, ConnectionResetError):
            writer.close()
            with suppress(Exception):
                await writer.wait_closed()
        except Exception as exc:
            LOGGER.warning("Navico icon request failed: %s", exc)
            with suppress(Exception):
                await write_http_response(writer, "500 Internal Server Error", "text/plain", b"Icon error")


async def write_http_response(
    writer: asyncio.StreamWriter,
    status: str,
    content_type: str,
    body: bytes,
    *,
    content_length: int | None = None,
) -> None:
    length = len(body) if content_length is None else content_length
    try:
        writer.write(
            (
                f"HTTP/1.1 {status}\r\n"
                f"Content-Type: {content_type}\r\n"
                f"Content-Length: {length}\r\n"
                "Cache-Control: public, max-age=86400\r\n"
                "Connection: close\r\n\r\n"
            ).encode("ascii")
            + body
        )
        await writer.drain()
    finally:
        writer.close()
        with suppress(Exception):
            await writer.wait_closed()


async def sleep_until_stopped(stop_event: asyncio.Event, seconds: float) -> None:
    try:
        await asyncio.wait_for(stop_event.wait(), timeout=max(0.0, seconds))
    except asyncio.TimeoutError:
        return


def utc_timestamp() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
