# src/app/services/base.py
"""Base service class for all external services."""

from __future__ import annotations

import logging
from abc import ABC
from typing import Optional


class BaseService(ABC):
    """
    Base class for all external service wrappers.

    Provides common functionality like logging and health checking.
    """

    def __init__(self, name: str):
        """
        Initialize the base service.

        Args:
            name: Service name for logging.
        """
        self._name = name
        self._logger = logging.getLogger(f"services.{name}")
        self._initialized = False

    @property
    def name(self) -> str:
        """Get the service name."""
        return self._name

    @property
    def logger(self) -> logging.Logger:
        """Get the service logger."""
        return self._logger

    @property
    def is_initialized(self) -> bool:
        """Check if service is initialized."""
        return self._initialized

    def _mark_initialized(self) -> None:
        """Mark the service as initialized."""
        self._initialized = True
        self._logger.info(f"{self._name} service initialized")

    def health_check(self) -> bool:
        """
        Check if the service is healthy.

        Override in subclasses for actual health checks.

        Returns:
            True if healthy, False otherwise.
        """
        return self._initialized
