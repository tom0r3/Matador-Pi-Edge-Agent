from __future__ import annotations

import argparse
import asyncio
import calendar
import hashlib
import html
import json
import logging
import os
import re
import secrets
import shutil
import socket
import sqlite3
import subprocess
import threading
import time
import urllib.error
import urllib.request
import uuid
from contextlib import contextmanager, suppress
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import websockets


APP_NAME = "Matador Pi Edge Agent"
DEFAULT_APP_VERSION = "3.5.8"
DEFAULT_SERVER = "https://matador.torodatasystems.eu"
GOFREE_DISCOVERY_GROUP = "239.2.1.1"
GOFREE_DISCOVERY_PORTS = (2052, 2050)
GOFREE_DATA_INFO_REFRESH_SECONDS = 30.0
GOFREE_DATA_SILENCE_RECONNECT_SECONDS = 90.0
GOFREE_PROCESSOR_PING_INTERVAL_SECONDS = 30.0
GOFREE_PROCESSOR_PING_TIMEOUT_SECONDS = 15.0
UPLOAD_BATCH_MAX_READINGS = 250
UPLOAD_BATCH_MAX_PAYLOADS = 50
STORAGE_SAMPLE_HZ = 1.0
GOLDEN_IMAGE_HOSTNAME_MARKER = "golden-image-hostname.pending"
SPOOL_MAX_PAYLOADS = 0
LOCAL_STATUS_HOST = "0.0.0.0"
LOCAL_STATUS_PORT = 8080
DISK_WARN_USED_PERCENT = 70.0
DISK_CRITICAL_USED_PERCENT = 85.0
DISK_STOP_BUFFERING_USED_PERCENT = 95.0
CONFIG_POLL_SECONDS = 10.0
CLAIM_POLL_SECONDS = 15.0
IDLE_SLEEP_SECONDS = 1.0
GOFREE_COMPASS_TRUE_MAG_SETTING_ID = 21
GOFREE_BARCODE_SERIAL_SETTING_ID = 89
GOFREE_SETTING_IDS = (GOFREE_COMPASS_TRUE_MAG_SETTING_ID, GOFREE_BARCODE_SERIAL_SETTING_ID)
GOFREE_DATA_INFO_METRIC_NAMES = {
    "COG",
    "HEADING",
    "TWD",
    "START_LINE_BIAS",
    "START_LINE_BEARING",
    "MAG_VARIATION",
}
GOFREE_COMPASS_TRUE_MAG_METRIC_NAMES = {"HEADING", "TWD", "START_LINE_BEARING"}

LOGGER = logging.getLogger("matador_pi_edge_agent")


def resolve_app_version() -> str:
    env_version = os.environ.get("MATADOR_PI_EDGE_VERSION", "").strip()
    if env_version:
        return env_version
    for version_path in (Path.cwd() / "VERSION", Path(__file__).resolve().parents[1] / "VERSION"):
        with suppress(OSError):
            version = version_path.read_text(encoding="utf-8").strip()
            if version:
                return version
    return DEFAULT_APP_VERSION


APP_VERSION = resolve_app_version()


@dataclass(frozen=True)
class DiscoveredGoFreeDevice:
    host: str
    port: int
    name: str
    model: str
    serial_number: str
    source: str

    @property
    def label(self) -> str:
        title = " - ".join(part for part in (self.name, self.model, normalized_serial_number(self.serial_number)) if part)
        prefix = f"{title} - " if title else ""
        return f"{prefix}{self.host}:{self.port} ({self.source})"

    def identity(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "model": self.model,
            "serial_number": normalized_serial_number(self.serial_number),
            "last_host": self.host,
            "port": self.port,
        }


