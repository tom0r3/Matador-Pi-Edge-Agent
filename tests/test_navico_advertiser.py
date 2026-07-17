from __future__ import annotations

import asyncio
import socket
import tempfile
import unittest
from pathlib import Path

from edge_agent.navico_advertiser import (
    DEFAULT_ICON_REVISION,
    MDNS_GROUP,
    MDNS_PORT,
    NAVICO_APP_PORT,
    NAVICO_DEVICE_PORT,
    NAVICO_GROUP,
    NavicoAdvertiserConfigError,
    NavicoAdvertiserInterfaceError,
    NavicoAdvertiserSettings,
    NavicoHtml5Advertiser,
    build_navico_descriptor,
    validate_navico_settings,
)


ADDRESS = "169.254.18.218"


class NavicoDescriptorTests(unittest.TestCase):
    def test_descriptor_preserves_proven_field_names_and_types(self) -> None:
        settings = NavicoAdvertiserSettings()
        payload = build_navico_descriptor(ADDRESS, settings)

        self.assertEqual(
            list(payload.keys()),
            [
                "Version",
                "Source",
                "IP",
                "FeatureName",
                "Text",
                "Icon",
                "URL",
                "OnlyShowOnClientIP",
                "BrowserPanel",
            ],
        )
        self.assertEqual(payload["Version"], "1")
        self.assertEqual(payload["Source"], "TORO")
        self.assertEqual(payload["IP"], ADDRESS)
        self.assertEqual(payload["FeatureName"], "TORO HTML5 App")
        self.assertEqual(payload["Text"][0]["Name"], "Matador")
        self.assertEqual(payload["Text"][0]["Language"], "en")
        self.assertEqual(payload["URL"], "https://matador.torodatasystems.eu/")
        self.assertEqual(payload["OnlyShowOnClientIP"], "true")
        self.assertIsInstance(payload["OnlyShowOnClientIP"], str)
        self.assertEqual(payload["BrowserPanel"]["Enable"], True)
        self.assertEqual(payload["BrowserPanel"]["ProgressBarEnable"], True)
        self.assertEqual(payload["BrowserPanel"]["MenuText"][0]["Name"], "Home")

    def test_icon_url_is_local_versioned_and_uses_selected_address(self) -> None:
        payload = build_navico_descriptor(ADDRESS, NavicoAdvertiserSettings())

        self.assertEqual(
            payload["Icon"],
            f"http://{ADDRESS}/icon.png?v={DEFAULT_ICON_REVISION}",
        )

    def test_production_profile_disables_2052_mdns_and_nav_ws(self) -> None:
        settings = NavicoAdvertiserSettings()

        self.assertEqual(settings.multicast_group, NAVICO_GROUP)
        self.assertEqual(settings.multicast_port, NAVICO_APP_PORT)
        self.assertEqual(NAVICO_DEVICE_PORT, 2052)
        self.assertEqual((MDNS_GROUP, MDNS_PORT), ("224.0.0.251", 5353))
        self.assertFalse(settings.device_broadcast_enabled)
        self.assertFalse(settings.mdns_enabled)
        self.assertFalse(settings.navico_nav_ws_enabled)

        with self.assertRaisesRegex(NavicoAdvertiserConfigError, "UDP 2052"):
            validate_navico_settings(NavicoAdvertiserSettings(device_broadcast_enabled=True))
        with self.assertRaisesRegex(NavicoAdvertiserConfigError, "mDNS"):
            validate_navico_settings(NavicoAdvertiserSettings(mdns_enabled=True))
        with self.assertRaisesRegex(NavicoAdvertiserConfigError, "navico-nav-ws"):
            validate_navico_settings(NavicoAdvertiserSettings(navico_nav_ws_enabled=True))

    def test_invalid_urls_and_embedded_credentials_fail(self) -> None:
        with self.assertRaisesRegex(NavicoAdvertiserConfigError, "HTTP or HTTPS"):
            validate_navico_settings(NavicoAdvertiserSettings(app_url="ftp://example.test/app"))
        with self.assertRaisesRegex(NavicoAdvertiserConfigError, "credentials"):
            validate_navico_settings(NavicoAdvertiserSettings(app_url="https://user:pass@example.test/app"))


class NavicoRuntimeTests(unittest.TestCase):
    def test_send_due_is_immediate_then_interval_based_and_resets_on_address_change(self) -> None:
        advertiser = NavicoHtml5Advertiser(NavicoAdvertiserSettings())

        self.assertTrue(advertiser.set_selected_address("192.168.10.12"))
        self.assertTrue(advertiser.send_due(100.0))
        advertiser._last_send_monotonic = 100.0
        self.assertFalse(advertiser.send_due(109.9))
        self.assertTrue(advertiser.send_due(110.0))
        self.assertTrue(advertiser.set_selected_address("192.168.10.13"))
        self.assertTrue(advertiser.send_due(101.0))

    def test_repeated_same_address_does_not_reset_send_timer(self) -> None:
        advertiser = NavicoHtml5Advertiser(NavicoAdvertiserSettings())

        self.assertTrue(advertiser.set_selected_address("192.168.10.12"))
        advertiser._last_send_monotonic = 100.0
        self.assertFalse(advertiser.set_selected_address("192.168.10.12"))
        self.assertFalse(advertiser.send_due(109.0))

    def test_missing_configured_interface_fails_startup(self) -> None:
        advertiser = NavicoHtml5Advertiser(
            NavicoAdvertiserSettings(interface="missing0"),
            interface_checker=lambda _name: False,
        )
        stop_event = asyncio.Event()

        with self.assertRaises(NavicoAdvertiserInterfaceError):
            asyncio.run(advertiser.run(stop_event))


class NavicoHttpTests(unittest.IsolatedAsyncioTestCase):
    async def test_icon_endpoint_serves_png_and_ignores_query_string(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            icon_path = Path(temp_dir) / "icon.png"
            icon_path.write_bytes(b"\x89PNG\r\n\x1a\nTEST")
            port = free_tcp_port()
            advertiser = NavicoHtml5Advertiser(
                NavicoAdvertiserSettings(
                    icon_file=icon_path,
                    icon_http_port=port,
                )
            )
            await advertiser.ensure_icon_server("127.0.0.1")
            try:
                reader, writer = await asyncio.open_connection("127.0.0.1", port)
                writer.write(b"GET /icon.png?v=toro-favicon-1 HTTP/1.1\r\nHost: 127.0.0.1\r\n\r\n")
                await writer.drain()
                response = await reader.read()
                writer.close()
                await writer.wait_closed()
            finally:
                await advertiser.close_icon_server()

        self.assertIn(b"HTTP/1.1 200 OK", response)
        self.assertIn(b"Content-Type: image/png", response)
        self.assertTrue(response.endswith(b"\x89PNG\r\n\x1a\nTEST"))


def free_tcp_port() -> int:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])
    finally:
        sock.close()


if __name__ == "__main__":
    unittest.main()
