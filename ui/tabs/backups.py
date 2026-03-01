"""
Backups tab - manage server world backups and restoration.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox,
    QPushButton, QComboBox, QLineEdit, QTableWidget, QTableWidgetItem,
    QMessageBox, QProgressDialog
)
from PySide6.QtCore import Qt, QThread, Signal
from typing import Optional
from ui.widgets.widgets import LogsViewer


class BackupWorker(QThread):
    """Background worker for backup operations."""
    
    progress = Signal(str)
    finished = Signal(bool, str)
    
    def __init__(self, operation, done_message: str):
        super().__init__()
        self.operation = operation
        self.done_message = done_message
    
    def run(self) -> None:
        try:
            result = self.operation(self.progress.emit)
            self.finished.emit(bool(result), self.done_message if result else "Operation failed")
        except Exception as e:
            self.finished.emit(False, f"Error: {e}")


class BackupsTab(QWidget):
    """Backup management and restoration control panel."""

    def __init__(self, server_manager, config_manager, parent=None):
        super().__init__(parent)
        self.server_manager = server_manager
        self.config_manager = config_manager
        self.worker: Optional[BackupWorker] = None
        self.init_ui()
        self.refresh_backup_list()

    def init_ui(self) -> None:
        """Initialize UI."""
        layout = QVBoxLayout()

        # Create/manage backups
        manage_group = QGroupBox("Backup Management")
        manage_layout = QVBoxLayout()
        
        # Create backup section
        create_layout = QHBoxLayout()
        create_layout.addWidget(QLabel("Backup Name:"))
        self.backup_name = QLineEdit()
        self.backup_name.setPlaceholderText("optional custom name")
        create_layout.addWidget(self.backup_name)
        
        self.create_backup_btn = QPushButton("📦 Create Backup")
        self.create_backup_btn.clicked.connect(self.create_backup)
        create_layout.addWidget(self.create_backup_btn)
        
        manage_layout.addLayout(create_layout)
        
        # Available backups section
        backups_layout = QHBoxLayout()
        backups_layout.addWidget(QLabel("Available Backups:"))
        self.backups_combo = QComboBox()
        backups_layout.addWidget(self.backups_combo)
        
        refresh_btn = QPushButton("🔄 Refresh List")
        refresh_btn.clicked.connect(self.refresh_backup_list)
        backups_layout.addWidget(refresh_btn)
        
        manage_layout.addLayout(backups_layout)
        
        # Restore buttons
        restore_layout = QHBoxLayout()
        
        self.deploy_backup_btn = QPushButton("🚀 Deploy Selected Backup")
        self.deploy_backup_btn.clicked.connect(self.deploy_selected_backup)
        restore_layout.addWidget(self.deploy_backup_btn)
        
        self.deploy_latest_btn = QPushButton("🕒 Deploy Latest Backup")
        self.deploy_latest_btn.clicked.connect(self.deploy_latest_backup)
        restore_layout.addWidget(self.deploy_latest_btn)
        
        manage_layout.addLayout(restore_layout)
        
        manage_group.setLayout(manage_layout)
        layout.addWidget(manage_group)
        
        # Backups table
        table_group = QGroupBox("Backup History")
        table_layout = QVBoxLayout()
        
        self.backups_table = QTableWidget()
        self.backups_table.setColumnCount(4)
        self.backups_table.setHorizontalHeaderLabels([
            "Name",
            "Created",
            "Size",
            "Actions"
        ])
        table_layout.addWidget(self.backups_table)
        
        table_group.setLayout(table_layout)
        layout.addWidget(table_group)
        
        # Activity log
        self.activity_log = LogsViewer()
        activity_group = QGroupBox("Backup Activity")
        activity_layout = QVBoxLayout()
        activity_layout.addWidget(self.activity_log)
        activity_group.setLayout(activity_layout)
        layout.addWidget(activity_group, 1)
        
        self.setLayout(layout)

    def refresh_backup_list(self) -> None:
        """Refresh list of available backups."""
        try:
            backups = self.server_manager.list_backups()
            self.backups_combo.clear()
            
            for backup in backups:
                self.backups_combo.addItem(backup["name"], backup)
            
            # Update table
            self.backups_table.setRowCount(len(backups))
            for row, backup in enumerate(backups):
                name_item = QTableWidgetItem(backup["name"])
                created_item = QTableWidgetItem(backup.get("created", "-"))
                size_item = QTableWidgetItem(backup.get("size", "-"))
                
                for item in [name_item, created_item, size_item]:
                    item.setFlags(item.flags() ^ Qt.ItemIsEditable)
                
                self.backups_table.setItem(row, 0, name_item)
                self.backups_table.setItem(row, 1, created_item)
                self.backups_table.setItem(row, 2, size_item)
                
                # Action buttons
                btn_widget = QWidget()
                btn_layout = QHBoxLayout()
                btn_layout.setContentsMargins(0, 0, 0, 0)
                
                delete_btn = QPushButton("Delete")
                delete_btn.setMaximumWidth(70)
                delete_btn.clicked.connect(lambda checked, r=row: self.delete_backup(r))
                btn_layout.addWidget(delete_btn)
                
                btn_widget.setLayout(btn_layout)
                self.backups_table.setCellWidget(row, 3, btn_widget)
            
            self.activity_log.append("✓ Backup list refreshed")
        except Exception as e:
            self.activity_log.append(f"✗ Error refreshing backups: {e}")

    def create_backup(self) -> None:
        """Create a new backup."""
        custom_name = self.backup_name.text().strip()
        
        def do_backup(progress_callback):
            progress_callback(f"Creating backup{' (custom name)' if custom_name else ''}...")
            result = self.server_manager.backup_world(custom_name=custom_name if custom_name else None)
            progress_callback("Backup created successfully")
            return result
        
        self.worker = BackupWorker(do_backup, "Backup created")
        self.worker.progress.connect(self.activity_log.append)
        self.worker.finished.connect(self.on_backup_finished)
        self.worker.start()
        
        self.backup_name.clear()

    def deploy_selected_backup(self) -> None:
        """Deploy the selected backup."""
        if self.backups_combo.currentIndex() < 0:
            QMessageBox.warning(self, "Selection", "Please select a backup to deploy")
            return
        
        backup = self.backups_combo.currentData()
        backup_name = backup["name"]
        
        reply = QMessageBox.question(
            self,
            "Restore Backup",
            f"Restore backup '{backup_name}'? Server will be stopped.",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        def do_restore(progress_callback):
            progress_callback(f"Stopping server...")
            self.server_manager.stop_server()
            progress_callback(f"Restoring backup '{backup_name}'...")
            result = self.server_manager.restore_backup(backup_name)
            progress_callback("Backup restored successfully")
            return result
        
        self.worker = BackupWorker(do_restore, "Backup restored")
        self.worker.progress.connect(self.activity_log.append)
        self.worker.finished.connect(self.on_restore_finished)
        self.worker.start()

    def deploy_latest_backup(self) -> None:
        """Deploy the latest backup."""
        backups = self.server_manager.list_backups()
        if not backups:
            QMessageBox.warning(self, "Backups", "No backups available")
            return
        
        latest = backups[0]
        
        reply = QMessageBox.question(
            self,
            "Restore Latest Backup",
            f"Restore latest backup '{latest['name']}'? Server will be stopped.",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        def do_restore(progress_callback):
            progress_callback("Stopping server...")
            self.server_manager.stop_server()
            progress_callback(f"Restoring latest backup...")
            result = self.server_manager.restore_backup(latest["name"])
            progress_callback("Latest backup restored successfully")
            return result
        
        self.worker = BackupWorker(do_restore, "Latest backup restored")
        self.worker.progress.connect(self.activity_log.append)
        self.worker.finished.connect(self.on_restore_finished)
        self.worker.start()

    def delete_backup(self, row: int) -> None:
        """Delete a backup."""
        if row < 0:
            return
        
        backup_name = self.backups_table.item(row, 0).text()
        
        reply = QMessageBox.question(
            self,
            "Delete Backup",
            f"Delete backup '{backup_name}' permanently?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                self.server_manager.delete_backup(backup_name)
                self.activity_log.append(f"✓ Backup '{backup_name}' deleted")
                self.refresh_backup_list()
            except Exception as e:
                self.activity_log.append(f"✗ Error deleting backup: {e}")

    def on_backup_finished(self, success: bool, message: str) -> None:
        """Handle backup completion."""
        if success:
            self.activity_log.append(f"✓ {message}")
            self.refresh_backup_list()
            QMessageBox.information(self, "Success", message)
        else:
            self.activity_log.append(f"✗ {message}")
            QMessageBox.warning(self, "Error", message)

    def on_restore_finished(self, success: bool, message: str) -> None:
        """Handle restore completion."""
        if success:
            self.activity_log.append(f"✓ {message}")
            self.refresh_backup_list()
            QMessageBox.information(self, "Success", message)
        else:
            self.activity_log.append(f"✗ {message}")
            QMessageBox.warning(self, "Error", message)
