"""
Core server management - install, update, start, stop, and check server status.
"""

import subprocess
import os
import shutil
import threading
import zipfile
import random
import re
import socket
import tempfile
import urllib.request
from pathlib import Path
from typing import Optional, Callable
from datetime import datetime
import psutil
import time

from utils.logger import log
from config.schema import Config
from core.rcon_client import RconClient
from core.console_triggers import ConsoleTriggersEngine


class ServerManager:
    """Manage Rust server lifecycle operations."""

    def __init__(self, config: Config):
        self.config = config
        self.rust_dir = Path(config.paths.rust_data_dir)
        self.steam_cmd = Path(config.paths.steamcmd_path)
        self.steamcmd_download_url = config.paths.steamcmd_download_url
        self.server_process: Optional[subprocess.Popen] = None
        self._output_listeners: list[Callable[[str], None]] = []
        self._output_lock = threading.Lock()
        self._stdout_thread: Optional[threading.Thread] = None
        self._stderr_thread: Optional[threading.Thread] = None
        self._last_net_sample: Optional[tuple[float, int, int]] = None
        self._last_player_poll_time: float = 0.0
        self._cached_player_count: Optional[int] = None
        self._last_public_check_time: float = 0.0
        self._cached_public_status: dict = {
            "public_ip": "N/A",
            "public_port_open": False,
            "public_check_error": None,
        }
        self._public_check_thread: Optional[threading.Thread] = None
        self._public_check_lock = threading.Lock()
        
        # Console triggers engine
        self.triggers_engine = ConsoleTriggersEngine()
        self.load_console_triggers()

    @property
    def backups_dir(self) -> Path:
        """Directory where compressed server backups are stored."""
        return Path("./backups")

    def add_output_listener(self, callback: Callable[[str], None]) -> None:
        """Register a callback for unified console output."""
        with self._output_lock:
            if callback not in self._output_listeners:
                self._output_listeners.append(callback)

    def remove_output_listener(self, callback: Callable[[str], None]) -> None:
        """Unregister a callback for unified console output."""
        with self._output_lock:
            if callback in self._output_listeners:
                self._output_listeners.remove(callback)

    def emit_console_output(self, message: str) -> None:
        """Broadcast a message to all in-app console listeners."""
        if not message:
            return
        
        # Process console triggers
        self.triggers_engine.process_output(message)

        with self._output_lock:
            listeners = list(self._output_listeners)

        for callback in listeners:
            try:
                callback(message)
            except Exception as e:
                log.error(f"Console output listener failed: {e}")

    def load_console_triggers(self) -> None:
        """Load console triggers from configuration."""
        triggers = self.config.automation.console_triggers
        self.triggers_engine.load_triggers(triggers)

    def _read_process_stream(self, stream, prefix: str) -> None:
        """Read process output stream and forward to unified console."""
        try:
            for line in iter(stream.readline, ""):
                text = line.strip()
                if text:
                    self.emit_console_output(f"[{prefix}] {text}")
            stream.close()
        except Exception as e:
            log.error(f"Failed reading {prefix} stream: {e}")

    def _start_server_output_streams(self) -> None:
        """Start background readers for server stdout/stderr."""
        if self.server_process is None:
            return

        if self.server_process.stdout:
            self._stdout_thread = threading.Thread(
                target=self._read_process_stream,
                args=(self.server_process.stdout, "RUST"),
                daemon=True,
            )
            self._stdout_thread.start()

        if self.server_process.stderr:
            self._stderr_thread = threading.Thread(
                target=self._read_process_stream,
                args=(self.server_process.stderr, "RUST-ERR"),
                daemon=True,
            )
            self._stderr_thread.start()

    def _emit_subprocess_output(self, stdout: str, stderr: str, source: str) -> None:
        """Forward captured subprocess output into unified in-app console."""
        for line in (stdout or "").splitlines():
            text = line.strip()
            if text:
                self.emit_console_output(f"[{source}] {text}")

        for line in (stderr or "").splitlines():
            text = line.strip()
            if text:
                self.emit_console_output(f"[{source}-ERR] {text}")

    def initialize_directories(self) -> bool:
        """Create necessary directories if they don't exist."""
        try:
            self.rust_dir.mkdir(parents=True, exist_ok=True)
            managed_dir = self.rust_dir / "RustDedicated_Data" / "Managed"
            managed_dir.mkdir(parents=True, exist_ok=True)
            log.info(f"Directories initialized at {self.rust_dir}")
            return True
        except Exception as e:
            log.error(f"Failed to initialize directories: {e}")
            return False

    def is_server_running(self) -> bool:
        """Check if the Rust server process is currently running."""
        if self.server_process is None:
            return False
        
        try:
            if self.server_process.poll() is None:  # Process still running
                return True
            else:
                self.server_process = None
                return False
        except Exception as e:
            log.error(f"Error checking server status: {e}")
            return False

    def _download_file(self, url: str, destination: Path, progress_callback: Optional[Callable[[str], None]] = None) -> None:
        """Download a file from URL to destination path."""
        destination.parent.mkdir(parents=True, exist_ok=True)
        self._emit_progress(progress_callback, f"Downloading: {url}")
        with urllib.request.urlopen(url, timeout=120) as response, open(destination, "wb") as out_file:
            shutil.copyfileobj(response, out_file)

    def _ensure_steamcmd_installed(self, progress_callback: Optional[Callable[[str], None]] = None) -> bool:
        """Ensure SteamCMD exists locally; download and extract if missing."""
        if self.steam_cmd.exists():
            return True

        try:
            self._emit_progress(progress_callback, "SteamCMD not found. Downloading SteamCMD...")
            steam_dir = self.steam_cmd.parent
            steam_dir.mkdir(parents=True, exist_ok=True)

            with tempfile.TemporaryDirectory() as tmp_dir:
                zip_path = Path(tmp_dir) / "steamcmd.zip"
                self._download_file(self.steamcmd_download_url, zip_path, progress_callback)

                self._emit_progress(progress_callback, "Extracting SteamCMD...")
                with zipfile.ZipFile(zip_path, "r") as archive:
                    archive.extractall(steam_dir)

            if not self.steam_cmd.exists():
                msg = f"SteamCMD download completed but executable not found at {self.steam_cmd}"
                self._emit_progress(progress_callback, msg)
                log.error(msg)
                return False

            self._emit_progress(progress_callback, f"SteamCMD installed at {self.steam_cmd}")
            log.info(f"SteamCMD installed at {self.steam_cmd}")
            return True
        except Exception as e:
            msg = f"Failed to download SteamCMD: {e}"
            self._emit_progress(progress_callback, msg)
            log.error(msg, exc_info=True)
            return False

    def install_rust_server(self, progress_callback: Optional[Callable[[str], None]] = None) -> bool:
        """
        Install or update Rust server using SteamCMD.
        
        Args:
            progress_callback: Optional callback for progress messages
        """
        if not self.initialize_directories():
            return False

        if not self._ensure_steamcmd_installed(progress_callback):
            return False

        try:
            self._emit_progress(progress_callback, "Starting Rust server installation...")
            
            # Use absolute path to ensure correct installation location
            rust_path = Path(self.rust_dir).absolute()
            rust_path_str = str(rust_path).replace("\\", "/")
            cmd = (
                f'"{self.steam_cmd}" +force_install_dir "{rust_path_str}" '
                f"+login anonymous +app_update 258550 +quit"
            )
            
            self._emit_progress(progress_callback, f"Executing: {cmd}")
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=3600)
            self._emit_subprocess_output(result.stdout, result.stderr, "STEAMCMD")
            
            if result.returncode == 0:
                self._emit_progress(progress_callback, "Rust server installed successfully")
                log.info("Rust server installation completed")
                return True
            else:
                msg = f"Failed to install Rust server: {result.stderr}"
                self._emit_progress(progress_callback, msg)
                log.error(msg)
                return False
        except Exception as e:
            msg = f"Error installing Rust server: {e}"
            self._emit_progress(progress_callback, msg)
            log.error(msg, exc_info=True)
            return False

    def install_oxide(self, progress_callback: Optional[Callable[[str], None]] = None) -> bool:
        """Download and install Oxide modification framework."""
        try:
            self._emit_progress(progress_callback, "Installing Oxide...")

            with tempfile.TemporaryDirectory() as tmp_dir:
                oxide_zip = Path(tmp_dir) / "oxide.zip"
                oxide_url = "https://github.com/OxideMod/Oxide.Rust/releases/latest/download/Oxide.Rust.zip" # for windows
                # linux url https://github.com/OxideMod/Oxide.Rust/releases/latest/download/Oxide.Rust-linux.zip

                self._emit_progress(progress_callback, "Downloading Oxide...")
                self._download_file(oxide_url, oxide_zip, progress_callback)

                self._emit_progress(progress_callback, "Extracting Oxide...")
                with zipfile.ZipFile(oxide_zip, "r") as archive:
                    archive.extractall(self.rust_dir)

            self._emit_progress(progress_callback, "Oxide installed successfully")
            log.info("Oxide installation completed")
            return True
        except Exception as e:
            msg = f"Error installing Oxide: {e}"
            self._emit_progress(progress_callback, msg)
            log.error(msg, exc_info=True)
            return False

    def install_rust_edit(self, progress_callback: Optional[Callable[[str], None]] = None) -> bool:
        """Download and install RustEdit extension."""
        try:
            self._emit_progress(progress_callback, "Installing RustEdit...")

            managed_dir = self.rust_dir / "RustDedicated_Data" / "Managed"
            rustedit_dll = managed_dir / "Oxide.Ext.RustEdit.dll"
            managed_dir.mkdir(parents=True, exist_ok=True)

            rustedit_url = "https://github.com/k1lly0u/Oxide.Ext.RustEdit/raw/master/Oxide.Ext.RustEdit.dll"
            self._download_file(rustedit_url, rustedit_dll, progress_callback)

            self._emit_progress(progress_callback, "RustEdit installed successfully")
            log.info("RustEdit installation completed")
            return True
        except Exception as e:
            msg = f"Error installing RustEdit: {e}"
            self._emit_progress(progress_callback, msg)
            log.error(msg, exc_info=True)
            return False

    def start_server(self, progress_callback: Optional[Callable[[str], None]] = None) -> bool:
        """
        Start the Rust server with configured parameters.
        """
        if self.is_server_running():
            msg = "Server is already running"
            self._emit_progress(progress_callback, msg)
            log.warning(msg)
            return False

        try:
            self._emit_progress(progress_callback, "Starting Rust server...")
            
            server_exe = self.rust_dir / "RustDedicated.exe"
            if not server_exe.exists():
                msg = f"Server executable not found at {server_exe}"
                self._emit_progress(progress_callback, msg)
                log.error(msg)
                return False
            
            # Build startup parameters from config
            cfg = self.config.server
            map_mode = (cfg.map_mode or "procedural").lower()
            gamemode = (cfg.gamemode or "vanilla").lower()

            args = [
                str(server_exe),
                "-batchmode",
                "-nographics",
                "+server.port", str(cfg.port),
                "+app.port", str(cfg.app_port),
                "+server.hostname", str(cfg.description),
                "+server.maxplayers", str(cfg.max_players),
                "+server.worldsize", str(cfg.world_size),
                "+server.saveinterval", str(getattr(cfg, "save_interval", 300)),
                "+server.tickrate", str(cfg.tickrate),
                "+fps.limit", str(getattr(cfg, "fps_limit", 256)),
            ]
            
            # Gamemode
            if gamemode == "softcore":
                args.extend(["+server.gamemode", "softcore"])
            
            # Queue
            if hasattr(cfg, "queue_size"):
                args.extend(["+server.queuesize", str(cfg.queue_size)])

            # PVE mode
            if getattr(cfg, "pve", False):
                args.extend(["+server.pve", "true"])
            
            # Gameplay settings
            if not getattr(cfg, "radiation", True):
                args.extend(["+server.radiation", "false"])
            if not getattr(cfg, "stability", True):
                args.extend(["+server.stability", "false"])
            if not getattr(cfg, "comfort", True):
                args.extend(["+server.comfort", "false"])
            if not getattr(cfg, "events", True):
                args.extend(["+server.events", "false"])
            
            # Decay settings
            if not getattr(cfg, "decay_upkeep", True):
                args.extend(["+decay.upkeep", "false"])
            decay_scale = getattr(cfg, "decay_scale", 1.0)
            if decay_scale != 1.0:
                args.extend(["+decay.scale", str(decay_scale)])
            decay_delay = getattr(cfg, "decay_delay_override", None)
            if decay_delay is not None:
                args.extend(["+decay.delay_override", str(int(decay_delay * 60))])  # hours to minutes
            
            # Header image
            if hasattr(cfg, "header_image") and cfg.header_image:
                args.extend(["+server.headerimage", str(cfg.header_image)])

            if map_mode == "custom" and cfg.custom_map_path:
                args.extend(["+server.levelurl", str(cfg.custom_map_path)])
                self._emit_progress(progress_callback, f"Using custom map: {cfg.custom_map_path}")
            else:
                args.extend(["+server.level", str(cfg.map or "Procedural Map")])
                seed_value = cfg.seed if cfg.seed is not None else random.randint(1, 2_147_483_647)
                if cfg.seed is None:
                    self._emit_progress(progress_callback, f"No seed set, using random seed: {seed_value}")
                args.extend(["+server.seed", str(seed_value)])

            if cfg.url:
                args.extend(["+server.url", str(cfg.url)])
            if cfg.tag_language:
                args.extend(["+server.language", str(cfg.tag_language)])

            self._emit_progress(progress_callback, f"Launching: {' '.join(args)[:100]}...")

            popen_kwargs = {
                "cwd": str(self.rust_dir),
                "stdout": subprocess.PIPE,
                "stderr": subprocess.PIPE,
                "text": True,
                "bufsize": 1,
                "shell": False,
            }

            if os.name == "nt":
                popen_kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW

            # Start server process (don't wait for it)
            self.server_process = subprocess.Popen(args, **popen_kwargs)
            self._start_server_output_streams()
            
            # Give it a second to validate it started
            time.sleep(1)
            
            if self.is_server_running():
                self._emit_progress(progress_callback, f"Server started (PID: {self.server_process.pid})")
                log.info(f"Server started (PID: {self.server_process.pid})")
                return True
            else:
                msg = f"Server process exited unexpectedly. Check logs for details."
                self._emit_progress(progress_callback, msg)
                log.error(msg)
                return False
        except Exception as e:
            msg = f"Error starting server: {e}"
            self._emit_progress(progress_callback, msg)
            log.error(msg, exc_info=True)
            return False

    def stop_server(self, progress_callback: Optional[Callable[[str], None]] = None) -> bool:
        """Stop the running Rust server."""
        try:
            if not self.is_server_running():
                msg = "Server is not running"
                self._emit_progress(progress_callback, msg)
                log.warning(msg)
                return False
            
            self._emit_progress(progress_callback, "Stopping server...")
            self.server_process.terminate()
            
            try:
                self.server_process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self._emit_progress(progress_callback, "Force killing server...")
                self.server_process.kill()
                self.server_process.wait()
            
            self.server_process = None
            self._emit_progress(progress_callback, "Server stopped")
            log.info("Server stopped")
            return True
        except Exception as e:
            msg = f"Error stopping server: {e}"
            self._emit_progress(progress_callback, msg)
            log.error(msg, exc_info=True)
            return False

    def save_server(self, progress_callback: Optional[Callable[[str], None]] = None) -> bool:
        """Trigger a Rust server save via RCON when possible."""
        if not self.is_server_running():
            msg = "Save skipped: server is not running"
            self._emit_progress(progress_callback, msg)
            log.warning(msg)
            return False

        rcon_cfg = self.config.rcon
        if not rcon_cfg.password:
            msg = "Save skipped: RCON password is not configured"
            self._emit_progress(progress_callback, msg)
            log.warning(msg)
            return False

        client = RconClient(host=rcon_cfg.host, port=rcon_cfg.port, password=rcon_cfg.password)
        try:
            self._emit_progress(progress_callback, "Connecting to RCON for save...")
            if not client.connect():
                msg = "Failed to connect to RCON for save"
                self._emit_progress(progress_callback, msg)
                log.error(msg)
                return False

            ok = client.send_command("server.save")
            if ok:
                self._emit_progress(progress_callback, "Save command sent via RCON")
                self.emit_console_output("[AUTOMATION] Sent RCON command: server.save")
                return True

            msg = "Failed to send save command"
            self._emit_progress(progress_callback, msg)
            log.error(msg)
            return False
        except Exception as e:
            msg = f"Error during save: {e}"
            self._emit_progress(progress_callback, msg)
            log.error(msg, exc_info=True)
            return False
        finally:
            client.disconnect()

    def wipe_server(self, progress_callback: Optional[Callable[[str], None]] = None) -> bool:
        """Wipe map/save files from server data directory."""
        try:
            self._emit_progress(progress_callback, "Wiping map/save files...")
            deleted = 0
            patterns = ["*.sav*", "*.map", "*.db", "*.db-journal"]
            target_root = self.rust_dir / "server"
            search_root = target_root if target_root.exists() else self.rust_dir

            for pattern in patterns:
                for file_path in search_root.rglob(pattern):
                    if file_path.is_file():
                        file_path.unlink(missing_ok=True)
                        deleted += 1

            msg = f"Wipe completed, removed {deleted} file(s)"
            self._emit_progress(progress_callback, msg)
            self.emit_console_output(f"[AUTOMATION] {msg}")
            log.info(msg)
            return True
        except Exception as e:
            msg = f"Error wiping server: {e}"
            self._emit_progress(progress_callback, msg)
            log.error(msg, exc_info=True)
            return False

    def wipe_blueprints(self, progress_callback: Optional[Callable[[str], None]] = None) -> bool:
        """Wipe blueprint-related files only."""
        try:
            self._emit_progress(progress_callback, "Wiping blueprint files...")
            deleted = 0
            target_root = self.rust_dir / "server"
            search_root = target_root if target_root.exists() else self.rust_dir

            for file_path in search_root.rglob("*blueprint*"):
                if file_path.is_file():
                    file_path.unlink(missing_ok=True)
                    deleted += 1

            msg = f"Blueprint wipe completed, removed {deleted} file(s)"
            self._emit_progress(progress_callback, msg)
            self.emit_console_output(f"[AUTOMATION] {msg}")
            log.info(msg)
            return True
        except Exception as e:
            msg = f"Error wiping blueprints: {e}"
            self._emit_progress(progress_callback, msg)
            log.error(msg, exc_info=True)
            return False

    def create_backup(self, name: Optional[str] = None, progress_callback: Optional[Callable[[str], None]] = None) -> bool:
        """Create a compressed backup of rust data directory."""
        try:
            self.backups_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = name.strip() if name else f"rust_backup_{timestamp}"
            safe_name = "".join(ch for ch in backup_name if ch.isalnum() or ch in ("-", "_"))
            if not safe_name:
                safe_name = f"rust_backup_{timestamp}"

            backup_path = self.backups_dir / f"{safe_name}.zip"
            self._emit_progress(progress_callback, f"Creating backup: {backup_path.name}")

            with zipfile.ZipFile(backup_path, "w", zipfile.ZIP_DEFLATED) as archive:
                for file_path in self.rust_dir.rglob("*"):
                    if file_path.is_file():
                        archive.write(file_path, file_path.relative_to(self.rust_dir))

            msg = f"Backup created: {backup_path}"
            self._emit_progress(progress_callback, msg)
            self.emit_console_output(f"[AUTOMATION] {msg}")
            log.info(msg)
            
            # Clean up old backups based on max_backups config
            self._cleanup_old_backups(progress_callback)
            
            return True
        except Exception as e:
            msg = f"Error creating backup: {e}"
            self._emit_progress(progress_callback, msg)
            log.error(msg, exc_info=True)
            return False

    def deploy_backup(self, backup_file: str, progress_callback: Optional[Callable[[str], None]] = None) -> bool:
        """Deploy a selected backup archive to rust data directory."""
        try:
            backup_path = Path(backup_file)
            if not backup_path.exists() or backup_path.suffix.lower() != ".zip":
                msg = f"Invalid backup archive: {backup_file}"
                self._emit_progress(progress_callback, msg)
                log.error(msg)
                return False

            if self.is_server_running():
                self._emit_progress(progress_callback, "Server is running, stopping before deploy...")
                self.stop_server(progress_callback)

            self._emit_progress(progress_callback, f"Deploying backup: {backup_path.name}")

            if self.rust_dir.exists():
                shutil.rmtree(self.rust_dir)
            self.rust_dir.mkdir(parents=True, exist_ok=True)

            with zipfile.ZipFile(backup_path, "r") as archive:
                archive.extractall(self.rust_dir)

            msg = f"Backup deployed: {backup_path.name}"
            self._emit_progress(progress_callback, msg)
            self.emit_console_output(f"[AUTOMATION] {msg}")
            log.info(msg)
            return True
        except Exception as e:
            msg = f"Error deploying backup: {e}"
            self._emit_progress(progress_callback, msg)
            log.error(msg, exc_info=True)
            return False

    def deploy_latest_backup(self, progress_callback: Optional[Callable[[str], None]] = None) -> bool:
        """Deploy the most recent backup archive."""
        backups = self.list_backups()
        if not backups:
            msg = "No backups available to deploy"
            self._emit_progress(progress_callback, msg)
            log.warning(msg)
            return False
        return self.deploy_backup(str(backups[0]), progress_callback)

    def list_backups(self) -> list[Path]:
        """List backups sorted newest first."""
        if not self.backups_dir.exists():
            return []
        return sorted(
            self.backups_dir.glob("*.zip"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )

    def _cleanup_old_backups(self, progress_callback: Optional[Callable[[str], None]] = None) -> None:
        """Delete oldest backups when count exceeds max_backups."""
        try:
            max_backups = self.config.automation.max_backups
            backups = self.list_backups()
            
            if len(backups) > max_backups:
                to_delete = backups[max_backups:]
                for backup in to_delete:
                    backup.unlink()
                    msg = f"Deleted old backup: {backup.name}"
                    self._emit_progress(progress_callback, msg)
                    log.info(msg)
        except Exception as e:
            log.error(f"Error cleaning up old backups: {e}", exc_info=True)

    def run_actions(self, actions: list[str], progress_callback: Optional[Callable[[str], None]] = None) -> bool:
        """Execute a sequence of automation actions in order."""
        action_map = {
            "start": self.start_server,
            "stop": self.stop_server,
            "restart": self.restart_server,
            "wipe": self.wipe_server,
            "wipebp": self.wipe_blueprints,
            "save": self.save_server,
            "backup": lambda cb: self.create_backup(progress_callback=cb),
            "restore_latest_backup": self.deploy_latest_backup,
        }

        all_ok = True
        for action in actions:
            fn = action_map.get(action)
            if not fn:
                msg = f"Unknown action: {action}"
                self._emit_progress(progress_callback, msg)
                self.emit_console_output(f"[AUTOMATION-ERR] {msg}")
                log.error(msg)
                all_ok = False
                continue

            self._emit_progress(progress_callback, f"Running action: {action}")
            ok = fn(progress_callback)
            if not ok:
                all_ok = False

        return all_ok

    def run_task_steps(self, steps: list[dict], progress_callback: Optional[Callable[[str], None]] = None) -> bool:
        """Execute a sequence of task steps including actions, delays, messages, and conditionals."""
        action_map = {
            "start": self.start_server,
            "stop": self.stop_server,
            "restart": self.restart_server,
            "save": self.save_server,
            "backup": lambda cb: self.create_backup(progress_callback=cb),
            "restore_latest_backup": self.deploy_latest_backup,
            "wipe": self.wipe_server,
            "wipebp": self.wipe_blueprints,
            "install_rust": self.install_rust_server,
            "install_oxide": self.install_oxide,
            "install_rustedit": self.install_rust_edit,
            "check_wan": lambda cb: self._check_wan_wrapper(cb),
            "cleanup_backups": lambda cb: self._cleanup_old_backups(cb),
        }

        all_ok = True
        skip_until_next_conditional = False
        
        for step in steps:
            step_type = step.get("type")
            
            # Handle conditional checks
            if step_type == "conditional":
                condition = step.get("condition")
                condition_met = self._evaluate_condition(condition)
                skip_until_next_conditional = not condition_met
                
                status = "✅ Passed" if condition_met else "❌ Failed"
                msg = f"Condition: {step.get('label', condition)} - {status}"
                self._emit_progress(progress_callback, msg)
                self.emit_console_output(f"[AUTOMATION] {msg}")
                log.info(msg)
                continue
            
            # Skip steps if previous conditional failed
            if skip_until_next_conditional:
                continue
            
            if step_type == "action":
                action = step.get("action")
                label = step.get("label", action)
                fn = action_map.get(action)
                if not fn:
                    msg = f"Unknown action: {action}"
                    self._emit_progress(progress_callback, msg)
                    self.emit_console_output(f"[AUTOMATION-ERR] {msg}")
                    log.error(msg)
                    all_ok = False
                    continue

                self._emit_progress(progress_callback, f"Running: {label}")
                ok = fn(progress_callback)
                if not ok:
                    all_ok = False
                    
            elif step_type == "delay":
                seconds = step.get("seconds", 0)
                msg = f"Waiting {seconds} seconds..."
                self._emit_progress(progress_callback, msg)
                self.emit_console_output(f"[AUTOMATION] {msg}")
                log.info(msg)
                time.sleep(seconds)
                
            elif step_type == "message":
                message = step.get("message", "")
                msg = f"Sending message: {message}"
                self._emit_progress(progress_callback, msg)
                self.emit_console_output(f"[AUTOMATION] {msg}")
                log.info(msg)
                # Send message via RCON if server is running
                if self.is_server_running():
                    try:
                        from core.rcon_client import RconClient
                        client = RconClient(
                            host=self.config.rcon.host,
                            port=self.config.rcon.port,
                            password=self.config.rcon.password
                        )
                        if client.connect():
                            client.send_command(f"say {message}")
                            client.disconnect()
                    except Exception as e:
                        log.error(f"Failed to send RCON message: {e}")
            else:
                log.warning(f"Unknown step type: {step_type}")

        return all_ok
    
    def _evaluate_condition(self, condition: str) -> bool:
        """Evaluate a conditional check."""
        if condition == "if_running":
            return self.is_server_running()
        elif condition == "if_stopped":
            return not self.is_server_running()
        elif condition == "if_players":
            return self._get_cached_player_count() is not None and self._get_cached_player_count() > 0
        elif condition == "if_no_players":
            count = self._get_cached_player_count()
            return count is None or count == 0
        else:
            log.warning(f"Unknown condition: {condition}")
            return False
    
    def _check_wan_wrapper(self, progress_callback: Optional[Callable[[str], None]] = None) -> bool:
        """Wrapper for WAN check to fit task execution signature."""
        self._emit_progress(progress_callback, "Checking WAN accessibility...")
        result = self.test_wan_access(force=True)
        success = result.get("public_port_open", False)
        if success:
            msg = f"WAN check passed: {result.get('public_ip')}:{self.config.server.port}"
        else:
            msg = f"WAN check failed: {result.get('public_check_error', 'Port not reachable')}"
        self._emit_progress(progress_callback, msg)
        return success
    
    def _cleanup_old_backups(self, progress_callback: Optional[Callable[[str], None]] = None) -> bool:
        """Clean up old backups beyond the configured limit."""
        try:
            max_backups = self.config.automation.max_backups
            backups_dir = self.backups_dir
            
            if not backups_dir.exists():
                self._emit_progress(progress_callback, "No backups directory found")
                return True
            
            # Get all backup files sorted by modification time (newest first)
            backup_files = sorted(
                backups_dir.glob("*.zip"),
                key=lambda f: f.stat().st_mtime,
                reverse=True
            )
            
            if len(backup_files) <= max_backups:
                self._emit_progress(progress_callback, f"Backup count ({len(backup_files)}) within limit ({max_backups})")
                return True
            
            # Delete old backups
            deleted = 0
            for old_backup in backup_files[max_backups:]:
                old_backup.unlink()
                deleted += 1
                self._emit_progress(progress_callback, f"Deleted old backup: {old_backup.name}")
            
            msg = f"Cleaned up {deleted} old backup(s)"
            self._emit_progress(progress_callback, msg)
            log.info(msg)
            return True
            
        except Exception as e:
            msg = f"Error cleaning backups: {e}"
            self._emit_progress(progress_callback, msg)
            log.error(msg, exc_info=True)
            return False

    def restart_server(self, progress_callback: Optional[Callable[[str], None]] = None) -> bool:
        """Restart the Rust server."""
        self.stop_server(progress_callback)
        time.sleep(2)
        return self.start_server(progress_callback)

    def get_server_status(self) -> dict:
        """Get current server status and resource usage."""
        server_exe = self.rust_dir / "RustDedicated.exe"
        oxide_marker = self.rust_dir / "RustDedicated_Data" / "Managed" / "Oxide.Core.dll"
        status = {
            "running": False,
            "pid": None,
            "memory_mb": 0,
            "cpu_percent": 0,
            "uptime": 0,
            "network_rx_mb": 0.0,
            "network_tx_mb": 0.0,
            "network_rx_kbps": 0.0,
            "network_tx_kbps": 0.0,
            "players_online": self._cached_player_count,
            "public_ip": self._cached_public_status.get("public_ip", "N/A"),
            "public_port_open": self._cached_public_status.get("public_port_open", False),
            "public_check_error": self._cached_public_status.get("public_check_error"),
            "executable_exists": server_exe.exists(),
            "oxide_installed": oxide_marker.exists(),
        }

        self._update_public_access_status(force=False)
        status["public_ip"] = self._cached_public_status.get("public_ip", "N/A")
        status["public_port_open"] = self._cached_public_status.get("public_port_open", False)
        status["public_check_error"] = self._cached_public_status.get("public_check_error")
        
        if not self.is_server_running() or self.server_process is None:
            return status
        
        try:
            process = psutil.Process(self.server_process.pid)
            status["running"] = process.is_running()
            status["pid"] = process.pid
            
            mem_info = process.memory_info()
            status["memory_mb"] = mem_info.rss / 1024 / 1024
            
            status["cpu_percent"] = process.cpu_percent(interval=0.1)
            
            create_time = process.create_time()
            status["uptime"] = int(time.time() - create_time)

            self._update_network_stats(status)
            status["players_online"] = self._get_cached_player_count()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
        
        return status

    def _update_network_stats(self, status: dict) -> None:
        """Update network totals and throughput stats."""
        try:
            counters = psutil.net_io_counters()
            now = time.time()

            status["network_rx_mb"] = counters.bytes_recv / 1024 / 1024
            status["network_tx_mb"] = counters.bytes_sent / 1024 / 1024

            if self._last_net_sample is not None:
                last_time, last_recv, last_sent = self._last_net_sample
                elapsed = max(0.001, now - last_time)
                status["network_rx_kbps"] = ((counters.bytes_recv - last_recv) / elapsed) / 1024
                status["network_tx_kbps"] = ((counters.bytes_sent - last_sent) / elapsed) / 1024

            self._last_net_sample = (now, counters.bytes_recv, counters.bytes_sent)
        except Exception as e:
            log.error(f"Failed to update network stats: {e}")

    def _get_cached_player_count(self) -> Optional[int]:
        """Fetch player count via RCON at a controlled interval."""
        now = time.time()
        if now - self._last_player_poll_time < 10:
            return self._cached_player_count

        self._last_player_poll_time = now
        self._cached_player_count = self._query_player_count_rcon()
        return self._cached_player_count

    def _query_player_count_rcon(self) -> Optional[int]:
        """Best-effort player count query using RCON 'players' command."""
        if not self.config.rcon.password:
            return None

        client = RconClient(
            host=self.config.rcon.host,
            port=self.config.rcon.port,
            password=self.config.rcon.password,
            connect_timeout=2.0,
        )

        messages: list[str] = []

        def on_message(message: str) -> None:
            messages.append(message or "")

        client.on_message = on_message

        try:
            if not client.connect():
                return self._cached_player_count

            if not client.send_command("players"):
                return self._cached_player_count

            time.sleep(0.8)
            combined = "\n".join(messages)
            if not combined.strip():
                return self._cached_player_count

            match = re.search(r"(\d+)\s+players?", combined, re.IGNORECASE)
            if match:
                return int(match.group(1))

            lines = [line for line in combined.splitlines() if line.strip()]
            if lines:
                return max(0, len(lines) - 1)
            return self._cached_player_count
        except Exception:
            return self._cached_player_count
        finally:
            client.disconnect()

    def test_wan_access(self, force: bool = True) -> dict:
        """Run WAN/public accessibility test and return latest result."""
        self._update_public_access_status(force=force)
        return dict(self._cached_public_status)

    def _update_public_access_status(self, force: bool = False) -> None:
        """Check public IP and whether server port is reachable on that IP (async)."""
        now = time.time()
        if not force and now - self._last_public_check_time < 30:
            return

        # Check if a thread is already running
        with self._public_check_lock:
            if self._public_check_thread and self._public_check_thread.is_alive():
                return  # Already checking
            
            # Start background check
            self._public_check_thread = threading.Thread(
                target=self._do_public_check_background,
                args=(now,),
                daemon=True
            )
            self._public_check_thread.start()

    def _do_public_check_background(self, check_time: float) -> None:
        """Background task to check public IP and port accessibility."""
        port = int(self.config.server.port)
        public_ip = "N/A"
        open_ok = False
        error_text: Optional[str] = None

        try:
            with urllib.request.urlopen("https://api.ipify.org", timeout=3) as response:
                public_ip = response.read().decode("utf-8").strip()

            try:
                with socket.create_connection((public_ip, port), timeout=2):
                    open_ok = True
            except Exception as port_error:
                open_ok = False
                error_text = str(port_error)
        except Exception as e:
            error_text = str(e)

        with self._public_check_lock:
            self._last_public_check_time = check_time
            self._cached_public_status = {
                "public_ip": public_ip,
                "public_port_open": open_ok,
                "public_check_error": error_text,
            }

    def _emit_progress(self, callback: Optional[Callable[[str], None]], message: str) -> None:
        """Emit progress message through callback if provided."""
        if callback:
            callback(message)