class PayloadSpool:
    def __init__(self, path: Path, max_rows: int) -> None:
        self.path = path
        self.max_rows = max_rows
        self._lock = threading.RLock()
        self._ensure_schema()

    def _connect(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.path, timeout=30.0)
        conn.execute("PRAGMA busy_timeout=30000")
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        return conn

    @contextmanager
    def _connection(self):
        with self._lock:
            conn = self._connect()
            try:
                yield conn
                conn.commit()
            finally:
                conn.close()

    def _ensure_schema(self) -> None:
        with self._connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS outbound_payloads (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at REAL NOT NULL,
                    payload_json TEXT NOT NULL
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS outbound_payloads_created_idx ON outbound_payloads(created_at)")

    def enqueue(self, payload: dict[str, Any]) -> None:
        encoded = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
        with self._connection() as conn:
            conn.execute(
                "INSERT INTO outbound_payloads (created_at, payload_json) VALUES (?, ?)",
                (time.time(), encoded),
            )
            if self.max_rows > 0:
                conn.execute(
                    """
                    DELETE FROM outbound_payloads
                    WHERE id IN (
                        SELECT id
                        FROM outbound_payloads
                        ORDER BY id ASC
                        LIMIT max((SELECT count(*) FROM outbound_payloads) - ?, 0)
                    )
                    """,
                    (self.max_rows,),
                )

    def peek_oldest(self) -> tuple[int, dict[str, Any]] | None:
        with self._connection() as conn:
            row = conn.execute(
                "SELECT id, payload_json FROM outbound_payloads ORDER BY id ASC LIMIT 1"
            ).fetchone()
        if row is None:
            return None
        return int(row[0]), json.loads(str(row[1]))

    def peek_oldest_batch(self, max_payloads: int, max_readings: int) -> list[tuple[int, dict[str, Any]]]:
        row_limit = max(1, max_payloads)
        reading_limit = max(1, max_readings)
        with self._connection() as conn:
            rows = conn.execute(
                "SELECT id, payload_json FROM outbound_payloads ORDER BY id ASC LIMIT ?",
                (row_limit,),
            ).fetchall()
        batch: list[tuple[int, dict[str, Any]]] = []
        reading_count = 0
        for row in rows:
            payload = json.loads(str(row[1]))
            data = payload.get("Data")
            payload_readings = len(data) if isinstance(data, list) else 0
            if batch and reading_count + payload_readings > reading_limit:
                break
            batch.append((int(row[0]), payload))
            reading_count += payload_readings
        return batch

    def ack(self, payload_id: int) -> None:
        with self._connection() as conn:
            conn.execute("DELETE FROM outbound_payloads WHERE id = ?", (payload_id,))

    def ack_many(self, payload_ids: list[int]) -> None:
        if not payload_ids:
            return
        placeholders = ",".join("?" for _ in payload_ids)
        with self._connection() as conn:
            conn.execute(f"DELETE FROM outbound_payloads WHERE id IN ({placeholders})", payload_ids)

    def clear(self) -> None:
        with self._connection() as conn:
            conn.execute("DELETE FROM outbound_payloads")
            conn.execute("DELETE FROM sqlite_sequence WHERE name = 'outbound_payloads'")

    def stats(self) -> dict[str, Any]:
        with self._connection() as conn:
            row = conn.execute(
                "SELECT count(*), min(created_at), max(created_at), coalesce(sum(length(payload_json)), 0) FROM outbound_payloads"
            ).fetchone()
        count = int(row[0] or 0)
        return {
            "pending_payloads": count,
            "oldest_payload_age_seconds": max(0.0, time.time() - float(row[1])) if row[1] else None,
            "newest_payload_age_seconds": max(0.0, time.time() - float(row[2])) if row[2] else None,
            "queued_payload_bytes": int(row[3] or 0),
            "spool_bytes": self.path.stat().st_size if self.path.exists() else 0,
            "spool_max_payloads": self.max_rows,
            "spool_unlimited": self.max_rows <= 0,
        }


def default_state_dir() -> Path:
    if os.name == "nt":
        return Path(os.environ.get("APPDATA", Path.home())) / "MatadorPiEdgeAgent"
    return Path(os.environ.get("MATADOR_PI_EDGE_STATE_DIR", "/var/lib/matador-pi-edge-agent"))


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        LOGGER.warning("Ignoring unreadable state file at %s", path)
        return {}


def save_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f"{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        temporary.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
        temporary.replace(path)
        with suppress(OSError):
            path.chmod(0o600)
    finally:
        with suppress(OSError):
            temporary.unlink()


def stable_claim_code(device_uid: str) -> str:
    compact = "".join(ch for ch in device_uid.upper() if ch.isalnum())
    return "-".join((compact + "00000000")[idx : idx + 4] for idx in (0, 4))


def random_claim_code() -> str:
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    value = "".join(secrets.choice(alphabet) for _ in range(8))
    return f"{value[:4]}-{value[4:]}"


def int_or_none(value: Any) -> int | None:
    try:
        if value is None:
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def float_or_none(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def utc_timestamp() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def human_duration(seconds: Any) -> str:
    value = float_or_none(seconds)
    if value is None:
        return "-"
    value = max(0, int(value))
    if value < 60:
        return f"{value}s"
    minutes, sec = divmod(value, 60)
    if minutes < 60:
        return f"{minutes}m {sec}s"
    hours, minute = divmod(minutes, 60)
    if hours < 48:
        return f"{hours}h {minute}m"
    days, hour = divmod(hours, 24)
    return f"{days}d {hour}h"


def iso_age_seconds(value: Any) -> float | None:
    if not value:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        if text.endswith("Z"):
            parsed = time.strptime(text, "%Y-%m-%dT%H:%M:%SZ")
            timestamp = calendar.timegm(parsed)
        else:
            return None
    except ValueError:
        return None
    return max(0.0, time.time() - timestamp)


def normalized_serial_number(value: Any) -> str:
    serial = str(value or "").strip()
    return "" if serial.lower() in {"", "0", "n/a", "na", "none", "null"} else serial


def hostname() -> str:
    try:
        return socket.gethostname()
    except OSError:
        return "matador-pi-edge-agent"


def stable_device_suffix() -> str:
    hardware_candidates: list[str] = []
    with suppress(OSError):
        for line in Path("/proc/cpuinfo").read_text(encoding="utf-8").splitlines():
            key, _, value = line.partition(":")
            if key.strip().lower() == "serial":
                serial = value.strip().lower()
                if serial and serial.strip("0"):
                    hardware_candidates.append(f"cpu:{serial}")
                    break
    for interface_path in sorted(Path("/sys/class/net").glob("*/address")) if Path("/sys/class/net").exists() else []:
        interface_name = interface_path.parent.name
        if interface_name == "lo" or interface_name.startswith(("docker", "veth", "br-", "virbr")):
            continue
        with suppress(OSError):
            value = interface_path.read_text(encoding="utf-8").strip().lower()
            if value and value != "00:00:00:00:00:00":
                hardware_candidates.append(f"mac:{interface_name}:{value}")
    if hardware_candidates:
        return hashlib.sha256("|".join(hardware_candidates).encode("utf-8")).hexdigest()[:6]

    cloned_os_candidates: list[str] = []
    for path in (Path("/etc/machine-id"), Path("/var/lib/dbus/machine-id")):
        with suppress(OSError):
            value = path.read_text(encoding="utf-8").strip()
            if value:
                cloned_os_candidates.append(f"machine:{value}")
    seed = "|".join(cloned_os_candidates) or str(uuid.uuid4())
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()[:6]


def hostname_is_generic(value: str) -> bool:
    normalized = value.strip().lower()
    return normalized in {
        "raspberrypi",
        "matador-pi-edge",
        "matador-pi-edge-agent",
        "localhost",
        "localhost.localdomain",
    }


def hostname_is_generated_by_agent(value: str) -> bool:
    return re.fullmatch(r"matador-pi-edge-[0-9a-f]{6}", value.strip().lower()) is not None


def disk_stats(path: Path) -> dict[str, Any]:
    try:
        usage = shutil.disk_usage(path)
        return {
            "path": str(path),
            "total_bytes": usage.total,
            "used_bytes": usage.used,
            "free_bytes": usage.free,
            "used_percent": round((usage.used / usage.total) * 100, 2) if usage.total else None,
        }
    except OSError as exc:
        return {"path": str(path), "error": str(exc)}


def tail_text(path: Path, max_bytes: int = 20000) -> str:
    try:
        size = path.stat().st_size
        with path.open("rb") as handle:
            if size > max_bytes:
                handle.seek(-max_bytes, os.SEEK_END)
            return handle.read().decode("utf-8", errors="replace")
    except OSError:
        return ""


def load_average() -> dict[str, Any]:
    try:
        one, five, fifteen = os.getloadavg()
        return {"load_1m": one, "load_5m": five, "load_15m": fifteen}
    except (AttributeError, OSError):
        return {}


def command_output(command: list[str], *, timeout: int = 3) -> dict[str, Any]:
    try:
        result = subprocess.run(command, text=True, capture_output=True, timeout=timeout)
    except FileNotFoundError:
        return {"ok": False, "returncode": None, "stdout": "", "stderr": f"{command[0]} not found"}
    except subprocess.TimeoutExpired:
        return {"ok": False, "returncode": None, "stdout": "", "stderr": f"{' '.join(command)} timed out after {timeout}s"}
    return {
        "ok": result.returncode == 0,
        "returncode": result.returncode,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
    }


def active_wifi_ssid(interface: str = "wlan0") -> dict[str, Any]:
    iwgetid = command_output(["iwgetid", interface, "-r"], timeout=3)
    ssid = str(iwgetid.get("stdout") or "").strip()
    if ssid:
        return {"interface": interface, "ssid": ssid, "connected": True, "source": "iwgetid"}

    iw_link = command_output(["iw", "dev", interface, "link"], timeout=3)
    for line in str(iw_link.get("stdout") or "").splitlines():
        stripped = line.strip()
        if stripped.startswith("SSID:"):
            ssid = stripped.split(":", 1)[1].strip()
            if ssid:
                return {"interface": interface, "ssid": ssid, "connected": True, "source": "iw"}

    error = str(iwgetid.get("stderr") or iw_link.get("stderr") or "").strip()
    return {
        "interface": interface,
        "ssid": None,
        "connected": False,
        "source": "iwgetid/iw",
        "error": error or "No active SSID reported",
    }


def network_snapshot() -> dict[str, Any]:
    snapshot: dict[str, Any] = {"hostname": hostname()}
    hostname_ips = command_output(["hostname", "-I"], timeout=3)
    snapshot["ip_addresses"] = [part for part in str(hostname_ips.get("stdout") or "").split() if part]

    default_route_output = command_output(["ip", "route", "show", "default"], timeout=3)
    default_route = str(default_route_output.get("stdout") or "").splitlines()[0] if default_route_output.get("ok") else ""
    route_match = re.search(r"default(?: via (?P<gateway>\S+))?(?: dev (?P<interface>\S+))?", default_route)
    snapshot["default_route"] = {
        "raw": default_route or None,
        "gateway": route_match.group("gateway") if route_match else None,
        "interface": route_match.group("interface") if route_match else None,
        "ok": bool(default_route),
    }

    interface_output = command_output(["ip", "-o", "-4", "addr", "show", "scope", "global"], timeout=3)
    interfaces: list[dict[str, Any]] = []
    if interface_output.get("ok"):
        for line in str(interface_output.get("stdout") or "").splitlines():
            match = re.match(r"\d+:\s+(?P<interface>\S+)\s+inet\s+(?P<address>\S+)", line)
            if match:
                interfaces.append({"interface": match.group("interface"), "address": match.group("address")})
    snapshot["interfaces"] = interfaces

    nameservers: list[str] = []
    with suppress(OSError):
        for line in Path("/etc/resolv.conf").read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped.startswith("nameserver "):
                nameservers.append(stripped.split(None, 1)[1])
    snapshot["dns_servers"] = nameservers
    snapshot["wifi"] = active_wifi_ssid("wlan0")
    snapshot["ok"] = bool(snapshot["ip_addresses"] and snapshot["default_route"]["ok"])
    return snapshot


def bearer_headers(token: str | None = None) -> dict[str, str]:
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def request_json(server_url: str, path: str, payload: dict[str, Any] | None = None, token: str | None = None) -> dict[str, Any]:
    url = f"{server_url.rstrip('/')}{path}"
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(
        url,
        data=data,
        headers=bearer_headers(token),
        method="POST" if payload is not None else "GET",
    )
    with urllib.request.urlopen(request, timeout=15) as response:
        return json.loads(response.read().decode("utf-8"))


def device_from_discovery_payload(payload: str, sender_host: str, source: str) -> DiscoveredGoFreeDevice | None:
    text = payload.strip().strip("\x00")
    if not text:
        return None
    try:
        data = json.loads(text)
        services = data.get("Services") or []
        websocket_service = next(
            (
                service
                for service in services
                if isinstance(service, dict)
                and str(service.get("Service") or "").lower() == "navico-nav-ws"
            ),
            None,
        )
        if websocket_service or data.get("IP"):
            return DiscoveredGoFreeDevice(
                host=str(data.get("IP") or sender_host).strip(),
                port=int(websocket_service.get("Port") or 2053) if websocket_service else 2053,
                name=str(data.get("Name") or "").strip(),
                model=str(data.get("Model") or "").strip(),
                serial_number=str(data.get("SerialNumber") or "").strip(),
                source=source,
            )
    except (json.JSONDecodeError, TypeError, ValueError):
        pass

    parts = [part.strip() for part in text.split(",")]
    if len(parts) >= 4 and parts[2]:
        return DiscoveredGoFreeDevice(
            host=parts[2],
            port=int_or_none(parts[3]) or 2053,
            name=parts[0],
            model="",
            serial_number="",
            source=source,
        )
    return None


def unique_devices(devices: list[DiscoveredGoFreeDevice]) -> list[DiscoveredGoFreeDevice]:
    seen: set[tuple[str, int]] = set()
    unique: list[DiscoveredGoFreeDevice] = []
    for device in devices:
        key = (device.host, device.port)
        if key in seen:
            continue
        seen.add(key)
        unique.append(device)
    return sorted(unique, key=lambda item: (item.host, item.port, item.name))


def device_matches_identity(device: DiscoveredGoFreeDevice, identity: dict[str, Any]) -> bool:
    serial = normalized_serial_number(identity.get("serial_number"))
    device_serial = normalized_serial_number(device.serial_number)
    if serial and device_serial and serial == device_serial:
        return True
    name = str(identity.get("name") or "").strip()
    model = str(identity.get("model") or "").strip()
    if name and model:
        return name == device.name and model == device.model
    if name:
        return name == device.name
    return False


def discover_gofree_devices(timeout_seconds: float = 8.0) -> list[DiscoveredGoFreeDevice]:
    devices: list[DiscoveredGoFreeDevice] = []
    deadline = time.monotonic() + timeout_seconds
    for port in GOFREE_DISCOVERY_PORTS:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        try:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.settimeout(max(0.2, remaining))
            sock.bind(("", port))
            membership = socket.inet_aton(GOFREE_DISCOVERY_GROUP) + socket.inet_aton("0.0.0.0")
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, membership)
            while time.monotonic() < deadline:
                try:
                    data, address = sock.recvfrom(4096)
                except socket.timeout:
                    break
                device = device_from_discovery_payload(data.decode("ascii", errors="ignore"), address[0], f"UDP {port}")
                if device:
                    devices.append(device)
        except OSError as exc:
            LOGGER.debug("GoFree discovery on UDP %s failed: %s", port, exc)
        finally:
            sock.close()
    return unique_devices(devices)


class RestartRequested(Exception):
    """Raised when Matador asks systemd to restart the agent."""


class PiEdgeAgent:
    def __init__(
        self,
        *,
        server_url: str,
        state_dir: Path,
        enrollment_code: str,
        processor_host: str,
        discovery_timeout: float,
        spool_max_payloads: int,
        data_silence_reconnect_seconds: float,
        processor_ping_interval_seconds: float,
        processor_ping_timeout_seconds: float,
        upload_batch_max_readings: int,
        upload_batch_max_payloads: int,
        storage_sample_hz: float,
        local_status_host: str,
        local_status_port: int,
    ) -> None:
        self.server_url = server_url.rstrip("/")
        self.state_dir = state_dir
        self.state_path = state_dir / "state.json"
        self.spool = PayloadSpool(state_dir / "outbound-spool.sqlite3", spool_max_payloads)
        self.state = load_json(self.state_path)
        self.enrollment_code = enrollment_code.strip().upper()
        self.processor_host_override = processor_host.strip()
        self.discovery_timeout = discovery_timeout
        self.data_silence_reconnect_seconds = max(10.0, data_silence_reconnect_seconds)
        self.processor_ping_interval_seconds = processor_ping_interval_seconds if processor_ping_interval_seconds > 0 else None
        self.processor_ping_timeout_seconds = processor_ping_timeout_seconds if processor_ping_timeout_seconds > 0 else None
        self.upload_batch_max_readings = max(1, min(500, upload_batch_max_readings))
        self.upload_batch_max_payloads = max(1, upload_batch_max_payloads)
        self.storage_sample_hz = max(0.0, storage_sample_hz)
        self.storage_sample_interval_seconds = 0.0 if self.storage_sample_hz <= 0 else 1.0 / self.storage_sample_hz
        self.local_status_host = local_status_host.strip() or LOCAL_STATUS_HOST
        self.local_status_port = max(0, local_status_port)
        self.data_info_by_metric_id: dict[int, dict[str, Any]] = {}
        self.setting_by_id: dict[int, dict[str, Any]] = {}
        self.stop_event = asyncio.Event()
        self.current_config: dict[str, Any] = {}
        self.processor_enabled = bool(self.state.get("processor_enabled", True))
        self.streaming_enabled = bool(self.state.get("streaming_enabled", True))
        self.upload_paused = bool(self.state.get("upload_paused", False))
        self.last_remote_command_at = str(self.state.get("last_remote_command_at") or "")
        self.counters = dict(self.state.get("counters") or {})
        self.current_processor_identity = dict(self.state.get("current_processor_identity") or {})
        self.processor_reconnect_requested = False
        self.config_status = "starting"
        self.processor_connection_status = "starting"
        self.upstream_connection_status = "starting"
        self.latest_values_by_metric: dict[str, dict[str, Any]] = {}
        self.live_payload_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=100)
        self._storage_sample_bucket: int | None = None
        self._storage_sample_payload: dict[str, Any] | None = None
        self._storage_sample_items: dict[tuple[int, int], dict[str, Any]] = {}

    def increment_counter(self, name: str, amount: int = 1) -> None:
        self.counters[name] = int(self.counters.get(name) or 0) + amount
        self.state["counters"] = self.counters

    @property
    def device_token(self) -> str:
        return str(self.state.get("device_token") or "")

    def save_state(self) -> None:
        save_json(self.state_path, self.state)

    def claim_identity(self) -> tuple[str, str, str]:
        device_uid = str(self.state.get("device_uid") or "").strip()
        if not device_uid:
            device_uid = str(uuid.uuid4())
            self.state["device_uid"] = device_uid
        claim_token = str(self.state.get("claim_device_token") or "").strip()
        if not claim_token:
            claim_token = secrets.token_urlsafe(32)
            self.state["claim_device_token"] = claim_token
        claim_code = str(self.state.get("claim_code") or "").strip()
        if not claim_code:
            claim_code = stable_claim_code(device_uid)
            self.state["claim_code"] = claim_code
        self.save_state()
        return device_uid, claim_token, claim_code

    def reset_claim_identity(self) -> None:
        self.state["device_uid"] = str(uuid.uuid4())
        self.state["claim_device_token"] = secrets.token_urlsafe(32)
        self.state["claim_code"] = random_claim_code()

    def request_claim(self) -> dict[str, Any]:
        device_uid, claim_token, claim_code = self.claim_identity()
        LOGGER.info("Requesting Matador admin claim approval with claim code %s", claim_code)
        local_host = str(self.state.get("last_processor_host") or self.processor_host_override or "").strip()
        discovered_processors = []
        with suppress(Exception):
            devices = discover_gofree_devices(min(self.discovery_timeout, 3.0))
            discovered_processors = [device.identity() for device in devices]
            if devices:
                self.state["last_discovered_processors"] = discovered_processors
                self.state["last_discovered_device"] = devices[0].__dict__
                self.save_state()
                if not local_host:
                    local_host = devices[0].host
                    self.state["last_processor_host"] = devices[0].host
        if not local_host:
            with suppress(Exception):
                local_host = str(self.state.get("last_processor_host") or "").strip()
        return request_json(
            self.server_url,
            "/edge/pi-claim",
            {
                "device_uid": device_uid,
                "device_token": claim_token,
                "claim_code": claim_code,
                "device_label": APP_NAME,
                "app_version": APP_VERSION,
                "client_hostname": hostname(),
                "local_processor_host": local_host or None,
                "discovered_processors": discovered_processors,
                "pi_health": self.health_payload(),
            },
        )

    def claim_until_approved(self) -> None:
        while not self.device_token:
            response = self.request_claim()
            if response.get("status") == "approved":
                _, claim_token, _ = self.claim_identity()
                self.state["device_token"] = claim_token
                self.state["config"] = response.get("config") or {}
                self.state["enrolled_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                self.save_state()
                LOGGER.info("Pi Edge Agent claim approved by Matador")
                return
            if response.get("status") == "rejected":
                raise RuntimeError("Pi Edge Agent claim was rejected by Matador admin")
            claim_code = response.get("claim_code") or self.state.get("claim_code") or ""
            LOGGER.info("Waiting for Matador admin approval. Claim code: %s", claim_code)
            time.sleep(CLAIM_POLL_SECONDS)

    def enroll_if_needed(self) -> None:
        if self.device_token:
            return
        if not self.enrollment_code:
            self.claim_until_approved()
            return
        LOGGER.info("Enrolling Pi Edge Agent with Matador")
        response = request_json(
            self.server_url,
            "/edge/enroll",
            {
                "enrollment_code": self.enrollment_code,
                "device_label": APP_NAME,
                "app_version": APP_VERSION,
                "client_hostname": hostname(),
            },
        )
        token = str(response.get("device_token") or "")
        if not token:
            raise RuntimeError("Matador enrollment response did not include a device token")
        self.state["device_token"] = token
        self.state["config"] = response.get("config") or {}
        self.state["enrolled_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        self.save_state()
        LOGGER.info("Pi Edge Agent enrolled")

    def fetch_config(self) -> dict[str, Any]:
        self.enroll_if_needed()
        try:
            response = self.request_config()
        except urllib.error.HTTPError as exc:
            if exc.code in (401, 403) and not self.enrollment_code:
                LOGGER.warning("Stored Matador token was rejected; clearing token and entering Pi claim mode")
                self.state.pop("device_token", None)
                self.state.pop("config", None)
                self.save_state()
                self.claim_until_approved()
                response = self.request_config()
            else:
                raise
        self.state["config"] = response
        self.state["last_config_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        self.current_config = response
        self.config_status = "ok"
        self.handle_remote_command(response.get("command") or {})
        self.save_state()
        return response

    def request_config(self) -> dict[str, Any]:
        payload = {
            "agent_kind": "pi_edge_agent",
            "app_version": APP_VERSION,
            "client_hostname": hostname(),
            "local_processor_host": self.state.get("last_processor_host") or self.processor_host_override or None,
            "pi_health": self.health_payload(),
        }
        try:
            return request_json(self.server_url, "/edge/config", payload, token=self.device_token)
        except urllib.error.HTTPError as exc:
            if exc.code in (404, 405):
                return request_json(self.server_url, "/edge/config", token=self.device_token)
            raise

    def acknowledge_remote_command(self, requested_at: str | None) -> bool:
        if not requested_at:
            return True
        try:
            request_json(self.server_url, "/edge/command-ack", {"requested_at": requested_at}, token=self.device_token)
            return True
        except Exception as exc:
            LOGGER.warning("Failed to acknowledge remote command: %s", exc)
            return False

    def record_command_result(self, action: str, status: str, detail: str = "") -> None:
        self.state["last_command_result"] = {
            "action": action,
            "status": status,
            "detail": detail,
            "time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }

    def support_bundle(self) -> str:
        safe_state = {key: value for key, value in self.state.items() if key not in {"device_token", "claim_device_token", "config"}}
        return json.dumps(
            {
                "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "agent": {"name": APP_NAME, "version": APP_VERSION, "hostname": hostname()},
                "health": self.health_payload(include_support_bundle=False),
                "state": safe_state,
            },
            indent=2,
            sort_keys=True,
            default=str,
        )

    def matador_reachability(self) -> dict[str, Any]:
        url = f"{self.server_url.rstrip('/')}/edge/health"
        started = time.monotonic()
        try:
            request = urllib.request.Request(url, headers={"Accept": "application/json"})
            with urllib.request.urlopen(request, timeout=5) as response:
                latency_ms = round((time.monotonic() - started) * 1000)
                status = int(getattr(response, "status", 0) or response.getcode())
                return {"ok": 200 <= status < 500, "url": url, "status": status, "latency_ms": latency_ms}
        except Exception as exc:
            return {"ok": False, "url": url, "error": str(exc), "latency_ms": round((time.monotonic() - started) * 1000)}

    def run_checked_command(self, command: list[str], *, timeout: int, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
        try:
            result = subprocess.run(
                command,
                cwd=str(cwd) if cwd else None,
                text=True,
                capture_output=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(f"{' '.join(command)} timed out after {timeout}s") from exc
        output = "\n".join(part.strip() for part in (result.stdout, result.stderr) if part and part.strip())
        if result.returncode != 0:
            detail = output or f"exit status {result.returncode}"
            raise RuntimeError(f"{' '.join(command)} failed: {detail}")
        if output:
            LOGGER.info("Command %s output: %s", " ".join(command), output)
        return result

    def command_status(self, command: list[str], *, timeout: int = 8) -> dict[str, Any]:
        try:
            result = subprocess.run(command, text=True, capture_output=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            return {"ok": False, "returncode": None, "detail": f"{' '.join(command)} timed out after {timeout}s"}
        output = "\n".join(part.strip() for part in (result.stdout, result.stderr) if part and part.strip())
        return {"ok": result.returncode == 0, "returncode": result.returncode, "detail": output}

    def update_timer_state(self, *, force: bool = False) -> dict[str, Any]:
        cached = self.state.get("update_timer_state")
        cached_at = float_or_none(self.state.get("update_timer_state_checked_at"))
        if not force and isinstance(cached, dict) and cached_at is not None and time.time() - cached_at < 60:
            return cached
        if os.name == "nt":
            return {"available": False, "detail": "systemd timer state is only available on Linux agents"}
        timer = "matador-pi-edge-update.timer"
        service = "matador-pi-edge-update.service"
        enabled = self.command_status(["systemctl", "is-enabled", timer], timeout=5)
        active = self.command_status(["systemctl", "is-active", timer], timeout=5)
        timer_show = self.command_status(
            ["systemctl", "show", timer, "-p", "NextElapseUSecRealtime", "-p", "LastTriggerUSec", "-p", "UnitFileState"],
            timeout=5,
        )
        service_show = self.command_status(
            ["systemctl", "show", service, "-p", "Result", "-p", "ExecMainStatus", "-p", "ActiveState", "-p", "SubState"],
            timeout=5,
        )
        details: dict[str, str] = {}
        for output in (timer_show.get("detail"), service_show.get("detail")):
            for line in str(output or "").splitlines():
                if "=" in line:
                    key, value = line.split("=", 1)
                    details[key] = value
        state = {
            "available": True,
            "enabled": str(enabled.get("detail") or "").strip() or "unknown",
            "active": str(active.get("detail") or "").strip() or "unknown",
            "next_run": details.get("NextElapseUSecRealtime") or None,
            "last_trigger": details.get("LastTriggerUSec") or None,
            "unit_file_state": details.get("UnitFileState") or None,
            "last_result": details.get("Result") or None,
            "service_state": details.get("ActiveState") or None,
            "service_substate": details.get("SubState") or None,
            "service_exit_status": details.get("ExecMainStatus") or None,
            "ok": enabled.get("ok") and active.get("ok"),
            "detail": enabled.get("detail") if not enabled.get("ok") else active.get("detail") if not active.get("ok") else "",
        }
        self.state["update_timer_state"] = state
        self.state["update_timer_state_checked_at"] = time.time()
        return state

    def record_upload_progress(self, payload_count: int, reading_count: int) -> None:
        now = time.time()
        previous = float_or_none(self.state.get("upload_rate_sample_time"))
        if previous is not None:
            elapsed = max(0.001, now - previous)
            payload_rate = max(0.0, payload_count / elapsed)
            reading_rate = max(0.0, reading_count / elapsed)
            old_payload_rate = float_or_none(self.state.get("upload_rate_payloads_per_second"))
            old_reading_rate = float_or_none(self.state.get("upload_rate_readings_per_second"))
            self.state["upload_rate_payloads_per_second"] = (
                payload_rate if old_payload_rate is None else (old_payload_rate * 0.75) + (payload_rate * 0.25)
            )
            self.state["upload_rate_readings_per_second"] = (
                reading_rate if old_reading_rate is None else (old_reading_rate * 0.75) + (reading_rate * 0.25)
            )
        self.state["upload_rate_sample_time"] = now

    def _storage_sample_key(self, item: dict[str, Any]) -> tuple[int, int] | None:
        metric_id = int_or_none(item.get("id") or item.get("metric_id"))
        if metric_id is None:
            return None
        instance = int_or_none(item.get("inst") or item.get("instance")) or 0
        return metric_id, instance

    def _build_storage_sample_payload(self) -> dict[str, Any] | None:
        if not self._storage_sample_payload or not self._storage_sample_items:
            return None
        payload = dict(self._storage_sample_payload)
        payload["Data"] = list(self._storage_sample_items.values())
        return payload

    def _reset_storage_sample(self, *, bucket: int | None = None, payload: dict[str, Any] | None = None) -> None:
        self._storage_sample_bucket = bucket
        self._storage_sample_payload = dict(payload) if payload else None
        self._storage_sample_items = {}

    def historical_payloads_for_storage(self, outgoing: dict[str, Any]) -> list[dict[str, Any]]:
        if self.storage_sample_interval_seconds <= 0:
            return [outgoing]
        sent_at = float_or_none(outgoing.get("sent_at")) or time.time()
        bucket = int(sent_at / self.storage_sample_interval_seconds)
        payloads: list[dict[str, Any]] = []
        if self._storage_sample_bucket is None:
            self._reset_storage_sample(bucket=bucket, payload=outgoing)
        elif bucket != self._storage_sample_bucket:
            flushed = self._build_storage_sample_payload()
            if flushed:
                payloads.append(flushed)
            self._reset_storage_sample(bucket=bucket, payload=outgoing)
        else:
            self._storage_sample_payload = dict(outgoing)

        for item in outgoing.get("Data") or []:
            if not isinstance(item, dict):
                continue
            key = self._storage_sample_key(item)
            if key is None:
                continue
            stored_item = dict(item)
            stored_item.setdefault("time", sent_at)
            self._storage_sample_items[key] = stored_item
        return payloads

    def flush_historical_storage_sample(self) -> dict[str, Any] | None:
        payload = self._build_storage_sample_payload()
        self._reset_storage_sample()
        return payload

    async def enqueue_historical_payloads(self, outgoing: dict[str, Any]) -> None:
        for payload in self.historical_payloads_for_storage(outgoing):
            self.increment_counter("processor_payloads_queued")
            await asyncio.to_thread(self.spool.enqueue, payload)

    async def flush_historical_payloads(self) -> None:
        payload = self.flush_historical_storage_sample()
        if payload:
            self.increment_counter("processor_payloads_queued")
            await asyncio.to_thread(self.spool.enqueue, payload)

    def enqueue_live_payload(self, outgoing: dict[str, Any]) -> None:
        if self.live_payload_queue.full():
            with suppress(asyncio.QueueEmpty):
                self.live_payload_queue.get_nowait()
        with suppress(asyncio.QueueFull):
            self.live_payload_queue.put_nowait(outgoing)

    def clear_runtime_queues(self) -> None:
        while True:
            try:
                self.live_payload_queue.get_nowait()
            except asyncio.QueueEmpty:
                break
        self._reset_storage_sample()

    def latest_metric_key(self, item: dict[str, Any]) -> str | None:
        metric_id = int_or_none(item.get("id") or item.get("metric_id"))
        if metric_id is None:
            return None
        instance = int_or_none(item.get("inst") or item.get("instance")) or 0
        return f"{metric_id}:{instance}"

    def latest_metric_value_text(self, item: dict[str, Any]) -> str:
        for key in ("valStr", "value_text", "dampedVal", "val", "value", "sysVal"):
            value = item.get(key)
            if value is not None:
                return str(value)
        return "-"

    def record_latest_values(self, readings: list[dict[str, Any]]) -> None:
        timestamp = utc_timestamp()
        for item in readings:
            key = self.latest_metric_key(item)
            if key is None:
                continue
            metric_name = str(item.get("metric_name") or item.get("sname") or item.get("id") or key).strip()
            unit = str(item.get("unit") or "").replace("&deg;", "deg").strip()
            self.latest_values_by_metric[key] = {
                "key": key,
                "id": int_or_none(item.get("id") or item.get("metric_id")),
                "instance": int_or_none(item.get("inst") or item.get("instance")) or 0,
                "metric_name": metric_name,
                "value_text": self.latest_metric_value_text(item),
                "unit": unit,
                "valid": item.get("valid"),
                "updated_at": timestamp,
            }
        if len(self.latest_values_by_metric) > 200:
            ordered = sorted(self.latest_values_by_metric.values(), key=lambda item: str(item.get("updated_at") or ""), reverse=True)
            self.latest_values_by_metric = {str(item["key"]): item for item in ordered[:200] if item.get("key")}

    def subscribed_metric_rows(self) -> list[dict[str, Any]]:
        try:
            metrics = self.subscription_metrics()
        except Exception:
            metrics = []
        rows: list[dict[str, Any]] = []
        for item in metrics:
            metric_id = int_or_none(item.get("id"))
            if metric_id is None:
                continue
            instance = int_or_none(item.get("inst") or item.get("instance")) or 0
            key = f"{metric_id}:{instance}"
            latest = dict(self.latest_values_by_metric.get(key) or {})
            rows.append(
                {
                    "key": key,
                    "id": metric_id,
                    "instance": instance,
                    "name": str(item.get("name") or item.get("metric_name") or metric_id),
                    "latest": latest or None,
                }
            )
        if not rows:
            rows = [
                {
                    "key": key,
                    "id": item.get("id"),
                    "instance": item.get("instance"),
                    "name": item.get("metric_name") or key,
                    "latest": item,
                }
                for key, item in sorted(self.latest_values_by_metric.items())
            ]
        return rows

    def local_status_snapshot(self) -> dict[str, Any]:
        errors: list[str] = []
        try:
            health = self.health_payload(include_support_bundle=False)
        except Exception as exc:
            LOGGER.warning("Local status health snapshot failed: %s", exc)
            errors.append(f"health snapshot: {exc}")
            health = {
                "agent": {
                    "kind": "pi_edge_agent",
                    "name": APP_NAME,
                    "version": APP_VERSION,
                    "hostname": hostname(),
                },
                "controls": {
                    "processor_enabled": self.processor_enabled,
                    "streaming_enabled": self.streaming_enabled,
                    "upload_paused": self.upload_paused,
                    "historical_storage_sample_hz": self.storage_sample_hz,
                },
                "storage": {
                    "state_dir": disk_stats(self.state_dir),
                    "spool": {},
                    "disk_guard": {"status": "unknown", "message": "Health snapshot failed"},
                },
                "network": {"hostname": hostname()},
                "links": {
                    "last_config_at": self.state.get("last_config_at") or None,
                    "last_processor_data_at": self.state.get("last_processor_data_at") or None,
                    "last_upstream_connected_at": self.state.get("last_upstream_connected_at") or None,
                    "last_upload_at": self.state.get("last_upload_at") or None,
                },
                "counters": self.counters,
                "last_discovered_processors": self.state.get("last_discovered_processors") or [],
                "locked_processor_identity": self.locked_processor_identity(),
                "lock_confidence": "unknown",
            }
        try:
            subscribed = self.subscribed_metric_rows()
        except Exception as exc:
            LOGGER.warning("Local status subscribed metrics snapshot failed: %s", exc)
            errors.append(f"subscribed metrics: {exc}")
            subscribed = []
        return {
            "generated_at": utc_timestamp(),
            "agent": health.get("agent") or {},
            "connectivity": {
                "config": self.config_status,
                "processor": self.processor_connection_status,
                "upstream": self.upstream_connection_status,
                "last_config_age_seconds": iso_age_seconds((health.get("links") or {}).get("last_config_at")),
                "last_processor_data_age_seconds": iso_age_seconds((health.get("links") or {}).get("last_processor_data_at")),
                "last_upload_age_seconds": iso_age_seconds((health.get("links") or {}).get("last_upload_at")),
                "last_upstream_connected_age_seconds": iso_age_seconds((health.get("links") or {}).get("last_upstream_connected_at")),
            },
            "health": health,
            "subscribed_metrics": subscribed,
            "subscribed_metric_count": len(subscribed),
            "latest_value_count": len(self.latest_values_by_metric),
            "live_queue_size": self.live_payload_queue.qsize(),
            "errors": errors,
        }

    def local_status_pill_class(self, value: Any) -> str:
        text = str(value or "").lower()
        if any(token in text for token in ("error", "failed", "reconnecting", "interrupted", "critical", "rejected")):
            return "bad"
        if any(token in text for token in ("disabled", "paused", "waiting", "starting", "warn")):
            return "warn"
        if any(token in text for token in ("ok", "connected", "streaming", "active")):
            return "good"
        return "neutral"

    def render_local_status_html(self, snapshot: dict[str, Any]) -> str:
        def esc(value: Any) -> str:
            return html.escape("-" if value is None else str(value))

        def as_dict(value: Any) -> dict[str, Any]:
            return value if isinstance(value, dict) else {}

        def as_list(value: Any) -> list[Any]:
            return value if isinstance(value, list) else []

        def join_values(value: Any) -> str:
            return ", ".join(str(item) for item in as_list(value))

        agent = as_dict(snapshot.get("agent"))
        health = as_dict(snapshot.get("health"))
        controls = as_dict(health.get("controls"))
        storage = as_dict(health.get("storage"))
        spool = as_dict(storage.get("spool"))
        disk = as_dict(storage.get("disk_guard"))
        links = as_dict(health.get("links"))
        network = as_dict(health.get("network"))
        wifi = as_dict(network.get("wifi"))
        default_route = as_dict(network.get("default_route"))
        lock = as_dict(health.get("locked_processor_identity"))
        connectivity = as_dict(snapshot.get("connectivity"))

        def pill(label: str, value: Any) -> str:
            css = self.local_status_pill_class(value)
            return f'<div class="pill {css}"><span>{esc(label)}</span><strong>{esc(value)}</strong></div>'

        metric_rows = []
        for item in as_list(snapshot.get("subscribed_metrics")):
            row = as_dict(item)
            latest = as_dict(row.get("latest"))
            age = human_duration(iso_age_seconds(latest.get("updated_at"))) if latest else "-"
            valid = latest.get("valid")
            valid_text = "-" if valid is None else "yes" if bool(valid) else "no"
            value = latest.get("value_text") if latest else "waiting"
            unit = latest.get("unit") if latest else ""
            metric_rows.append(
                "<tr>"
                f"<td>{esc(row.get('id'))}</td>"
                f"<td>{esc(row.get('name'))}</td>"
                f"<td>{esc(value)} {esc(unit)}</td>"
                f"<td>{esc(valid_text)}</td>"
                f"<td>{esc(age)}</td>"
                "</tr>"
            )
        metrics_html = "\n".join(metric_rows) or '<tr><td colspan="5">No subscribed metrics received yet.</td></tr>'

        discovered = as_list(health.get("last_discovered_processors"))
        discovered_items = "\n".join(
            f"<li>{esc(item.get('name') or 'Processor')} - {esc(item.get('model'))} - {esc(item.get('serial_number'))} @ {esc(item.get('last_host'))}:{esc(item.get('port'))}</li>"
            for item in discovered
            if isinstance(item, dict)
        ) or "<li>No recent discovery results.</li>"
        errors = as_list(snapshot.get("errors"))
        errors_html = ""
        if errors:
            error_items = "".join(f"<li>{esc(error)}</li>" for error in errors)
            errors_html = f"""
    <div class="card full">
      <h2>Status Page Warnings</h2>
      <ul>{error_items}</ul>
    </div>"""

        return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta http-equiv="refresh" content="5">
  <title>Matador Pi Edge Health</title>
  <style>
    :root {{
      color-scheme: dark;
      --bg: #071018;
      --panel: #101a26;
      --panel-2: #162332;
      --border: #2d4054;
      --text: #eef6ff;
      --muted: #9db1c5;
      --good: #4ade80;
      --warn: #fbbf24;
      --bad: #fb7185;
      --accent: #38bdf8;
    }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background: radial-gradient(circle at top left, #143044, var(--bg) 42rem); color: var(--text); }}
    main {{ width: min(1180px, calc(100% - 28px)); margin: 22px auto 34px; }}
    header {{ display: flex; gap: 16px; justify-content: space-between; align-items: flex-start; margin-bottom: 18px; }}
    h1 {{ margin: 0; font-size: clamp(1.6rem, 3vw, 2.3rem); letter-spacing: -0.03em; }}
    h2 {{ margin: 0 0 12px; font-size: 0.9rem; text-transform: uppercase; letter-spacing: 0.12em; color: var(--muted); }}
    .sub {{ color: var(--muted); margin-top: 5px; }}
    .grid {{ display: grid; grid-template-columns: repeat(12, 1fr); gap: 14px; }}
    .card {{ grid-column: span 4; background: linear-gradient(180deg, rgba(22,35,50,.94), rgba(10,18,28,.94)); border: 1px solid var(--border); border-radius: 18px; padding: 16px; box-shadow: 0 18px 50px rgba(0,0,0,.25); }}
    .card.wide {{ grid-column: span 8; }}
    .card.full {{ grid-column: 1 / -1; }}
    .pillgrid {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10px; }}
    .pill {{ border: 1px solid var(--border); border-radius: 14px; padding: 11px 12px; background: rgba(255,255,255,.03); }}
    .pill span {{ display: block; color: var(--muted); font-size: .72rem; text-transform: uppercase; letter-spacing: .1em; }}
    .pill strong {{ display: block; margin-top: 4px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
    .good {{ border-color: rgba(74,222,128,.55); }}
    .good strong {{ color: var(--good); }}
    .warn {{ border-color: rgba(251,191,36,.6); }}
    .warn strong {{ color: var(--warn); }}
    .bad {{ border-color: rgba(251,113,133,.7); }}
    .bad strong {{ color: var(--bad); }}
    .kv {{ display: grid; grid-template-columns: 11rem 1fr; gap: 8px 12px; font-size: .95rem; }}
    .kv div:nth-child(odd) {{ color: var(--muted); }}
    table {{ width: 100%; border-collapse: collapse; overflow: hidden; border-radius: 12px; }}
    th, td {{ text-align: left; padding: 9px 10px; border-bottom: 1px solid rgba(157,177,197,.18); }}
    th {{ color: var(--muted); font-size: .74rem; text-transform: uppercase; letter-spacing: .09em; }}
    tr:last-child td {{ border-bottom: 0; }}
    ul {{ margin: 0; padding-left: 1.1rem; color: var(--muted); }}
    code {{ color: var(--accent); }}
    @media (max-width: 880px) {{ .card, .card.wide {{ grid-column: 1 / -1; }} .pillgrid {{ grid-template-columns: 1fr; }} header {{ flex-direction: column; }} }}
  </style>
</head>
<body>
<main>
  <header>
    <div>
      <h1>{esc(agent.get("hostname") or hostname())}</h1>
      <div class="sub">{esc(APP_NAME)} {esc(agent.get("version") or APP_VERSION)} / refreshed {esc(snapshot.get("generated_at"))}</div>
    </div>
    <div class="sub">JSON: <code>/api/status</code> / Health: <code>/health</code></div>
  </header>
  <section class="grid">
    <div class="card full">
      <h2>Connectivity</h2>
      <div class="pillgrid">
        {pill("Matador config", connectivity.get("config"))}
        {pill("GoFree processor", connectivity.get("processor"))}
        {pill("Matador stream", connectivity.get("upstream"))}
      </div>
    </div>
    <div class="card">
      <h2>Current Links</h2>
      <div class="kv">
        <div>Last config</div><div>{esc(links.get("last_config_at"))} ({esc(human_duration(connectivity.get("last_config_age_seconds")))} ago)</div>
        <div>Last GoFree data</div><div>{esc(links.get("last_processor_data_at"))} ({esc(human_duration(connectivity.get("last_processor_data_age_seconds")))} ago)</div>
        <div>Last upload</div><div>{esc(links.get("last_upload_at"))} ({esc(human_duration(connectivity.get("last_upload_age_seconds")))} ago)</div>
        <div>Last upstream</div><div>{esc(links.get("last_upstream_connected_at"))} ({esc(human_duration(connectivity.get("last_upstream_connected_age_seconds")))} ago)</div>
      </div>
    </div>
    <div class="card">
      <h2>Message Queue</h2>
      <div class="kv">
        <div>Pending payloads</div><div>{esc(spool.get("pending_payloads"))}</div>
        <div>Queued bytes</div><div>{esc(spool.get("queued_payload_bytes"))}</div>
        <div>Live queue</div><div>{esc(snapshot.get("live_queue_size"))}</div>
        <div>Oldest pending</div><div>{esc(human_duration(spool.get("oldest_pending_message_age_seconds")))}</div>
        <div>Drain ETA</div><div>{esc(human_duration(spool.get("estimated_drain_eta_seconds")))}</div>
        <div>Disk guard</div><div>{esc(disk.get("status"))} - {esc(disk.get("message"))}</div>
      </div>
    </div>
    <div class="card">
      <h2>Pi Network</h2>
      <div class="kv">
        <div>IP addresses</div><div>{esc(join_values(network.get("ip_addresses")))}</div>
        <div>Default route</div><div>{esc(default_route.get("raw"))}</div>
        <div>wlan0 SSID</div><div>{esc(wifi.get("ssid") or "-")}</div>
        <div>DNS</div><div>{esc(join_values(network.get("dns_servers")))}</div>
      </div>
    </div>
    <div class="card wide">
      <h2>Processor Lock</h2>
      <div class="kv">
        <div>Name</div><div>{esc(lock.get("name"))}</div>
        <div>Model</div><div>{esc(lock.get("model"))}</div>
        <div>Serial</div><div>{esc(lock.get("serial_number"))}</div>
        <div>Host</div><div>{esc(lock.get("last_host"))}:{esc(lock.get("port"))}</div>
        <div>Confidence</div><div>{esc(health.get("lock_confidence"))}</div>
      </div>
    </div>
    <div class="card">
      <h2>Controls</h2>
      <div class="kv">
        <div>Processor</div><div>{esc(controls.get("processor_enabled"))}</div>
        <div>Streaming</div><div>{esc(controls.get("streaming_enabled"))}</div>
        <div>Uploads paused</div><div>{esc(controls.get("upload_paused"))}</div>
        <div>Storage sample</div><div>{esc(controls.get("historical_storage_sample_hz"))} Hz</div>
      </div>
    </div>
    <div class="card full">
      <h2>Subscribed Data ({esc(snapshot.get("subscribed_metric_count"))})</h2>
      <table>
        <thead><tr><th>ID</th><th>Metric</th><th>Latest</th><th>Valid</th><th>Age</th></tr></thead>
        <tbody>{metrics_html}</tbody>
      </table>
    </div>
    <div class="card full">
      <h2>Discovered GoFree Processors</h2>
      <ul>{discovered_items}</ul>
    </div>{errors_html}
  </section>
</main>
</body>
</html>"""

    def render_local_status_error_html(self, exc: Exception) -> str:
        message = html.escape(f"{type(exc).__name__}: {exc!s}" if str(exc) else type(exc).__name__)
        return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Matador Pi Edge Local Status Error</title>
  <style>
    body {{ margin: 0; font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background: #071018; color: #eef6ff; }}
    main {{ width: min(760px, calc(100% - 32px)); margin: 42px auto; background: #101a26; border: 1px solid #2d4054; border-radius: 18px; padding: 22px; }}
    h1 {{ margin: 0 0 10px; font-size: 1.45rem; }}
    p {{ color: #9db1c5; line-height: 1.5; }}
    code {{ display: block; margin-top: 14px; padding: 14px; background: #071018; border: 1px solid #2d4054; border-radius: 12px; color: #fb7185; white-space: pre-wrap; }}
  </style>
</head>
<body>
<main>
  <h1>Local status page error</h1>
  <p>The Pi Edge Agent is running, but the local status page hit an internal rendering/request error. The full traceback is in the service journal.</p>
  <code>{message}</code>
</main>
</body>
</html>"""

    async def write_local_status_response(self, writer: asyncio.StreamWriter, status: str, content_type: str, body: str) -> None:
        encoded = body.encode("utf-8")
        try:
            writer.write(
                (
                    f"HTTP/1.1 {status}\r\n"
                    f"Content-Type: {content_type}; charset=utf-8\r\n"
                    f"Content-Length: {len(encoded)}\r\n"
                    "Cache-Control: no-store\r\n"
                    "Connection: close\r\n\r\n"
                ).encode("ascii")
                + encoded
            )
            await writer.drain()
        finally:
            writer.close()
            with suppress(Exception):
                await writer.wait_closed()

    async def handle_local_status_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        try:
            request = await asyncio.wait_for(reader.read(8192), timeout=3.0)
            request_lines = request.decode("iso-8859-1", errors="ignore").splitlines()
            if not request_lines:
                writer.close()
                with suppress(Exception):
                    await writer.wait_closed()
                return
            request_line = request_lines[0]
            parts = request_line.split(" ", 2)
            if len(parts) < 2:
                await self.write_local_status_response(writer, "400 Bad Request", "text/plain", "Bad request")
                return
            method, target = parts[0], parts[1]
            path = target.split("?", 1)[0] or "/"
            if method.upper() != "GET":
                await self.write_local_status_response(writer, "405 Method Not Allowed", "text/plain", "Method not allowed")
                return
            if path == "/favicon.ico":
                await self.write_local_status_response(writer, "404 Not Found", "text/plain", "Not found")
                return
            snapshot = self.local_status_snapshot()
            if path in {"/api/status", "/status.json"}:
                await self.write_local_status_response(writer, "200 OK", "application/json", json.dumps(snapshot, indent=2, sort_keys=True, default=str))
            elif path == "/health":
                body = json.dumps({"ok": True, "agent": snapshot.get("agent"), "connectivity": snapshot.get("connectivity")}, indent=2, sort_keys=True)
                await self.write_local_status_response(writer, "200 OK", "application/json", body)
            elif path in {"/", "/index.html"}:
                await self.write_local_status_response(writer, "200 OK", "text/html", self.render_local_status_html(snapshot))
            else:
                await self.write_local_status_response(writer, "404 Not Found", "text/plain", "Not found")
        except asyncio.TimeoutError as exc:
            # Browsers can open speculative/preload sockets and send no request.
            # Treat that as a quiet disconnect, not as a local status page error.
            LOGGER.debug("Local status client sent no request before timeout: %r", exc)
            writer.close()
            with suppress(Exception):
                await writer.wait_closed()
        except (BrokenPipeError, ConnectionResetError) as exc:
            LOGGER.debug("Local status client disconnected before response completed: %r", exc)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            LOGGER.warning("Local status request failed", exc_info=True)
            with suppress(Exception):
                await self.write_local_status_response(writer, "500 Internal Server Error", "text/html", self.render_local_status_error_html(exc))

    async def local_status_loop(self) -> None:
        if self.local_status_port <= 0:
            LOGGER.info("Pi Edge local status page disabled")
            return
        try:
            server = await asyncio.start_server(
                self.handle_local_status_client,
                self.local_status_host,
                self.local_status_port,
                reuse_address=True,
            )
        except OSError as exc:
            LOGGER.warning("Unable to start Pi Edge local status page on %s:%s: %s", self.local_status_host, self.local_status_port, exc)
            return
        sockets = ", ".join(str(sock.getsockname()) for sock in (server.sockets or []))
        LOGGER.info("Pi Edge local status page available on http://%s:%s/ (%s)", self.local_status_host, self.local_status_port, sockets)
        async with server:
            while not self.stop_event.is_set():
                await asyncio.sleep(1.0)
            server.close()
            await server.wait_closed()

    def run_self_test(self) -> dict[str, Any]:
        generated_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        checks: list[dict[str, Any]] = []

        def add(name: str, status: str, detail: str = "", extra: dict[str, Any] | None = None) -> None:
            checks.append({"name": name, "status": status, "detail": detail, **(extra or {})})

        state_stats = disk_stats(self.state_dir)
        free_bytes = int(state_stats.get("free_bytes") or 0)
        add("State directory", "pass" if free_bytes > 100 * 1024 * 1024 else "warn", f"{int(free_bytes / 1024 / 1024)} MB free", state_stats)

        try:
            spool_stats = self.spool.stats()
            add("Queue database", "pass", f"{spool_stats.get('pending_payloads', 0)} pending payloads", spool_stats)
        except Exception as exc:
            add("Queue database", "fail", str(exc))

        server_version = (self.config() or {}).get("server_version")
        update_available = bool(server_version and server_version != APP_VERSION)
        add(
            "Agent version",
            "warn" if update_available else "pass",
            f"local {APP_VERSION}; server {server_version or 'unknown'}",
            {"update_available": update_available},
        )

        timer = self.update_timer_state(force=True)
        add(
            "Update timer",
            "pass" if timer.get("ok") else "warn",
            f"enabled={timer.get('enabled')}; active={timer.get('active')}; result={timer.get('last_result') or 'unknown'}",
            timer,
        )

        sudo_check = self.command_status(["sudo", "-n", "true"], timeout=5) if os.name != "nt" else {"ok": False, "detail": "not Linux"}
        add("Maintenance sudo", "pass" if sudo_check.get("ok") else "fail", str(sudo_check.get("detail") or "sudo preflight ok"))

        network = network_snapshot()
        route = network.get("default_route") if isinstance(network.get("default_route"), dict) else {}
        add(
            "Network address",
            "pass" if network.get("ip_addresses") else "fail",
            ", ".join(network.get("ip_addresses") or []) or "No IP addresses reported",
            network,
        )
        add(
            "Default route",
            "pass" if route.get("ok") else "fail",
            f"{route.get('interface') or 'no interface'} via {route.get('gateway') or 'direct/no gateway'}",
            route,
        )
        add(
            "DNS servers",
            "pass" if network.get("dns_servers") else "warn",
            ", ".join(network.get("dns_servers") or []) or "No DNS servers in /etc/resolv.conf",
            {"dns_servers": network.get("dns_servers") or []},
        )
        wifi = network.get("wifi") if isinstance(network.get("wifi"), dict) else {}
        add(
            "Wi-Fi SSID",
            "pass" if wifi.get("ssid") else "warn",
            str(wifi.get("ssid") or wifi.get("error") or "No active wlan0 SSID reported"),
            wifi,
        )
        reachability = self.matador_reachability()
        add(
            "Matador reachability",
            "pass" if reachability.get("ok") else "fail",
            f"{reachability.get('status') or reachability.get('error') or 'unknown'} in {reachability.get('latency_ms')} ms",
            reachability,
        )

        try:
            devices = discover_gofree_devices(min(self.discovery_timeout, 4.0))
            lock = self.locked_processor_identity()
            lock_match = any(device_matches_identity(device, lock) for device in devices) if lock else None
            status = "pass" if devices and (lock_match is not False) else "warn" if devices else "fail"
            detail = f"{len(devices)} processor(s) discovered"
            if lock:
                detail = f"{detail}; lock match={'yes' if lock_match else 'no'}"
            add("GoFree discovery", status, detail, {"processors": [device.identity() for device in devices]})
        except Exception as exc:
            add("GoFree discovery", "fail", str(exc))

        last_processor_data_at = self.state.get("last_processor_data_at")
        add("GoFree telemetry", "pass" if last_processor_data_at else "warn", f"last data {last_processor_data_at or 'never'}")
        last_upload_at = self.state.get("last_upload_at")
        add("Matador upload", "pass" if last_upload_at else "warn", f"last upload {last_upload_at or 'never'}")

        severity = {"fail": 2, "warn": 1, "pass": 0}
        worst = max((severity.get(check["status"], 1) for check in checks), default=0)
        summary = "fail" if worst >= 2 else "warn" if worst == 1 else "pass"
        report = {"generated_at": generated_at, "summary": summary, "checks": checks}
        self.state["last_self_test"] = report
        return report

    def run_background_update(self) -> None:
        script = Path(__file__).resolve().parents[1] / "scripts" / "update.sh"
        if not script.exists():
            raise RuntimeError(f"Update script not found: {script}")
        self.state["last_update_requested_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        if os.name != "nt":
            self.run_checked_command(["sudo", "-n", "true"], timeout=5)
            self.run_checked_command(["sudo", "-n", "systemctl", "--no-block", "start", "matador-pi-edge-update.service"], timeout=10)
            return
        subprocess.Popen([str(script)], cwd=str(script.parents[1]), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def update_result(self) -> dict[str, Any] | None:
        log_path = self.state_dir / "update.log"
        if not log_path.exists():
            return None
        content = tail_text(log_path)
        lower = content.lower()
        status = "unknown"
        if "update completed at" in lower:
            status = "ok"
        elif any(token in lower for token in ("fatal:", "error:", "failed", "traceback")):
            status = "error"
        result: dict[str, Any] = {
            "status": status,
            "log_path": str(log_path),
            "requested_at": self.state.get("last_update_requested_at") or None,
            "log_tail": content[-8000:],
        }
        with suppress(OSError):
            result["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(log_path.stat().st_mtime))
        return result

    def disk_guard(self, state_stats: dict[str, Any], spool_stats: dict[str, Any]) -> dict[str, Any]:
        used = float_or_none(state_stats.get("used_percent"))
        pending = int(spool_stats.get("pending_payloads") or 0)
        queue_bytes = int(spool_stats.get("queued_payload_bytes") or 0)
        if used is None:
            return {"level": "unknown", "message": "Disk usage unavailable", "can_buffer": True}
        if used >= DISK_STOP_BUFFERING_USED_PERCENT:
            level = "critical"
            message = f"Disk is {used:.1f}% full; buffering is at risk."
            can_buffer = False
        elif used >= DISK_CRITICAL_USED_PERCENT:
            level = "critical"
            message = f"Disk is {used:.1f}% full; resume uploads or clear backlog soon."
            can_buffer = True
        elif used >= DISK_WARN_USED_PERCENT:
            level = "warn"
            message = f"Disk is {used:.1f}% full; monitor queue growth."
            can_buffer = True
        else:
            level = "ok"
            message = f"Disk is {used:.1f}% full."
            can_buffer = True
        return {
            "level": level,
            "message": message,
            "can_buffer": can_buffer,
            "used_percent": used,
            "pending_payloads": pending,
            "queued_payload_bytes": queue_bytes,
        }

    def set_auto_update_timer(self, enabled: bool) -> None:
        if os.name == "nt":
            raise RuntimeError("Auto-update timer control is only supported on Raspberry Pi/Linux agents")
        action = "enable" if enabled else "disable"
        command = ["sudo", "-n", "systemctl", action]
        if enabled:
            command.append("--now")
        else:
            command.append("--now")
        command.append("matador-pi-edge-update.timer")
        self.run_checked_command(command, timeout=20)

    def set_system_hostname(self, requested_hostname: str) -> None:
        cleaned = "".join(ch for ch in requested_hostname.strip().lower() if ch.isalnum() or ch == "-").strip("-")
        if not cleaned or len(cleaned) > 63:
            raise RuntimeError("Hostname must contain letters, numbers, or hyphens and be 1-63 characters")
        if os.name == "nt":
            raise RuntimeError("Hostname changes are only supported on Raspberry Pi/Linux agents")
        helper = Path(__file__).resolve().parents[1] / "scripts" / "set-hostname.sh"
        if helper.exists():
            self.run_checked_command(["sudo", "-n", str(helper), cleaned], timeout=20)
        else:
            self.run_checked_command(["sudo", "-n", "hostnamectl", "set-hostname", cleaned], timeout=15)
        self.state["requested_hostname"] = cleaned

    def ensure_unique_hostname_for_golden_image(self) -> None:
        if os.name == "nt":
            return
        marker_path = self.state_dir / GOLDEN_IMAGE_HOSTNAME_MARKER
        marker_pending = marker_path.exists()
        current = hostname().strip().lower()
        generated_hostname = f"matador-pi-edge-{stable_device_suffix()}"
        current_is_stale_generated_clone = hostname_is_generated_by_agent(current) and current != generated_hostname
        should_generate = marker_pending or hostname_is_generic(current) or current_is_stale_generated_clone
        if not should_generate:
            if self.state.get("hostname_uniqued_at") or self.state.get("requested_hostname"):
                return
            self.state["hostname_uniqued_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            self.state["hostname_uniqued_from"] = current
            self.save_state()
            return
        if current == generated_hostname:
            self.state["hostname_uniqued_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            self.state["hostname_uniqued_from"] = current
            self.state["requested_hostname"] = generated_hostname
            with suppress(OSError):
                marker_path.unlink()
            self.save_state()
            return
        try:
            self.set_system_hostname(generated_hostname)
            self.state["hostname_uniqued_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            self.state["hostname_uniqued_from"] = current
            with suppress(OSError):
                marker_path.unlink()
            LOGGER.info("Updated hostname %s to %s for cloned-image uniqueness", current, generated_hostname)
            self.save_state()
        except Exception as exc:
            LOGGER.warning("Unable to set unique first-boot hostname: %s", exc)
            self.state["hostname_uniquing_error"] = str(exc)
            self.save_state()

    def handle_remote_command(self, command: dict[str, Any]) -> None:
        raw_action = str(command.get("action") or "").strip()
        action, _, argument = raw_action.partition("|")
        action = action.strip()
        argument = argument.strip()
        requested_at = str(command.get("requested_at") or "").strip()
        if not action or not requested_at or requested_at == self.last_remote_command_at:
            return
        LOGGER.info("Applying remote command %s requested at %s", action, requested_at)
        try:
            if action == "connect_processor":
                self.processor_enabled = True
            elif action == "reconnect_processor":
                self.processor_enabled = True
                self.processor_reconnect_requested = True
            elif action == "refresh_discovery":
                self.processor_reconnect_requested = True
            elif action == "start_streaming":
                self.processor_enabled = True
                self.streaming_enabled = True
                self.upload_paused = False
            elif action == "stop_streaming":
                self.streaming_enabled = False
            elif action == "pause_uploads":
                self.upload_paused = True
            elif action == "resume_uploads":
                self.upload_paused = False
                self.streaming_enabled = True
            elif action == "clear_queue":
                self.clear_runtime_queues()
                self.spool.clear()
                self.state["upload_rate_payloads_per_second"] = 0
                self.state["upload_rate_readings_per_second"] = 0
                self.state["last_queue_cleared_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            elif action == "support_bundle":
                self.state["last_support_bundle"] = self.support_bundle()
            elif action == "self_test":
                self.run_self_test()
            elif action == "reboot_system":
                acked = self.acknowledge_remote_command(requested_at)
                self.record_command_result(action, "ok", "System reboot requested by Matador admin")
                if acked:
                    self.last_remote_command_at = requested_at
                    self.state["last_remote_command_at"] = requested_at
                self.save_state()
                self.run_checked_command(["sudo", "-n", "systemctl", "reboot"], timeout=10)
                return
            elif action == "set_hostname":
                self.set_system_hostname(argument)
            elif action == "update_agent":
                self.run_background_update()
            elif action == "enable_auto_update":
                self.set_auto_update_timer(True)
            elif action == "disable_auto_update":
                self.set_auto_update_timer(False)
            elif action == "reset_agent":
                acked = self.acknowledge_remote_command(requested_at)
                for key in ("device_token", "config", "enrolled_at", "last_remote_command_at"):
                    self.state.pop(key, None)
                self.reset_claim_identity()
                self.current_config = {}
                self.record_command_result(action, "ok", "Agent reset to claim mode; restarting.")
                if acked:
                    self.state["last_remote_command_at"] = requested_at
                self.save_state()
                raise RestartRequested("Reset to claim mode requested by Matador admin")
            elif action == "restart_agent":
                self.record_command_result(action, "ok", "Restart requested by Matador admin")
                self.acknowledge_remote_command(requested_at)
                self.last_remote_command_at = requested_at
                self.state["last_remote_command_at"] = requested_at
                self.save_state()
                raise RestartRequested("Restart requested by Matador admin")
            else:
                LOGGER.warning("Ignoring unknown remote command: %s", action)
                self.record_command_result(action, "ignored", "Unknown remote command")
                return
            self.record_command_result(action, "ok", "Command applied")
        except RestartRequested:
            raise
        except Exception as exc:
            LOGGER.warning("Remote command %s failed: %s", action, exc)
            self.record_command_result(action, "error", str(exc))
        self.state["processor_enabled"] = self.processor_enabled
        self.state["streaming_enabled"] = self.streaming_enabled
        self.state["upload_paused"] = self.upload_paused
        if self.acknowledge_remote_command(requested_at):
            self.last_remote_command_at = requested_at
            self.state["last_remote_command_at"] = requested_at
        self.save_state()

    def health_payload(self, *, include_support_bundle: bool = True) -> dict[str, Any]:
        spool_stats = self.spool.stats()
        state_stats = disk_stats(self.state_dir)
        processor_queued = int(self.counters.get("processor_payloads_queued") or 0)
        pending = int(spool_stats.get("pending_payloads") or 0)
        upload_rate = float_or_none(self.state.get("upload_rate_payloads_per_second"))
        queue_eta_seconds = (pending / upload_rate) if pending and upload_rate and upload_rate > 0 else None
        lock = self.locked_processor_identity()
        serial = normalized_serial_number((lock or {}).get("serial_number")) if lock else ""
        server_version = (self.config() or {}).get("server_version")
        lock_confidence = (
            "serial"
            if serial
            else "identity"
            if lock and (lock.get("name") or lock.get("model"))
            else "host"
            if lock and lock.get("last_host")
            else "none"
        )
        payload = {
            "agent": {
                "kind": "pi_edge_agent",
                "name": APP_NAME,
                "version": APP_VERSION,
                "hostname": hostname(),
                "latest_server_version": server_version,
                "update_available": bool(server_version and server_version != APP_VERSION),
                "hostname_uniqued_at": self.state.get("hostname_uniqued_at") or None,
                "hostname_uniqued_from": self.state.get("hostname_uniqued_from") or None,
                "hostname_uniquing_error": self.state.get("hostname_uniquing_error") or None,
            },
            "controls": {
                "processor_enabled": self.processor_enabled,
                "streaming_enabled": self.streaming_enabled,
                "upload_paused": self.upload_paused,
                "last_remote_command_at": self.last_remote_command_at or None,
                "processor_ping_interval_seconds": self.processor_ping_interval_seconds,
                "processor_ping_timeout_seconds": self.processor_ping_timeout_seconds,
                "data_silence_reconnect_seconds": self.data_silence_reconnect_seconds,
                "upload_batch_max_readings": self.upload_batch_max_readings,
                "upload_batch_max_payloads": self.upload_batch_max_payloads,
                "historical_storage_sample_hz": self.storage_sample_hz,
            },
            "storage": {
                "state_dir": state_stats,
                "spool": {
                    **spool_stats,
                    "estimated_delivered_payloads": max(0, processor_queued - pending),
                    "oldest_pending_message_age_seconds": spool_stats.get("oldest_payload_age_seconds"),
                    "upload_rate_payloads_per_second": upload_rate,
                    "upload_rate_readings_per_second": float_or_none(self.state.get("upload_rate_readings_per_second")),
                    "estimated_drain_eta_seconds": queue_eta_seconds,
                },
                "disk_guard": self.disk_guard(state_stats, spool_stats),
            },
            "system": load_average(),
            "network": network_snapshot(),
            "update_timer": self.update_timer_state(),
            "update_result": self.update_result(),
            "counters": self.counters,
            "links": {
                "last_config_at": self.state.get("last_config_at") or None,
                "last_processor_data_at": self.state.get("last_processor_data_at") or None,
                "last_upstream_connected_at": self.state.get("last_upstream_connected_at") or None,
                "last_upload_at": self.state.get("last_upload_at") or None,
            },
            "command": self.state.get("last_command_result") or None,
            "last_discovered_device": self.state.get("last_discovered_device") or None,
            "last_discovered_processors": self.state.get("last_discovered_processors") or [],
            "locked_processor_identity": lock,
            "lock_confidence": lock_confidence,
            "current_processor_identity": self.current_processor_identity or None,
            "last_processor_host": self.state.get("last_processor_host") or None,
            "self_test": self.state.get("last_self_test") or None,
        }
        if include_support_bundle:
            payload["support_bundle"] = self.state.get("last_support_bundle") or None
        return payload

    def config(self) -> dict[str, Any]:
        return self.current_config or self.state.get("config") or {}

    def locked_processor_identity(self) -> dict[str, Any] | None:
        config_lock = self.config().get("processor_lock")
        if isinstance(config_lock, dict) and config_lock:
            return config_lock
        state_lock = self.state.get("locked_processor_identity")
        return state_lock if isinstance(state_lock, dict) and state_lock else None

    def set_current_processor_identity(self, identity: dict[str, Any]) -> None:
        cleaned = {
            "name": str(identity.get("name") or "").strip(),
            "model": str(identity.get("model") or "").strip(),
            "serial_number": normalized_serial_number(identity.get("serial_number")),
            "last_host": str(identity.get("last_host") or "").strip(),
            "port": int_or_none(identity.get("port")) or 2053,
        }
        self.current_processor_identity = cleaned
        self.state["current_processor_identity"] = cleaned

    def h5000_barcode_serial_number(self) -> str:
        setting = self.setting_by_id.get(GOFREE_BARCODE_SERIAL_SETTING_ID)
        if not setting:
            return ""
        for key in ("valStr", "value_text", "text", "str", "value", "val"):
            serial = normalized_serial_number(setting.get(key))
            if serial:
                return serial
        return ""

    def refresh_processor_identity_from_settings(self) -> None:
        serial = self.h5000_barcode_serial_number()
        if not serial or not self.current_processor_identity:
            return
        if self.current_processor_identity.get("serial_number") == serial:
            return
        previous_serial = self.current_processor_identity.get("serial_number") or "none"
        self.current_processor_identity["serial_number"] = serial
        LOGGER.info("Resolved GoFree processor barcode serial from setting %s: %s (was %s)", GOFREE_BARCODE_SERIAL_SETTING_ID, serial, previous_serial)
        self.state["current_processor_identity"] = dict(self.current_processor_identity)
        lock = self.locked_processor_identity()
        if lock and str(lock.get("name") or "") == str(self.current_processor_identity.get("name") or ""):
            lock = dict(lock)
            lock["serial_number"] = serial
            lock["last_host"] = self.current_processor_identity.get("last_host") or lock.get("last_host")
            lock["port"] = self.current_processor_identity.get("port") or lock.get("port")
            self.state["locked_processor_identity"] = lock
        self.save_state()

    def resolve_processor(self) -> tuple[str, int, str]:
        config = self.config()
        local = config.get("local_processor") or {}
        port = int_or_none(local.get("port")) or 2053
        path = str(local.get("path") or "/")
        if self.processor_host_override:
            return self.processor_host_override, port, path
        configured_host = str(local.get("manual_host") or "").strip()
        lock = self.locked_processor_identity()
        LOGGER.info("Discovering GoFree processors over multicast")
        devices = discover_gofree_devices(self.discovery_timeout)
        discovered_processors = [device.identity() for device in devices]
        self.state["last_discovered_processors"] = discovered_processors
        if devices:
            self.state["last_discovered_device"] = devices[0].__dict__
        self.save_state()
        if lock:
            selected = next((device for device in devices if device_matches_identity(device, lock)), None)
            if selected:
                LOGGER.info("Selected locked GoFree processor: %s", selected.label)
                self.set_current_processor_identity(selected.identity())
                self.state["locked_processor_identity"] = selected.identity()
                self.state["last_processor_host"] = selected.host
                self.save_state()
                return selected.host, selected.port or port, path
            last_host = str(lock.get("last_host") or configured_host or "").strip()
            if last_host and last_host != "0.0.0.0":
                LOGGER.warning("Locked GoFree processor not discovered; trying last known host %s", last_host)
                fallback_identity = dict(lock)
                fallback_identity["last_host"] = last_host
                fallback_identity["port"] = int_or_none(lock.get("port")) or port
                self.set_current_processor_identity(fallback_identity)
                return last_host, int_or_none(lock.get("port")) or port, path
            raise RuntimeError("Locked GoFree processor was not discovered")
        if configured_host and configured_host != "0.0.0.0":
            return configured_host, port, path
        if not devices:
            last_host = str(self.state.get("last_processor_host") or "").strip()
            if last_host:
                LOGGER.warning("No GoFree discovery result; falling back to last processor host %s", last_host)
                return last_host, port, path
            raise RuntimeError("No GoFree processor discovered")
        if len(devices) > 1:
            labels = "; ".join(device.label for device in devices[:5])
            raise RuntimeError(f"Multiple GoFree processors discovered; admin processor lock required. Found: {labels}")
        selected = devices[0]
        LOGGER.info("Selected GoFree processor: %s", selected.label)
        self.state["last_discovered_device"] = selected.__dict__
        self.state["last_discovered_processors"] = [selected.identity()]
        self.state["last_processor_host"] = selected.host
        self.set_current_processor_identity(selected.identity())
        self.save_state()
        return selected.host, selected.port or port, path

    def subscription_metrics(self) -> list[dict[str, Any]]:
        metrics = self.config().get("metrics") or []
        if not metrics:
            raise RuntimeError("Matador config did not include metric subscriptions")
        return [item for item in metrics if isinstance(item, dict) and int_or_none(item.get("id")) is not None]

    def subscription_message(self) -> str:
        return json.dumps(
            {
                "DataReq": [
                    {"id": int(item["id"]), "repeat": True, "inst": 0}
                    for item in self.subscription_metrics()
                ]
            },
            separators=(",", ":"),
        )

    def data_info_message(self) -> str | None:
        metric_ids = sorted(
            {
                metric_id
                for item in self.subscription_metrics()
                if str(item.get("name") or "") in GOFREE_DATA_INFO_METRIC_NAMES
                for metric_id in [int_or_none(item.get("id"))]
                if metric_id is not None and metric_id < 10000
            }
        )
        return json.dumps({"DataInfoReq": metric_ids}, separators=(",", ":")) if metric_ids else None

    def setting_message(self) -> str:
        return json.dumps({"SettingReq": {"ids": list(GOFREE_SETTING_IDS)}}, separators=(",", ":"))

    async def request_metadata(self, websocket) -> None:
        data_info_message = self.data_info_message()
        if data_info_message:
            await websocket.send(data_info_message)
        await websocket.send(self.setting_message())

    def update_data_info(self, payload: dict[str, Any]) -> bool:
        data_info = payload.get("DataInfo")
        if not isinstance(data_info, list):
            return False
        updated = False
        for item in data_info:
            if not isinstance(item, dict):
                continue
            metric_id = int_or_none(item.get("id"))
            if metric_id is None:
                continue
            self.data_info_by_metric_id[metric_id] = dict(item)
            updated = True
        return updated

    def update_settings(self, payload: dict[str, Any]) -> bool:
        settings = payload.get("Setting")
        if not isinstance(settings, list):
            return False
        updated = False
        for item in settings:
            if not isinstance(item, dict):
                continue
            setting_id = int_or_none(item.get("id"))
            if setting_id is None:
                continue
            self.setting_by_id[setting_id] = dict(item)
            updated = True
        if updated:
            self.refresh_processor_identity_from_settings()
        return updated

    def metric_name_by_id(self) -> dict[int, str]:
        return {
            int(item["id"]): str(item.get("name") or "")
            for item in self.subscription_metrics()
            if int_or_none(item.get("id")) is not None
        }

    def compass_reference(self) -> str | None:
        setting = self.setting_by_id.get(GOFREE_COMPASS_TRUE_MAG_SETTING_ID)
        if not setting:
            return None
        value = int_or_none(setting.get("value"))
        if value == 0:
            return "magnetic"
        if value == 1:
            return "true"
        return None

    def enrich_data_item(self, item: dict[str, Any]) -> dict[str, Any]:
        metric_id = int_or_none(item.get("id"))
        if metric_id is None:
            return dict(item)
        metric_name = self.metric_name_by_id().get(metric_id, "")
        enriched = dict(item)
        info = self.data_info_by_metric_id.get(metric_id)
        if info:
            for key in ("sname", "lname", "unit", "min", "max"):
                if key in info and enriched.get(key) is None:
                    enriched[key] = info[key]
        compass_reference = self.compass_reference()
        if metric_name:
            enriched.setdefault("metric_name", metric_name)
        if metric_name in GOFREE_COMPASS_TRUE_MAG_METRIC_NAMES and compass_reference is not None:
            enriched["compassTrueMagSettingId"] = GOFREE_COMPASS_TRUE_MAG_SETTING_ID
            enriched["compassTrueMagSettingValue"] = 1 if compass_reference == "true" else 0
            enriched["compassTrueMagReference"] = compass_reference
            enriched["unit"] = "&deg;T" if compass_reference == "true" else "&deg;M"
        return enriched

    async def processor_loop(self) -> None:
        backoff = 1.0
        while not self.stop_event.is_set():
            try:
                await asyncio.to_thread(self.fetch_config)
                if not self.processor_enabled:
                    self.processor_connection_status = "disabled"
                    await asyncio.sleep(IDLE_SLEEP_SECONDS)
                    continue
                processor_host, processor_port, processor_path = self.resolve_processor()
                await self.processor_once(processor_host, processor_port, processor_path)
                await self.flush_historical_payloads()
                backoff = 1.0
            except RestartRequested:
                await self.flush_historical_payloads()
                self.stop_event.set()
                raise
            except Exception as exc:
                await self.flush_historical_payloads()
                self.processor_connection_status = f"reconnecting: {exc}"
                LOGGER.warning("Processor loop interrupted: %s. Reconnecting in %.1fs", exc, backoff)
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 60.0)

    async def processor_once(self, processor_host: str, processor_port: int, processor_path: str) -> None:
        self.data_info_by_metric_id.clear()
        self.setting_by_id.clear()
        url = f"ws://{processor_host}:{processor_port}{processor_path or '/'}"
        LOGGER.info("Connecting to GoFree processor at %s", url)
        self.processor_connection_status = f"connecting {processor_host}:{processor_port}"
        async with websockets.connect(
            url,
            ping_interval=self.processor_ping_interval_seconds,
            ping_timeout=self.processor_ping_timeout_seconds,
            max_queue=1024,
        ) as websocket:
            await websocket.send(self.subscription_message())
            await self.request_metadata(websocket)
            last_metadata_request = time.monotonic()
            last_data_received = time.monotonic()
            self.state["last_processor_host"] = processor_host
            self.save_state()
            self.processor_connection_status = f"connected {processor_host}:{processor_port}"
            LOGGER.info("Subscribed to %s GoFree metrics", len(self.subscription_metrics()))
            while not self.stop_event.is_set() and self.processor_enabled:
                if self.processor_reconnect_requested:
                    self.processor_reconnect_requested = False
                    raise RuntimeError("Processor reconnect requested by Matador admin")
                if time.monotonic() - last_data_received >= self.data_silence_reconnect_seconds:
                    LOGGER.warning(
                        "No GoFree telemetry received for %.0fs; reconnecting processor websocket",
                        self.data_silence_reconnect_seconds,
                    )
                    raise RuntimeError("GoFree processor telemetry silence timeout")
                if time.monotonic() - last_metadata_request >= GOFREE_DATA_INFO_REFRESH_SECONDS:
                    await self.request_metadata(websocket)
                    last_metadata_request = time.monotonic()
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                except TimeoutError:
                    continue
                payload = json.loads(message.decode("utf-8") if isinstance(message, bytes) else message)
                if self.update_data_info(payload) or self.update_settings(payload):
                    LOGGER.debug("Updated GoFree processor metadata")
                    continue
                values = payload.get("Data") or []
                if not isinstance(values, list) or not values:
                    continue
                last_data_received = time.monotonic()
                self.state["last_processor_data_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                self.increment_counter("processor_messages_received")
                outgoing = {
                    "agent_kind": "pi_edge_agent",
                    "app_version": APP_VERSION,
                    "processor_host": processor_host,
                    "processor_identity": self.current_processor_identity or None,
                    "sent_at": time.time(),
                    "Data": [
                        self.enrich_data_item(item)
                        for item in values
                        if isinstance(item, dict)
                    ],
                }
                if not outgoing["Data"]:
                    continue
                self.record_latest_values(outgoing["Data"])
                self.enqueue_live_payload(outgoing)
                await self.enqueue_historical_payloads(outgoing)

    async def stream_loop(self) -> None:
        backoff = 1.0
        while not self.stop_event.is_set():
            try:
                await asyncio.to_thread(self.fetch_config)
                if not self.streaming_enabled or self.upload_paused:
                    self.upstream_connection_status = "paused" if self.upload_paused else "disabled"
                    await asyncio.sleep(IDLE_SLEEP_SECONDS)
                    continue
                await self.stream_once()
                backoff = 1.0
            except RestartRequested:
                self.stop_event.set()
                raise
            except urllib.error.HTTPError as exc:
                if exc.code in (401, 403):
                    LOGGER.error("Matador rejected this Pi Edge Agent token; re-enrollment is required")
                    self.upstream_connection_status = "rejected"
                    self.stop_event.set()
                    return
                self.upstream_connection_status = f"reconnecting: {exc}"
                LOGGER.warning("Matador config failed: %s. Reconnecting in %.1fs", exc, backoff)
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 60.0)
            except Exception as exc:
                self.upstream_connection_status = f"reconnecting: {exc}"
                LOGGER.warning("Upstream stream interrupted: %s. Reconnecting in %.1fs", exc, backoff)
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 60.0)

    def build_upload_payload(self, rows: list[tuple[int, dict[str, Any]]]) -> dict[str, Any]:
        first_payload = dict(rows[0][1])
        readings: list[dict[str, Any]] = []
        queued_sent_at_values: list[float] = []
        for _, payload in rows:
            sent_at = float_or_none(payload.get("sent_at"))
            if sent_at is not None:
                queued_sent_at_values.append(sent_at)
            data = payload.get("Data")
            if not isinstance(data, list):
                continue
            for item in data:
                if not isinstance(item, dict):
                    continue
                reading = dict(item)
                if sent_at is not None:
                    reading.setdefault("time", sent_at)
                readings.append(reading)

        first_payload["Data"] = readings
        first_payload["agent_kind"] = "pi_edge_agent"
        first_payload["app_version"] = APP_VERSION
        first_payload["payload_batch"] = {
            "payload_count": len(rows),
            "reading_count": len(readings),
            "oldest_payload_sent_at": min(queued_sent_at_values) if queued_sent_at_values else None,
            "newest_payload_sent_at": max(queued_sent_at_values) if queued_sent_at_values else None,
        }
        return first_payload

    async def send_upstream_payload(self, websocket: Any, outgoing: dict[str, Any], *, timeout_seconds: float = 15.0) -> dict[str, Any]:
        outgoing["pi_health"] = self.health_payload()
        await websocket.send(json.dumps(outgoing, separators=(",", ":")))
        response_text = await asyncio.wait_for(websocket.recv(), timeout=timeout_seconds)
        response = json.loads(response_text)
        if not response.get("ok", False):
            raise RuntimeError(str(response.get("error") or "Matador rejected Edge payload"))
        return response

    async def stream_once(self) -> None:
        token = self.device_token
        if not token:
            raise RuntimeError("No device token available")
        upstream_url = f"{self.server_url.replace('https://', 'wss://').replace('http://', 'ws://')}/edge/stream?token={token}"
        LOGGER.info("Connecting upstream to %s", upstream_url.split("?token=", 1)[0])
        self.upstream_connection_status = "connecting"
        async with websockets.connect(upstream_url, ping_interval=30, ping_timeout=30) as websocket:
            LOGGER.info("Upstream Matador stream connected")
            self.upstream_connection_status = "connected"
            self.state["last_upstream_connected_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            while not self.stop_event.is_set() and self.streaming_enabled:
                if self.upload_paused:
                    return
                sent_live_payload = False
                with suppress(asyncio.QueueEmpty):
                    live_outgoing = self.live_payload_queue.get_nowait()
                    await self.send_upstream_payload(websocket, dict(live_outgoing), timeout_seconds=5.0)
                    self.increment_counter("upstream_live_payloads_sent")
                    self.increment_counter("upstream_readings_sent", len(live_outgoing.get("Data") or []))
                    self.state["last_upload_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                    self.save_state()
                    sent_live_payload = True
                rows = await asyncio.to_thread(
                    self.spool.peek_oldest_batch,
                    self.upload_batch_max_payloads,
                    self.upload_batch_max_readings,
                )
                if not rows:
                    if sent_live_payload:
                        continue
                    await asyncio.sleep(IDLE_SLEEP_SECONDS)
                    continue
                payload_ids = [payload_id for payload_id, _ in rows]
                outgoing = self.build_upload_payload(rows)
                try:
                    await self.send_upstream_payload(websocket, outgoing)
                except RuntimeError:
                    self.increment_counter("upstream_payloads_failed", len(rows))
                    raise
                await asyncio.to_thread(self.spool.ack_many, payload_ids)
                self.increment_counter("upstream_batches_sent")
                self.increment_counter("upstream_payloads_sent", len(rows))
                self.increment_counter("upstream_readings_sent", len(outgoing.get("Data") or []))
                self.record_upload_progress(len(rows), len(outgoing.get("Data") or []))
                self.state["last_upload_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                self.save_state()

    async def run(self) -> None:
        await asyncio.to_thread(self.ensure_unique_hostname_for_golden_image)
        await asyncio.to_thread(self.fetch_config)
        await asyncio.gather(self.config_loop(), self.processor_loop(), self.stream_loop(), self.local_status_loop())

    async def config_loop(self) -> None:
        while not self.stop_event.is_set():
            try:
                await asyncio.to_thread(self.fetch_config)
            except RestartRequested:
                self.stop_event.set()
                raise
            except urllib.error.HTTPError as exc:
                if exc.code in (401, 403):
                    LOGGER.error("Matador rejected this Pi Edge Agent token; re-enrollment is required")
                    self.config_status = "rejected"
                    self.stop_event.set()
                    return
                self.config_status = f"error: {exc}"
                LOGGER.warning("Config poll failed: %s", exc)
            except Exception as exc:
                self.config_status = f"error: {exc}"
                LOGGER.warning("Config poll failed: %s", exc)
            await asyncio.sleep(CONFIG_POLL_SECONDS)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Headless Matador Pi Edge Agent")
    parser.add_argument("--server", default=os.environ.get("MATADOR_EDGE_SERVER", DEFAULT_SERVER), help="Matador server URL")
    parser.add_argument("--state-dir", default=os.environ.get("MATADOR_PI_EDGE_STATE_DIR", str(default_state_dir())), help="State directory")
    parser.add_argument("--enrollment-code", default=os.environ.get("MATADOR_EDGE_ENROLLMENT_CODE", ""), help="One-time Matador Edge enrollment code")
    parser.add_argument("--processor-host", default=os.environ.get("MATADOR_PROCESSOR_HOST", ""), help="Optional fixed GoFree processor IP")
    parser.add_argument("--discovery-timeout", type=float, default=float(os.environ.get("MATADOR_DISCOVERY_TIMEOUT", "8")), help="GoFree discovery timeout in seconds")
    parser.add_argument(
        "--data-silence-reconnect-seconds",
        type=float,
        default=float(os.environ.get("MATADOR_PI_EDGE_DATA_SILENCE_RECONNECT_SECONDS", str(GOFREE_DATA_SILENCE_RECONNECT_SECONDS))),
        help="Reconnect the GoFree processor websocket if no telemetry Data messages arrive for this many seconds",
    )
    parser.add_argument(
        "--processor-ping-interval-seconds",
        type=float,
        default=float(os.environ.get("MATADOR_PI_EDGE_PROCESSOR_PING_INTERVAL_SECONDS", str(GOFREE_PROCESSOR_PING_INTERVAL_SECONDS))),
        help="Websocket ping interval for the local GoFree processor connection. Set to 0 to disable.",
    )
    parser.add_argument(
        "--processor-ping-timeout-seconds",
        type=float,
        default=float(os.environ.get("MATADOR_PI_EDGE_PROCESSOR_PING_TIMEOUT_SECONDS", str(GOFREE_PROCESSOR_PING_TIMEOUT_SECONDS))),
        help="Websocket ping timeout for the local GoFree processor connection. Set to 0 to disable.",
    )
    parser.add_argument(
        "--upload-batch-max-readings",
        type=int,
        default=int(os.environ.get("MATADOR_PI_EDGE_UPLOAD_BATCH_MAX_READINGS", str(UPLOAD_BATCH_MAX_READINGS))),
        help="Maximum readings to send to Matador in one queued upload batch. Clamped to 500.",
    )
    parser.add_argument(
        "--upload-batch-max-payloads",
        type=int,
        default=int(os.environ.get("MATADOR_PI_EDGE_UPLOAD_BATCH_MAX_PAYLOADS", str(UPLOAD_BATCH_MAX_PAYLOADS))),
        help="Maximum queued SQLite payload rows to merge into one Matador upload batch.",
    )
    parser.add_argument(
        "--spool-max-payloads",
        "--queue-size",
        dest="spool_max_payloads",
        type=int,
        default=int(os.environ.get("MATADOR_PI_EDGE_SPOOL_MAX_PAYLOADS", os.environ.get("MATADOR_PI_EDGE_QUEUE_SIZE", str(SPOOL_MAX_PAYLOADS)))),
        help="Maximum durable outbound payloads to retain before oldest payloads are discarded. Set 0 for unlimited.",
    )
    parser.add_argument(
        "--storage-sample-hz",
        type=float,
        default=float(os.environ.get("MATADOR_PI_EDGE_STORAGE_SAMPLE_HZ", str(STORAGE_SAMPLE_HZ))),
        help="Durable queue sampling rate for historical/export data. Default 1 Hz; set 0 to queue every GoFree payload.",
    )
    parser.add_argument(
        "--local-status-host",
        default=os.environ.get("MATADOR_PI_EDGE_LOCAL_STATUS_HOST", LOCAL_STATUS_HOST),
        help="Bind address for the local Pi health web page. Default 0.0.0.0 for LAN access.",
    )
    parser.add_argument(
        "--local-status-port",
        type=int,
        default=int(os.environ.get("MATADOR_PI_EDGE_LOCAL_STATUS_PORT", str(LOCAL_STATUS_PORT))),
        help="Port for the local Pi health web page. Default 8080; set 0 to disable.",
    )
    parser.add_argument("--discover-once", action="store_true", help="Print discovered GoFree processors and exit")
    parser.add_argument("--log-level", default=os.environ.get("MATADOR_PI_EDGE_LOG_LEVEL", "INFO"), help="Python logging level")
    return parser.parse_args()


def configure_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


def main() -> None:
    args = parse_args()
    configure_logging(args.log_level)
    if args.discover_once:
        for device in discover_gofree_devices(args.discovery_timeout):
            print(device.label)
        return
    agent = PiEdgeAgent(
        server_url=args.server,
        state_dir=Path(args.state_dir),
        enrollment_code=args.enrollment_code,
        processor_host=args.processor_host,
        discovery_timeout=args.discovery_timeout,
        spool_max_payloads=args.spool_max_payloads,
        data_silence_reconnect_seconds=args.data_silence_reconnect_seconds,
        processor_ping_interval_seconds=args.processor_ping_interval_seconds,
        processor_ping_timeout_seconds=args.processor_ping_timeout_seconds,
        upload_batch_max_readings=args.upload_batch_max_readings,
        upload_batch_max_payloads=args.upload_batch_max_payloads,
        storage_sample_hz=args.storage_sample_hz,
        local_status_host=args.local_status_host,
        local_status_port=args.local_status_port,
    )
    try:
        asyncio.run(agent.run())
    except RestartRequested:
        LOGGER.info("Restart requested by Matador admin")
        raise SystemExit(75)
    except KeyboardInterrupt:
        LOGGER.info("Stopping Pi Edge Agent")


if __name__ == "__main__":
    main()
