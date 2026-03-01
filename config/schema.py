"""
Configuration schema definitions using Pydantic for validation.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional


class ServerConfig(BaseModel):
    """Rust server runtime configuration."""

    # Connection & Identity
    port: int = Field(default=28015, ge=1024, le=65535)
    app_port: int = Field(default=28016, ge=1024, le=65535)
    description: str = Field(default="My Rust Server")
    url: str = Field(default="")
    header_image: str = Field(default="")
    
    # Map Configuration
    map: str = Field(default="Procedural Map")
    map_mode: str = Field(default="procedural")
    custom_map_path: str = Field(default="")
    seed: Optional[int] = Field(default=None, ge=0)
    world_size: int = Field(default=3000, ge=1000, le=6000)
    
    # Players & Server Limits
    max_players: int = Field(default=10, ge=1, le=500)
    queue_size: int = Field(default=100, ge=0, le=1000)
    
    # Performance
    tickrate: int = Field(default=30, ge=10, le=60)
    fps_limit: int = Field(default=256, ge=60, le=512)
    save_interval: int = Field(default=300, ge=60, le=3600)
    
    # Server Mode & Gameplay
    gamemode: str = Field(default="vanilla")
    pve: bool = Field(default=False)
    official: bool = Field(default=False)
    modded: bool = Field(default=False)
    
    # Gameplay Settings
    radiation: bool = Field(default=True)
    stability: bool = Field(default=True)
    decay_delay_override: Optional[int] = Field(default=None, ge=0, le=168)  # hours
    decay_upkeep: bool = Field(default=True)
    decay_scale: float = Field(default=1.0, ge=0.0, le=2.0)
    
    # Environmental  
    comfort: bool = Field(default=True)
    events: bool = Field(default=True)
    
    # Tags
    tag_generic: str = Field(default="")
    tag_environment: str = Field(default="")
    tag_language: str = Field(default="en")
    tag_official: bool = Field(default=False)
    tag_modded: bool = Field(default=False)

    @field_validator("map_mode")
    @classmethod
    def validate_map_mode(cls, v: str) -> str:
        normalized = (v or "procedural").strip().lower()
        if normalized not in {"procedural", "custom"}:
            raise ValueError("map_mode must be 'procedural' or 'custom'")
        return normalized
    
    @field_validator("gamemode")
    @classmethod
    def validate_gamemode(cls, v: str) -> str:
        normalized = (v or "vanilla").strip().lower()
        valid_modes = {"vanilla", "softcore", "hardcore", "creative"}
        if normalized not in valid_modes:
            raise ValueError(f"gamemode must be one of {valid_modes}")
        return normalized

    class Config:
        extra = "allow"  # Allow additional fields


class RconConfig(BaseModel):
    """RCON connection configuration."""

    host: str = Field(default="127.0.0.1")
    port: int = Field(default=28016, ge=1024, le=65535)
    password: str = Field(default="")

    @field_validator("host")
    @classmethod
    def validate_host(cls, v: str) -> str:
        if not v:
            raise ValueError("Host cannot be empty")
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) > 256:
            raise ValueError("Password too long (max 256 chars)")
        return v


class PathConfig(BaseModel):
    """Path configuration for tools and server."""

    rust_data_dir: str = Field(default="./addons/steam/rust_data")
    steamcmd_path: str = Field(default="./addons/steam/steamcmd.exe")
    steamcmd_download_url: str = Field(
        default="https://steamcdn-a.akamaihd.net/client/installer/steamcmd.zip"
    )

    @field_validator("rust_data_dir", "steamcmd_path", "steamcmd_download_url")
    @classmethod
    def validate_paths(cls, v: str) -> str:
        if not v:
            raise ValueError("Path cannot be empty")
        return v


class AutomationConfig(BaseModel):
    """Automation and scheduling configuration."""

    auto_check_rust_updates: bool = Field(default=False)
    auto_update_rust: bool = Field(default=False)
    auto_check_oxide_updates: bool = Field(default=False)
    auto_update_oxide: bool = Field(default=False)
    auto_restart_after_update: bool = Field(default=False)
    update_check_interval_minutes: int = Field(default=60, ge=5, le=1440)
    max_backups: int = Field(default=3, ge=1, le=100)
    auto_start_with_windows: bool = Field(default=False)
    auto_start_server_on_boot: bool = Field(default=False)
    custom_schedules: list[dict] = Field(default_factory=list)
    console_triggers: list[dict] = Field(default_factory=list)


class Config(BaseModel):
    """Root configuration model."""

    server: ServerConfig = Field(default_factory=ServerConfig)
    rcon: RconConfig = Field(default_factory=RconConfig)
    paths: PathConfig = Field(default_factory=PathConfig)
    automation: AutomationConfig = Field(default_factory=AutomationConfig)

    class Config:
        extra = "allow"
