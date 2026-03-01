"""
Predefined console trigger templates for common Rust server events.
"""

TRIGGER_TEMPLATES = [
    {
        "name": "Player Join Event",
        "enabled": True,
        "pattern": r"(\w+) joined \[.+\]",
        "message_template": "Player {0} just joined the server!",
        "webhook_type": "discord",
        "webhook_url": "",
        "embed_color": "2ecc71",  # Green
        "description": "Triggers when a player joins. Extracts player name from console."
    },
    {
        "name": "Player Leave Event",
        "enabled": True,
        "pattern": r"(\w+) disconnected \[.+\]",
        "message_template": "Player {0} left the server.",
        "webhook_type": "discord",
        "webhook_url": "",
        "embed_color": "e74c3c",  # Red
        "description": "Triggers when a player leaves."
    },
    {
        "name": "Server Startup",
        "enabled": True,
        "pattern": r"Server startup complete",
        "message_template": "🚀 Rust server is online and ready!",
        "webhook_type": "discord",
        "webhook_url": "",
        "embed_color": "3498db",  # Blue
        "description": "Triggers when server starts up successfully."
    },
    {
        "name": "Server Shutdown",
        "enabled": True,
        "pattern": r"Stripping inventory",
        "message_template": "⏹️ Rust server is shutting down.",
        "webhook_type": "discord",
        "webhook_url": "",
        "embed_color": "95a5a6",  # Gray
        "description": "Triggers when server begins shutdown process."
    },
    {
        "name": "Kill Report",
        "enabled": True,
        "pattern": r"(\w+) was killed by (\w+)",
        "message_template": "{0} was killed by {1}",
        "webhook_type": "discord",
        "webhook_url": "",
        "embed_color": "e67e22",  # Orange
        "description": "Reports when one player kills another."
    },
    {
        "name": "Chat Message",
        "enabled": False,
        "pattern": r"(\w+) : (.+?)(?=\n|$)",
        "message_template": "[CHAT] {0}: {1}",
        "webhook_type": "discord",
        "webhook_url": "",
        "embed_color": "9b59b6",  # Purple
        "description": "Captures chat messages. Disabled by default (verbose)."
    },
    {
        "name": "Server Error Alert",
        "enabled": True,
        "pattern": r"\[ERROR\]|NullReferenceException|Exception",
        "message_template": "⚠️ Server error detected! Check logs immediately.",
        "webhook_type": "discord",
        "webhook_url": "",
        "embed_color": "e74c3c",  # Red
        "description": "Sends alert when errors occur in server logs."
    },
    {
        "name": "Plugin/Mod Loaded",
        "enabled": False,
        "pattern": r"(luaoscript\.ls|modded|oxide)",
        "message_template": "Loaded extension: {0}",
        "webhook_type": "discord",
        "webhook_url": "",
        "embed_color": "1abc9c",  # Turquoise
        "description": "Tracks when plugins/mods are loaded."
    },
    {
        "name": "Wipe Event",
        "enabled": True,
        "pattern": r"Saving world|wipe|Cleaning up",
        "message_template": "🧹 Server wipe/reset in progress...",
        "webhook_type": "discord",
        "webhook_url": "",
        "embed_color": "f39c12",  # Yellow
        "description": "Alerts when a wipe or cleanup is happening."
    },
]


def get_template_by_name(name: str) -> dict:
    """Get a template by name."""
    for template in TRIGGER_TEMPLATES:
        if template["name"] == name:
            return template.copy()
    return None


def get_all_template_names() -> list[str]:
    """Get list of all template names."""
    return [t["name"] for t in TRIGGER_TEMPLATES]


def create_trigger_from_template(template_name: str, webhook_url: str = "") -> dict:
    """Create a trigger configuration from a template."""
    template = get_template_by_name(template_name)
    if not template:
        return None
    
    # Remove description and return trigger config
    trigger = {k: v for k, v in template.items() if k != "description"}
    if webhook_url:
        trigger["webhook_url"] = webhook_url
    
    return trigger
