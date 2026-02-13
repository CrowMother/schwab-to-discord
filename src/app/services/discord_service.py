# src/app/services/discord_service.py
"""Discord webhook service."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Dict, List, Optional

import requests

from app.services.base import BaseService
from app.core.errors import DiscordError, DiscordSendError

if TYPE_CHECKING:
    from app.core.config import Settings


@dataclass
class DiscordEmbed:
    """Discord embed data structure."""
    title: Optional[str] = None
    description: Optional[str] = None
    color: Optional[int] = None
    fields: Optional[List[Dict[str, Any]]] = None
    footer: Optional[Dict[str, str]] = None
    timestamp: Optional[str] = None
    thumbnail: Optional[Dict[str, str]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to Discord API format."""
        data = {}
        if self.title:
            data["title"] = self.title
        if self.description:
            data["description"] = self.description
        if self.color is not None:
            data["color"] = self.color
        if self.fields:
            data["fields"] = self.fields
        if self.footer:
            data["footer"] = self.footer
        if self.timestamp:
            data["timestamp"] = self.timestamp
        if self.thumbnail:
            data["thumbnail"] = self.thumbnail
        return data


class DiscordChannel:
    """Represents a single Discord webhook channel."""

    def __init__(self, webhook_url: str, role_id: Optional[str] = None):
        """
        Initialize the Discord channel.

        Args:
            webhook_url: The Discord webhook URL.
            role_id: Optional role ID to mention.
        """
        self._webhook_url = webhook_url
        self._role_id = role_id
        self._enabled = bool(webhook_url and webhook_url.startswith("https://"))

    @property
    def enabled(self) -> bool:
        """Check if this channel is enabled."""
        return self._enabled

    def send(
        self,
        content: Optional[str] = None,
        embeds: Optional[List[DiscordEmbed]] = None,
        mention_role: bool = False,
    ) -> bool:
        """
        Send a message to this channel.

        Args:
            content: Text content.
            embeds: List of embeds to send.
            mention_role: Whether to mention the configured role.

        Returns:
            True if sent successfully.

        Raises:
            DiscordSendError: If sending fails.
        """
        if not self._enabled:
            return False

        payload: Dict[str, Any] = {}

        # Add role mention if requested
        if mention_role and self._role_id:
            payload["content"] = f"<@&{self._role_id}>"
        elif content:
            payload["content"] = content

        # Add embeds
        if embeds:
            payload["embeds"] = [e.to_dict() for e in embeds]

        if not payload:
            return False

        try:
            response = requests.post(
                self._webhook_url,
                json=payload,
                timeout=10,
            )
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException as e:
            raise DiscordSendError(f"Failed to send Discord message: {e}") from e


class DiscordService(BaseService):
    """
    Multi-channel Discord webhook service.

    Supports sending to primary and secondary webhooks,
    with optional role mentions.
    """

    def __init__(self, settings: "Settings"):
        """
        Initialize the Discord service.

        Args:
            settings: Application settings containing Discord credentials.
        """
        super().__init__("discord")
        self._settings = settings

        # Initialize channels
        self._primary = DiscordChannel(
            settings.discord_webhook,
            settings.discord_role_id,
        )
        self._secondary = DiscordChannel(
            settings.discord_webhook_2,
            settings.discord_role_id,
        )

        self._mark_initialized()

    @property
    def primary(self) -> DiscordChannel:
        """Get the primary Discord channel."""
        return self._primary

    @property
    def secondary(self) -> DiscordChannel:
        """Get the secondary Discord channel."""
        return self._secondary

    def send_to_all(
        self,
        content: Optional[str] = None,
        embeds: Optional[List[DiscordEmbed]] = None,
        mention_role: bool = False,
    ) -> bool:
        """
        Send a message to all enabled channels.

        Args:
            content: Text content.
            embeds: List of embeds to send.
            mention_role: Whether to mention the configured role.

        Returns:
            True if sent to at least one channel.
        """
        success = False

        for channel in [self._primary, self._secondary]:
            if channel.enabled:
                try:
                    if channel.send(content, embeds, mention_role):
                        success = True
                        # Small delay between channels to avoid rate limits
                        time.sleep(0.5)
                except DiscordSendError as e:
                    self._logger.error(f"Failed to send to channel: {e}")

        return success

    def send_trade_alert(
        self,
        embed: DiscordEmbed,
        mention_role: bool = True,
    ) -> bool:
        """
        Send a trade alert to all channels.

        Args:
            embed: The trade embed to send.
            mention_role: Whether to mention the role.

        Returns:
            True if sent successfully.
        """
        return self.send_to_all(embeds=[embed], mention_role=mention_role)

    def health_check(self) -> bool:
        """
        Check if Discord service is configured.

        Returns:
            True if at least one channel is enabled.
        """
        return self._primary.enabled or self._secondary.enabled
