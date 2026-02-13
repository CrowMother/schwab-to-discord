# src/app/main.py
"""Main application entry point with robust error handling."""

from __future__ import annotations

import os
import sqlite3
import time
import logging
from typing import Optional

from requests.exceptions import RequestException, ConnectionError, Timeout

from app.db.trades_db import init_trades_db
from app.db.trade_state_db import init_trade_state_db
from app.db.cost_basis_db import init_cost_basis_db
from app.db.queries import get_unposted_trade_ids
from app.db.trades_repo import ensure_trade_state, load_trade_from_db, mark_posted, store_trade
from app.discord.discord_message import build_option_embed
from app.discord.discord_webhook import post_embed
from app.models.data import load_trade
from app.models.config import load_config, ConfigurationError
from app.cost_basis import process_buy_order, process_sell_order, get_gain_for_order
from app.db.cost_basis_db import get_matches_for_sell
from app.api.positions import get_schwab_positions
from app.api.schwab import SchwabApi
from app.constants import Defaults
from app.utils.logging import setup_logging
from app.scheduler import start_gsheet_scheduler, stop_gsheet_scheduler

logger = logging.getLogger(__name__)


class MainLoopError(Exception):
    """Raised for recoverable errors in the main loop."""
    pass


def get_total_sold(conn: sqlite3.Connection, symbol: str) -> int:
    """Get total quantity sold for an exact symbol from trade history."""
    try:
        cursor = conn.execute("""
            SELECT SUM(filled_quantity) FROM trades
            WHERE symbol = ? AND instruction LIKE '%SELL%'
        """, (symbol,))
        result = cursor.fetchone()[0]
        return int(result) if result else 0
    except sqlite3.Error as e:
        logger.error(f"Database error getting total sold for {symbol}: {e}")
        return 0


def load_trade_orders(raw_orders: list, conn: sqlite3.Connection) -> int:
    """
    Load trade orders from Schwab API response into database.

    Returns:
        Number of orders processed.
    """
    processed = 0
    for order in raw_orders:
        try:
            logger.debug(f"Loading trade: {order}")
            trade = load_trade(order)
            logger.debug(f"Loaded trade: {trade}")

            trade_id = store_trade(conn, trade)
            logger.debug(f"Stored trade with ID: {trade_id}")
            ensure_trade_state(conn, trade_id)

            # Process cost basis for FIFO tracking
            if trade.instruction and trade.order_id:
                if "BUY" in trade.instruction.upper():
                    process_buy_order(
                        conn=conn,
                        order_id=trade.order_id,
                        symbol=trade.symbol,
                        filled_quantity=trade.filled_quantity,
                        price=trade.price,
                        entered_time=trade.entered_time or ""
                    )
                elif "SELL" in trade.instruction.upper():
                    process_sell_order(
                        conn=conn,
                        order_id=trade.order_id,
                        symbol=trade.symbol,
                        filled_quantity=trade.filled_quantity,
                        sell_price=trade.price
                    )
            processed += 1
        except Exception as e:
            logger.error(f"Error processing order {order.get('orderId', 'unknown')}: {e}")
            # Continue processing other orders

    conn.commit()
    return processed


def send_unposted_trades(conn: sqlite3.Connection, config, unposted_trade_ids: list,
                         positions_by_symbol: dict) -> int:
    """
    Send unposted trades to Discord.

    Returns:
        Number of trades successfully posted.
    """
    posted = 0
    for trade_id in unposted_trade_ids:
        try:
            trade = load_trade_from_db(conn, trade_id)
            if not trade:
                logger.warning(f"Trade {trade_id} not found in database")
                continue

            # Get position data - use underlying for position lookup
            position_left = positions_by_symbol.get(trade.underlying, 0)
            total_sold = get_total_sold(conn, trade.symbol)

            # Get gain percentage for sell orders only
            gain_pct = None
            entry_price = None
            if trade.instruction and "SELL" in trade.instruction.upper() and trade.order_id:
                gain_pct = get_gain_for_order(conn, trade.order_id)
                # Get entry price from lot matches if available
                matches = get_matches_for_sell(conn, trade.order_id)
                if matches:
                    # Weighted average entry price
                    total_qty = sum(m[2] for m in matches)
                    if total_qty > 0:
                        entry_price = sum(m[2] * m[3] for m in matches) / total_qty

            # Build embed using Option Bot format
            embed, role_mention = build_option_embed(
                trade,
                position_left=position_left,
                total_sold=total_sold,
                gain_pct=gain_pct,
                entry_price=entry_price,
                role_id=config.discord_role_id
            )

            # Post to primary webhook
            resp = post_embed(config.discord_webhook, embed, content=role_mention,
                              timeout=config.schwab_timeout)
            logger.debug(f"Posted trade ID {trade_id} to Discord (primary), response: {resp}")

            # Post to secondary webhook if configured
            if config.discord_webhook_secondary:
                resp2 = post_embed(config.discord_webhook_secondary, embed, content=role_mention,
                                   timeout=config.schwab_timeout)
                logger.debug(f"Posted trade ID {trade_id} to Discord (secondary), response: {resp2}")

            with conn:
                mark_posted(conn, trade_id, discord_message_id=None)
            posted += 1

        except Exception as e:
            logger.error(f"Error posting trade {trade_id}: {e}")
            # Continue with other trades

    conn.commit()
    return posted


