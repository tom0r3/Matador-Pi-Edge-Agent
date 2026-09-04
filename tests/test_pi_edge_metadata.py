from __future__ import annotations

import asyncio
import unittest
from types import SimpleNamespace

from edge_agent.pi_edge_agent import PiEdgeAgent


class PiEdgeMetadataTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
