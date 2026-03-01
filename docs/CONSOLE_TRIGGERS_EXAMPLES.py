"""
Example console trigger configurations.
Save these to your config file to enable them.
"""

# Example 1: Basic Discord Notifications

EXAMPLE_CONFIG = {
    # In your main config.yaml or automation section:
    "automation": {
        "console_triggers": [
            # Player Join Notification
            {
                "name": "Player Join Alert",
                "enabled": True,
                "pattern": r"(\w+) joined \[.+\]",
                "message_template": "🎮 Player {0} joined the server",
                "webhook_type": "discord",
                "webhook_url": "https://discord.com/api/webhooks/YOUR_WEBHOOK_ID/YOUR_WEBHOOK_TOKEN",
                "embed_color": "2ecc71"  # Green
            },
            
            # Player Leave Notification
            {
                "name": "Player Leave Alert",
                "enabled": True,
                "pattern": r"(\w+) disconnected \[.+\]",
                "message_template": "👋 Player {0} left the server",
                "webhook_type": "discord",
                "webhook_url": "https://discord.com/api/webhooks/YOUR_WEBHOOK_ID/YOUR_WEBHOOK_TOKEN",
                "embed_color": "e74c3c"  # Red
            },
            
            # Server Startup
            {
                "name": "Server Online",
                "enabled": True,
                "pattern": "Server startup complete",
                "message_template": "🚀 Rust server is now ONLINE",
                "webhook_type": "discord",
                "webhook_url": "https://discord.com/api/webhooks/YOUR_WEBHOOK_ID/YOUR_WEBHOOK_TOKEN",
                "embed_color": "3498db"  # Blue
            },
            
            # Server Shutdown
            {
                "name": "Server Offline",
                "enabled": True,
                "pattern": "Stripping inventory",
                "message_template": "⏹️ Rust server is shutting down",
                "webhook_type": "discord",
                "webhook_url": "https://discord.com/api/webhooks/YOUR_WEBHOOK_ID/YOUR_WEBHOOK_TOKEN",
                "embed_color": "95a5a6"  # Gray
            },
            
            # Critical Errors
            {
                "name": "Server Error Alert",
                "enabled": True,
                "pattern": r"\[ERROR\]|NullReferenceException|FATAL",
                "message_template": "⚠️ CRITICAL ERROR DETECTED - Check logs immediately!",
                "webhook_type": "discord",
                "webhook_url": "https://discord.com/api/webhooks/YOUR_ERROR_WEBHOOK_ID/YOUR_ERROR_WEBHOOK_TOKEN",
                "embed_color": "c0392b"  # Dark Red
            },
            
            # Kill/Death Tracking
            {
                "name": "Death Report",
                "enabled": True,
                "pattern": r"(\w+) was killed by (\w+)",
                "message_template": "☠️ {0} was killed by {1}",
                "webhook_type": "discord",
                "webhook_url": "https://discord.com/api/webhooks/YOUR_WEBHOOK_ID/YOUR_WEBHOOK_TOKEN",
                "embed_color": "e67e22"  # Orange
            },
            
            # Wipe Events
            {
                "name": "Wipe Started",
                "enabled": True,
                "pattern": r"Saving world|wipe|cleaning up",
                "message_template": "🧹 World wipe/reset in progress",
                "webhook_type": "discord",
                "webhook_url": "https://discord.com/api/webhooks/YOUR_WEBHOOK_ID/YOUR_WEBHOOK_TOKEN",
                "embed_color": "f39c12"  # Yellow
            }
        ]
    }
}


# Example 2: Generic JSON Webhook (for custom logging services)

GENERIC_WEBHOOK_EXAMPLE = {
    "console_triggers": [
        {
            "name": "Log to Custom API",
            "enabled": True,
            "pattern": r"(\w+) joined",
            "message_template": "{0} joined the Rust server",
            "webhook_type": "generic",
            "webhook_url": "https://your-logging-service.com/api/events",
            "embed_color": ""  # Not used for generic webhooks
        }
    ]
}

# The generic webhook sends JSON like:
"""
{
    "trigger": "Log to Custom API",
    "message": "john joined the Rust server",
    "groups": ["john"],
    "timestamp": "2024-01-15T14:30:45.123456"
}
"""


# Example 3: Advanced Pattern Matching

ADVANCED_EXAMPLES = {
    "console_triggers": [
        # Extract player name and steam ID from join event
        {
            "name": "Player Join with SteamID",
            "enabled": True,
            "pattern": r"(\w+) joined \[(\d+)\]",
            "message_template": "{0} (SteamID: {1}) connected",
            "webhook_type": "discord",
            "webhook_url": "https://discord.com/api/webhooks/...",
            "embed_color": "2ecc71"
        },
        
        # Multiple kill scenarios
        {
            "name": "Combat Report",
            "enabled": True,
            "pattern": r"(\w+).*?(?:killed|murdered|eliminated|executed).*?(\w+)",
            "message_template": "{0} defeated {1}",
            "webhook_type": "discord",
            "webhook_url": "https://discord.com/api/webhooks/...",
            "embed_color": "8e44ad"  # Purple
        },
        
        # Chat message capture (careful with this - can be spammy!)
        {
            "name": "Chat Mirror",
            "enabled": False,  # Disabled by default (high volume)
            "pattern": r"(\w+) : (.+?)(?=\n|$)",
            "message_template": "{0} in chat: {1}",
            "webhook_type": "discord",
            "webhook_url": "https://discord.com/api/webhooks/...",
            "embed_color": "34495e"  # Dark Gray
        },
        
        # Oxide plugin loading
        {
            "name": "Plugin Loaded",
            "enabled": True,
            "pattern": r"[Pp]lugin (\w+) (?:loaded|loaded successfully)",
            "message_template": "✅ Plugin loaded: {0}",
            "webhook_type": "discord",
            "webhook_url": "https://discord.com/api/webhooks/...",
            "embed_color": "27ae60"
        },
        
        # Server crashes
        {
            "name": "Server Crash Alert",
            "enabled": True,
            "pattern": r"crash|segfault|out of memory|Unhandled Exception",
            "message_template": "💥 Server has crashed! Immediate attention required!",
            "webhook_type": "discord",
            "webhook_url": "https://discord.com/api/webhooks/...",
            "embed_color": "c0392b"
        }
    ]
}


# How to Use These Examples:

"""
1. Get your Discord webhook URLs:
   - Right-click channel in Discord
   - Select "Edit Channel" → "Integrations" → "Webhooks"
   - Create new webhook and copy URL
   - Replace YOUR_WEBHOOK_ID and YOUR_WEBHOOK_TOKEN with actual values

2. Add to your config.yaml:
   - Copy the console_triggers list
   - Paste under automation: section
   - Update webhook URLs with your actual Discord webhooks
   - Save and restart the server

3. Test triggers:
   - In the UI, click "🔄 Reload" to load triggers
   - The console triggers are now active
   - Watch Discord channel for notifications as events occur

4. Disable spammy triggers:
   - Set enabled: False for chat message or other high-volume events
   - Adjust patterns to be more specific

5. Monitor performance:
   - Check Automation Activity log for trigger firings
   - Use statistics to see how often triggers match
"""
