# src/app/services/registry.py
"""Service registry with lazy initialization."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from app.core.config import Settings
    from app.services.schwab_service import SchwabService
    from app.services.discord_service import DiscordService


logger = logging.getLogger(__name__)


class ServiceRegistry:
    """
    Lazy-loading registry for all external services.

    Services are initialized on first access, not at construction time.
    This allows for faster startup and better error isolation.

    Usage:
        registry = ServiceRegistry(settings)
        orders = registry.schwab.get_orders()
        registry.discord.send_trade_alert(embed)
    """

    def __init__(self, settings: "Settings"):
        """
        Initialize the service registry.

        Args:
            settings: Application settings.
        """
        self._settings = settings
        self._schwab: Optional["SchwabService"] = None
        self._discord: Optional["DiscordService"] = None

        logger.info("ServiceRegistry initialized (services will load on first access)")

    @property
    def schwab(self) -> "SchwabService":
        """
        Get the Schwab service (lazy initialization).

        Returns:
            Initialized Schwab service.
        """
        if self._schwab is None:
            from app.services.schwab_service import SchwabService
            self._schwab = SchwabService(self._settings)
            logger.info("SchwabService loaded")
        return self._schwab

    @property
    def discord(self) -> "DiscordService":
        """
        Get the Discord service (lazy initialization).

        Returns:
            Initialized Discord service.
        """
        if self._discord is None:
            from app.services.discord_service import DiscordService
            self._discord = DiscordService(self._settings)
            logger.info("DiscordService loaded")
        return self._discord

    def health_check(self) -> dict[str, bool]:
        """
        Check health of all initialized services.

        Returns:
            Dictionary mapping service name to health status.
        """
        results = {}

        if self._schwab is not None:
            results["schwab"] = self._schwab.health_check()
        if self._discord is not None:
            results["discord"] = self._discord.health_check()

        return results

    def shutdown(self) -> None:
        """
        Shutdown all services gracefully.

        Called during application shutdown.
        """
        logger.info("Shutting down services...")

        # Clear references (services will be garbage collected)
        self._schwab = None
        self._discord = None

        logger.info("Services shutdown complete")
