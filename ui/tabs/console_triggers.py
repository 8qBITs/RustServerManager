"""
Console Triggers UI - manage console triggers and webhooks.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox,
    QPushButton, QTableWidget, QTableWidgetItem, QDialog, QLineEdit,
    QTextEdit, QComboBox, QMessageBox, QSpinBox, QCheckBox, QFormLayout
)
from PySide6.QtCore import Qt
from typing import Optional
import re
from config.trigger_templates import get_all_template_names, create_trigger_from_template


class TriggerEditorDialog(QDialog):
    """Dialog for creating/editing console triggers."""

    def __init__(self, trigger_dict: Optional[dict] = None, parent=None):
        super().__init__(parent)
        self.trigger_dict = trigger_dict or {}
        self.setWindowTitle("Console Trigger")
        self.setMinimumWidth(600)
        self.init_ui()
        self.load_trigger()

    def init_ui(self) -> None:
        """Initialize UI."""
        layout = QFormLayout()

        # Name
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("e.g., Player Join, Chat Message")
        layout.addRow("Trigger Name:", self.name_input)

        # Enabled
        self.enabled_check = QCheckBox("Enabled")
        self.enabled_check.setChecked(True)
        layout.addRow("Status:", self.enabled_check)

        # Pattern (Regex)
        pattern_group = QGroupBox("Regex Pattern")
        pattern_layout = QVBoxLayout()
        self.pattern_input = QTextEdit()
        self.pattern_input.setPlaceholderText('Example: (\\w+) joined the game\nGroups can be referenced as {0}, {1}, etc in message template')
        self.pattern_input.setMaximumHeight(80)
        pattern_layout.addWidget(self.pattern_input)

        # Pattern test
        test_layout = QHBoxLayout()
        test_layout.addWidget(QLabel("Test pattern:"))
        self.test_input = QLineEdit()
        self.test_input.setPlaceholderText("Enter test text")
        test_layout.addWidget(self.test_input)
        self.test_btn = QPushButton("Test")
        self.test_btn.clicked.connect(self.test_pattern)
        test_layout.addWidget(self.test_btn)
        self.test_result = QLabel("")
        test_layout.addWidget(self.test_result)
        pattern_layout.addLayout(test_layout)

        pattern_group.setLayout(pattern_layout)
        layout.addRow(pattern_group)

        # Message template
        layout.addRow(QLabel("Message Template:"))
        self.message_input = QTextEdit()
        self.message_input.setPlaceholderText('Use {0}, {1}, etc for captured groups\nExample: Player {0} joined the server')
        self.message_input.setMaximumHeight(80)
        layout.addRow(self.message_input)

        # Webhook type
        self.webhook_type_combo = QComboBox()
        self.webhook_type_combo.addItem("Discord", "discord")
        self.webhook_type_combo.addItem("Generic JSON", "generic")
        layout.addRow("Webhook Type:", self.webhook_type_combo)

        # Webhook URL
        self.webhook_url_input = QLineEdit()
        self.webhook_url_input.setPlaceholderText("https://discord.com/api/webhooks/...")
        layout.addRow("Webhook URL:", self.webhook_url_input)

        # Discord embed color (for Discord webhooks)
        self.color_input = QLineEdit()
        self.color_input.setPlaceholderText("3498db (default blue), or any hex color without #")
        self.color_input.setText("3498db")
        layout.addRow("Embed Color:", self.color_input)

        # Buttons
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("💾 Save")
        save_btn.clicked.connect(self.accept)
        btn_layout.addWidget(save_btn)

        cancel_btn = QPushButton("✕ Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        layout.addRow(btn_layout)

        self.setLayout(layout)

    def load_trigger(self) -> None:
        """Load trigger data into UI."""
        self.name_input.setText(self.trigger_dict.get("name", ""))
        self.enabled_check.setChecked(self.trigger_dict.get("enabled", True))
        self.pattern_input.setText(self.trigger_dict.get("pattern", ""))
        self.message_input.setText(self.trigger_dict.get("message_template", ""))
        self.webhook_type_combo.setCurrentText(self.trigger_dict.get("webhook_type", "discord").capitalize())
        self.webhook_url_input.setText(self.trigger_dict.get("webhook_url", ""))
        self.color_input.setText(self.trigger_dict.get("embed_color", "3498db"))

    def test_pattern(self) -> None:
        """Test regex pattern."""
        pattern = self.pattern_input.toPlainText().strip()
        test_text = self.test_input.text().strip()

        if not pattern:
            self.test_result.setText("❌ Empty pattern")
            self.test_result.setStyleSheet("color: red;")
            return

        if not test_text:
            self.test_result.setText("❌ Empty test text")
            self.test_result.setStyleSheet("color: red;")
            return

        try:
            regex = re.compile(pattern)
            match = regex.search(test_text)
            if match:
                groups = match.groups()
                self.test_result.setText(f"✅ Match! Groups: {groups}")
                self.test_result.setStyleSheet("color: green;")
            else:
                self.test_result.setText("❌ No match")
                self.test_result.setStyleSheet("color: orange;")
        except re.error as e:
            self.test_result.setText(f"❌ Invalid regex: {e}")
            self.test_result.setStyleSheet("color: red;")

    def get_trigger(self) -> dict:
        """Get trigger dictionary from UI."""
        return {
            "name": self.name_input.text().strip(),
            "enabled": self.enabled_check.isChecked(),
            "pattern": self.pattern_input.toPlainText().strip(),
            "message_template": self.message_input.toPlainText().strip(),
            "webhook_type": self.webhook_type_combo.currentData(),
            "webhook_url": self.webhook_url_input.text().strip(),
            "embed_color": self.color_input.text().strip(),
        }

    def accept(self) -> None:
        """Validate and accept."""
        trigger = self.get_trigger()

        if not trigger["name"]:
            QMessageBox.warning(self, "Validation", "Trigger name is required")
            return

        if not trigger["pattern"]:
            QMessageBox.warning(self, "Validation", "Regex pattern is required")
            return

        try:
            re.compile(trigger["pattern"])
        except re.error as e:
            QMessageBox.warning(self, "Validation", f"Invalid regex pattern: {e}")
            return

        if not trigger["webhook_url"]:
            QMessageBox.warning(self, "Validation", "Webhook URL is required")
            return

        if not trigger["message_template"]:
            QMessageBox.warning(self, "Validation", "Message template is required")
            return

        super().accept()


class ConsoleTriggersWidget(QWidget):
    """Widget for managing console triggers."""

    def __init__(self, config_manager, server_manager, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.server_manager = server_manager
        self.init_ui()
        self.load_triggers()

    def init_ui(self) -> None:
        """Initialize UI."""
        layout = QVBoxLayout()

        # Header
        header_layout = QHBoxLayout()
        header_layout.addWidget(QLabel("Console Triggers: Monitor logs and send webhooks"))
        header_layout.addStretch()
        layout.addLayout(header_layout)

        # Triggers table
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(
            ["Name", "Pattern", "Enabled", "Matches", "Last Match", "Actions"]
        )
        self.table.horizontalHeader().setStretchLastSection(False)
        self.table.setColumnWidth(1, 300)
        layout.addWidget(self.table)

        # Controls
        control_layout = QHBoxLayout()

        add_btn = QPushButton("➕ Add Trigger")
        add_btn.clicked.connect(self.add_trigger)
        control_layout.addWidget(add_btn)

        template_btn = QPushButton("📋 Add from Template")
        template_btn.clicked.connect(self.add_from_template)
        control_layout.addWidget(template_btn)

        edit_btn = QPushButton("✏️ Edit")
        edit_btn.clicked.connect(self.edit_trigger)
        control_layout.addWidget(edit_btn)

        delete_btn = QPushButton("🗑️ Delete")
        delete_btn.clicked.connect(self.delete_trigger)
        control_layout.addWidget(delete_btn)

        control_layout.addStretch()

        reload_btn = QPushButton("🔄 Reload")
        reload_btn.clicked.connect(self.reload_triggers)
        control_layout.addWidget(reload_btn)

        layout.addLayout(control_layout)

        self.setLayout(layout)

    def load_triggers(self) -> None:
        """Load triggers from config."""
        cfg = self.config_manager.get_config()
        triggers = cfg.automation.console_triggers

        self.table.setRowCount(len(triggers))

        for row, trigger_dict in enumerate(triggers):
            name_item = QTableWidgetItem(trigger_dict.get("name", ""))
            pattern_item = QTableWidgetItem(trigger_dict.get("pattern", "")[:50])
            enabled_item = QTableWidgetItem("✓" if trigger_dict.get("enabled", True) else "✗")
            matches_item = QTableWidgetItem("0")
            last_match_item = QTableWidgetItem("-")

            # Make read-only
            for item in [name_item, pattern_item, enabled_item, matches_item, last_match_item]:
                item.setFlags(item.flags() ^ Qt.ItemIsEditable)

            self.table.setItem(row, 0, name_item)
            self.table.setItem(row, 1, pattern_item)
            self.table.setItem(row, 2, enabled_item)
            self.table.setItem(row, 3, matches_item)
            self.table.setItem(row, 4, last_match_item)

            # Actions column
            btn_widget = QWidget()
            btn_layout = QHBoxLayout()
            btn_layout.setContentsMargins(0, 0, 0, 0)

            test_btn = QPushButton("Test")
            test_btn.setMaximumWidth(60)
            test_btn.clicked.connect(lambda checked, r=row: self.test_trigger(r))
            btn_layout.addWidget(test_btn)

            btn_widget.setLayout(btn_layout)
            self.table.setCellWidget(row, 5, btn_widget)
            
            # Update statistics if engine is loaded
            if hasattr(self.server_manager, 'triggers_engine'):
                stats = self.server_manager.triggers_engine.get_trigger_stats()
                if row < len(stats):
                    stat = stats[row]
                    matches_item.setText(str(stat['match_count']))
                    last_match_item.setText(stat['last_match'] or "-")

    def add_trigger(self) -> None:
        """Add new trigger."""
        dialog = TriggerEditorDialog(parent=self)
        if dialog.exec():
            cfg = self.config_manager.get_config()
            cfg.automation.console_triggers.append(dialog.get_trigger())
            self.config_manager.save_config()
            self.load_triggers()
            self.server_manager.load_console_triggers()

    def add_from_template(self) -> None:
        """Add a trigger from predefined templates."""
        template_names = get_all_template_names()
        
        if not template_names:
            QMessageBox.warning(self, "Templates", "No templates available")
            return
        
        # Simple selection dialog
        dialog = QDialog(self)
        dialog.setWindowTitle("Select Trigger Template")
        layout = QVBoxLayout()
        
        layout.addWidget(QLabel("Choose a template to load:"))
        
        combo = QComboBox()
        combo.addItems(template_names)
        layout.addWidget(combo)
        
        # Webhook URL input
        layout.addWidget(QLabel("Webhook URL:"))
        webhook_input = QLineEdit()
        webhook_input.setPlaceholderText("https://discord.com/api/webhooks/...")
        layout.addWidget(webhook_input)
        
        # Buttons
        btn_layout = QHBoxLayout()
        load_btn = QPushButton("Load Template")
        cancel_btn = QPushButton("Cancel")
        btn_layout.addWidget(load_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)
        
        dialog.setLayout(layout)
        
        def load_template():
            template_name = combo.currentText()
            webhook_url = webhook_input.text().strip()
            
            if not webhook_url:
                QMessageBox.warning(dialog, "Validation", "Webhook URL is required")
                return
            
            trigger = create_trigger_from_template(template_name, webhook_url)
            if trigger:
                cfg = self.config_manager.get_config()
                cfg.automation.console_triggers.append(trigger)
                self.config_manager.save_config()
                self.load_triggers()
                self.server_manager.load_console_triggers()
                dialog.accept()
        
        load_btn.clicked.connect(load_template)
        cancel_btn.clicked.connect(dialog.reject)
        
        dialog.exec()

    def edit_trigger(self) -> None:
        """Edit selected trigger."""
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Selection", "Please select a trigger to edit")
            return

        cfg = self.config_manager.get_config()
        trigger_dict = cfg.automation.console_triggers[row]

        dialog = TriggerEditorDialog(trigger_dict, parent=self)
        if dialog.exec():
            cfg.automation.console_triggers[row] = dialog.get_trigger()
            self.config_manager.save_config()
            self.load_triggers()
            self.server_manager.load_console_triggers()

    def delete_trigger(self) -> None:
        """Delete selected trigger."""
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Selection", "Please select a trigger to delete")
            return

        reply = QMessageBox.question(
            self, "Confirm Delete", "Delete this trigger?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            cfg = self.config_manager.get_config()
            del cfg.automation.console_triggers[row]
            self.config_manager.save_config()
            self.load_triggers()
            self.server_manager.load_console_triggers()

    def test_trigger(self, row: int) -> None:
        """Test a trigger (show stats)."""
        stats = self.server_manager.triggers_engine.get_trigger_stats()
        if row < len(stats):
            stat = stats[row]
            msg = f"""
Trigger: {stat['name']}
Matches: {stat['match_count']}
Last Match: {stat['last_match'] or 'Never'}
            """
            QMessageBox.information(self, "Trigger Stats", msg.strip())

    def reload_triggers(self) -> None:
        """Reload triggers from file."""
        self.config_manager.load()
        self.server_manager.load_console_triggers()
        self.load_triggers()
        QMessageBox.information(self, "Reloaded", "Triggers reloaded from configuration")
