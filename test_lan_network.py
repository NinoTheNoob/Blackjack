import queue
import time
import unittest

from lan_network import LanClient, LanServer, parse_server_address


def wait_for_state(client: LanClient, predicate) -> dict:
    deadline = time.monotonic() + 4
    while time.monotonic() < deadline:
        try:
            update = client.updates.get(timeout=0.2)
        except queue.Empty:
            continue
        if update.get("type") == "error" and update.get("fatal"):
            raise AssertionError(update.get("message"))
        if update.get("type") == "state" and predicate(update):
            return update
    raise AssertionError("Timed out waiting for the LAN table update.")


class LanNetworkTests(unittest.TestCase):
    def test_server_address_accepts_host_with_and_without_port(self) -> None:
        self.assertEqual(parse_server_address("192.168.1.12"), ("192.168.1.12", 47920))
        self.assertEqual(
            parse_server_address("192.168.1.12:47920"),
            ("192.168.1.12", 47920),
        )
        self.assertEqual(parse_server_address("localhost:5000"), ("localhost", 5000))
        self.assertEqual(parse_server_address("[::1]:47920"), ("::1", 47920))

    def test_server_address_reports_invalid_input_clearly(self) -> None:
        for address in ("", "192.168.1.12:abc", "[::1", "localhost:70000"):
            with self.subTest(address=address), self.assertRaises(ValueError):
                parse_server_address(address)

    def test_host_and_client_share_a_server_authoritative_table(self) -> None:
        server = LanServer(port=0)
        host = None
        guest = None
        try:
            server.start()
            host = LanClient("127.0.0.1", "Host", server.port)
            guest = LanClient(f"127.0.0.1:{server.port}", "Guest")
            wait_for_state(host, lambda state: len(state["players"]) == 2)
            wait_for_state(guest, lambda state: len(state["players"]) == 2)

            host.send_ready(20)
            guest.send_ready(20)
            host_state = wait_for_state(
                host, lambda state: state["phase"] == "playing"
            )
            guest_state = wait_for_state(
                guest, lambda state: state["phase"] == "playing"
            )
            self.assertEqual(host_state["dealer_cards"][1], "BACK")
            self.assertEqual(guest_state["dealer_cards"][1], "BACK")

            if host_state["is_viewer_turn"]:
                host.send_action("stand")
                next_state = wait_for_state(
                    guest,
                    lambda state: state["is_viewer_turn"]
                    or state["phase"] == "betting",
                )
            else:
                guest.send_action("stand")
                next_state = wait_for_state(
                    host,
                    lambda state: state["is_viewer_turn"]
                    or state["phase"] == "betting",
                )
            self.assertTrue(
                next_state["is_viewer_turn"] or next_state["phase"] == "betting"
            )
        finally:
            if host is not None:
                host.close()
            if guest is not None:
                guest.close()
            server.stop()


if __name__ == "__main__":
    unittest.main()
