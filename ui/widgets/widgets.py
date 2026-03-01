"""
Reusable UI widgets.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit,
    QLabel, QPushButton, QLineEdit, QSpinBox, QCheckBox,
    QComboBox, QFormLayout, QGroupBox, QMessageBox, QDialog
)
from PySide6.QtCore import Qt, Signal, QThread, QPropertyAnimation, QEasingCurve, Property
from PySide6.QtGui import QPainter, QColor, QPen
from typing import Optional
import json


class ToggleSwitch(QWidget):
    """
    Modern iOS-style toggle switch widget.
    """
    toggled = Signal(bool)

    def __init__(self, parent=None, checked=False):
        super().__init__(parent)
        self._checked = checked
        self._circle_position = 1.0 if checked else 0.0
        self.setFixedSize(35, 20)  # 70% of original 50x28
        self.setCursor(Qt.PointingHandCursor)
        
        # Animation for smooth transition
        self.animation = QPropertyAnimation(self, b"circle_position")
        self.animation.setEasingCurve(QEasingCurve.InOutCubic)
        self.animation.setDuration(120)

    def paintEvent(self, event):
        """Draw the toggle switch."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Track (background)
        track_color = QColor(0, 150, 0) if self._checked else QColor(120, 120, 120)
        painter.setBrush(track_color)
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(0, 0, self.width(), self.height(), self.height() / 2, self.height() / 2)
        
        # Circle (thumb)
        circle_x = int(self._circle_position * (self.width() - self.height()) + 2)
        painter.setBrush(QColor(255, 255, 255))
        painter.drawEllipse(circle_x, 2, self.height() - 4, self.height() - 4)

    def mousePressEvent(self, event):
        """Handle mouse click to toggle."""
        if event.button() == Qt.LeftButton:
            self.setChecked(not self._checked)

    def isChecked(self) -> bool:
        """Return current checked state."""
        return self._checked

    def setChecked(self, checked: bool):
        """Set the checked state with animation."""
        if self._checked == checked:
            return
        
        self._checked = checked
        
        # Animate circle position
        self.animation.stop()
        self.animation.setStartValue(self._circle_position)
        self.animation.setEndValue(1.0 if checked else 0.0)
        self.animation.start()
        
        self.toggled.emit(checked)

    def get_circle_position(self):
        """Get circle position (for animation)."""
        return self._circle_position

    def set_circle_position(self, position):
        """Set circle position (for animation)."""
        self._circle_position = position
        self.update()

    circle_position = Property(float, get_circle_position, set_circle_position)


class LogsViewer(QTextEdit):
    """
    Read-only text widget for displaying logs with auto-scroll.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                font-family: 'Courier New', monospace;
                font-size: 10px;
            }
        """)

    def log(self, message: str) -> None:
        """Append a log message and auto-scroll to bottom."""
        self.append(message)
        self.verticalScrollBar().setValue(self.verticalScrollBar().maximum())

    def clear_logs(self) -> None:
        """Clear all logs."""
        self.clear()


class FieldGroup(QGroupBox):
    """
    Grouped form fields for organized settings layout.
    """

    def __init__(self, title: str, parent=None):
        super().__init__(title, parent)
        self.layout = QFormLayout()
        self.setLayout(self.layout)
        self.fields = {}

    def add_text_field(self, name: str, label: str, default: str = "") -> QLineEdit:
        """Add a text input field."""
        field = QLineEdit()
        field.setText(default)
        self.layout.addRow(label, field)
        self.fields[name] = field
        return field

    def add_int_field(self, name: str, label: str, default: int = 0, min_val: int = 0, max_val: int = 65535) -> QSpinBox:
        """Add an integer input field."""
        field = QSpinBox()
        field.setMinimum(min_val)
        field.setMaximum(max_val)
        field.setValue(default)
        self.layout.addRow(label, field)
        self.fields[name] = field
        return field

    def add_bool_field(self, name: str, label: str, default: bool = False) -> ToggleSwitch:
        """Add a boolean toggle switch field."""
        field = ToggleSwitch(checked=default)
        self.layout.addRow(label, field)
        self.fields[name] = field
        return field

    def add_combo_field(self, name: str, label: str, options: list, default: str = "") -> QComboBox:
        """Add a dropdown/combo field."""
        field = QComboBox()
        field.addItems(options)
        if default:
            field.setCurrentText(default)
        self.layout.addRow(label, field)
        self.fields[name] = field
        return field

    def get_values(self) -> dict:
        """Get all field values as dictionary."""
        values = {}
        for name, field in self.fields.items():
            if isinstance(field, QLineEdit):
                values[name] = field.text()
            elif isinstance(field, QSpinBox):
                values[name] = field.value()
            elif isinstance(field, (QCheckBox, ToggleSwitch)):
                values[name] = field.isChecked()
            elif isinstance(field, QComboBox):
                values[name] = field.currentText()
        return values

    def set_values(self, values: dict) -> None:
        """Set field values from dictionary."""
        for name, value in values.items():
            if name in self.fields:
                field = self.fields[name]
                if isinstance(field, QLineEdit):
                    field.setText(str(value))
                elif isinstance(field, QSpinBox):
                    field.setValue(int(value))
                elif isinstance(field, (QCheckBox, ToggleSwitch)):
                    field.setChecked(bool(value))
                elif isinstance(field, QComboBox):
                    field.setCurrentText(str(value))


class ErrorDialog(QMessageBox):
    """Simple error dialog."""

    def __init__(self, title: str, message: str, parent=None):
        super().__init__(parent)
        self.setIcon(QMessageBox.Critical)
        self.setWindowTitle(title)
        self.setText(message)
        self.setStandardButtons(QMessageBox.Ok)


class SuccessDialog(QMessageBox):
    """Simple success dialog."""

    def __init__(self, title: str, message: str, parent=None):
        super().__init__(parent)
        self.setIcon(QMessageBox.Information)
        self.setWindowTitle(title)
        self.setText(message)
        self.setStandardButtons(QMessageBox.Ok)