def run_export(export_func, name: str) -> None:
    """Run an export function with error handling."""
    try:
        export_func()
        logger.info(f"{name} export completed successfully")
    except Exception as e:
        logger.warning(f"{name} export failed: {e}")


def main_loop(conn: sqlite3.Connection, config, client: SchwabApi) -> None:
    """
    Main processing loop with proper error handling and retry logic.

    Uses exponential backoff for transient errors, continues on non-fatal errors.
    """
    consecutive_errors = 0
    max_consecutive_errors = 10
    base_delay = Defaults.RETRY_DELAY_BASE

    while True:
        try:
            # Fetch orders from Schwab
            raw_orders = client.get_orders(config)
            load_trade_orders(raw_orders, conn)

            # Get current positions from Schwab
            _, positions_by_symbol = get_schwab_positions(client)

            # Send unposted trades to Discord
            unposted_trade_ids = get_unposted_trade_ids(conn)
            if unposted_trade_ids:
                posted_count = send_unposted_trades(conn, config, unposted_trade_ids, positions_by_symbol)
                logger.info(f"Posted {posted_count} of {len(unposted_trade_ids)} trades to Discord")

                # Auto-export to Excel when new trades are processed
                if posted_count > 0:
                    try:
                        from app.exports.excel_exporter import export_trades
                        run_export(export_trades, "Excel")
                    except ImportError:
                        # Fall back to old export if new one not available yet
                        try:
                            from export_trades import export_trades as legacy_export
                            run_export(legacy_export, "Excel (legacy)")
                        except ImportError:
                            logger.debug("No export module available")

            # Reset error counter on successful iteration
            consecutive_errors = 0
            time.sleep(Defaults.MAIN_LOOP_INTERVAL)

        except (ConnectionError, Timeout) as e:
            # Network errors - retry with backoff
            consecutive_errors += 1
            delay = min(base_delay * (2 ** consecutive_errors), 300)  # Max 5 minutes
            logger.warning(f"Network error (attempt {consecutive_errors}): {e}")
            logger.info(f"Retrying in {delay} seconds...")
            time.sleep(delay)

        except RequestException as e:
            # Other request errors - log and retry
            consecutive_errors += 1
            delay = min(base_delay * (2 ** consecutive_errors), 300)
            logger.error(f"Request error (attempt {consecutive_errors}): {e}")
            time.sleep(delay)

        except sqlite3.Error as e:
            # Database errors - log and retry (might be locked)
            consecutive_errors += 1
            delay = min(base_delay * consecutive_errors, 60)
            logger.error(f"Database error (attempt {consecutive_errors}): {e}")
            time.sleep(delay)

        except KeyboardInterrupt:
            logger.info("Received shutdown signal, exiting...")
            break

        except Exception as e:
            # Unexpected errors - log full traceback, increment counter
            consecutive_errors += 1
            delay = min(base_delay * (2 ** consecutive_errors), 300)
            logger.error(f"Unexpected error (attempt {consecutive_errors}): {e}", exc_info=True)
            time.sleep(delay)

        # Check if we've hit too many consecutive errors
        if consecutive_errors >= max_consecutive_errors:
            logger.critical(f"Too many consecutive errors ({consecutive_errors}), shutting down")
            break


def main() -> None:
    """Application entry point."""
    # Set up logging first
    setup_logging()

    # Load and validate configuration
    try:
        config = load_config(validate=True)
    except ConfigurationError as e:
        logger.critical(f"Configuration error: {e}")
        logger.critical("Please check your .env and .env.secrets files")
        return

    # Initialize database
    os.makedirs(os.path.dirname(config.db_path) or ".", exist_ok=True)
    conn = sqlite3.connect(config.db_path)

    try:
        init_trades_db(config.db_path, conn)
        init_trade_state_db(config.db_path, conn)
        init_cost_basis_db(config.db_path, conn)

        logger.info("Starting %s", config.app_name)

        # Start weekly Google Sheets export scheduler
        try:
            start_gsheet_scheduler()
            logger.info("Weekly Google Sheets export scheduler started")
        except Exception as e:
            logger.warning(f"Could not start Google Sheets scheduler: {e}")

        # Initialize Schwab API client
        client = SchwabApi(config)
        logger.info(f"Schwab API client initialized")

        # Run main loop
        main_loop(conn, config, client)

    finally:
        # Cleanup
        logger.info("Shutting down...")
        stop_gsheet_scheduler()
        conn.close()
        logger.info("Shutdown complete")


if __name__ == "__main__":
    main()
