from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from typing import Any, Optional, List
from dataclasses import dataclass, field

import requests

logger = logging.getLogger(__name__)


class DiscordWebhookError(RuntimeError):
    pass


# Import centralized colors
from app.constants import DiscordColors as Colors


@dataclass
class DiscordEmbed:
    """Discord embed builder with cool-toned theme."""
    title: str = ""
    description: str = ""
    color: int = Colors.SLATE
    url: str = ""
    timestamp: str = ""
    fields: List[dict] = field(default_factory=list)
    footer: dict = field(default_factory=dict)
    author: dict = field(default_factory=dict)
    thumbnail: dict = field(default_factory=dict)

    def add_field(self, name: str, value: str, inline: bool = True) -> "DiscordEmbed":
        """Add a field to the embed."""
        self.fields.append({
            "name": name,
            "value": str(value),
            "inline": inline
        })
        return self

    def set_footer(self, text: str, icon_url: str = "") -> "DiscordEmbed":
        """Set footer text."""
        self.footer = {"text": text}
        if icon_url:
            self.footer["icon_url"] = icon_url
        return self

    def set_author(self, name: str, url: str = "", icon_url: str = "") -> "DiscordEmbed":
        """Set author info."""
        self.author = {"name": name}
        if url:
            self.author["url"] = url
        if icon_url:
            self.author["icon_url"] = icon_url
        return self

    def set_thumbnail(self, url: str) -> "DiscordEmbed":
        """Set thumbnail image."""
        self.thumbnail = {"url": url}
        return self

    def set_timestamp(self) -> "DiscordEmbed":
        """Set timestamp to now (UTC)."""
        self.timestamp = datetime.now(timezone.utc).isoformat()
        return self

    def to_dict(self) -> dict:
        """Convert to Discord API format."""
        data = {}
        if self.title:
            data["title"] = self.title[:256]
        if self.description:
            data["description"] = self.description[:4096]
        if self.color:
            data["color"] = self.color
        if self.url:
            data["url"] = self.url
        if self.timestamp:
            data["timestamp"] = self.timestamp
        if self.fields:
            data["fields"] = self.fields[:25]
        if self.footer:
            data["footer"] = self.footer
        if self.author:
            data["author"] = self.author
        if self.thumbnail:
            data["thumbnail"] = self.thumbnail
        return data


def post_webhook(
    webhook_url: str,
    content: str,
    username: Optional[str] = None,
    avatar_url: Optional[str] = None,
    timeout: float = 10.0,
) -> dict[str, Any]:
    """
    Post a simple message to a Discord webhook.
    Returns response info (status, body). Raises on non-2xx.
    """
    # Skip if webhook is disabled
    if not webhook_url:
        logger.debug("Discord webhook disabled, skipping post")
        return {"status_code": 200, "body": {"skipped": True}}

    payload: dict[str, Any] = {"content": content}

    # Optional cosmetics (safe to omit)
    if username:
        payload["username"] = username
    if avatar_url:
        payload["avatar_url"] = avatar_url

    logger.debug("Posting to Discord webhook...")
    resp = requests.post(webhook_url, json=payload, timeout=timeout)

    if resp.status_code == 429:
        while resp.status_code == 429:
            retry_after = resp.json().get("retry_after", 5)
            logger.warning(f"Rate limited by Discord webhook, retrying after {retry_after} seconds...")
            time.sleep(retry_after)
            resp = requests.post(webhook_url, json=payload, timeout=timeout)

    if resp.status_code < 200 or resp.status_code >= 300:
        raise DiscordWebhookError(
            f"Discord webhook failed: {resp.status_code} {resp.text}"
        )

    # Discord webhooks sometimes return empty body; handle both
    try:
        body = resp.json() if resp.text else {}
    except json.JSONDecodeError:
        body = {"raw": resp.text}

    return {"status_code": resp.status_code, "body": body}


def post_embed(
    webhook_url: str,
    embed: DiscordEmbed,
    content: str = "",
    username: Optional[str] = None,
    avatar_url: Optional[str] = None,
    timeout: float = 10.0,
) -> dict[str, Any]:
    """
    Post an embed message to a Discord webhook.
    Returns response info (status, body). Raises on non-2xx.
    """
    # Skip if webhook is disabled
    if not webhook_url:
        logger.debug("Discord webhook disabled, skipping embed post")
        return {"status_code": 200, "body": {"skipped": True}}

    payload: dict[str, Any] = {
        "embeds": [embed.to_dict()]
    }

    # Optional content outside embed (for role mentions)
    if content:
        payload["content"] = content

    # Optional cosmetics
    if username:
        payload["username"] = username
    if avatar_url:
        payload["avatar_url"] = avatar_url

    logger.debug("Posting embed to Discord webhook...")
    resp = requests.post(webhook_url, json=payload, timeout=timeout)

    if resp.status_code == 429:
        while resp.status_code == 429:
            retry_after = resp.json().get("retry_after", 5)
            logger.warning(f"Rate limited by Discord webhook, retrying after {retry_after} seconds...")
            time.sleep(retry_after)
            resp = requests.post(webhook_url, json=payload, timeout=timeout)

    if resp.status_code < 200 or resp.status_code >= 300:
        raise DiscordWebhookError(
            f"Discord webhook failed: {resp.status_code} {resp.text}"
        )

    try:
        body = resp.json() if resp.text else {}
    except json.JSONDecodeError:
        body = {"raw": resp.text}

    return {"status_code": resp.status_code, "body": body}
