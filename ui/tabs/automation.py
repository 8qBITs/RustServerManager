"""Automation tab - schedule builder with internal subtabs for scheduler and console triggers."""

from datetime import datetime
from typing import Callable, Optional

from PySide6.QtCore import Qt, QThread, Signal, QTime, QTimer
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QGroupBox,
    QPushButton,
    QGridLayout,
    QTableWidget,
    QTableWidgetItem,
    QLineEdit,
    QComboBox,
    QSpinBox,
    QTimeEdit,
    QCheckBox,
    QMessageBox,
    QListWidget,
    QListWidgetItem,
    QTabWidget,
    QScrollArea,
    QFrame,
)

from ui.widgets.widgets import LogsViewer
from ui.tabs.console_triggers import ConsoleTriggersWidget
from ui.tabs.backups import BackupsTab


class AutomationWorker(QThread):
    """Background worker for automation actions triggered from UI."""

    progress = Signal(str)
    finished = Signal(bool, str)

    def __init__(self, operation: Callable[[Callable[[str], None]], bool], done_message: str):
        super().__init__()
        self.operation = operation
        self.done_message = done_message

    def run(self) -> None:
        try:
            result = self.operation(self.progress.emit)
            self.finished.emit(bool(result), self.done_message if result else "Operation failed")
        except Exception as e:
            self.finished.emit(False, f"Error: {e}")


