"""
RCON (Remote Console) client for Rust servers.
Implements the Rust RCON protocol via TCP.
"""

import socket
import struct
import time
from typing import Optional, Callable, List
from threading import Thread, Event
from datetime import datetime

from utils.logger import log


class RconClient:
    """
    Rust RCON client implementation.
    """

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 28016,
        password: str = "",
        connect_timeout: float = 5.0,
    ):
        self.host = host
        self.port = port
        self.password = password
        self.connect_timeout = connect_timeout

        self.socket: Optional[socket.socket] = None
        self.connected = False
        self.authenticated = False
        
        self._receive_thread: Optional[Thread] = None
        self._stop_event = Event()
        self._message_id = 0
        
        self.on_message: Optional[Callable[[str], None]] = None
        self.on_connected: Optional[Callable[[], None]] = None
        self.on_disconnected: Optional[Callable[[], None]] = None
        
        self.command_history: List[tuple[str, str]] = []  # (command, timestamp)

    def connect(self) -> bool:
        """
        Connect to the RCON server.
        """
        try:
            log.info(f"Connecting to RCON at {self.host}:{self.port}")
            
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(self.connect_timeout)
            self.socket.connect((self.host, self.port))
            
            self.connected = True
            log.info("RCON connection established")
            
            # Authenticate
            if not self._authenticate():
                self.disconnect()
                return False
            
            # Start receive thread
            self._stop_event.clear()
            self._receive_thread = Thread(target=self._receive_loop, daemon=True)
            self._receive_thread.start()
            
            if self.on_connected:
                self.on_connected()
            
            return True
        except socket.timeout:
            log.error(f"Connection timeout ({self.connect_timeout}s)")
            return False
        except ConnectionRefusedError:
            log.error(f"Connection refused by {self.host}:{self.port}")
            return False
        except Exception as e:
            log.error(f"Failed to connect to RCON: {e}")
            return False

    def disconnect(self) -> None:
        """
        Disconnect from RCON server.
        """
        if not self.connected:
            return

        try:
            log.info("Disconnecting from RCON")
            self._stop_event.set()
            
            if self.socket:
                self.socket.close()
                self.socket = None
            
            self.connected = False
            self.authenticated = False
            
            if self._receive_thread:
                self._receive_thread.join(timeout=2)
            
            if self.on_disconnected:
                self.on_disconnected()
            
            log.info("RCON disconnected")
        except Exception as e:
            log.error(f"Error during disconnect: {e}")

    def send_command(self, command: str) -> bool:
        """
        Send a command to the RCON server.
        """
        if not self.connected or not self.authenticated or not self.socket:
            log.error("RCON not connected or authenticated")
            return False

        try:
            self._message_id += 1
            msg = self._format_message(self._message_id, 2, command)
            self.socket.sendall(msg)
            
            # Store in history
            self.command_history.append((command, datetime.now().isoformat()))
            log.info(f"RCON command sent: {command}")
            
            return True
        except Exception as e:
            log.error(f"Failed to send command: {e}")
            self.connected = False
            return False

    def get_command_history(self) -> List[tuple[str, str]]:
        """
        Get command history as list of (command, timestamp) tuples.
        """
        return self.command_history[-50:]  # Return last 50 commands

    def _authenticate(self) -> bool:
        """
        Authenticate with the RCON server.
        """
        try:
            self._message_id = 1
            auth_msg = self._format_message(self._message_id, 3, self.password)
            self.socket.sendall(auth_msg)
            
            # Read response
            response = self.socket.recv(4096)
            if len(response) < 12:
                log.error("Invalid authentication response")
                return False
            
            size, msg_id, msg_type = struct.unpack("<3I", response[:12])
            
            # Type 2 = command response, Type 0 = auth response
            if msg_type == 2:  # Successful auth
                self.authenticated = True
                log.info("RCON authentication successful")
                return True
            elif msg_type == 0:  # Auth failed
                log.error("RCON authentication failed (invalid password)")
                return False
            else:
                log.error(f"Unknown auth response type: {msg_type}")
                return False
        except Exception as e:
            log.error(f"Authentication error: {e}")
            return False

    def _receive_loop(self) -> None:
        """
        Background receive loop to handle incoming messages.
        """
        while not self._stop_event.is_set() and self.connected:
            try:
                self.socket.settimeout(1.0)
                data = self.socket.recv(4096)
                
                if not data:
                    log.warning("RCON connection closed by server")
                    self.connected = False
                    break
                
                # Parse message
                if len(data) >= 12:
                    size, msg_id, msg_type = struct.unpack("<3I", data[:12])
                    body = data[12:12 + size - 8].decode("utf-8", errors="ignore")
                    
                    if msg_type == 0:  # Auth response
                        if msg_id == -1:
                            log.error("RCON authentication failed")
                            self.authenticated = False
                    elif msg_type == 1:  # Command response
                        if self.on_message:
                            self.on_message(body)
            except socket.timeout:
                continue
            except Exception as e:
                if not self._stop_event.is_set():
                    log.error(f"Error in receive loop: {e}")
                break
        
        self.connected = False

    def _format_message(self, msg_id: int, msg_type: int, body: str) -> bytes:
        """
        Format a message according to Rust RCON protocol.
        
        Structure:
        - Size (4 bytes, little-endian): size of (ID + Type + String + null)
        - ID (4 bytes, little-endian)
        - Type (4 bytes, little-endian): 3=auth, 2=command, 1=response
        - String (variable): null-terminated UTF-8
        """
        body_bytes = body.encode("utf-8") + b"\x00"
        size = 8 + len(body_bytes)  # ID + Type + body
        
        return struct.pack("<3I", size, msg_id, msg_type) + body_bytes
