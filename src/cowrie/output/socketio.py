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
    url = None
    connected = False

    def start(self) -> None:
        """
        Initialize the SocketIO client and connect to the backend.
        """
        try:
            self.url = CowrieConfig.get("output_socketio", "url")
            log.msg(f"output_socketio: Connecting to {self.url}") # todo: disable or make debug
            reactor.callInThread(self._connect)
        except Exception as e:
            log.err(f"output_socketio: Error initializing: {e}")

    def _connect(self):
        """
        Connect to the SocketIO server in a separate thread.
        """
        try:
            self.sio.connect(self.url)
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
        try:
            event_name = event.get("eventid", "cowrie_event")
            # Bereinige Event-Dictionary
            cleaned_event = self._clean_event(event)
            reactor.callInThread(self._send_event, event_name, cleaned_event)
        except Exception as e:
            log.err(f"output_socketio: Error preparing event {event.get('eventid', 'unknown')}: {e}")

    def _clean_event(self, event: dict) -> dict:
        """
        Convert non-serializable objects in the event dictionary to JSON-serializable types.
        """
        def convert_value(value):
            if isinstance(value, (str, int, float, bool, type(None))):
                return value
            elif isinstance(value, (bytes, bytearray)):
                try:
                    return value.decode("utf-8")
                except UnicodeDecodeError:
                    return repr(value)
            elif isinstance(value, (list, tuple)):
                return [convert_value(item) for item in value]
            elif isinstance(value, dict):
                return {str(key): convert_value(val) for key, val in value.items()}
            else:
                # Fallback für Objekte wie NamedConstant
                return str(value)

        return {key: convert_value(value) for key, value in event.items()}

    def _send_event(self, event_name: str, event: dict):
        """
        Send the event to the SocketIO backend in a separate thread.
        """
        try:
            self.sio.emit(event_name, event)
            log.msg(f"output_socketio: Sent event {event_name}")
        except Exception as e:
            log.err(f"output_socketio: Failed to send event {event_name}: {e}")