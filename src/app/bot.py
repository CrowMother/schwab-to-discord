# src/app/bot.py
"""Main bot orchestrator."""

from __future__ import annotations

import os
import signal
import sqlite3
import time
import logging
from typing import Optional

from requests.exceptions import RequestException, ConnectionError, Timeout

from app.core import Settings, get_settings, setup_logging
from app.core.errors import ConfigError, SchwabError, DiscordError
from app.services import ServiceRegistry
from app.db.trades_db import init_trades_db
from app.db.trade_state_db import init_trade_state_db
from app.db.cost_basis_db import init_cost_basis_db
from app.db.queries import get_unposted_trade_ids
from app.db.trades_repo import ensure_trade_state, load_trade_from_db, mark_posted, store_trade
from app.discord.discord_message import build_option_embed
from app.discord.discord_webhook import post_embed
from app.models.data import load_trade
from app.cost_basis import process_buy_order, process_sell_order, get_gain_for_order
from app.db.cost_basis_db import get_matches_for_sell
from app.scheduler import start_gsheet_scheduler, stop_gsheet_scheduler


logger = logging.getLogger(__name__)


class SchwabBot:
    """
    Main bot orchestrator.

    Coordinates all services and runs the main processing loop.
    """

    # Error handling constants
    MAX_CONSECUTIVE_ERRORS = 10
    BASE_RETRY_DELAY = 5  # seconds
    MAX_RETRY_DELAY = 300  # 5 minutes

    def __init__(self):
        """Initialize the bot."""
        self.settings: Optional[Settings] = None
        self.services: Optional[ServiceRegistry] = None
        self.conn: Optional[sqlite3.Connection] = None
        self.running = False
        self._consecutive_errors = 0

    def _init_settings(self) -> None:
        """Load and validate settings."""
        try:
            self.settings = get_settings()
            logger.info(f"Loaded settings for {self.settings.app_name}")
        except ConfigError as e:
            logger.critical(f"Configuration error: {e}")
            raise

    def _init_services(self) -> None:
        """Initialize the service registry."""
        self.services = ServiceRegistry(self.settings)
        logger.info("Service registry initialized")

    def _init_database(self) -> None:
        """Initialize database connection and tables."""
        db_path = self.settings.db_path
        os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)

        self.conn = sqlite3.connect(db_path)
        init_trades_db(db_path, self.conn)
        init_trade_state_db(db_path, self.conn)
        init_cost_basis_db(db_path, self.conn)

        logger.info(f"Database initialized at {db_path}")

    def _init_scheduler(self) -> None:
        """Start scheduled tasks if enabled."""
        if self.settings.gsheet_enabled:
            try:
                start_gsheet_scheduler()
                logger.info("Google Sheets export scheduler started")
            except Exception as e:
                logger.warning(f"Could not start Google Sheets scheduler: {e}")

    def _setup_signal_handlers(self) -> None:
        """Setup graceful shutdown handlers."""
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, initiating shutdown...")
            self.running = False

        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)

    def run(self) -> int:
        """
        Main entry point - initialize and run the bot.

        Returns:
            Exit code (0 for success, 1 for error).
        """
        setup_logging()
        logger.info("Starting Schwab to Discord bot...")

        try:
            self._init_settings()
            self._init_services()
            self._init_database()
            self._init_scheduler()
            self._setup_signal_handlers()

            self.running = True
            self._main_loop()
            return 0

        except ConfigError as e:
            logger.critical(f"Configuration error: {e}")
            return 1
        except Exception as e:
            logger.critical(f"Fatal error: {e}", exc_info=True)
            return 1
        finally:
            self.shutdown()

    def _main_loop(self) -> None:
        """Main processing loop with error handling."""
        logger.info("Entering main loop")

        while self.running:
            try:
                self._run_iteration()
                self._consecutive_errors = 0
                time.sleep(self.settings.poll_interval)

            except (ConnectionError, Timeout) as e:
                self._handle_error(e, "Network error")

            except RequestException as e:
                self._handle_error(e, "Request error")

            except sqlite3.Error as e:
                self._handle_error(e, "Database error", max_delay=60)

            except (SchwabError, DiscordError) as e:
                self._handle_error(e, "Service error")

            except KeyboardInterrupt:
                logger.info("Received keyboard interrupt")
                self.running = False

            except Exception as e:
                self._handle_error(e, "Unexpected error", log_traceback=True)

            if self._consecutive_errors >= self.MAX_CONSECUTIVE_ERRORS:
                logger.critical(
                    f"Too many consecutive errors ({self._consecutive_errors}), "
                    "shutting down"
                )
                self.running = False

    def _run_iteration(self) -> None:
        """Run a single iteration of the main loop."""
        # 1. Fetch and store new trades from Schwab
        raw_orders = self.services.schwab.get_orders()
        new_count = self._load_trade_orders(raw_orders)

        if new_count > 0:
            logger.info(f"Loaded {new_count} orders from Schwab")

        # 2. Get current positions
        positions_by_symbol = self._get_positions()

        # 3. Post unposted trades to Discord
        unposted_ids = get_unposted_trade_ids(self.conn)
        if unposted_ids:
            posted = self._send_unposted_trades(unposted_ids, positions_by_symbol)
            logger.info(f"Posted {posted} of {len(unposted_ids)} trades to Discord")

            # 4. Export if we posted new trades
            if posted > 0:
                self._run_export()

    def _load_trade_orders(self, raw_orders: list) -> int:
        """Load trade orders into database."""
        processed = 0

        for order in raw_orders:
            try:
                trade = load_trade(order)
                trade_id = store_trade(self.conn, trade)
                ensure_trade_state(self.conn, trade_id)

                # Process cost basis
                if trade.instruction and trade.order_id:
                    if "BUY" in trade.instruction.upper():
                        process_buy_order(
                            conn=self.conn,
                            order_id=trade.order_id,
                            symbol=trade.symbol,
                            filled_quantity=trade.filled_quantity,
                            price=trade.price,
                            entered_time=trade.entered_time or ""
                        )
                    elif "SELL" in trade.instruction.upper():
                        process_sell_order(
                            conn=self.conn,
                            order_id=trade.order_id,
                            symbol=trade.symbol,
                            filled_quantity=trade.filled_quantity,
                            sell_price=trade.price
                        )
                processed += 1

            except Exception as e:
                logger.error(f"Error processing order {order.get('orderId', 'unknown')}: {e}")

        self.conn.commit()
        return processed

    def _get_positions(self) -> dict:
        """Get current positions by symbol."""
        try:
            from app.api.positions import get_schwab_positions
            # Use the legacy positions function for now
            # TODO: Move to SchwabService
            from app.api.schwab import SchwabApi
            from app.models.config import load_config
            config = load_config(validate=False)
            client = SchwabApi(config)
            _, positions_by_symbol = get_schwab_positions(client)
            return positions_by_symbol
        except Exception as e:
            logger.warning(f"Could not fetch positions: {e}")
            return {}

    def _get_total_sold(self, symbol: str) -> int:
        """Get total quantity sold for a symbol."""
        try:
            cursor = self.conn.execute("""
                SELECT SUM(filled_quantity) FROM trades
                WHERE symbol = ? AND instruction LIKE '%SELL%'
            """, (symbol,))
            result = cursor.fetchone()[0]
            return int(result) if result else 0
        except sqlite3.Error as e:
            logger.error(f"Database error getting total sold for {symbol}: {e}")
            return 0

    def _send_unposted_trades(self, trade_ids: list, positions: dict) -> int:
        """Send unposted trades to Discord."""
        posted = 0

        for trade_id in trade_ids:
            try:
                trade = load_trade_from_db(self.conn, trade_id)
                if not trade:
                    continue

                position_left = positions.get(trade.underlying, 0)
                total_sold = self._get_total_sold(trade.symbol)

                # Get gain info for sell orders
                gain_pct = None
                entry_price = None
                if trade.instruction and "SELL" in trade.instruction.upper() and trade.order_id:
                    gain_pct = get_gain_for_order(self.conn, trade.order_id)
                    matches = get_matches_for_sell(self.conn, trade.order_id)
                    if matches:
                        total_qty = sum(m[2] for m in matches)
                        if total_qty > 0:
                            entry_price = sum(m[2] * m[3] for m in matches) / total_qty

                # Build embed
                embed, role_mention = build_option_embed(
                    trade,
                    position_left=position_left,
                    total_sold=total_sold,
                    gain_pct=gain_pct,
                    entry_price=entry_price,
                    role_id=self.settings.discord_role_id
                )

                # Post to webhooks
                post_embed(
                    self.settings.discord_webhook,
                    embed,
                    content=role_mention,
                    timeout=self.settings.schwab_timeout
                )

                if self.settings.discord_webhook_2:
                    post_embed(
                        self.settings.discord_webhook_2,
                        embed,
                        content=role_mention,
                        timeout=self.settings.schwab_timeout
                    )

                mark_posted(self.conn, trade_id, discord_message_id=None)
                posted += 1

            except Exception as e:
                logger.error(f"Error posting trade {trade_id}: {e}")

        self.conn.commit()
        return posted

    def _run_export(self) -> None:
        """Run Excel export after posting trades."""
        try:
            from app.exports.excel_exporter import export_trades
            export_trades()
            logger.info("Excel export completed")
        except Exception as e:
            logger.warning(f"Excel export failed: {e}")

    def _handle_error(
        self,
        error: Exception,
        error_type: str,
        max_delay: int = None,
        log_traceback: bool = False
    ) -> None:
        """Handle errors with exponential backoff."""
        self._consecutive_errors += 1
        max_delay = max_delay or self.MAX_RETRY_DELAY
        delay = min(
            self.BASE_RETRY_DELAY * (2 ** self._consecutive_errors),
            max_delay
        )

        if log_traceback:
            logger.error(
                f"{error_type} (attempt {self._consecutive_errors}): {error}",
                exc_info=True
            )
        else:
            logger.warning(
                f"{error_type} (attempt {self._consecutive_errors}): {error}"
            )

        logger.info(f"Retrying in {delay} seconds...")
        time.sleep(delay)

    def shutdown(self) -> None:
        """Graceful shutdown."""
        logger.info("Shutting down...")

        stop_gsheet_scheduler()

        if self.services:
            self.services.shutdown()

        if self.conn:
            self.conn.close()

        logger.info("Shutdown complete")


def run_bot() -> int:
    """
    Convenience function to run the bot.

    Returns:
        Exit code.
    """
    bot = SchwabBot()
    return bot.run()
