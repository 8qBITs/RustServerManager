"""
Windows startup management utilities.
"""

import os
import sys
import winreg
from pathlib import Path
from typing import Tuple
import logging

log = logging.getLogger(__name__)


def get_app_path() -> str:
    """Get the full path to the application executable or script."""
    if getattr(sys, 'frozen', False):
        # Running as compiled executable
        return sys.executable
    else:
        # Running as script - use pythonw.exe to avoid console window
        python_exe = sys.executable.replace('python.exe', 'pythonw.exe')
        script_path = Path(__file__).parent.parent / 'app.py'
        return f'"{python_exe}" "{script_path}"'


def is_startup_enabled() -> bool:
    """Check if the application is set to start with Windows."""
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_READ
        )
        try:
            winreg.QueryValueEx(key, "RustServerManager")
            winreg.CloseKey(key)
            return True
        except FileNotFoundError:
            winreg.CloseKey(key)
            return False
    except Exception as e:
        log.error(f"Error checking startup status: {e}")
        return False


def enable_startup() -> Tuple[bool, str]:
    """
    Enable the application to start with Windows.
    Returns (success, message).
    """
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_SET_VALUE
        )
        
        app_path = get_app_path()
        winreg.SetValueEx(key, "RustServerManager", 0, winreg.REG_SZ, app_path)
        winreg.CloseKey(key)
        
        log.info(f"Startup enabled: {app_path}")
        return True, "Application will now start with Windows"
        
    except Exception as e:
        log.error(f"Failed to enable startup: {e}")
        return False, f"Failed to enable startup: {str(e)}"


def disable_startup() -> Tuple[bool, str]:
    """
    Disable the application from starting with Windows.
    Returns (success, message).
    """
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_SET_VALUE
        )
        
        try:
            winreg.DeleteValue(key, "RustServerManager")
            winreg.CloseKey(key)
            log.info("Startup disabled")
            return True, "Application will no longer start with Windows"
        except FileNotFoundError:
            # Already disabled
            winreg.CloseKey(key)
            return True, "Startup was already disabled"
            
    except Exception as e:
        log.error(f"Failed to disable startup: {e}")
        return False, f"Failed to disable startup: {str(e)}"


def toggle_startup(enable: bool) -> Tuple[bool, str]:
    """
    Enable or disable startup with Windows.
    Returns (success, message).
    """
    if enable:
        return enable_startup()
    else:
        return disable_startup()
