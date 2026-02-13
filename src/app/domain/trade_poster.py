# src/app/domain/trade_poster.py
"""Trade posting - sends trades to Discord."""

from __future__ import annotations

import sqlite3
import logging
from typing import TYPE_CHECKING, List, Optional

from app.db.queries import get_unposted_trade_ids
from app.db.trades_repo import load_trade_from_db, mark_posted
from app.db.cost_basis_db import get_matches_for_sell
from app.discord.discord_message import build_option_embed
from app.discord.discord_webhook import post_embed
from app.domain.cost_basis import get_gain_for_order

if TYPE_CHECKING:
    from app.services.discord_service import DiscordService
    from app.core.config import Settings

logger = logging.getLogger(__name__)


class TradePoster:
    """
    Handles posting trades to Discord.

    Responsible for:
    - Finding unposted trades
    - Building Discord embeds
    - Sending to configured webhooks
    - Marking trades as posted
    """

    def __init__(
        self,
        settings: "Settings",
        discord: Optional["DiscordService"] = None
    ):
        """
        Initialize the trade poster.

        Args:
            settings: Application settings.
            discord: Optional Discord service (uses direct webhook if not provided).
        """
        self.settings = settings
        self.discord = discord
        self.logger = logging.getLogger("domain.trade_poster")

    def post_unposted_trades(
        self,
        conn: sqlite3.Connection,
        positions_by_symbol: Optional[dict] = None
    ) -> int:
        """
        Find and post all unposted trades.

        Args:
            conn: Database connection.
            positions_by_symbol: Optional dict of current positions.

        Returns:
            Number of trades successfully posted.
        """
        positions = positions_by_symbol or {}
        unposted_ids = get_unposted_trade_ids(conn)

        if not unposted_ids:
            return 0

        posted = 0
        for trade_id in unposted_ids:
            try:
                if self._post_trade(conn, trade_id, positions):
                    posted += 1
            except Exception as e:
                self.logger.error(f"Error posting trade {trade_id}: {e}")

        conn.commit()
        return posted

    def _post_trade(
        self,
        conn: sqlite3.Connection,
        trade_id: int,
        positions: dict
    ) -> bool:
        """
        Post a single trade to Discord.

        Args:
            conn: Database connection.
            trade_id: ID of the trade to post.
            positions: Current positions by symbol.

        Returns:
            True if posted successfully.
        """
        trade = load_trade_from_db(conn, trade_id)
        if not trade:
            self.logger.warning(f"Trade {trade_id} not found")
            return False

        # Get position and sold counts
        position_left = positions.get(trade.underlying, 0)
        total_sold = self._get_total_sold(conn, trade.symbol)

        # Get gain info for sell orders
        gain_pct = None
        entry_price = None
        if trade.instruction and "SELL" in trade.instruction.upper() and trade.order_id:
            gain_pct = get_gain_for_order(conn, trade.order_id)
            entry_price = self._get_entry_price(conn, trade.order_id)

        # Build the embed
        embed, role_mention = build_option_embed(
            trade,
            position_left=position_left,
            total_sold=total_sold,
            gain_pct=gain_pct,
            entry_price=entry_price,
            role_id=self.settings.discord_role_id
        )

        # Post to webhooks
        success = self._send_to_webhooks(embed, role_mention)

        if success:
            mark_posted(conn, trade_id, discord_message_id=None)

        return success

    def _send_to_webhooks(self, embed: dict, content: str) -> bool:
        """
        Send embed to all configured webhooks.

        Args:
            embed: Discord embed dictionary.
            content: Message content (role mention).

        Returns:
            True if sent to at least one webhook.
        """
        success = False

        # Primary webhook
        try:
            post_embed(
                self.settings.discord_webhook,
                embed,
                content=content,
                timeout=self.settings.schwab_timeout
            )
            success = True
        except Exception as e:
            self.logger.error(f"Failed to post to primary webhook: {e}")

        # Secondary webhook
        if self.settings.discord_webhook_2:
            try:
                post_embed(
                    self.settings.discord_webhook_2,
                    embed,
                    content=content,
                    timeout=self.settings.schwab_timeout
                )
            except Exception as e:
                self.logger.error(f"Failed to post to secondary webhook: {e}")

        return success

    def _get_total_sold(self, conn: sqlite3.Connection, symbol: str) -> int:
        """Get total quantity sold for a symbol."""
        try:
            cursor = conn.execute("""
                SELECT SUM(filled_quantity) FROM trades
                WHERE symbol = ? AND instruction LIKE '%SELL%'
            """, (symbol,))
            result = cursor.fetchone()[0]
            return int(result) if result else 0
        except sqlite3.Error as e:
            self.logger.error(f"Error getting total sold for {symbol}: {e}")
            return 0

    def _get_entry_price(self, conn: sqlite3.Connection, order_id: int) -> Optional[float]:
        """Get weighted average entry price from lot matches."""
        matches = get_matches_for_sell(conn, order_id)
        if not matches:
            return None

        total_qty = sum(m[2] for m in matches)
        if total_qty <= 0:
            return None

        return sum(m[2] * m[3] for m in matches) / total_qty
