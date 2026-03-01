"""
Settings tab - configurable application and server settings.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QScrollArea,
    QMessageBox, QLabel, QFileDialog, QLineEdit
)
from PySide6.QtCore import Qt
from ui.widgets.widgets import FieldGroup
from utils.startup import toggle_startup, is_startup_enabled
import logging

log = logging.getLogger(__name__)


class SettingsTab(QWidget):
    """Application and server settings panel."""

    def __init__(self, config_manager, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.init_ui()
        self.load_settings()

    def init_ui(self) -> None:
        """Initialize UI elements."""
        main_layout = QVBoxLayout()
        
        # Scroll area for settings
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout()
        
        # Server Settings
        self.server_group = FieldGroup("Server Settings")
        
        # Connection & Identity
        self.server_port_field = self.server_group.add_int_field(
            "port", "Server Port:", 28015, 1024, 65535
        )
        self.app_port_field = self.server_group.add_int_field(
            "app_port", "App Port:", 28016, 1024, 65535
        )
        self.hostname_field = self.server_group.add_text_field(
            "hostname", "Server Name:", "My Rust Server"
        )
        self.url_field = self.server_group.add_text_field(
            "url", "Server URL:", ""
        )
        self.header_image_field = self.server_group.add_text_field(
            "header_image", "Header Image URL:", ""
        )
        
        # Map Configuration
        self.map_field = self.server_group.add_text_field(
            "map", "Map:", "Procedural Map"
        )
        self.map_mode_field = self.server_group.add_combo_field(
            "map_mode", "Map Mode:", ["procedural", "custom"], "procedural"
        )

        self.custom_map_path_field = QLineEdit()
        self.custom_map_path_field.setPlaceholderText("Path or URL for custom map")
        self.import_map_btn = QPushButton("Import/Select")
        self.import_map_btn.clicked.connect(self.import_custom_map)
        custom_map_row = QHBoxLayout()
        custom_map_row.addWidget(self.custom_map_path_field)
        custom_map_row.addWidget(self.import_map_btn)
        self.server_group.layout.addRow("Custom Map:", custom_map_row)

        self.seed_field = self.server_group.add_text_field(
            "seed", "Seed (blank = random):", ""
        )
        self.world_size_field = self.server_group.add_int_field(
            "world_size", "World Size:", 3000, 1000, 6000
        )
        
        # Players & Limits
        self.max_players_field = self.server_group.add_int_field(
            "max_players", "Max Players:", 10, 1, 500
        )
        self.queue_size_field = self.server_group.add_int_field(
            "queue_size", "Queue Size:", 100, 0, 1000
        )
        
        # Performance
        self.tickrate_field = self.server_group.add_int_field(
            "tickrate", "Tickrate:", 30, 10, 60
        )
        self.fps_limit_field = self.server_group.add_int_field(
            "fps_limit", "FPS Limit:", 256, 60, 512
        )
        self.save_interval_field = self.server_group.add_int_field(
            "save_interval", "Save Interval (sec):", 300, 60, 3600
        )
        
        # Gameplay Mode
        self.gamemode_field = self.server_group.add_combo_field(
            "gamemode", "Game Mode:", ["vanilla", "softcore", "hardcore", "creative"], "vanilla"
        )
        self.pve_field = self.server_group.add_bool_field(
            "pve", "PVE Mode", False
        )
        self.official_field = self.server_group.add_bool_field(
            "official", "Official", False
        )
        self.modded_field = self.server_group.add_bool_field(
            "modded", "Modded", False
        )
        
        # Gameplay Features
        self.radiation_field = self.server_group.add_bool_field(
            "radiation", "Radiation", True
        )
        self.stability_field = self.server_group.add_bool_field(
            "stability", "Stability", True
        )
        self.comfort_field = self.server_group.add_bool_field(
            "comfort", "Comfort", True
        )
        self.events_field = self.server_group.add_bool_field(
            "events", "Events", True
        )
        
        # Decay Settings
        self.decay_upkeep_field = self.server_group.add_bool_field(
            "decay_upkeep", "Decay Upkeep", True
        )
        self.decay_scale_field = self.server_group.add_text_field(
            "decay_scale", "Decay Scale (0.0-2.0):", "1.0"
        )
        self.decay_delay_field = self.server_group.add_text_field(
            "decay_delay", "Decay Delay (hours, blank=default):", ""
        )
        
        scroll_layout.addWidget(self.server_group)
        
        # Path Settings
        self.path_group = FieldGroup("Path Settings")
        self.rust_data_field = self.path_group.add_text_field(
            "rust_data_dir", "Rust Data Directory:", "./addons/steam/rust_data"
        )
        self.steamcmd_field = self.path_group.add_text_field(
            "steamcmd_path", "SteamCMD Path:", "./addons/steam/steamcmd.exe"
        )
        self.steamcmd_url_field = self.path_group.add_text_field(
            "steamcmd_download_url",
            "SteamCMD Download URL:",
            "https://steamcdn-a.akamaihd.net/client/installer/steamcmd.zip",
        )
        scroll_layout.addWidget(self.path_group)
        
        # RCON Settings
        self.rcon_group = FieldGroup("RCON Settings")
        self.rcon_host_field = self.rcon_group.add_text_field(
            "rcon_host", "RCON Host:", "127.0.0.1"
        )
        self.rcon_port_field = self.rcon_group.add_int_field(
            "rcon_port", "RCON Port:", 28016, 1024, 65535
        )
        self.rcon_password_field = self.rcon_group.add_text_field(
            "rcon_password", "RCON Password:", ""
        )
        self.rcon_password_field.setEchoMode(QLineEdit.EchoMode.Password)
        scroll_layout.addWidget(self.rcon_group)
        
        # Automation Settings
        self.automation_group = FieldGroup("Automation Settings")
        self.auto_start_with_windows = self.automation_group.add_bool_field(
            "auto_start_with_windows", "Start with Windows", False
        )
        self.auto_start_with_windows.toggled.connect(self.on_auto_start_toggled)
        self.auto_start_server_on_boot = self.automation_group.add_bool_field(
            "auto_start_server_on_boot", "Start server on app launch", False
        )
        self.max_backups_field = self.automation_group.add_int_field(
            "max_backups", "Max backups to keep:", 3, 1, 100
        )
        scroll_layout.addWidget(self.automation_group)
        
        scroll_layout.addStretch()
        scroll_widget.setLayout(scroll_layout)
        scroll.setWidget(scroll_widget)
        main_layout.addWidget(scroll)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.save_btn = QPushButton("💾 Save Settings")
        self.save_btn.clicked.connect(self.save_settings)
        button_layout.addWidget(self.save_btn)
        
        self.validate_btn = QPushButton("✓ Validate Settings")
        self.validate_btn.clicked.connect(self.validate_settings)
        button_layout.addWidget(self.validate_btn)
        
        button_layout.addStretch()
        main_layout.addLayout(button_layout)
        
        self.setLayout(main_layout)

    def load_settings(self) -> None:
        """Load settings from config into UI."""
        cfg = self.config_manager.get_config()
        
        # Server settings - Connection & Identity
        self.server_port_field.setValue(cfg.server.port)
        self.app_port_field.setValue(cfg.server.app_port)
        self.hostname_field.setText(cfg.server.description)
        self.url_field.setText(getattr(cfg.server, "url", ""))
        self.header_image_field.setText(getattr(cfg.server, "header_image", ""))
        
        # Map Configuration
        self.map_field.setText(cfg.server.map)
        self.map_mode_field.setCurrentText(getattr(cfg.server, "map_mode", "procedural"))
        self.custom_map_path_field.setText(getattr(cfg.server, "custom_map_path", ""))
        self.seed_field.setText("" if cfg.server.seed is None else str(cfg.server.seed))
        self.world_size_field.setValue(cfg.server.world_size)
        
        # Players & Limits
        self.max_players_field.setValue(cfg.server.max_players)
        self.queue_size_field.setValue(getattr(cfg.server, "queue_size", 100))
        
        # Performance
        self.tickrate_field.setValue(cfg.server.tickrate)
        self.fps_limit_field.setValue(getattr(cfg.server, "fps_limit", 256))
        self.save_interval_field.setValue(getattr(cfg.server, "save_interval", 300))
        
        # Gameplay Mode
        self.gamemode_field.setCurrentText(getattr(cfg.server, "gamemode", "vanilla"))
        self.pve_field.setChecked(getattr(cfg.server, "pve", False))
        self.official_field.setChecked(getattr(cfg.server, "official", False))
        self.modded_field.setChecked(getattr(cfg.server, "modded", False))
        
        # Gameplay Features
        self.radiation_field.setChecked(getattr(cfg.server, "radiation", True))
        self.stability_field.setChecked(getattr(cfg.server, "stability", True))
        self.comfort_field.setChecked(getattr(cfg.server, "comfort", True))
        self.events_field.setChecked(getattr(cfg.server, "events", True))
        
        # Decay Settings
        self.decay_upkeep_field.setChecked(getattr(cfg.server, "decay_upkeep", True))
        self.decay_scale_field.setText(str(getattr(cfg.server, "decay_scale", 1.0)))
        decay_delay = getattr(cfg.server, "decay_delay_override", None)
        self.decay_delay_field.setText("" if decay_delay is None else str(decay_delay))
        
        # Path settings
        self.rust_data_field.setText(cfg.paths.rust_data_dir)
        self.steamcmd_field.setText(cfg.paths.steamcmd_path)
        self.steamcmd_url_field.setText(cfg.paths.steamcmd_download_url)
        
        # RCON settings
        self.rcon_host_field.setText(cfg.rcon.host)
        self.rcon_port_field.setValue(cfg.rcon.port)
        self.rcon_password_field.setText(cfg.rcon.password)
        
        # Automation settings
        # Synchronize UI with actual Windows startup status
        actual_startup_enabled = is_startup_enabled()
        self.auto_start_with_windows.setChecked(actual_startup_enabled)
        self.auto_start_server_on_boot.setChecked(getattr(cfg.automation, "auto_start_server_on_boot", False))
        self.max_backups_field.setValue(cfg.automation.max_backups)

    def save_settings(self) -> None:
        """Save settings from UI to config."""
        # Validate seed
        seed_text = self.seed_field.text().strip()
        if seed_text:
            try:
                seed_value = int(seed_text)
                if seed_value < 0:
                    raise ValueError("Seed cannot be negative")
            except ValueError:
                QMessageBox.warning(self, "Validation", "Seed must be a non-negative integer or blank")
                return
        else:
            seed_value = None
        
        # Validate decay scale
        try:
            decay_scale = float(self.decay_scale_field.text())
            if not 0.0 <= decay_scale <= 2.0:
                raise ValueError()
        except ValueError:
            QMessageBox.warning(self, "Validation", "Decay scale must be a number between 0.0 and 2.0")
            return
        
        # Validate decay delay
        decay_delay_text = self.decay_delay_field.text().strip()
        if decay_delay_text:
            try:
                decay_delay_value = int(decay_delay_text)
                if decay_delay_value < 0:
                    raise ValueError()
            except ValueError:
                QMessageBox.warning(self, "Validation", "Decay delay must be a non-negative integer or blank")
                return
        else:
            decay_delay_value = None

        updates = {
            # Connection & Identity
            "server.port": self.server_port_field.value(),
            "server.app_port": self.app_port_field.value(),
            "server.description": self.hostname_field.text(),
            "server.url": self.url_field.text(),
            "server.header_image": self.header_image_field.text(),
            
            # Map Configuration
            "server.map": self.map_field.text(),
            "server.map_mode": self.map_mode_field.currentText(),
            "server.custom_map_path": self.custom_map_path_field.text(),
            "server.seed": seed_value,
            "server.world_size": self.world_size_field.value(),
            
            # Players & Limits
            "server.max_players": self.max_players_field.value(),
            "server.queue_size": self.queue_size_field.value(),
            
            # Performance
            "server.tickrate": self.tickrate_field.value(),
            "server.fps_limit": self.fps_limit_field.value(),
            "server.save_interval": self.save_interval_field.value(),
            
            # Gameplay Mode
            "server.gamemode": self.gamemode_field.currentText(),
            "server.pve": self.pve_field.isChecked(),
            "server.official": self.official_field.isChecked(),
            "server.modded": self.modded_field.isChecked(),
            
            # Gameplay Features
            "server.radiation": self.radiation_field.isChecked(),
            "server.stability": self.stability_field.isChecked(),
            "server.comfort": self.comfort_field.isChecked(),
            "server.events": self.events_field.isChecked(),
            
            # Decay Settings
            "server.decay_upkeep": self.decay_upkeep_field.isChecked(),
            "server.decay_scale": decay_scale,
            "server.decay_delay_override": decay_delay_value,
            
            # Paths
            "paths.rust_data_dir": self.rust_data_field.text(),
            "paths.steamcmd_path": self.steamcmd_field.text(),
            "paths.steamcmd_download_url": self.steamcmd_url_field.text(),
            
            # RCON
            "rcon.host": self.rcon_host_field.text(),
            "rcon.port": self.rcon_port_field.value(),
            "rcon.password": self.rcon_password_field.text(),
            
            # Automation
            "automation.auto_start_with_windows": self.auto_start_with_windows.isChecked(),
            "automation.auto_start_server_on_boot": self.auto_start_server_on_boot.isChecked(),
            "automation.max_backups": self.max_backups_field.value(),
        }
        
        if self.config_manager.update_config(**updates):
            QMessageBox.information(self, "Success", "Settings saved successfully!")
        else:
            QMessageBox.critical(self, "Error", "Failed to save settings. Check the logs.")

    def validate_settings(self) -> None:
        """Validate current settings."""
        valid, errors = self.config_manager.validate()
        
        if valid:
            QMessageBox.information(
                self, "Validation", "✓ All settings are valid!"
            )
        else:
            error_msg = "\n".join([f"• {e}" for e in errors])
            QMessageBox.warning(
                self, "Validation Errors", f"Found {len(errors)} error(s):\n\n{error_msg}"
            )

    def import_custom_map(self) -> None:
        """Import/select a custom map file and set map mode accordingly."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Custom Map",
            "",
            "Map files (*.map *.sav *.zip);;All files (*.*)",
        )
        if file_path:
            self.custom_map_path_field.setText(file_path)
            self.map_mode_field.setCurrentText("custom")

    def on_auto_start_toggled(self, checked: bool) -> None:
        """Handle auto-start with Windows toggle."""
        success, message = toggle_startup(checked)
        
        if not success:
            # Revert the toggle if it failed
            self.auto_start_with_windows.setChecked(not checked)
            QMessageBox.warning(self, "Startup Configuration", message)
        else:
            log.info(f"Auto-start with Windows: {checked}")
