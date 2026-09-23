from __future__ import annotations

import asyncio
import json
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from edge_agent.pi_edge_agent import PiEdgeAgent


class PiEdgeMetadataTests(unittest.TestCase):
    def test_health_payload_captures_network_before_rendering(self) -> None:
        agent = object.__new__(PiEdgeAgent)
        agent.spool = SimpleNamespace(stats=lambda: {"pending_payloads": 0})
        agent.state_dir = Path("/tmp/matador-test-state")
        agent.counters = {}
        agent.state = {}
        agent.current_config = {}
        agent.processor_enabled = True
        agent.streaming_enabled = True
        agent.upload_paused = False
        agent.last_remote_command_at = None
        agent.processor_ping_interval_seconds = 0
        agent.processor_ping_timeout_seconds = 0
        agent.data_silence_reconnect_seconds = 0
        agent.upload_batch_max_readings = 250
        agent.upload_batch_max_payloads = 25
        agent.storage_sample_hz = 1.0
        agent.current_processor_identity = {}
        agent.locked_processor_identity = lambda: None
        agent.authorization_block_reason = lambda: None
        agent.disk_guard = lambda *_args: {}
        agent.update_timer_state = lambda: {}
        agent.update_result = lambda: {}

        with patch("edge_agent.pi_edge_agent.disk_stats", return_value={}), patch(
            "edge_agent.pi_edge_agent.network_snapshot", return_value={"interfaces": ["eth0"]}
        ), patch("edge_agent.pi_edge_agent.load_average", return_value={}):
            payload = agent.health_payload(include_support_bundle=False)

        self.assertEqual(payload["network"], {"interfaces": ["eth0"]})

    def test_idle_remote_channel_receive_uses_initialized_queue(self) -> None:
        agent = object.__new__(PiEdgeAgent)
        agent.remote_channel_executor = SimpleNamespace(active_command=None)
        agent.remote_channel_command_queue = asyncio.Queue(maxsize=1)

        self.assertFalse(agent.remote_channel_command_waiting())
        agent.remote_channel_command_queue.put_nowait({"command_id": "pending"})
        self.assertTrue(agent.remote_channel_command_waiting())

    def test_combined_metadata_frame_keeps_mast_height_setting(self) -> None:
        agent = object.__new__(PiEdgeAgent)
        agent.data_info_by_metric_id = {}
        agent.setting_by_id = {}
        agent.current_processor_identity = {}

        updated = agent.update_processor_metadata(
            {
                "DataInfo": [{"id": 47, "sname": "TWS", "unit": "kn"}],
                "Setting": [{"id": 31, "value": "37.00", "units": "m"}],
            }
        )

        self.assertTrue(updated)
        self.assertEqual(agent.data_info_by_metric_id[47]["sname"], "TWS")
        self.assertEqual(agent.mast_height_above_wl_m(), 37.0)

    def test_gofree_boat_speed_uses_data_id_42_and_uploads_canonical_metric(self) -> None:
        agent = object.__new__(PiEdgeAgent)
        agent.current_config = {
            "metrics": [
                {"id": 18008, "name": "BOAT_SPEED_WATER", "gofree_data_id": 42},
                {"id": 47, "name": "TWS"},
            ]
        }
        agent.state = {}
        agent.data_info_by_metric_id = {42: {"id": 42, "sname": "BSP", "unit": "kn"}}
        agent.setting_by_id = {}

        subscription = json.loads(agent.subscription_message())
        metadata = json.loads(agent.data_info_message() or "{}")
        reading = agent.enrich_data_item({"id": 42, "inst": 0, "dampedVal": 6.4, "valid": True})

        self.assertEqual([item["id"] for item in subscription["DataReq"]], [42, 47])
        self.assertIn(42, metadata["DataInfoReq"])
        self.assertEqual(reading["id"], 18008)
        self.assertEqual(reading["gofree_data_id"], 42)
        self.assertEqual(reading["metric_name"], "BOAT_SPEED_WATER")
        self.assertEqual(reading["unit"], "kn")


if __name__ == "__main__":
    unittest.main()