class AutomationTab(QWidget):
    """Automation control panel with scheduler and console triggers as subtabs."""

    activity_signal = Signal(str)

    ACTIONS = {
        "start": "Start Server",
        "stop": "Stop Server",
        "restart": "Restart Server",
        "save": "Save Server",
        "backup": "Create Backup",
        "restore_latest_backup": "Restore Latest Backup",
        "wipe": "Wipe World",
        "wipebp": "Wipe Blueprints",
        "install_rust": "Install/Update Rust Server",
        "install_oxide": "Install/Update Oxide",
        "install_rustedit": "Install/Update RustEdit",
        "check_wan": "Check WAN Accessibility",
        "cleanup_backups": "Clean Old Backups",
    }
    
    STEP_TYPES = {
        "action": "Server Action",
        "delay": "Wait/Delay",
        "message": "Send Message",
        "conditional": "Conditional Check",
    }

    def __init__(self, task_scheduler, config_manager, server_manager, parent=None):
        super().__init__(parent)
        self.task_scheduler = task_scheduler
        self.config_manager = config_manager
        self.server_manager = server_manager
        self.worker: Optional[AutomationWorker] = None
        self.custom_schedules: list[dict] = []
        self.task_steps: list[dict] = []  # Current task being built
        self.activity_signal.connect(self.append_activity)

        self.init_ui()
        self.load_custom_schedules()
        self.refresh_job_status()

        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.refresh_job_status)
        self.status_timer.start(3000)

    def init_ui(self) -> None:
        """Initialize UI with subtabs."""
        layout = QVBoxLayout()

        # Create subtabs for all features
        self.subtabs = QTabWidget()

        # Settings subtab (toggles + activity console)
        settings_subtab = self.create_settings_subtab()
        self.settings_tab_idx = self.subtabs.addTab(settings_subtab, "⚙️ Settings")

        # Scheduler subtab
        scheduler_subtab = self.create_scheduler_subtab()
        self.scheduler_tab_idx = self.subtabs.addTab(scheduler_subtab, "📅 Scheduler")

        # Console Triggers subtab
        triggers_subtab = QWidget()
        triggers_layout_widget = QVBoxLayout()
        self.console_triggers_widget = ConsoleTriggersWidget(
            self.config_manager,
            self.server_manager,
            parent=self
        )
        triggers_layout_widget.addWidget(self.console_triggers_widget)
        triggers_subtab.setLayout(triggers_layout_widget)
        self.triggers_tab_idx = self.subtabs.addTab(triggers_subtab, "🔔 Console Triggers")

        # Backups subtab
        self.backups_subtab = BackupsTab(self.server_manager, self.config_manager, parent=self)
        self.backups_tab_idx = self.subtabs.addTab(self.backups_subtab, "📦 Backups")

        layout.addWidget(self.subtabs)
        self.setLayout(layout)

    def create_settings_subtab(self) -> QWidget:
        """Create settings subtab with feature toggles and activity console."""
        widget = QWidget()
        layout = QVBoxLayout()

        # Feature toggles
        toggles_group = QGroupBox("Automation Features")
        toggles_layout = QHBoxLayout()

        toggles_layout.addWidget(QLabel("Enable Features:"))

        self.scheduler_toggle = QCheckBox("📅 Scheduler")
        self.scheduler_toggle.setChecked(True)
        self.scheduler_toggle.stateChanged.connect(self.on_feature_toggled)
        toggles_layout.addWidget(self.scheduler_toggle)

        self.triggers_toggle = QCheckBox("🔔 Console Triggers")
        self.triggers_toggle.setChecked(True)
        self.triggers_toggle.stateChanged.connect(self.on_feature_toggled)
        toggles_layout.addWidget(self.triggers_toggle)

        self.backups_toggle = QCheckBox("📦 Backups")
        self.backups_toggle.setChecked(True)
        self.backups_toggle.stateChanged.connect(self.on_feature_toggled)
        toggles_layout.addWidget(self.backups_toggle)

        toggles_layout.addStretch()
        toggles_group.setLayout(toggles_layout)
        layout.addWidget(toggles_group)

        # Activity console - main content area
        activity_group = QGroupBox("Automation Activity Console")
        activity_layout = QVBoxLayout()
        
        self.activity_log = LogsViewer()
        activity_layout.addWidget(self.activity_log)
        
        activity_group.setLayout(activity_layout)
        layout.addWidget(activity_group, 1)

        widget.setLayout(layout)
        return widget

    def on_feature_toggled(self) -> None:
        """Handle feature toggle - show/hide tabs based on enabled features."""
        # Update tab visibility
        self.subtabs.setTabVisible(self.scheduler_tab_idx, self.scheduler_toggle.isChecked())
        self.subtabs.setTabVisible(self.triggers_tab_idx, self.triggers_toggle.isChecked())
        self.subtabs.setTabVisible(self.backups_tab_idx, self.backups_toggle.isChecked())
        
        # Log the change
        features = []
        if self.scheduler_toggle.isChecked():
            features.append("Scheduler")
        if self.triggers_toggle.isChecked():
            features.append("Console Triggers")
        if self.backups_toggle.isChecked():
            features.append("Backups")
        
        enabled_text = ", ".join(features) if features else "None"
        self._log(f"Enabled features: {enabled_text}")

    def create_scheduler_subtab(self) -> QWidget:
        """Create scheduler subtab content."""
        widget = QWidget()
        layout = QVBoxLayout()

        control_group = QGroupBox("Scheduler Control")
        control_layout = QHBoxLayout()

        self.pause_btn = QPushButton("⏸ Pause All Tasks")
        self.pause_btn.clicked.connect(self.pause_scheduler)
        control_layout.addWidget(self.pause_btn)

        self.resume_btn = QPushButton("▶ Resume All Tasks")
        self.resume_btn.clicked.connect(self.resume_scheduler)
        control_layout.addWidget(self.resume_btn)

        control_layout.addStretch()
        control_group.setLayout(control_layout)
        layout.addWidget(control_group)

        builder_group = QGroupBox("Schedule Builder")
        builder_layout = QGridLayout()

        builder_layout.addWidget(QLabel("Schedule Name:"), 0, 0)
        self.schedule_name = QLineEdit()
        self.schedule_name.setPlaceholderText("e.g. nightly_maintenance")
        builder_layout.addWidget(self.schedule_name, 0, 1, 1, 3)

        builder_layout.addWidget(QLabel("Trigger Type:"), 1, 0)
        self.trigger_type = QComboBox()
        self.trigger_type.addItems(["Interval", "Daily"])
        self.trigger_type.currentTextChanged.connect(self.on_trigger_changed)
        builder_layout.addWidget(self.trigger_type, 1, 1)

        builder_layout.addWidget(QLabel("Interval (minutes):"), 1, 2)
        self.interval_minutes = QSpinBox()
        self.interval_minutes.setRange(1, 10080)
        self.interval_minutes.setValue(60)
        builder_layout.addWidget(self.interval_minutes, 1, 3)

        builder_layout.addWidget(QLabel("Daily Time:"), 2, 0)
        self.daily_time = QTimeEdit()
        self.daily_time.setDisplayFormat("HH:mm")
        self.daily_time.setTime(QTime(3, 0))
        builder_layout.addWidget(self.daily_time, 2, 1)

        # Task Steps Builder
        steps_group = QGroupBox("Task Steps (executed in order)")
        steps_layout = QVBoxLayout()
        
        # Step controls
        step_controls = QHBoxLayout()
        
        step_controls.addWidget(QLabel("Step Type:"))
        self.step_type_combo = QComboBox()
        self.step_type_combo.addItems(["Server Action", "Wait/Delay", "Send Message", "Conditional Check"])
        self.step_type_combo.currentTextChanged.connect(self.on_step_type_changed)
        step_controls.addWidget(self.step_type_combo)
        
        # Action selector (for action type)
        self.action_combo = QComboBox()
        for action_key, action_label in self.ACTIONS.items():
            self.action_combo.addItem(action_label, action_key)
        step_controls.addWidget(self.action_combo)
        
        # Conditional selector (for conditional type)
        self.condition_combo = QComboBox()
        self.condition_combo.addItem("If Server Running", "if_running")
        self.condition_combo.addItem("If Server Stopped", "if_stopped")
        self.condition_combo.addItem("If Players Online", "if_players")
        self.condition_combo.addItem("If No Players", "if_no_players")
        self.condition_combo.setVisible(False)
        step_controls.addWidget(self.condition_combo)
        
        # Delay input (for delay type)
        self.delay_input = QSpinBox()
        self.delay_input.setRange(1, 3600)
        self.delay_input.setValue(30)
        self.delay_input.setSuffix(" seconds")
        self.delay_input.setVisible(False)
        step_controls.addWidget(self.delay_input)
        
        # Message input (for message type)
        self.message_input = QLineEdit()
        self.message_input.setPlaceholderText("Message to broadcast")
        self.message_input.setVisible(False)
        step_controls.addWidget(self.message_input)
        
        add_step_btn = QPushButton("➕ Add Step")
        add_step_btn.clicked.connect(self.add_task_step)
        step_controls.addWidget(add_step_btn)
        
        steps_layout.addLayout(step_controls)
        
        # Steps list
        self.steps_list = QListWidget()
        self.steps_list.setMaximumHeight(150)
        steps_layout.addWidget(self.steps_list)
        
        # List controls
        list_controls = QHBoxLayout()
        
        move_up_btn = QPushButton("⬆ Move Up")
        move_up_btn.clicked.connect(self.move_step_up)
        list_controls.addWidget(move_up_btn)
        
        move_down_btn = QPushButton("⬇ Move Down")
        move_down_btn.clicked.connect(self.move_step_down)
        list_controls.addWidget(move_down_btn)
        
        remove_step_btn = QPushButton("❌ Remove Step")
        remove_step_btn.clicked.connect(self.remove_task_step)
        list_controls.addWidget(remove_step_btn)
        
        clear_steps_btn = QPushButton("🗑 Clear All")
        clear_steps_btn.clicked.connect(self.clear_task_steps)
        list_controls.addWidget(clear_steps_btn)
        
        steps_layout.addLayout(list_controls)
        steps_group.setLayout(steps_layout)
        builder_layout.addWidget(steps_group, 3, 0, 1, 4)

        self.save_schedule_btn = QPushButton("💾 Save/Update Schedule")
        self.save_schedule_btn.clicked.connect(self.save_schedule)
        builder_layout.addWidget(self.save_schedule_btn, 4, 0)

        self.delete_schedule_btn = QPushButton("🗑 Delete Schedule")
        self.delete_schedule_btn.clicked.connect(self.delete_selected_schedule)
        builder_layout.addWidget(self.delete_schedule_btn, 4, 1)

        self.run_now_btn = QPushButton("▶ Run Selected Now")
        self.run_now_btn.clicked.connect(self.run_selected_now)
        builder_layout.addWidget(self.run_now_btn, 4, 2)

        clear_editor_btn = QPushButton("Clear Editor")
        clear_editor_btn.clicked.connect(self.clear_editor)
        builder_layout.addWidget(clear_editor_btn, 4, 3)

        builder_group.setLayout(builder_layout)
        layout.addWidget(builder_group)

        jobs_group = QGroupBox("Scheduled Jobs")
        jobs_layout = QVBoxLayout()

        self.jobs_table = QTableWidget()
        self.jobs_table.setColumnCount(7)
        self.jobs_table.setHorizontalHeaderLabels([
            "Name",
            "Trigger",
            "Actions",
            "Next Run",
            "Last Run",
            "Status",
            "Enabled",
        ])
        self.jobs_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.jobs_table.setSelectionMode(QTableWidget.SingleSelection)
        self.jobs_table.itemSelectionChanged.connect(self.on_job_selected)
        jobs_layout.addWidget(self.jobs_table)

        jobs_group.setLayout(jobs_layout)
        layout.addWidget(jobs_group)

        widget.setLayout(layout)
        self.on_trigger_changed(self.trigger_type.currentText())
        
        return widget

    def on_step_type_changed(self, step_type: str) -> None:
        """Show/hide inputs based on step type."""
        is_action = step_type == "Server Action"
        is_delay = step_type == "Wait/Delay"
        is_message = step_type == "Send Message"
        is_conditional = step_type == "Conditional Check"
        
        self.action_combo.setVisible(is_action)
        self.delay_input.setVisible(is_delay)
        self.message_input.setVisible(is_message)
        self.condition_combo.setVisible(is_conditional)

    def add_task_step(self) -> None:
        """Add a step to the current task."""
        step_type = self.step_type_combo.currentText()
        
        if step_type == "Server Action":
            action_key = self.action_combo.currentData()
            action_label = self.action_combo.currentText()
            step = {"type": "action", "action": action_key, "label": action_label}
            display = f"🎬 Action: {action_label}"
        elif step_type == "Wait/Delay":
            delay_seconds = self.delay_input.value()
            step = {"type": "delay", "seconds": delay_seconds}
            display = f"⏱️ Wait: {delay_seconds} seconds"
        elif step_type == "Send Message":
            message = self.message_input.text().strip()
            if not message:
                QMessageBox.warning(self, "Validation", "Message cannot be empty")
                return
            step = {"type": "message", "message": message}
            display = f"💬 Message: {message}"
        elif step_type == "Conditional Check":
            condition_key = self.condition_combo.currentData()
            condition_label = self.condition_combo.currentText()
            step = {"type": "conditional", "condition": condition_key, "label": condition_label}
            display = f"❓ {condition_label}"
        else:
            return
        
        self.task_steps.append(step)
        item = QListWidgetItem(display)
        item.setData(Qt.UserRole, step)
        self.steps_list.addItem(item)
        self.message_input.clear()
    
    def move_step_up(self) -> None:
        """Move selected step up in the list."""
        row = self.steps_list.currentRow()
        if row > 0:
            self.task_steps[row], self.task_steps[row - 1] = self.task_steps[row - 1], self.task_steps[row]
            item = self.steps_list.takeItem(row)
            self.steps_list.insertItem(row - 1, item)
            self.steps_list.setCurrentRow(row - 1)
    
    def move_step_down(self) -> None:
        """Move selected step down in the list."""
        row = self.steps_list.currentRow()
        if row >= 0 and row < self.steps_list.count() - 1:
            self.task_steps[row], self.task_steps[row + 1] = self.task_steps[row + 1], self.task_steps[row]
            item = self.steps_list.takeItem(row)
            self.steps_list.insertItem(row + 1, item)
            self.steps_list.setCurrentRow(row + 1)
    
    def remove_task_step(self) -> None:
        """Remove selected step from the list."""
        row = self.steps_list.currentRow()
        if row >= 0:
            self.task_steps.pop(row)
            self.steps_list.takeItem(row)
    
    def clear_task_steps(self) -> None:
        """Clear all steps."""
        self.task_steps.clear()
        self.steps_list.clear()

    def on_trigger_changed(self, trigger_text: str) -> None:
        is_interval = trigger_text == "Interval"
        self.interval_minutes.setEnabled(is_interval)
        self.daily_time.setEnabled(not is_interval)
    
    def clear_editor(self) -> None:
        """Clear the schedule editor."""
        self.schedule_name.clear()
        self.clear_task_steps()
        self.trigger_type.setCurrentIndex(0)
        self.interval_minutes.setValue(60)
        self.daily_time.setTime(QTime(3, 0))

    def _log(self, message: str) -> None:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.activity_signal.emit(f"[{timestamp}] {message}")

    def append_activity(self, message: str) -> None:
        self.activity_log.log(message)

    def _steps_to_legacy_actions(self, steps: list[dict]) -> list[str]:
        """Convert steps to simple action list for backward compatibility display."""
        actions = []
        for step in steps:
            if step.get("type") == "action":
                actions.append(step.get("action", "unknown"))
            elif step.get("type") == "delay":
                actions.append(f"wait_{step.get('seconds', 0)}s")
            elif step.get("type") == "message":
                actions.append(f"msg")
        return actions if actions else ["empty"]

    def _job_id(self, schedule_name: str) -> str:
        cleaned = "".join(ch.lower() if ch.isalnum() else "_" for ch in schedule_name.strip())
        while "__" in cleaned:
            cleaned = cleaned.replace("__", "_")
        cleaned = cleaned.strip("_") or "schedule"
        return f"custom_{cleaned}"

    def _current_editor_schedule(self) -> Optional[dict]:
        name = self.schedule_name.text().strip()
        if not name:
            QMessageBox.warning(self, "Validation", "Schedule name is required")
            return None
        if not self.task_steps:
            QMessageBox.warning(self, "Validation", "Add at least one task step")
            return None

        trigger_type = "interval" if self.trigger_type.currentText() == "Interval" else "daily"
        return {
            "job_id": self._job_id(name),
            "name": name,
            "trigger_type": trigger_type,
            "interval_minutes": int(self.interval_minutes.value()),
            "daily_time": self.daily_time.time().toString("HH:mm"),
            "steps": list(self.task_steps),  # Use steps instead of actions
        }

    def save_schedule(self) -> None:
        schedule = self._current_editor_schedule()
        if not schedule:
            return

        self._upsert_schedule(schedule)
        self._persist_schedules()
        self._register_schedule(schedule)
        self.refresh_job_status()
        self._log(f"Saved schedule '{schedule['name']}'")

    def _upsert_schedule(self, schedule: dict) -> None:
        idx = next((i for i, s in enumerate(self.custom_schedules) if s.get("job_id") == schedule["job_id"]), -1)
        if idx >= 0:
            self.custom_schedules[idx] = schedule
        else:
            self.custom_schedules.append(schedule)

    def _persist_schedules(self) -> None:
        self.config_manager.update_config(**{"automation.custom_schedules": self.custom_schedules})

    def _register_schedule(self, schedule: dict) -> None:
        def callback() -> bool:
            # Format step summary for logging
            step_summary = ", ".join([self._format_step_for_log(s) for s in schedule.get('steps', [])])
            self.server_manager.emit_console_output(
                f"[SCHEDULE] Triggered {schedule['name']} -> {step_summary}"
            )
            self._log(f"Triggered schedule '{schedule['name']}'")
            return self.server_manager.run_task_steps(schedule.get("steps", []), self.server_manager.emit_console_output)

        self.task_scheduler.schedule_custom_task(
            callback=callback,
            job_id=schedule["job_id"],
            name=schedule["name"],
            trigger_type=schedule["trigger_type"],
            interval_minutes=schedule["interval_minutes"],
            daily_time=schedule["daily_time"],
        )
    
    def _format_step_for_log(self, step: dict) -> str:
        """Format a step for logging."""
        if step.get("type") == "action":
            return step.get("label", step.get("action", "?"))
        elif step.get("type") == "delay":
            return f"wait {step.get('seconds', 0)}s"
        elif step.get("type") == "message":
            return f"msg: {step.get('message', '')[:20]}"
        return "unknown"

    def load_custom_schedules(self) -> None:
        cfg = self.config_manager.get_config()
        loaded = list(cfg.automation.custom_schedules or [])
        self.custom_schedules = []
        for entry in loaded:
            if not isinstance(entry, dict):
                continue
            if not entry.get("job_id"):
                entry["job_id"] = self._job_id(entry.get("name", "schedule"))
            
            # Convert old "actions" format to new "steps" format
            if "actions" in entry and "steps" not in entry:
                steps = []
                for action in entry.get("actions", []):
                    if isinstance(action, str):
                        steps.append({"type": "action", "action": action, "label": self.ACTIONS.get(action, action)})
                entry["steps"] = steps
            
            if "steps" not in entry:
                entry["steps"] = [{"type": "action", "action": "restart", "label": "Restart Server"}]
            if "trigger_type" not in entry:
                entry["trigger_type"] = "interval"
            if "interval_minutes" not in entry:
                entry["interval_minutes"] = 60
            if "daily_time" not in entry:
                entry["daily_time"] = "03:00"
            if "enabled" not in entry:
                entry["enabled"] = True

            self.custom_schedules.append(entry)
            self._register_schedule(entry)

        if self.custom_schedules:
            self._log(f"Loaded {len(self.custom_schedules)} custom schedule(s)")

    def refresh_job_status(self) -> None:
        jobs = self.task_scheduler.get_scheduled_jobs()
        self.jobs_table.setRowCount(len(jobs))

        for row, job in enumerate(jobs):
            schedule = next((s for s in self.custom_schedules if s.get("job_id") == job.id), None)
            trigger_text = "System"
            actions_text = "-"
            if schedule:
                trigger_text = (
                    f"every {schedule.get('interval_minutes', 60)}m"
                    if schedule.get("trigger_type") == "interval"
                    else f"daily {schedule.get('daily_time', '03:00')}"
                )
                # Display steps summary
                steps =schedule.get("steps", [])
                if steps:
                    step_summary = []
                    for step in steps[:3]:  # Show first 3 steps
                        if step.get("type") == "action":
                            step_summary.append(step.get("label", step.get("action", "?")))
                        elif step.get("type") == "delay":
                            step_summary.append(f"wait {step.get('seconds')}s")
                        elif step.get("type") == "message":
                            step_summary.append("message")
                    actions_text = ", ".join(step_summary)
                    if len(steps) > 3:
                        actions_text += f" (+{len(steps)-3} more)"
                else:
                    actions_text = "no steps"

            self.jobs_table.setItem(row, 0, QTableWidgetItem(job.name or job.id))
            self.jobs_table.item(row, 0).setData(Qt.UserRole, job.id)
            self.jobs_table.setItem(row, 1, QTableWidgetItem(trigger_text))
            self.jobs_table.setItem(row, 2, QTableWidgetItem(actions_text))

            next_run = job.next_run_time.strftime("%Y-%m-%d %H:%M:%S") if job.next_run_time else "N/A"
            self.jobs_table.setItem(row, 3, QTableWidgetItem(next_run))

            last_run = self.task_scheduler.last_run_times.get(job.id)
            last_run_text = last_run.strftime("%Y-%m-%d %H:%M:%S") if last_run else "Never"
            self.jobs_table.setItem(row, 4, QTableWidgetItem(last_run_text))

            status_info = self.task_scheduler.task_status.get(job.id, {})
            status = status_info.get("status", "scheduled")
            status_item = QTableWidgetItem(status)
            if status == "completed":
                status_item.setForeground(Qt.green)
            elif status == "running":
                status_item.setForeground(Qt.blue)
            elif status == "failed":
                status_item.setForeground(Qt.red)
            self.jobs_table.setItem(row, 5, status_item)

            # Enabled switch in column 6
            enabled_widget = QWidget()
            enabled_layout = QHBoxLayout()
            enabled_layout.setContentsMargins(0, 0, 0, 0)
            
            enabled_check = QCheckBox()
            enabled_check.setChecked(schedule.get("enabled", True) if schedule else True)
            enabled_check.stateChanged.connect(lambda state, job_id=job.id, r=row: self.on_job_enabled_toggled(job_id, state))
            enabled_layout.addWidget(enabled_check)
            enabled_layout.addStretch()
            enabled_widget.setLayout(enabled_layout)
            self.jobs_table.setCellWidget(row, 6, enabled_widget)

    def on_job_selected(self) -> None:
        selected = self.jobs_table.selectedItems()
        if not selected:
            return

        row = selected[0].row()
        id_item = self.jobs_table.item(row, 0)
        if not id_item:
            return

        job_id = id_item.data(Qt.UserRole)
        schedule = next((s for s in self.custom_schedules if s.get("job_id") == job_id), None)
        if not schedule:
            return

        # Load schedule into editor
        self.schedule_name.setText(schedule.get("name", ""))
        self.trigger_type.setCurrentText("Interval" if schedule.get("trigger_type") == "interval" else "Daily")
        self.interval_minutes.setValue(int(schedule.get("interval_minutes", 60)))

        hhmm = schedule.get("daily_time", "03:00")
        try:
            hour, minute = hhmm.split(":", maxsplit=1)
            self.daily_time.setTime(QTime(int(hour), int(minute)))
        except Exception:
            self.daily_time.setTime(QTime(3, 0))

        # Load steps into task builder
        self.clear_task_steps()
        for step in schedule.get("steps", []):
            self.task_steps.append(step)
            if step.get("type") == "action":
                display = f"🎬 Action: {step.get('label', step.get('action', '?'))}"
            elif step.get("type") == "delay":
                display = f"⏱️ Wait: {step.get('seconds', 0)} seconds"
            elif step.get("type") == "message":
                display = f"💬 Message: {step.get('message', '')}"
            else:
                display = f"Unknown: {step}"
            item = QListWidgetItem(display)
            item.setData(Qt.UserRole, step)
            self.steps_list.addItem(item)

    def on_job_enabled_toggled(self, job_id: str, state: int) -> None:
        """Handle job enabled/disabled toggle."""
        is_enabled = state == Qt.Checked
        
        # Find and update the schedule
        schedule = next((s for s in self.custom_schedules if s.get("job_id") == job_id), None)
        if schedule:
            schedule["enabled"] = is_enabled
            self._persist_schedules()
            self._log(f"Schedule '{schedule.get('name')}' is now {'enabled' if is_enabled else 'disabled'}")

    def delete_selected_schedule(self) -> None:
        selected = self.jobs_table.selectedItems()
        if not selected:
            QMessageBox.information(self, "Delete Schedule", "Select a custom schedule to delete.")
            return

        row = selected[0].row()
        id_item = self.jobs_table.item(row, 0)
        if not id_item:
            return

        job_id = id_item.data(Qt.UserRole)
        schedule = next((s for s in self.custom_schedules if s.get("job_id") == job_id), None)
        if not schedule:
            QMessageBox.information(self, "Delete Schedule", "Only custom schedules can be deleted here.")
            return

        self.task_scheduler.unschedule_job(job_id)
        self.custom_schedules = [s for s in self.custom_schedules if s.get("job_id") != job_id]
        self._persist_schedules()
        self.refresh_job_status()
        self._log(f"Deleted schedule '{schedule.get('name', job_id)}'")

    def run_selected_now(self) -> None:
        selected = self.jobs_table.selectedItems()
        if not selected:
            QMessageBox.information(self, "Run Now", "Select a schedule to run.")
            return

        row = selected[0].row()
        id_item = self.jobs_table.item(row, 0)
        if not id_item:
            return

        job_id = id_item.data(Qt.UserRole)
        schedule = next((s for s in self.custom_schedules if s.get("job_id") == job_id), None)
        if not schedule:
            QMessageBox.information(self, "Run Now", "Selected job is not a custom schedule.")
            return

        def operation(progress_emit):
            progress_emit(f"Running schedule now: {schedule['name']}")
            return self.server_manager.run_task_steps(schedule.get("steps", []), progress_emit)

        self._run_worker(operation, f"Schedule '{schedule['name']}' executed")

    def _run_worker(self, operation: Callable[[Callable[[str], None]], bool], done_message: str) -> None:
        if self.worker and self.worker.isRunning():
            QMessageBox.information(self, "Busy", "Another automation operation is already running.")
            return

        self.worker = AutomationWorker(operation, done_message)
        self.worker.progress.connect(self._log)
        self.worker.finished.connect(self.on_worker_finished)
        self.worker.start()

    def on_worker_finished(self, success: bool, message: str) -> None:
        if success:
            self._log(f"✓ {message}")
        else:
            self._log(f"✗ {message}")

        self.refresh_job_status()

    def pause_scheduler(self) -> None:
        self.task_scheduler.pause_scheduler()
        self.pause_btn.setEnabled(False)
        self.resume_btn.setEnabled(True)
        self._log("Scheduler paused")

    def resume_scheduler(self) -> None:
        self.task_scheduler.resume_scheduler()
        self.pause_btn.setEnabled(True)
        self.resume_btn.setEnabled(False)
        self._log("Scheduler resumed")

    def cleanup(self) -> None:
        self.status_timer.stop()
        if self.worker and self.worker.isRunning():
            self.worker.quit()
            self.worker.wait(1000)
