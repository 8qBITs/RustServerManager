"""
RCON Console tab - remote console for sending commands to the server.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox,
    QPushButton, QLineEdit, QTextEdit, QComboBox, QMessageBox
)
from PySide6.QtCore import Qt, Signal, QThread, QTimer
from core.rcon_client import RconClient
from typing import Optional


class RconWorker(QThread):
    """Background worker for RCON operations."""
    
    output = Signal(str)
    connected = Signal(bool)
    
    def __init__(self, client: RconClient):
        super().__init__()
        self.client = client
    
    def run(self):
        """Run RCON client."""
        pass


class RconConsoleTab(QWidget):
    """RCON remote console for server communication."""

    console_output = Signal(str)

    def __init__(self, config_manager, server_manager=None, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.server_manager = server_manager
        self.rcon_client: Optional[RconClient] = None
        self.console_output.connect(self.append_console_line)
        if self.server_manager:
            self.server_manager.add_output_listener(self.on_shared_console_output)
        self.init_ui()
        
        # Auto-connect timer - checks every 5 seconds
        self.auto_connect_timer = QTimer()
        self.auto_connect_timer.timeout.connect(self.check_auto_connect)
        self.auto_connect_timer.start(5000)

    def init_ui(self) -> None:
        """Initialize UI elements."""
        layout = QVBoxLayout()
        
        # Connection group
        conn_group = QGroupBox("RCON Connection")
        conn_layout = QHBoxLayout()
        
        self.host_label = QLabel("Host:")
        self.host_input = QLineEdit()
        conn_layout.addWidget(self.host_label)
        conn_layout.addWidget(self.host_input)
        
        self.port_label = QLabel("Port:")
        self.port_input = QLineEdit()
        self.port_input.setMaximumWidth(100)
        conn_layout.addWidget(self.port_label)
        conn_layout.addWidget(self.port_input)
        
        self.password_label = QLabel("Password:")
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setMaximumWidth(150)
        conn_layout.addWidget(self.password_label)
        conn_layout.addWidget(self.password_input)
        
        self.connect_btn = QPushButton("🔗 Connect")
        self.connect_btn.clicked.connect(self.toggle_connection)
        self.connect_btn.setMaximumWidth(100)
        conn_layout.addWidget(self.connect_btn)
        
        self.status_label = QLabel("● Disconnected")
        self.status_label.setStyleSheet("color: red; font-weight: bold;")
        self.status_label.setMinimumWidth(100)
        conn_layout.addWidget(self.status_label)
        
        conn_layout.addStretch()
        conn_group.setLayout(conn_layout)
        layout.addWidget(conn_group)
        
        # Output display
        output_group = QGroupBox("Console Output")
        output_layout = QVBoxLayout()
        
        self.output_display = QTextEdit()
        self.output_display.setReadOnly(True)
        self.output_display.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                font-family: 'Courier New', monospace;
                font-size: 9px;
            }
        """)
        output_layout.addWidget(self.output_display)
        
        output_group.setLayout(output_layout)
        layout.addWidget(output_group, 1)
        
        # Command input
        cmd_group = QGroupBox("Send Command")
        cmd_layout = QHBoxLayout()
        
        self.command_input = QLineEdit()
        self.command_input.setPlaceholderText("Enter command (e.g., status, say Hello World)")
        self.command_input.returnPressed.connect(self.send_command)
        cmd_layout.addWidget(self.command_input)
        
        self.send_btn = QPushButton("Send")
        self.send_btn.clicked.connect(self.send_command)
        self.send_btn.setMaximumWidth(80)
        cmd_layout.addWidget(self.send_btn)
        
        cmd_group.setLayout(cmd_layout)
        layout.addWidget(cmd_group)
        
        # Command history
        history_group = QGroupBox("Command History")
        history_layout = QHBoxLayout()
        
        self.history_combo = QComboBox()
        self.history_combo.currentTextChanged.connect(self.on_history_selected)
        history_layout.addWidget(QLabel("Recent:"))
        history_layout.addWidget(self.history_combo)
        history_layout.addStretch()
        
        clear_history_btn = QPushButton("Clear History")
        clear_history_btn.clicked.connect(self.clear_history)
        history_layout.addWidget(clear_history_btn)
        
        history_group.setLayout(history_layout)
        layout.addWidget(history_group)
        
        self.setLayout(layout)
        
        # Load config
        self.load_connection_settings()

    def load_connection_settings(self) -> None:
        """Load RCON settings from config."""
        cfg = self.config_manager.get_config()
        self.host_input.setText(cfg.rcon.host)
        self.port_input.setText(str(cfg.rcon.port))
        self.password_input.setText(cfg.rcon.password)

    def check_auto_connect(self) -> None:
        """Auto-connect RCON when server is running and not already connected."""
        if not self.server_manager:
            return
        
        # Check if server is running
        status = self.server_manager.get_server_status()
        is_running = status.get("running", False)
        
        # Auto-connect if:
        # 1. Server is running
        # 2. RCON is not already connected
        # 3. Password is configured
        if is_running and (not self.rcon_client or not self.rcon_client.connected):
            cfg = self.config_manager.get_config()
            if cfg.rcon.password:  # Only auto-connect if password is set
                self.connect_rcon()

    def toggle_connection(self) -> None:
        """Connect or disconnect from RCON."""
        if self.rcon_client and self.rcon_client.connected:
            self.disconnect_rcon()
        else:
            self.connect_rcon()

    def connect_rcon(self) -> None:
        """Connect to RCON server."""
        try:
            host = self.host_input.text()
            port = int(self.port_input.text())
            password = self.password_input.text()
            
            if not host:
                QMessageBox.warning(self, "Error", "Host cannot be empty")
                return
            
            self._publish_console(f"[RCON] Connecting to {host}:{port}...")
            
            self.rcon_client = RconClient(host=host, port=port, password=password)
            self.rcon_client.on_message = self.on_rcon_message
            self.rcon_client.on_connected = self.on_rcon_connected
            self.rcon_client.on_disconnected = self.on_rcon_disconnected
            
            if self.rcon_client.connect():
                self.on_rcon_connected()
            else:
                self._publish_console("[RCON-ERR] Failed to connect!")
                self.rcon_client = None
        except ValueError:
            QMessageBox.warning(self, "Error", "Invalid port number")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Connection failed: {str(e)}")

    def disconnect_rcon(self) -> None:
        """Disconnect from RCON."""
        if self.rcon_client:
            self.rcon_client.disconnect()

    def on_rcon_connected(self) -> None:
        """Handle successful connection."""
        self.status_label.setText("● Connected")
        self.status_label.setStyleSheet("color: green; font-weight: bold;")
        self.connect_btn.setText("🔌 Disconnect")
        self._publish_console("[RCON] Connected")
        self.command_input.setEnabled(True)
        self.send_btn.setEnabled(True)

    def on_rcon_disconnected(self) -> None:
        """Handle disconnection."""
        self.status_label.setText("● Disconnected")
        self.status_label.setStyleSheet("color: red; font-weight: bold;")
        self.connect_btn.setText("🔗 Connect")
        self._publish_console("[RCON] Disconnected")
        self.command_input.setEnabled(False)
        self.send_btn.setEnabled(False)

    def on_rcon_message(self, message: str) -> None:
        """Handle incoming RCON message."""
        self._publish_console(f"[RCON] {message}")

    def send_command(self) -> None:
        """Send command to RCON."""
        if not self.rcon_client or not self.rcon_client.connected:
            QMessageBox.warning(self, "Error", "Not connected to RCON")
            return
        
        command = self.command_input.text().strip()
        if not command:
            return
        
        self._publish_console(f"> {command}")
        self.rcon_client.send_command(command)
        self.command_input.clear()
        
        # Update history
        self.update_history()

    def update_history(self) -> None:
        """Update command history dropdown."""
        if not self.rcon_client:
            return
        
        history = self.rcon_client.get_command_history()
        self.history_combo.clear()
        
        for cmd, timestamp in reversed(history[-20:]):
            self.history_combo.addItem(cmd, cmd)

    def on_history_selected(self, cmd: str) -> None:
        """Handle history selection."""
        if cmd:
            self.command_input.setText(cmd)

    def clear_history(self) -> None:
        """Clear command history."""
        if self.rcon_client:
            self.rcon_client.command_history.clear()
            self.history_combo.clear()
        
    def on_shared_console_output(self, message: str) -> None:
        """Handle shared server output stream."""
        self.console_output.emit(message)

    def append_console_line(self, message: str) -> None:
        """Append one line to output safely on UI thread."""
        self.output_display.append(message)

    def _publish_console(self, message: str) -> None:
        """Publish line to shared in-app consoles."""
        if self.server_manager:
            self.server_manager.emit_console_output(message)
        else:
            self.console_output.emit(message)

    def cleanup(self) -> None:
        """Cleanup when tab is closed."""
        if self.server_manager:
            self.server_manager.remove_output_listener(self.on_shared_console_output)
        if self.rcon_client:
            self.rcon_client.disconnect()
