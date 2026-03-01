"""
Configuration management - load, save, and validate configuration from JSON.
"""

import json
from pathlib import Path
from typing import Optional
from pydantic import ValidationError

from .schema import Config
from utils.logger import log


class ConfigManager:
    """Manages application configuration with persistence and validation."""

    DEFAULT_CONFIG_FILE = "config.json"

    def __init__(self, config_file: Optional[str] = None):
        self.config_file = Path(config_file or self.DEFAULT_CONFIG_FILE)
        self.config: Optional[Config] = None
        self.load()

    def load(self) -> None:
        """Load configuration from file, or create default if not exists."""
        if self.config_file.exists():
            try:
                with open(self.config_file, "r") as f:
                    data = json.load(f)

                legacy_path = str(Path("./rust_data"))
                canonical_path = str(Path("./addons/steam/rust_data"))
                current_path = str(Path(data.get("paths", {}).get("rust_data_dir", canonical_path)))
                if current_path == legacy_path:
                    data.setdefault("paths", {})["rust_data_dir"] = canonical_path
                    log.info(
                        "Migrated paths.rust_data_dir from ./rust_data to ./addons/steam/rust_data"
                    )

                self.config = Config(**data)
                log.info(f"Configuration loaded from {self.config_file}")
            except (json.JSONDecodeError, ValidationError) as e:
                log.error(f"Failed to load config: {e}")
                self.config = Config()
                log.info("Using default configuration")
        else:
            log.info(f"No config file found at {self.config_file}, creating default")
            self.config = Config()
            self.save()

    def save(self) -> None:
        """Save current configuration to file."""
        if self.config is None:
            log.error("Cannot save: config is None")
            return

        try:
            with open(self.config_file, "w") as f:
                json.dump(self.config.model_dump(), f, indent=2)
            log.info(f"Configuration saved to {self.config_file}")
        except Exception as e:
            log.error(f"Failed to save config: {e}")

    def get_config(self) -> Config:
        """Get the current configuration object."""
        if self.config is None:
            self.config = Config()
        return self.config

    def update_config(self, **kwargs) -> bool:
        """
        Update configuration fields. Supports nested updates via dot notation.
        Returns True if successful, False otherwise.
        """
        if self.config is None:
            self.config = Config()

        try:
            data = self.config.model_dump()
            
            # Handle nested updates (e.g., "server.port" -> data["server"]["port"])
            for key, value in kwargs.items():
                if "." in key:
                    parts = key.split(".")
                    current = data
                    for part in parts[:-1]:
                        if part not in current:
                            current[part] = {}
                        current = current[part]
                    current[parts[-1]] = value
                else:
                    data[key] = value

            self.config = Config(**data)
            self.save()
            return True
        except ValidationError as e:
            log.error(f"Config validation failed: {e}")
            return False
        except Exception as e:
            log.error(f"Failed to update config: {e}")
            return False

    def validate(self) -> tuple[bool, list[str]]:
        """
        Validate current configuration and return (is_valid, error_messages).
        """
        errors = []
        cfg = self.get_config()

        # Check if required paths exist
        for path_name in ["rust_data_dir", "steamcmd_path"]:
            path = Path(getattr(cfg.paths, path_name))
            if not path.exists():
                errors.append(f"Path does not exist: {path_name} ({path})")

        # Check port ranges
        if cfg.server.port == cfg.server.app_port:
            errors.append("Server port and app port cannot be the same")

        # Check RCON config
        if not cfg.rcon.host:
            errors.append("RCON host cannot be empty")

        # Validate map configuration
        if getattr(cfg.server, "map_mode", "procedural") == "custom":
            custom_map = (getattr(cfg.server, "custom_map_path", "") or "").strip()
            if not custom_map:
                errors.append("Custom map mode requires server.custom_map_path")

        return (len(errors) == 0, errors)
