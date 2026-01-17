from __future__ import annotations

import json
import logging
from typing import Any, Optional

import requests

logger = logging.getLogger(__name__)


class DiscordWebhookError(RuntimeError):
    pass


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
    payload: dict[str, Any] = {"content": content}

    # Optional cosmetics (safe to omit)
    if username:
        payload["username"] = username
    if avatar_url:
        payload["avatar_url"] = avatar_url

    logger.debug("Posting to Discord webhook...")
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
