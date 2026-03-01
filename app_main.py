"""
Rust Server Manager - Modern Desktop Application
Main entry point for the PySide6 UI application.
"""

import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from config.manager import ConfigManager
from core.server_manager import ServerManager
from scheduler.task_scheduler import TaskScheduler
from ui.main_window import MainWindow
from utils.logger import log


def main():
    """Main application entry point."""
    try:
        log.info("=" * 60)
        log.info("Rust Server Manager Starting")
        log.info("=" * 60)
        
        # Initialize configuration
        log.info("Loading configuration...")
        config_manager = ConfigManager()
        config = config_manager.get_config()
        
        # Validate configuration
        is_valid, errors = config_manager.validate()
        if not is_valid:
            log.warning(f"Configuration validation warnings: {errors}")
        
        # Initialize server manager
        log.info("Initializing server manager...")
        server_manager = ServerManager(config)
        server_manager.initialize_directories()
        
        # Initialize task scheduler
        log.info("Initializing task scheduler...")
        task_scheduler = TaskScheduler()
        
        # Create Qt application
        qt_app = QApplication(sys.argv)
        
        # Create app context
        app_context = {
            "config_manager": config_manager,
            "server_manager": server_manager,
            "task_scheduler": task_scheduler,
        }
        
        # Create main window
        log.info("Creating main window...")
        window = MainWindow(app_context)
        window.show()
        
        log.info("Application ready")
        
        # Run
        sys.exit(qt_app.exec())
        
    except Exception as e:
        log.critical(f"Failed to start application: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
