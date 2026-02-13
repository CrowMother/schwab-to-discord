# src/app/constants.py
"""Centralized constants for the schwab-to-discord application."""

from __future__ import annotations
from enum import IntEnum


class DiscordColors(IntEnum):
    """Cool-toned color palette for Discord embeds."""
    # Primary actions
    TEAL = 0x1ABC9C       # BUY/Open positions
    BLUE = 0x3498DB       # SELL with profit
    PURPLE = 0x9B59B6     # SELL with loss
    SLATE = 0x5865F2      # Neutral/Info (Discord blurple)

    # Status colors
    SUCCESS = 0x2ECC71    # Green - successful actions
    WARNING = 0xF39C12    # Amber - caution
    DANGER = 0xE74C3C     # Red - errors/stops

    # Cool tones for variety
    CYAN = 0x00CED1       # Dark cyan
    INDIGO = 0x6366F1     # Indigo
    STEEL = 0x607D8B      # Steel blue-grey


# Win/Loss/Break-even thresholds
class TradeThresholds:
    """Thresholds for classifying trade outcomes."""
    BREAKEVEN_MIN = -10.0  # -10% to +10% is break-even
    BREAKEVEN_MAX = 10.0

    @classmethod
    def classify_trade(cls, gain_pct: float | None) -> str:
        """Classify a trade as WIN, LOSS, or BREAKEVEN based on gain percentage."""
        if gain_pct is None:
            return "UNKNOWN"
        if gain_pct > cls.BREAKEVEN_MAX:
            return "WIN"
        elif gain_pct < cls.BREAKEVEN_MIN:
            return "LOSS"
        else:
            return "BREAKEVEN"


# Default paths
class Defaults:
    """Default configuration values."""
    DB_PATH = "/data/trades.db"
    TOKENS_DB = "/data/tokens.db"
    EXPORT_PATH = "/data/trades.xlsx"
    CREDENTIALS_PATH = "/data/credentials.json"

    # Timeouts
    SCHWAB_TIMEOUT = 10
    DISCORD_TIMEOUT = 10.0

    # Scheduling
    TIME_DELTA_DAYS = 7
    GSHEET_EXPORT_DAY = "sat"
    GSHEET_EXPORT_HOUR = 8
    GSHEET_EXPORT_MINUTE = 0

    # Retry settings
    MAX_RETRIES = 3
    RETRY_DELAY_BASE = 2  # seconds, exponential backoff
    MAIN_LOOP_INTERVAL = 5  # seconds between polling


# Excel styling (Bloomberg Finance Standard)
class ExcelStyles:
    """Excel styling constants for Bloomberg-style formatting."""
    HEADER_BG_COLOR = "1E3A5F"  # Dark blue
    HEADER_FONT_COLOR = "FFFFFF"  # White

    ROW_ALT_COLOR_1 = "FFFFFF"  # White
    ROW_ALT_COLOR_2 = "F5F5F5"  # Light gray

    # Conditional formatting colors
    WIN_COLOR = "C6EFCE"      # Light green background
    WIN_FONT = "006100"       # Dark green font
    LOSS_COLOR = "FFC7CE"     # Light red background
    LOSS_FONT = "9C0006"      # Dark red font
    BREAKEVEN_COLOR = "FFEB9C"  # Light yellow background
    BREAKEVEN_FONT = "9C5700"   # Dark yellow/brown font
