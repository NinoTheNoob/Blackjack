"""Small newline-delimited JSON transport for LAN blackjack tables."""

from __future__ import annotations

import json
import queue
import socket
import threading
import uuid
from typing import Any

from lan_game import BlackjackTable


PORT = 47920
MAX_MESSAGE_BYTES = 8192


class LanServer:
    def __init__(self, port: int = PORT) -> None:
        self.port = port
        self.table = BlackjackTable()
        self._lock = threading.RLock()
        self._peers: dict[str, socket.socket] = {}
        self._listener: socket.socket | None = None
        self._accept_thread: threading.Thread | None = None
        self._stopping = threading.Event()

    def start(self) -> None:
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            listener.bind(("0.0.0.0", self.port))
            listener.listen(8)
            listener.settimeout(0.5)
        except OSError:
            listener.close()
            raise
        self.port = int(listener.getsockname()[1])
        self._listener = listener
        self._accept_thread = threading.Thread(
            target=self._accept_connections,
            name="blackjack-lan-accept",
            daemon=True,
        )
        self._accept_thread.start()

    def stop(self) -> None:
        self._stopping.set()
        if self._listener is not None:
            self._listener.close()
            self._listener = None
        with self._lock:
            peers = list(self._peers.values())
            self._peers.clear()
        for peer in peers:
            try:
                peer.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            peer.close()

    def _accept_connections(self) -> None:
        while not self._stopping.is_set():
            listener = self._listener
            if listener is None:
                return
            try:
                connection, _ = listener.accept()
            except socket.timeout:
                continue
            except OSError:
                return
            threading.Thread(
                target=self._serve_client,
                args=(connection,),
                name="blackjack-lan-client",
                daemon=True,
            ).start()

    def _serve_client(self, connection: socket.socket) -> None:
        player_id: str | None = None
        try:
            reader = connection.makefile("rb")
            first_line = reader.readline(MAX_MESSAGE_BYTES + 1)
            request = self._decode_line(first_line)
            if request.get("type") != "join":
                raise ValueError("The first network message must join the table.")

            assigned_id = uuid.uuid4().hex
            with self._lock:
                self.table.add_player(assigned_id, str(request.get("name", "")))
                player_id = assigned_id
                self._peers[player_id] = connection
                self._send_state_locked(player_id)
                self._broadcast_locked()

            while not self._stopping.is_set():
                line = reader.readline(MAX_MESSAGE_BYTES + 1)
                if not line:
                    break
                command = self._decode_line(line)
                self._handle_command(player_id, command)
        except (OSError, ValueError, UnicodeDecodeError, json.JSONDecodeError) as error:
            if player_id is None and not self._stopping.is_set():
                try:
                    self._send(
                        connection,
                        {"type": "error", "message": f"Could not join the table: {error}"},
                    )
                except OSError:
                    pass
        finally:
            if player_id is not None:
                with self._lock:
                    self._peers.pop(player_id, None)
                    try:
                        self.table.disconnect(player_id)
                    except ValueError:
                        pass
                    self._broadcast_locked()
            try:
                connection.close()
            except OSError:
                pass

    def _handle_command(self, player_id: str, command: dict[str, Any]) -> None:
        with self._lock:
            try:
                if command.get("type") == "ready":
                    bet = command.get("bet")
                    if not isinstance(bet, int) or isinstance(bet, bool):
                        raise ValueError("Bet must be a whole number.")
                    self.table.place_bet(player_id, bet)
                elif command.get("type") == "action":
                    action = command.get("action")
                    if not isinstance(action, str):
                        raise ValueError("Action must be text.")
                    self.table.act(player_id, action)
                else:
                    raise ValueError("Unknown network command.")
            except ValueError as error:
                self._send_to_player(
                    player_id, {"type": "error", "message": str(error)}
                )
            self._broadcast_locked()

    def _broadcast_locked(self) -> None:
        for player_id in list(self._peers):
            try:
                self._send_state_locked(player_id)
            except OSError:
                connection = self._peers.pop(player_id, None)
                if connection is not None:
                    try:
                        connection.shutdown(socket.SHUT_RDWR)
                    except OSError:
                        pass
                    connection.close()

    def _send_state_locked(self, player_id: str) -> None:
        try:
            state = self.table.snapshot(player_id)
        except ValueError:
            return
        self._send_to_player(player_id, state)

    def _send_to_player(self, player_id: str, message: dict[str, object]) -> None:
        connection = self._peers.get(player_id)
        if connection is not None:
            self._send(connection, message)

    @staticmethod
    def _send(connection: socket.socket, message: dict[str, object]) -> None:
        payload = json.dumps(message, separators=(",", ":")).encode("utf-8") + b"\n"
        if len(payload) > MAX_MESSAGE_BYTES:
            raise ValueError("Network message is too large.")
        connection.sendall(payload)

    @staticmethod
    def _decode_line(line: bytes) -> dict[str, Any]:
        if not line or len(line) > MAX_MESSAGE_BYTES or not line.endswith(b"\n"):
            raise ValueError("Invalid network message.")
        message = json.loads(line.decode("utf-8"))
        if not isinstance(message, dict):
            raise ValueError("Network message must be an object.")
        return message


class LanClient:
    def __init__(self, host: str, name: str, port: int = PORT) -> None:
        clean_name = " ".join(name.split())
        if not clean_name or len(clean_name) > 24:
            raise ValueError("Player names must contain 1 to 24 characters.")
        self.updates: queue.Queue[dict[str, Any]] = queue.Queue()
        self._socket = socket.create_connection((host, port), timeout=5)
        self._socket.settimeout(None)
        self._send_lock = threading.Lock()
        self._closed = False
        self._send({"type": "join", "name": clean_name})
        threading.Thread(
            target=self._read_updates,
            name="blackjack-lan-reader",
            daemon=True,
        ).start()

    def send_ready(self, bet: int) -> None:
        self._send({"type": "ready", "bet": bet})

    def send_action(self, action: str) -> None:
        self._send({"type": "action", "action": action})

    def close(self) -> None:
        self._closed = True
        try:
            self._socket.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        self._socket.close()

    def _send(self, message: dict[str, object]) -> None:
        payload = json.dumps(message, separators=(",", ":")).encode("utf-8") + b"\n"
        if len(payload) > MAX_MESSAGE_BYTES:
            raise ValueError("Network message is too large.")
        with self._send_lock:
            if self._closed:
                raise OSError("The LAN connection is closed.")
            self._socket.sendall(payload)

    def _read_updates(self) -> None:
        try:
            reader = self._socket.makefile("rb")
            while not self._closed:
                line = reader.readline(MAX_MESSAGE_BYTES + 1)
                if not line:
                    raise ConnectionError("The host closed the connection.")
                self.updates.put(LanServer._decode_line(line))
        except (OSError, ValueError, UnicodeDecodeError, json.JSONDecodeError) as error:
            if not self._closed:
                self.updates.put(
                    {
                        "type": "error",
                        "message": f"LAN connection lost: {error}",
                        "fatal": True,
                    }
                )


def get_local_ip() -> str:
    """Find the preferred LAN address without sending any network traffic."""
    probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        probe.connect(("192.0.2.1", 80))
        return str(probe.getsockname()[0])
    except OSError:
        return "127.0.0.1"
    finally:
        probe.close()
