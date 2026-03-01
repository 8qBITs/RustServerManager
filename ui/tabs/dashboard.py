"""
Dashboard tab - displays server status, versions, and update info.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox,
    QFormLayout, QPushButton, QGridLayout
)
from PySide6.QtCore import Qt, QTimer
from pathlib import Path


class DashboardTab(QWidget):
    """Dashboard showing server status and information."""

    def __init__(self, server_manager, parent=None):
        super().__init__(parent)
        self.server_manager = server_manager
        self.init_ui()
        
        # Timer to refresh status every 2 seconds
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.refresh_status)
        self.status_timer.start(2000)

    def init_ui(self) -> None:
        """Initialize UI elements."""
        layout = QVBoxLayout()
        
        # Status group
        status_group = QGroupBox("Server Status")
        status_layout = QGridLayout()
        
        self.status_label = QLabel("● Offline")
        self.status_label.setStyleSheet("color: red; font-weight: bold; font-size: 14px;")
        status_layout.addWidget(QLabel("Status:"), 0, 0)
        status_layout.addWidget(self.status_label, 0, 1)
        
        self.pid_label = QLabel("N/A")
        status_layout.addWidget(QLabel("Process ID:"), 1, 0)
        status_layout.addWidget(self.pid_label, 1, 1)
        
        self.memory_label = QLabel("N/A")
        status_layout.addWidget(QLabel("Memory:"), 2, 0)
        status_layout.addWidget(self.memory_label, 2, 1)
        
        self.cpu_label = QLabel("N/A")
        status_layout.addWidget(QLabel("CPU:"), 3, 0)
        status_layout.addWidget(self.cpu_label, 3, 1)

        self.network_label = QLabel("N/A")
        status_layout.addWidget(QLabel("Network:"), 4, 0)
        status_layout.addWidget(self.network_label, 4, 1)

        self.players_label = QLabel("N/A")
        status_layout.addWidget(QLabel("Players Online:"), 5, 0)
        status_layout.addWidget(self.players_label, 5, 1)

        self.public_test_btn = QPushButton("🌐 Test WAN Access")
        self.public_test_btn.clicked.connect(self.test_wan_access)
        self.public_test_btn.setStyleSheet("background-color: #2d5d7d; color: white; padding: 8px;")
        status_layout.addWidget(QLabel("Public Access:"), 6, 0)
        status_layout.addWidget(self.public_test_btn, 6, 1)
        
        status_group.setLayout(status_layout)
        layout.addWidget(status_group)
        
        # Installation info
        info_group = QGroupBox("Installation Info")
        info_layout = QGridLayout()
        
        self.executable_label = QLabel("✗ Not Found")
        self.executable_label.setStyleSheet("color: red;")
        info_layout.addWidget(QLabel("RustDedicated.exe:"), 0, 0)
        info_layout.addWidget(self.executable_label, 0, 1)
        
        self.oxide_label = QLabel("✗ Not Installed")
        self.oxide_label.setStyleSheet("color: red;")
        info_layout.addWidget(QLabel("Oxide Status:"), 1, 0)
        info_layout.addWidget(self.oxide_label, 1, 1)
        
        self.last_update_label = QLabel("Never")
        info_layout.addWidget(QLabel("Last Update:"), 2, 0)
        info_layout.addWidget(self.last_update_label, 2, 1)
        
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        
        # Refresh button
        refresh_btn = QPushButton("Refresh Now")
        refresh_btn.clicked.connect(self.refresh_status)
        layout.addWidget(refresh_btn)
        
        layout.addStretch()
        self.setLayout(layout)

    def refresh_status(self) -> None:
        """Refresh server status display."""
        status = self.server_manager.get_server_status()
        
        # Update status
        if status.get("running"):
            self.status_label.setText("● Online")
            self.status_label.setStyleSheet("color: green; font-weight: bold; font-size: 14px;")
            self.pid_label.setText(str(status.get("pid", "N/A")))
            self.memory_label.setText(f"{status.get('memory_mb', 0):.1f} MB")
            self.cpu_label.setText(f"{status.get('cpu_percent', 0):.1f}%")
            self.network_label.setText(
                f"↓ {status.get('network_rx_kbps', 0):.1f} KB/s | ↑ {status.get('network_tx_kbps', 0):.1f} KB/s"
            )
            players = status.get("players_online")
            self.players_label.setText("N/A" if players is None else str(players))
        else:
            self.status_label.setText("● Offline")
            self.status_label.setStyleSheet("color: red; font-weight: bold; font-size: 14px;")
            self.pid_label.setText("N/A")
            self.memory_label.setText("N/A")
            self.cpu_label.setText("N/A")
            self.network_label.setText("N/A")
            self.players_label.setText("N/A")
        
        # Check executable
        if status.get("executable_exists"):
            self.executable_label.setText("✓ Found")
            self.executable_label.setStyleSheet("color: green;")
        else:
            self.executable_label.setText("✗ Not Found")
            self.executable_label.setStyleSheet("color: red;")
        
        # Check Oxide
        if status.get("oxide_installed"):
            self.oxide_label.setText("✓ Installed")
            self.oxide_label.setStyleSheet("color: green;")
        else:
            self.oxide_label.setText("✗ Not Installed")
            self.oxide_label.setStyleSheet("color: red;")
    
    def test_wan_access(self) -> None:
        """Test WAN accessibility and show results."""
        from PySide6.QtWidgets import QMessageBox
        
        # Change button while testing
        self.public_test_btn.setEnabled(False)
        self.public_test_btn.setText("Testing...")
        
        result = self.server_manager.test_wan_access(force=True)
        
        self.public_test_btn.setEnabled(True)
        self.public_test_btn.setText("🌐 Test WAN Access")
        
        public_ip = result.get("public_ip", "N/A")
        open_ok = bool(result.get("public_port_open"))
        error_text = result.get("public_check_error")
        port = self.server_manager.config.server.port
        
        if open_ok:
            QMessageBox.information(
                self,
                "WAN Port Test",
                f"✓ Server is accessible from WAN\n\nPublic IP: {public_ip}\nPort: {port}\n\nNote: This test connects from your local network, which may fail even if port forwarding is correct due to NAT loopback limitations. Test from an external device for accurate results.",
            )
        else:
            details = f"✗ Cannot connect to {public_ip}:{port}\n\nThis could mean:\n• Port forwarding is not configured\n• Firewall is blocking the port\n• NAT loopback is not supported by your router\n• Server is not yet fully started\n\nIMPORTANT: Many routers don't support NAT loopback, so this test may fail even when port forwarding works correctly. Test from an external device (phone on mobile data) for accurate results."
            if error_text:
                details += f"\n\nTechnical error: {error_text}"
            QMessageBox.warning(self, "WAN Port Test", details)

    def cleanup(self) -> None:
        """Cleanup when tab is closed."""
        self.status_timer.stop()
