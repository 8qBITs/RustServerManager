"""
Controls tab - server and mod installation/update controls.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox,
    QPushButton, QGridLayout, QProgressBar, QFormLayout, QMessageBox, QLineEdit
)
from PySide6.QtCore import Qt, Signal, QThread, QTimer
from typing import Optional
from ui.widgets.widgets import LogsViewer, ToggleSwitch
from core.rcon_client import RconClient


class ControlWorker(QThread):
    """Background worker for long-running operations."""
    
    progress = Signal(str)
    finished = Signal(bool, str)  # success, message
    
    def __init__(self, operation, server_manager):
        super().__init__()
        self.operation = operation
        self.server_manager = server_manager
    
    def run(self):
        """Run the operation."""
        try:
            success = self.operation(self.progress.emit)
            self.finished.emit(success, "Operation completed" if success else "Operation failed")
        except Exception as e:
            self.finished.emit(False, f"Error: {str(e)}")


class ControlsTab(QWidget):
    """Server and mods control panel."""

    console_output = Signal(str)

    def __init__(self, server_manager, config_manager=None, parent=None):
        super().__init__(parent)
        self.server_manager = server_manager
        self.config_manager = config_manager
        self.worker: Optional[ControlWorker] = None
        self._check_wan_after_operation = False
        self.rcon_client: Optional[RconClient] = None
        self.rcon_connected = False
        self.console_output.connect(self.append_console_line)
        self.server_manager.add_output_listener(self.on_server_console_output)
        self.init_ui()

        self.stats_timer = QTimer()
        self.stats_timer.timeout.connect(self.refresh_live_stats)
        self.stats_timer.start(2000)
        
        # Initial button text update
        self.update_button_texts()

    def init_ui(self) -> None:
        """Initialize UI elements."""
        layout = QVBoxLayout()
        
        # Server control group
        server_group = QGroupBox("Server Control")
        server_layout = QGridLayout()
        
        self.start_btn = QPushButton("▶ Start Server")
        self.start_btn.clicked.connect(self.on_start_clicked)
        self.start_btn.setStyleSheet("background-color: #2d7d2d; color: white; padding: 8px;")
        server_layout.addWidget(self.start_btn, 0, 0)
        
        self.stop_btn = QPushButton("⏹ Stop Server")
        self.stop_btn.clicked.connect(self.on_stop_clicked)
        self.stop_btn.setStyleSheet("background-color: #7d2d2d; color: white; padding: 8px;")
        server_layout.addWidget(self.stop_btn, 0, 1)
        
        self.restart_btn = QPushButton("↻ Restart Server")
        self.restart_btn.clicked.connect(self.on_restart_clicked)
        self.restart_btn.setStyleSheet("background-color: #2d5d7d; color: white; padding: 8px;")
        server_layout.addWidget(self.restart_btn, 0, 2)
        
        server_group.setLayout(server_layout)
        layout.addWidget(server_group)
        
        # Installation group
        install_group = QGroupBox("Installation & Updates")
        install_layout = QVBoxLayout()
        
        # Rust Server row
        rust_row = QHBoxLayout()
        self.install_rust_btn = QPushButton("Install Rust Server")
        self.install_rust_btn.clicked.connect(self.on_install_rust_clicked)
        self.install_rust_btn.setMinimumWidth(200)
        rust_row.addWidget(self.install_rust_btn)
        
        rust_auto_label = QLabel("Auto-update:")
        rust_row.addWidget(rust_auto_label)
        self.auto_update_rust_switch = ToggleSwitch()
        if self.config_manager:
            cfg = self.config_manager.get_config()
            self.auto_update_rust_switch.setChecked(cfg.automation.auto_update_rust)
        self.auto_update_rust_switch.toggled.connect(self.on_auto_update_rust_toggled)
        rust_row.addWidget(self.auto_update_rust_switch)
        rust_row.addStretch()
        install_layout.addLayout(rust_row)
        
        # Oxide row
        oxide_row = QHBoxLayout()
        self.install_oxide_btn = QPushButton("Install Oxide")
        self.install_oxide_btn.clicked.connect(self.on_install_oxide_clicked)
        self.install_oxide_btn.setMinimumWidth(200)
        oxide_row.addWidget(self.install_oxide_btn)
        
        oxide_auto_label = QLabel("Auto-update:")
        oxide_row.addWidget(oxide_auto_label)
        self.auto_update_oxide_switch = ToggleSwitch()
        if self.config_manager:
            cfg = self.config_manager.get_config()
            self.auto_update_oxide_switch.setChecked(cfg.automation.auto_update_oxide)
        self.auto_update_oxide_switch.toggled.connect(self.on_auto_update_oxide_toggled)
        oxide_row.addWidget(self.auto_update_oxide_switch)
        oxide_row.addStretch()
        install_layout.addLayout(oxide_row)
        
        # RustEdit row
        rustedit_row = QHBoxLayout()
        self.install_rustedit_btn = QPushButton("Install RustEdit")
        self.install_rustedit_btn.clicked.connect(self.on_install_rustedit_clicked)
        self.install_rustedit_btn.setMinimumWidth(200)
        rustedit_row.addWidget(self.install_rustedit_btn)
        rustedit_row.addStretch()
        install_layout.addLayout(rustedit_row)
        
        install_group.setLayout(install_layout)
        layout.addWidget(install_group)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Status label
        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        stats_group = QGroupBox("Live Statistics")
        stats_layout = QFormLayout()

        self.stats_status = QLabel("Offline")
        self.stats_pid = QLabel("N/A")
        self.stats_cpu = QLabel("N/A")
        self.stats_mem = QLabel("N/A")
        self.stats_net = QLabel("N/A")
        self.stats_players = QLabel("N/A")
        self.stats_public = QLabel("N/A")

        stats_layout.addRow("Status:", self.stats_status)
        stats_layout.addRow("PID:", self.stats_pid)
        stats_layout.addRow("CPU:", self.stats_cpu)
        stats_layout.addRow("Memory:", self.stats_mem)
        stats_layout.addRow("Network:", self.stats_net)
        stats_layout.addRow("Players:", self.stats_players)
        stats_layout.addRow("Public Port Check:", self.stats_public)

        self.test_wan_btn = QPushButton("Test WAN Port")
        self.test_wan_btn.clicked.connect(self.on_test_wan_clicked)
        stats_layout.addRow("Connectivity:", self.test_wan_btn)

        stats_group.setLayout(stats_layout)
        layout.addWidget(stats_group)

        # Manager console (shared Rust process output stream + RCON)
        console_group = QGroupBox("Manager Console (with RCON)")
        console_layout = QVBoxLayout()
        
        # RCON status indicator
        rcon_status_layout = QHBoxLayout()
        self.rcon_status_label = QLabel("● RCON: Disconnected")
        self.rcon_status_label.setStyleSheet("color: #888888; font-weight: bold; font-size: 10px;")
        rcon_status_layout.addWidget(self.rcon_status_label)
        rcon_status_layout.addStretch()
        console_layout.addLayout(rcon_status_layout)
        
        self.console_viewer = LogsViewer()
        console_layout.addWidget(self.console_viewer)
        
        # Command input row
        cmd_layout = QHBoxLayout()
        self.rcon_input = QLineEdit()
        self.rcon_input.setPlaceholderText("Enter RCON command (e.g., status, say Hello)")
        self.rcon_input.returnPressed.connect(self.send_rcon_command)
        cmd_layout.addWidget(self.rcon_input)
        
        send_btn = QPushButton("📤 Send")
        send_btn.clicked.connect(self.send_rcon_command)
        send_btn.setMaximumWidth(100)
        cmd_layout.addWidget(send_btn)
        
        clear_btn = QPushButton("🗑️ Clear")
        clear_btn.clicked.connect(self.console_viewer.clear_logs)
        clear_btn.setMaximumWidth(100)
        cmd_layout.addWidget(clear_btn)
        
        console_layout.addLayout(cmd_layout)

        console_group.setLayout(console_layout)
        layout.addWidget(console_group, 1)
        
        layout.addStretch()
        self.setLayout(layout)

    def on_start_clicked(self) -> None:
        """Handle start button."""
        self.run_operation(
            self.server_manager.start_server,
            "Starting server...",
            check_wan_after=False,
        )

    def on_stop_clicked(self) -> None:
        """Handle stop button."""
        self.run_operation(self.server_manager.stop_server, "Stopping server...")

    def on_restart_clicked(self) -> None:
        """Handle restart button."""
        self.run_operation(self.server_manager.restart_server, "Restarting server...")

    def on_install_rust_clicked(self) -> None:
        """Handle install Rust button."""
        self.run_operation(self.server_manager.install_rust_server, "Installing Rust server...")

    def on_install_oxide_clicked(self) -> None:
        """Handle install Oxide button."""
        self.run_operation(self.server_manager.install_oxide, "Installing Oxide...")

    def on_install_rustedit_clicked(self) -> None:
        """Handle install RustEdit button."""
        self.run_operation(self.server_manager.install_rust_edit, "Installing RustEdit...")

    def run_operation(self, operation, status_text: str, check_wan_after: bool = False) -> None:
        """Run a long operation in background."""
        if self.worker and self.worker.isRunning():
            self.status_label.setText("An operation is already running!")
            return

        self._check_wan_after_operation = check_wan_after
        self.disable_buttons(True)
        self.progress_bar.setVisible(True)
        self.status_label.setText(status_text)
        
        self.worker = ControlWorker(operation, self.server_manager)
        self.worker.progress.connect(self.on_progress)
        self.worker.finished.connect(self.on_operation_finished)
        self.worker.start()

    def on_progress(self, message: str) -> None:
        """Handle progress message."""
        self.status_label.setText(message)
        self.console_output.emit(f"[MANAGER] {message}")
        self.progress_bar.setValue((self.progress_bar.value() + 10) % 100)

    def on_server_console_output(self, message: str) -> None:
        """Handle shared server console output stream and auto-connect RCON."""
        self.console_output.emit(message)
        
        # Auto-connect RCON when server is ready
        if "Server startup complete" in message or "RCON started" in message:
            if not self.rcon_connected and self.config_manager:
                cfg = self.config_manager.get_config()
                if cfg.rcon.password:  # Only if password is configured
                    self.connect_rcon()

    def append_console_line(self, message: str) -> None:
        """Append one line to manager console safely on UI thread."""
        self.console_viewer.log(message)

    def on_operation_finished(self, success: bool, message: str) -> None:
        """Handle operation completion."""
        self.disable_buttons(False)
        self.progress_bar.setVisible(False)
        
        if success:
            self.status_label.setText(f"✓ {message}")
            self.status_label.setStyleSheet("color: green;")
        else:
            self.status_label.setText(f"✗ {message}")
            self.status_label.setStyleSheet("color: red;")

        self.refresh_live_stats()

    def update_button_texts(self) -> None:
        """Update install/update button texts based on installation status."""
        status = self.server_manager.get_server_status()
        
        # Update Rust button
        if status.get("executable_exists"):
            self.install_rust_btn.setText("🔄 Update Rust Server")
        else:
            self.install_rust_btn.setText("📥 Install Rust Server")
        
        # Update Oxide button
        if status.get("oxide_installed"):
            self.install_oxide_btn.setText("🔄 Update Oxide")
        else:
            self.install_oxide_btn.setText("📥 Install Oxide")
        
        # Update RustEdit button (check if file exists)
        rust_dir = self.server_manager.rust_dir
        rustedit_dll = rust_dir / "RustDedicated_Data" / "Managed" / "Oxide.Ext.RustEdit.dll"
        if rustedit_dll.exists():
            self.install_rustedit_btn.setText("🔄 Update RustEdit")
        else:
            self.install_rustedit_btn.setText("📥 Install RustEdit")
    
    def refresh_live_stats(self) -> None:
        """Refresh live statistics in control panel."""
        status = self.server_manager.get_server_status()
        is_running = status.get("running")

        # Update button visibility based on server state
        if is_running:
            self.start_btn.setVisible(False)
            self.stop_btn.setVisible(True)
            self.restart_btn.setVisible(True)
            self.stop_btn.setText("⏹ Kill Server")
        else:
            self.start_btn.setVisible(True)
            self.stop_btn.setVisible(False)
            self.restart_btn.setVisible(False)
        
        # Update installation button texts
        self.update_button_texts()

        if is_running:
            self.stats_status.setText("Online")
            self.stats_status.setStyleSheet("color: green; font-weight: bold;")
            self.stats_pid.setText(str(status.get("pid", "N/A")))
            self.stats_cpu.setText(f"{status.get('cpu_percent', 0):.1f}%")
            self.stats_mem.setText(f"{status.get('memory_mb', 0):.1f} MB")
            self.stats_net.setText(
                f"↓ {status.get('network_rx_kbps', 0):.1f} KB/s | "
                f"↑ {status.get('network_tx_kbps', 0):.1f} KB/s"
            )
        else:
            self.stats_status.setText("Offline")
            self.stats_status.setStyleSheet("color: red; font-weight: bold;")
            self.stats_pid.setText("N/A")
            self.stats_cpu.setText("N/A")
            self.stats_mem.setText("N/A")
            self.stats_net.setText("N/A")

        players_online = status.get("players_online")
        self.stats_players.setText("N/A" if players_online is None else str(players_online))

        public_ip = status.get("public_ip", "N/A")
        public_ok = bool(status.get("public_port_open"))
        if public_ip == "N/A":
            self.stats_public.setText("Public IP unavailable")
            self.stats_public.setStyleSheet("color: #d28b00;")
        elif public_ok:
            self.stats_public.setText(f"{public_ip}:{self.server_manager.config.server.port} reachable")
            self.stats_public.setStyleSheet("color: green;")
        else:
            self.stats_public.setText(f"{public_ip}:{self.server_manager.config.server.port} not reachable")
            self.stats_public.setStyleSheet("color: red;")

    def on_test_wan_clicked(self) -> None:
        """Run explicit WAN accessibility check and notify user."""
        result = self.server_manager.test_wan_access(force=True)
        public_ip = result.get("public_ip", "N/A")
        open_ok = bool(result.get("public_port_open"))
        error_text = result.get("public_check_error")
        port = self.server_manager.config.server.port

        self.refresh_live_stats()

        if open_ok:
            QMessageBox.information(
                self,
                "WAN Port Test",
                f"Server is accessible from WAN at {public_ip}:{port}",
            )
        else:
            details = f"Public endpoint not reachable: {public_ip}:{port}"
            if error_text:
                details += f"\n\nError: {error_text}"
            QMessageBox.warning(self, "WAN Port Test", details)

    def disable_buttons(self, disable: bool) -> None:
        """Enable/disable all buttons."""
        for btn in [
            self.start_btn, self.stop_btn, self.restart_btn,
            self.install_rust_btn, self.install_oxide_btn, self.install_rustedit_btn
        ]:
            btn.setEnabled(not disable)

    def connect_rcon(self) -> None:
        """Connect to RCON server."""
        if not self.config_manager:
            return
        
        try:
            cfg = self.config_manager.get_config()
            self.console_output.emit("[RCON] Connecting...")
            
            self.rcon_client = RconClient(
                host=cfg.rcon.host,
                port=cfg.rcon.port,
                password=cfg.rcon.password
            )
            
            if self.rcon_client.connect():
                self.rcon_connected = True
                self.rcon_status_label.setText("● RCON: Connected")
                self.rcon_status_label.setStyleSheet("color: #2d7d2d; font-weight: bold; font-size: 10px;")
                self.console_output.emit("[RCON] Connected successfully")
            else:
                self.console_output.emit("[RCON] Failed to connect")
        except Exception as e:
            self.console_output.emit(f"[RCON-ERR] Connection error: {e}")
    
    def disconnect_rcon(self) -> None:
        """Disconnect from RCON server."""
        if self.rcon_client:
            self.rcon_client.disconnect()
            self.rcon_connected = False
            self.rcon_status_label.setText("● RCON: Disconnected")
            self.rcon_status_label.setStyleSheet("color: #888888; font-weight: bold; font-size: 10px;")
            self.console_output.emit("[RCON] Disconnected")
    
    def send_rcon_command(self) -> None:
        """Send RCON command from input field."""
        command = self.rcon_input.text().strip()
        if not command:
            return
        
        if not self.rcon_connected or not self.rcon_client:
            self.console_output.emit("[RCON-ERR] Not connected to RCON")
            # Try to connect
            self.connect_rcon()
            return
        
        try:
            self.console_output.emit(f"[RCON] > {command}")
            response = self.rcon_client.send_command(command)
            if response:
                self.console_output.emit(f"[RCON] {response}")
            self.rcon_input.clear()
        except Exception as e:
            self.console_output.emit(f"[RCON-ERR] Command failed: {e}")
            self.disconnect_rcon()
    
    def on_auto_update_rust_toggled(self, checked: bool) -> None:
        """Handle auto-update Rust toggle."""
        if self.config_manager:
            self.config_manager.update_config(**{"automation.auto_update_rust": checked})
    
    def on_auto_update_oxide_toggled(self, checked: bool) -> None:
        """Handle auto-update Oxide toggle."""
        if self.config_manager:
            self.config_manager.update_config(**{"automation.auto_update_oxide": checked})
    
    def cleanup(self) -> None:
        """Cleanup listeners when tab is closed."""
        self.stats_timer.stop()
        self.disconnect_rcon()
        self.server_manager.remove_output_listener(self.on_server_console_output)
