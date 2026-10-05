import queue
import time
import unittest

from lan_network import LanClient, LanServer


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
    def test_host_and_client_share_a_server_authoritative_table(self) -> None:
        server = LanServer(port=0)
        host = None
        guest = None
        try:
            server.start()
            host = LanClient("127.0.0.1", "Host", server.port)
            guest = LanClient("127.0.0.1", "Guest", server.port)
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
