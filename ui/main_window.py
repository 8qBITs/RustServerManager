"""
Main application window - ties together all UI tabs and manages the application.
"""

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QTabWidget,
    QMenuBar, QMenu, QStatusBar, QMessageBox
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon, QAction

from ui.tabs.dashboard import DashboardTab
from ui.tabs.controls import ControlsTab
from ui.tabs.settings import SettingsTab
from ui.tabs.automation import AutomationTab

from utils.logger import log


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self, app_context):
        super().__init__()
        
        self.app_context = app_context
        self.server_manager = app_context["server_manager"]
        self.config_manager = app_context["config_manager"]
        self.task_scheduler = app_context["task_scheduler"]
        
        self.init_ui()
        self.setup_automation()

    def init_ui(self) -> None:
        """Initialize main UI."""
        self.setWindowTitle("Rust Server Manager")
        self.setGeometry(100, 100, 1200, 800)
        
        # Create central widget and main layout
        central_widget = QWidget()
        main_layout = QVBoxLayout()
        
        # Create tab widget
        self.tabs = QTabWidget()
        
        # Add tabs
        self.dashboard_tab = DashboardTab(self.server_manager)
        self.tabs.addTab(self.dashboard_tab, "📊 Dashboard")
        
        self.controls_tab = ControlsTab(self.server_manager, self.config_manager)
        self.tabs.addTab(self.controls_tab, "🎮 Controls")
        
        self.settings_tab = SettingsTab(self.config_manager)
        self.tabs.addTab(self.settings_tab, "⚙️ Settings")
        
        self.automation_tab = AutomationTab(self.task_scheduler, self.config_manager, self.server_manager)
        self.tabs.addTab(self.automation_tab, "🔄 Automation")
        
        main_layout.addWidget(self.tabs)
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)
        
        # Menu bar
        self.create_menu_bar()
        
        # Status bar
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("Ready")

    def create_menu_bar(self) -> None:
        """Create application menu bar."""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("&File")
        
        reload_config = QAction("&Reload Configuration", self)
        reload_config.triggered.connect(self.reload_config)
        file_menu.addAction(reload_config)
        
        file_menu.addSeparator()
        
        exit_action = QAction("E&xit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Help menu
        help_menu = menubar.addMenu("&Help")
        
        about_action = QAction("&About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
        
        logs_action = QAction("&View Logs", self)
        logs_action.triggered.connect(self.show_logs)
        help_menu.addAction(logs_action)

    def reload_config(self) -> None:
        """Reload configuration from disk."""
        self.config_manager.load()
        self.settings_tab.load_settings()
        self.statusBar.showMessage("Configuration reloaded")
        log.info("Configuration reloaded from disk")

    def show_about(self) -> None:
        """Show about dialog."""
        QMessageBox.information(
            self,
            "About Rust Server Manager",
            "Rust Server Manager v2.0\n\n"
            "A modern desktop application for managing Rust game servers.\n\n"
            "Features:\n"
            "• Install/update Rust server\n"
            "• Install/update Oxide mods\n"
            "• Server control (start/stop/restart)\n"
            "• Automation and scheduling\n"
            "• RCON console\n"
            "• Configuration management\n\n"
            "Built with PySide6 and Python 3.9+"
        )

    def show_logs(self) -> None:
        """Open logs directory."""
        import subprocess
        from pathlib import Path
        
        logs_dir = Path("logs")
        if logs_dir.exists():
            subprocess.Popen(f'explorer "{logs_dir.absolute()}"')
        else:
            QMessageBox.information(self, "Logs", "Logs directory not found yet")

    def setup_automation(self) -> None:
        """Setup background automation based on config."""
        cfg = self.config_manager.get_config()
        
        # Auto-start server if configured
        if getattr(cfg.automation, "auto_start_server_on_boot", False):
            if not self.server_manager.is_server_running():
                log.info("Auto-starting server on application launch")
                self.controls_tab.on_start_clicked()
        
        if cfg.automation.auto_check_rust_updates:
            self.task_scheduler.schedule_update_check(
                callback=self.on_update_check,
                interval_minutes=cfg.automation.update_check_interval_minutes,
                job_id="rust_update_check"
            )
        
        if cfg.automation.auto_check_oxide_updates:
            self.task_scheduler.schedule_oxide_update_check(
                callback=self.on_oxide_update_check,
                interval_minutes=cfg.automation.update_check_interval_minutes,
                job_id="oxide_update_check"
            )
        
        log.info("Automation setup complete")

    def on_update_check(self) -> bool:
        """Handle scheduled update check."""
        log.info("Executing scheduled Rust update check")
        # TODO: Implement actual update check logic
        return True

    def on_oxide_update_check(self) -> bool:
        """Handle scheduled Oxide update check."""
        log.info("Executing scheduled Oxide update check")
        # TODO: Implement actual Oxide update check logic
        return True

    def closeEvent(self, event) -> None:
        """Handle window close."""
        # Cleanup
        if hasattr(self, 'dashboard_tab'):
            self.dashboard_tab.cleanup()
        if hasattr(self, 'controls_tab'):
            self.controls_tab.cleanup()
        if hasattr(self, 'automation_tab'):
            self.automation_tab.cleanup()
        
        # Shutdown scheduler
        self.task_scheduler.shutdown()
        
        # Stop server if running
        if self.server_manager.is_server_running():
            reply = QMessageBox.question(
                self,
                "Server Running",
                "Server is still running. Do you want to stop it?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.server_manager.stop_server()
        
        log.info("Application closing")
        event.accept()
