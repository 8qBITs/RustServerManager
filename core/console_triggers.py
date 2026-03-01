"""
Console trigger system - monitors console output and triggers webhooks based on patterns.
"""

import re
import threading
from typing import Optional, Callable, List
from datetime import datetime
from urllib.request import Request, urlopen
import json
import logging

from utils.logger import log


class ConsoleTrigger:
    """Single console trigger configuration."""

    def __init__(self, trigger_dict: dict):
        self.name = trigger_dict.get("name", "Unnamed")
        self.enabled = trigger_dict.get("enabled", True)
        self.pattern = trigger_dict.get("pattern", "")
        self.webhook_url = trigger_dict.get("webhook_url", "")
        self.webhook_type = trigger_dict.get("webhook_type", "discord")  # discord, generic
        self.message_template = trigger_dict.get("message_template", "{0}")
        self.embed_color = trigger_dict.get("embed_color", "3498db")  # Discord blue
        
        # Compile regex for performance
        try:
            self.regex = re.compile(self.pattern)
            self.pattern_valid = True
        except re.error as e:
            self.pattern_valid = False
            self.pattern_error = str(e)
            log.warning(f"Invalid regex pattern '{self.pattern}': {e}")
        
        # Statistics
        self.match_count = 0
        self.last_match_time: Optional[datetime] = None
        self.last_match_groups: Optional[tuple] = None

    def check_match(self, text: str) -> Optional[tuple]:
        """Check if text matches pattern and return captured groups."""
        if not self.enabled or not self.pattern_valid:
            return None
        
        match = self.regex.search(text)
        if match:
            self.match_count += 1
            self.last_match_time = datetime.now()
            self.last_match_groups = match.groups()
            return match.groups()
        
        return None

    def get_stats(self) -> dict:
        """Get trigger statistics."""
        return {
            "name": self.name,
            "enabled": self.enabled,
            "match_count": self.match_count,
            "last_match": self.last_match_time.isoformat() if self.last_match_time else None,
        }


class ConsoleTriggersEngine:
    """Engine for monitoring console output and triggering webhooks."""

    def __init__(self):
        self.triggers: List[ConsoleTrigger] = []
        self._lock = threading.Lock()

    def load_triggers(self, trigger_list: list[dict]) -> None:
        """Load triggers from configuration."""
        with self._lock:
            self.triggers.clear()
            for trigger_dict in trigger_list:
                trigger = ConsoleTrigger(trigger_dict)
                self.triggers.append(trigger)
            log.info(f"Loaded {len(self.triggers)} console triggers")

    def process_output(self, text: str) -> None:
        """Process console output and trigger webhooks if patterns match."""
        with self._lock:
            triggers_to_fire = []
            
            for trigger in self.triggers:
                groups = trigger.check_match(text)
                if groups:
                    triggers_to_fire.append((trigger, groups))
        
        # Fire webhooks outside of lock to avoid blocking
        for trigger, groups in triggers_to_fire:
            self._fire_webhook(trigger, groups)

    def _fire_webhook(self, trigger: ConsoleTrigger, groups: tuple) -> None:
        """Send webhook asynchronously."""
        # Run in background thread to not block console
        thread = threading.Thread(
            target=self._send_webhook_async,
            args=(trigger, groups),
            daemon=True
        )
        thread.start()

    def _send_webhook_async(self, trigger: ConsoleTrigger, groups: tuple) -> None:
        """Send webhook in background thread."""
        try:
            if trigger.webhook_type == "discord":
                self._send_discord_webhook(trigger, groups)
            else:
                self._send_generic_webhook(trigger, groups)
        except Exception as e:
            log.error(f"Failed to send webhook for trigger '{trigger.name}': {e}")

    def _send_discord_webhook(self, trigger: ConsoleTrigger, groups: tuple) -> None:
        """Send Discord webhook with formatted message."""
        if not trigger.webhook_url:
            return

        # Build message from template and groups
        try:
            message = trigger.message_template.format(*groups) if groups else trigger.message_template
        except (IndexError, KeyError):
            message = trigger.message_template

        # Discord embed format
        hex_color = int(trigger.embed_color.replace("#", ""), 16) if trigger.embed_color else 0x3498db
        
        payload = {
            "embeds": [
                {
                    "title": f"🔔 {trigger.name}",
                    "description": message,
                    "color": hex_color,
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                }
            ]
        }

        self._post_webhook(trigger.webhook_url, payload)

    def _send_generic_webhook(self, trigger: ConsoleTrigger, groups: tuple) -> None:
        """Send generic JSON webhook."""
        if not trigger.webhook_url:
            return

        # Build message
        try:
            message = trigger.message_template.format(*groups) if groups else trigger.message_template
        except (IndexError, KeyError):
            message = trigger.message_template

        payload = {
            "trigger": trigger.name,
            "message": message,
            "groups": list(groups) if groups else [],
            "timestamp": datetime.utcnow().isoformat(),
        }

        self._post_webhook(trigger.webhook_url, payload)

    def _post_webhook(self, url: str, payload: dict) -> bool:
        """POST to webhook URL."""
        try:
            data = json.dumps(payload).encode("utf-8")
            req = Request(
                url,
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            
            with urlopen(req, timeout=10) as response:
                status = response.status
                if 200 <= status < 300:
                    log.debug(f"Webhook {url} sent successfully")
                    return True
                else:
                    log.warning(f"Webhook returned status {status}")
                    return False
        except Exception as e:
            log.error(f"Webhook POST failed: {e}")
            return False

    def get_trigger_stats(self) -> List[dict]:
        """Get statistics for all triggers."""
        with self._lock:
            return [t.get_stats() for t in self.triggers]

    def get_trigger_count(self) -> int:
        """Get number of active triggers."""
        with self._lock:
            return len([t for t in self.triggers if t.enabled])
