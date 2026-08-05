from __future__ import annotations

import json
import unittest
from datetime import datetime, timedelta, timezone

from edge_agent.remote_channel_protocol import (
    RemoteChannelCommandError,
    RemoteChannelCommandExecutor,
    command_ack,
    sign_command,
    verify_command,
)


NOW = datetime(2026, 8, 5, 10, 0, tzinfo=timezone.utc)
TOKEN = "edge-enrollment-token"
TARGET_ID = "00000000-0000-0000-0000-000000000002"


def write_command(*, metric_id: int = 481) -> dict[str, object]:
    command = {
        "protocol_version": 1,
        "command_id": "00000000-0000-0000-0000-000000000010",
        "target_processor_id": TARGET_ID,
        "profile_id": "00000000-0000-0000-0000-000000000003",
        "profile_revision": 2,
        "lease_generation": 7,
        "action": "write",
        "payload": {
            "frames": [
                json.dumps(
                    {
                        "Data": [
                            {
                                "id": metric_id,
                                "valid": True,
                                "val": 271.0,
                                "sysVal": 271.0,
                                "unit": "",
                            }
                        ]
                    }
                )
            ]
        },
        "issued_at": NOW.isoformat(),
        "expires_at": (NOW + timedelta(seconds=2)).isoformat(),
    }
    return sign_command(command, TOKEN)


def configure_command() -> dict[str, object]:
    command = {
        "protocol_version": 1,
        "command_id": "00000000-0000-0000-0000-000000000011",
        "target_processor_id": TARGET_ID,
        "profile_id": "00000000-0000-0000-0000-000000000003",
        "profile_revision": 2,
        "lease_generation": 0,
        "action": "configure",
        "payload": {
            "sources": [
                {"slot": 1, "twd_caption": "ILCA6 TWD", "tws_caption": "ILCA6 TWS"}
            ]
        },
        "issued_at": NOW.isoformat(),
        "expires_at": (NOW + timedelta(seconds=45)).isoformat(),
    }
    return sign_command(command, TOKEN)


class RemoteChannelCommandSecurityTests(unittest.TestCase):
    def test_signed_target_bound_command_is_accepted(self) -> None:
        verified = verify_command(write_command(), TOKEN, TARGET_ID, now=NOW)
        self.assertEqual(verified["action"], "write")

    def test_tampered_command_is_rejected(self) -> None:
        command = write_command()
        command["profile_revision"] = 3
        with self.assertRaises(RemoteChannelCommandError):
            verify_command(command, TOKEN, TARGET_ID, now=NOW)

    def test_expired_command_is_rejected(self) -> None:
        with self.assertRaisesRegex(RemoteChannelCommandError, "expired"):
            verify_command(write_command(), TOKEN, TARGET_ID, now=NOW + timedelta(seconds=3))

    def test_command_for_another_target_is_rejected(self) -> None:
        with self.assertRaisesRegex(RemoteChannelCommandError, "target"):
            verify_command(write_command(), TOKEN, "another-processor", now=NOW)

    def test_write_outside_reserved_linear_channels_is_rejected(self) -> None:
        with self.assertRaisesRegex(RemoteChannelCommandError, "outside"):
            verify_command(write_command(metric_id=47), TOKEN, TARGET_ID, now=NOW)

    def test_rejection_ack_survives_malformed_numeric_fields(self) -> None:
        acknowledgement = command_ack(
            {
                "command_id": "bad-command",
                "target_processor_id": TARGET_ID,
                "profile_revision": "not-an-integer",
                "lease_generation": [],
            },
            status="rejected",
            error="invalid command",
        )
        self.assertEqual(acknowledgement["profile_revision"], 0)
        self.assertEqual(acknowledgement["lease_generation"], 0)


class RemoteChannelCommandExecutorTests(unittest.TestCase):
    def test_write_plan_completes_after_frames_are_sent(self) -> None:
        executor = RemoteChannelCommandExecutor()
        command = verify_command(write_command(), TOKEN, TARGET_ID, now=NOW)
        plan = executor.start(command)
        self.assertTrue(plan.complete_after_send)
        self.assertEqual(len(plan.frames), 1)
        acknowledgement = executor.sent(plan)
        self.assertEqual(acknowledgement["status"], "succeeded")
        self.assertIsNone(executor.active_command)

    def test_configuration_requires_writable_setting_and_exact_readback(self) -> None:
        executor = RemoteChannelCommandExecutor()
        command = verify_command(configure_command(), TOKEN, TARGET_ID, now=NOW)
        preflight = executor.start(command)
        executor.deadline = datetime.now(timezone.utc) + timedelta(seconds=45)
        self.assertEqual(len(preflight.frames), 3)

        setting_records = [
            {"id": 481, "userLong": "User 17", "userShort": "USER 17"},
            {"id": 482, "userLong": "User 18", "userShort": "USER 18"},
        ]
        write_plan, acknowledgement = executor.observe(
            {
                "DataInfo": [{"id": 481}, {"id": 482}],
                "SettingInfo": {"id": 91, "readOnly": False},
                "Setting": {"id": 91, "value": setting_records},
            }
        )
        self.assertIsNone(acknowledgement)
        self.assertEqual(len(write_plan.frames), 3)

        _, acknowledgement = executor.observe(
            {
                "Setting": {
                    "id": 91,
                    "value": [
                        {"id": 481, "userLong": "ILCA6 TWD", "userShort": "ILCA6 TWD"},
                        {"id": 482, "userLong": "ILCA6 TWS", "userShort": "ILCA6 TWS"},
                    ],
                }
            }
        )
        self.assertEqual(acknowledgement["status"], "succeeded")
        self.assertEqual(set(acknowledgement["evidence"]["caption_readback"]), {"481", "482"})


if __name__ == "__main__":
    unittest.main()
