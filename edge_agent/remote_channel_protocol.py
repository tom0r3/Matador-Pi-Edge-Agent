from __future__ import annotations

import hashlib
import hmac
import json
import math
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any


PROTOCOL_VERSION = 1
LINEAR_CHANNEL_FIRST_ID = 481
LINEAR_CHANNEL_LAST_ACTIVE_ID = 490
USER_DATA_SETTING_ID = 91
USER_DATA_EVENT_ID = 25
MAX_SOURCES = 5
MAX_COMMAND_FRAMES = 5
MAX_COMMAND_ITEMS = MAX_SOURCES * 2


class RemoteChannelCommandError(ValueError):
    """Raised when an Edge Remote Channels command is unsafe or malformed."""


@dataclass(frozen=True)
class RemoteChannelExecutionPlan:
    frames: tuple[str, ...]
    complete_after_send: bool = False


def canonical_command_bytes(command: dict[str, Any]) -> bytes:
    unsigned = {key: value for key, value in command.items() if key != "signature"}
    return json.dumps(unsigned, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def sign_command(command: dict[str, Any], token: str) -> dict[str, Any]:
    if not token:
        raise RemoteChannelCommandError("Edge command signing token is absent")
    signed = deepcopy(command)
    signed["signature"] = hmac.new(
        token.encode("utf-8"), canonical_command_bytes(signed), hashlib.sha256
    ).hexdigest()
    return signed


def verify_command(
    command: Any,
    token: str,
    target_processor_id: str,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    if not isinstance(command, dict):
        raise RemoteChannelCommandError("Edge command must be an object")
    signature = str(command.get("signature") or "").strip().lower()
    if len(signature) != 64 or any(char not in "0123456789abcdef" for char in signature):
        raise RemoteChannelCommandError("Edge command signature is invalid")
    expected = hmac.new(
        token.encode("utf-8"), canonical_command_bytes(command), hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(signature, expected):
        raise RemoteChannelCommandError("Edge command signature verification failed")
    if int(command.get("protocol_version") or 0) != PROTOCOL_VERSION:
        raise RemoteChannelCommandError("Unsupported Edge command protocol version")
    if str(command.get("target_processor_id") or "") != str(target_processor_id or ""):
        raise RemoteChannelCommandError("Edge command target does not match this processor")
    if not str(command.get("command_id") or "").strip():
        raise RemoteChannelCommandError("Edge command ID is absent")
    if not str(command.get("profile_id") or "").strip():
        raise RemoteChannelCommandError("Edge command profile ID is absent")
    if int(command.get("profile_revision") or 0) <= 0:
        raise RemoteChannelCommandError("Edge command profile revision is invalid")

    action = str(command.get("action") or "").strip().lower()
    if action not in {"write", "invalidate", "configure"}:
        raise RemoteChannelCommandError("Unsupported Edge command action")
    lease_generation = int(command.get("lease_generation") or 0)
    if action != "configure" and lease_generation <= 0:
        raise RemoteChannelCommandError("Edge write command lease generation is invalid")

    current = _aware_utc(now or datetime.now(timezone.utc))
    issued_at = _parse_time(command.get("issued_at"))
    expires_at = _parse_time(command.get("expires_at"))
    if issued_at > current + timedelta(seconds=10):
        raise RemoteChannelCommandError("Edge command issue time is in the future")
    if expires_at <= current:
        raise RemoteChannelCommandError("Edge command has expired")
    maximum_lifetime = 60.0 if action == "configure" else 5.0
    lifetime = (expires_at - issued_at).total_seconds()
    if lifetime <= 0 or lifetime > maximum_lifetime:
        raise RemoteChannelCommandError("Edge command lifetime exceeds its safety limit")

    payload = command.get("payload")
    if not isinstance(payload, dict):
        raise RemoteChannelCommandError("Edge command payload must be an object")
    if action == "configure":
        _validated_sources(payload.get("sources"))
    else:
        validate_frames(payload.get("frames"), require_invalid=(action == "invalidate"))
    return deepcopy(command)


def validate_frames(frames: Any, *, require_invalid: bool = False) -> tuple[str, ...]:
    if not isinstance(frames, list) or not 1 <= len(frames) <= MAX_COMMAND_FRAMES:
        raise RemoteChannelCommandError("Edge command must contain between one and five frames")
    normalized: list[str] = []
    item_count = 0
    for raw_frame in frames:
        if not isinstance(raw_frame, str):
            raise RemoteChannelCommandError("Edge command frame must be serialized JSON")
        try:
            frame = json.loads(raw_frame)
        except json.JSONDecodeError as exc:
            raise RemoteChannelCommandError("Edge command frame is not valid JSON") from exc
        if not isinstance(frame, dict) or set(frame) != {"Data"} or not isinstance(frame["Data"], list):
            raise RemoteChannelCommandError("Edge command frames may contain only a Data array")
        if not 1 <= len(frame["Data"]) <= 2:
            raise RemoteChannelCommandError("Each Edge command frame must contain one channel pair")
        item_count += len(frame["Data"])
        for item in frame["Data"]:
            if not isinstance(item, dict):
                raise RemoteChannelCommandError("Edge command Data item must be an object")
            metric_id = _integer(item.get("id"), "Linear Channel ID")
            if not LINEAR_CHANNEL_FIRST_ID <= metric_id <= LINEAR_CHANNEL_LAST_ACTIVE_ID:
                raise RemoteChannelCommandError("Edge command attempted to write outside Linear Channels 17-26")
            valid = item.get("valid")
            if not isinstance(valid, bool):
                raise RemoteChannelCommandError("Edge command Data validity must be explicit")
            if require_invalid and valid:
                raise RemoteChannelCommandError("Invalidation command contains a valid value")
            if valid:
                value = _finite_number(item.get("val"), "Linear Channel value")
                system_value = _finite_number(item.get("sysVal"), "Linear Channel system value")
                if not math.isclose(value, system_value, rel_tol=0, abs_tol=1e-9):
                    raise RemoteChannelCommandError("Linear Channel value and system value differ")
            if str(item.get("unit") or ""):
                raise RemoteChannelCommandError("Linear Channel command unit must be empty")
        normalized.append(json.dumps(frame, separators=(",", ":"), ensure_ascii=True))
    if item_count > MAX_COMMAND_ITEMS:
        raise RemoteChannelCommandError("Edge command exceeds the active channel limit")
    return tuple(normalized)


def command_ack(
    command: dict[str, Any],
    *,
    status: str,
    error: str | None = None,
    evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    normalized_status = str(status or "").strip().lower()
    if normalized_status not in {"succeeded", "failed", "rejected"}:
        raise RemoteChannelCommandError("Unsupported Edge command acknowledgement status")
    return {
        "command_id": str(command.get("command_id") or ""),
        "target_processor_id": str(command.get("target_processor_id") or ""),
        "profile_id": str(command.get("profile_id") or ""),
        "profile_revision": _safe_integer(command.get("profile_revision")),
        "lease_generation": _safe_integer(command.get("lease_generation")),
        "action": str(command.get("action") or ""),
        "status": normalized_status,
        "error": " ".join(str(error or "").split())[:1000] or None,
        "evidence": deepcopy(evidence or {}),
        "acknowledged_at": datetime.now(timezone.utc).isoformat(),
    }


class RemoteChannelCommandExecutor:
    """Execute only the allowlisted Hercules Linear Channel operations."""

    def __init__(self) -> None:
        self.active_command: dict[str, Any] | None = None
        self.phase: str | None = None
        self.deadline: datetime | None = None
        self.data_info: dict[int, dict[str, Any]] = {}
        self.setting_info: dict[str, Any] | None = None
        self.setting: dict[str, Any] | None = None
        self.expected_captions: dict[int, str] = {}

    @property
    def active_command_id(self) -> str | None:
        return str(self.active_command.get("command_id")) if self.active_command else None

    def start(self, command: dict[str, Any]) -> RemoteChannelExecutionPlan:
        if self.active_command is not None:
            raise RemoteChannelCommandError("Another Remote Channels command is already executing")
        action = str(command.get("action") or "")
        self.active_command = deepcopy(command)
        self.deadline = _parse_time(command.get("expires_at"))
        if action in {"write", "invalidate"}:
            frames = validate_frames(
                (command.get("payload") or {}).get("frames"),
                require_invalid=(action == "invalidate"),
            )
            self.phase = "send"
            return RemoteChannelExecutionPlan(frames=frames, complete_after_send=True)

        sources = _validated_sources((command.get("payload") or {}).get("sources"))
        self.expected_captions = {}
        requested_ids: list[int] = []
        for source in sources:
            twd_id = LINEAR_CHANNEL_FIRST_ID + ((source["slot"] - 1) * 2)
            tws_id = twd_id + 1
            requested_ids.extend((twd_id, tws_id))
            self.expected_captions[twd_id] = source["twd_caption"]
            self.expected_captions[tws_id] = source["tws_caption"]
        self.phase = "preflight"
        return RemoteChannelExecutionPlan(
            frames=(
                json.dumps({"DataInfoReq": requested_ids}, separators=(",", ":")),
                json.dumps({"SettingInfoReq": [USER_DATA_SETTING_ID]}, separators=(",", ":")),
                json.dumps(
                    {"SettingReq": {"ids": [USER_DATA_SETTING_ID], "register": False}},
                    separators=(",", ":"),
                ),
            )
        )

    def observe(self, payload: Any) -> tuple[RemoteChannelExecutionPlan | None, dict[str, Any] | None]:
        if self.active_command is None or not isinstance(payload, dict):
            return None, None
        timeout_ack = self.check_timeout()
        if timeout_ack is not None:
            return None, timeout_ack
        self._capture(payload)
        if self.phase == "preflight" and self._preflight_complete():
            try:
                updated = self._caption_setting()
            except Exception as exc:
                return None, self.fail(str(exc))
            self.phase = "readback"
            self.setting = None
            return RemoteChannelExecutionPlan(
                frames=(
                    json.dumps({"Setting": [updated]}, separators=(",", ":")),
                    json.dumps({"EventSet": [{"id": USER_DATA_EVENT_ID, "update": None}]}, separators=(",", ":")),
                    json.dumps(
                        {"SettingReq": {"ids": [USER_DATA_SETTING_ID], "register": False}},
                        separators=(",", ":"),
                    ),
                )
            ), None
        if self.phase == "readback" and self.setting is not None:
            try:
                readback = self._verify_readback()
            except Exception as exc:
                return None, self.fail(str(exc))
            acknowledgement = command_ack(
                self.active_command,
                status="succeeded",
                evidence={
                    "product": "B&G Hercules (Edge Linear Channel protocol verified)",
                    "model": "Hercules",
                    "caption_readback": readback,
                },
            )
            self.reset()
            return None, acknowledgement
        return None, None

    def sent(self, plan: RemoteChannelExecutionPlan) -> dict[str, Any] | None:
        if not plan.complete_after_send or self.active_command is None:
            return None
        acknowledgement = command_ack(self.active_command, status="succeeded")
        self.reset()
        return acknowledgement

    def fail(self, error: str, *, status: str = "failed") -> dict[str, Any] | None:
        if self.active_command is None:
            return None
        acknowledgement = command_ack(self.active_command, status=status, error=error)
        self.reset()
        return acknowledgement

    def check_timeout(self, *, now: datetime | None = None) -> dict[str, Any] | None:
        if self.active_command is None or self.deadline is None:
            return None
        if _aware_utc(now or datetime.now(timezone.utc)) < self.deadline:
            return None
        return self.fail("Remote Channels command expired before local execution completed")

    def reset(self) -> None:
        self.active_command = None
        self.phase = None
        self.deadline = None
        self.data_info = {}
        self.setting_info = None
        self.setting = None
        self.expected_captions = {}

    def _capture(self, payload: dict[str, Any]) -> None:
        for item in _items(payload, "DataInfo"):
            metric_id = _optional_integer(item.get("id"))
            if metric_id in self.expected_captions:
                self.data_info[metric_id] = deepcopy(item)
        for item in _items(payload, "SettingInfo"):
            if _optional_integer(item.get("id")) == USER_DATA_SETTING_ID:
                self.setting_info = deepcopy(item)
        for item in _items(payload, "Setting"):
            if _optional_integer(item.get("id")) == USER_DATA_SETTING_ID:
                self.setting = deepcopy(item)

    def _preflight_complete(self) -> bool:
        return (
            set(self.data_info) == set(self.expected_captions)
            and self.setting_info is not None
            and self.setting is not None
        )

    def _caption_setting(self) -> dict[str, Any]:
        if self.setting_info is None or self.setting_info.get("readOnly") is not False:
            raise RemoteChannelCommandError("Hercules did not explicitly report User Data Setting 91 as writable")
        if self.setting is None or not isinstance(self.setting.get("value"), list):
            raise RemoteChannelCommandError("Hercules did not return User Data Setting 91")
        updated = deepcopy(self.setting)
        matches = {metric_id: 0 for metric_id in self.expected_captions}
        for record in updated["value"]:
            if not isinstance(record, dict):
                continue
            metric_id = _optional_integer(record.get("id"))
            if metric_id not in self.expected_captions:
                continue
            matches[metric_id] += 1
            record["userLong"] = self.expected_captions[metric_id]
            record["userShort"] = self.expected_captions[metric_id]
        if any(count != 1 for count in matches.values()):
            raise RemoteChannelCommandError("Each selected Linear Channel must appear exactly once in Setting 91")
        return {"id": USER_DATA_SETTING_ID, "value": updated["value"]}

    def _verify_readback(self) -> dict[str, Any]:
        if self.setting is None or not isinstance(self.setting.get("value"), list):
            raise RemoteChannelCommandError("Hercules caption readback is absent")
        result: dict[str, Any] = {}
        for record in self.setting["value"]:
            if not isinstance(record, dict):
                continue
            metric_id = _optional_integer(record.get("id"))
            caption = self.expected_captions.get(metric_id)
            if caption is None:
                continue
            if record.get("userLong") != caption or record.get("userShort") != caption:
                raise RemoteChannelCommandError(f"Hercules caption readback mismatch for Linear Channel {metric_id}")
            result[str(metric_id)] = deepcopy(record)
        if len(result) != len(self.expected_captions):
            raise RemoteChannelCommandError("Hercules caption readback omitted a selected Linear Channel")
        return result


def _validated_sources(value: Any) -> tuple[dict[str, Any], ...]:
    if not isinstance(value, list) or not 1 <= len(value) <= MAX_SOURCES:
        raise RemoteChannelCommandError("Caption configuration requires between one and five sources")
    sources: list[dict[str, Any]] = []
    slots: set[int] = set()
    for raw in value:
        if not isinstance(raw, dict):
            raise RemoteChannelCommandError("Caption source must be an object")
        slot = _integer(raw.get("slot"), "source slot")
        if not 1 <= slot <= MAX_SOURCES or slot in slots:
            raise RemoteChannelCommandError("Caption source slots must be unique and between one and five")
        slots.add(slot)
        sources.append(
            {
                "slot": slot,
                "twd_caption": _caption(raw.get("twd_caption")),
                "tws_caption": _caption(raw.get("tws_caption")),
            }
        )
    return tuple(sources)


def _caption(value: Any) -> str:
    caption = " ".join(str(value or "").split())
    if not caption or len(caption) > 32:
        raise RemoteChannelCommandError("Linear Channel captions must contain 1-32 characters")
    return caption


def _items(payload: dict[str, Any], key: str) -> list[dict[str, Any]]:
    value = payload.get(key)
    if isinstance(value, dict):
        value = [value]
    return [item for item in value or [] if isinstance(item, dict)] if isinstance(value, list) else []


def _parse_time(value: Any) -> datetime:
    if isinstance(value, datetime):
        return _aware_utc(value)
    try:
        parsed = datetime.fromisoformat(str(value or "").replace("Z", "+00:00"))
    except ValueError as exc:
        raise RemoteChannelCommandError("Edge command timestamp is invalid") from exc
    return _aware_utc(parsed)


def _aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise RemoteChannelCommandError("Edge command timestamps must include a timezone")
    return value.astimezone(timezone.utc)


def _safe_integer(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError, OverflowError):
        return 0


def _integer(value: Any, label: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise RemoteChannelCommandError(f"{label} is invalid") from exc


def _optional_integer(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _finite_number(value: Any, label: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise RemoteChannelCommandError(f"{label} is invalid") from exc
    if not math.isfinite(number):
        raise RemoteChannelCommandError(f"{label} must be finite")
    return number
