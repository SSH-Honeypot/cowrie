"""
Minimal SocketIO Output Plugin for Cowrie using reactor.callInThread
"""

from __future__ import annotations

from twisted.internet import reactor
from twisted.python import log
import socketio

import cowrie.core.output
from cowrie.core.config import CowrieConfig


class Output(cowrie.core.output.Output):
    sio = socketio.SimpleClient()
    url: str = None
    connected: bool = False

    def start(self) -> None:
        """
        Initialize the SocketIO client and connect to the backend.
        """
        try:
            self.url = CowrieConfig.get("output_socketio", "url")
            reactor.callInThread(self._connect)
        except Exception as e:
            log.err(f"output_socketio: Error initializing: {e}")

    def _connect(self):
        """
        Connect to the SocketIO server in a separate thread.
        """
        try:
            self.sio.connect(self.url, auth={ "sensor": self.sensor })
            self.connected = True
            log.msg("output_socketio: Connected to server")
        except Exception as e:
            self.connected = False
            log.err(f"output_socketio: Connection failed: {e}")
            reactor.callLater(5, self._connect)

    def stop(self) -> None:
        """
        Disconnect the SocketIO client.
        """
        try:
            self.sio.disconnect()
            self.connected = False
            log.msg("output_socketio: Disconnected")
        except Exception as e:
            log.err(f"output_socketio: Error disconnecting: {e}")

    def write(self, event: dict) -> None:
        """
        Send Cowrie event to the SocketIO backend.
        """
        if not self.connected:
            log.msg(f"output_socketio: Not connected, skipping event {event.get('eventid', 'unknown')}")
            return
        if not (event["eventid"] == "cowrie.login.failed" or event["eventid"] == "cowrie.login.success"):
            return
        reactor.callInThread(self._send_event, event["eventid"], event)

    def _send_event(self, event_name: str, event: dict) -> None:
        """
        Send the event to the SocketIO backend in a separate thread.
        """
        try:
            self.sio.emit(event_name, { "session": event["session"], "src_ip": event["src_ip"], "username": event["username"], "password": event["password"] })
            log.msg(f"output_socketio: Sent event {event_name}")
        except Exception as e:
            log.err(f"output_socketio: Failed to send event {event_name}: {e}")