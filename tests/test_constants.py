# tests/test_constants.py
"""Tests for constants and trade classification."""

import pytest

from app.constants import TradeThresholds, DiscordColors, ExcelStyles


class TestTradeThresholds:
    """Tests for trade classification using -10% to +10% breakeven rule."""

    def test_classify_win_above_10_percent(self):
        """Test gains > +10% are classified as WIN."""
        assert TradeThresholds.classify_trade(10.1) == "WIN"
        assert TradeThresholds.classify_trade(50.0) == "WIN"
        assert TradeThresholds.classify_trade(100.0) == "WIN"

    def test_classify_loss_below_minus_10_percent(self):
        """Test losses < -10% are classified as LOSS."""
        assert TradeThresholds.classify_trade(-10.1) == "LOSS"
        assert TradeThresholds.classify_trade(-50.0) == "LOSS"
        assert TradeThresholds.classify_trade(-100.0) == "LOSS"

    def test_classify_breakeven_between_minus_10_and_plus_10(self):
        """Test trades between -10% and +10% are classified as BREAKEVEN."""
        assert TradeThresholds.classify_trade(-10.0) == "BREAKEVEN"
        assert TradeThresholds.classify_trade(-5.0) == "BREAKEVEN"
        assert TradeThresholds.classify_trade(0.0) == "BREAKEVEN"
        assert TradeThresholds.classify_trade(5.0) == "BREAKEVEN"
        assert TradeThresholds.classify_trade(10.0) == "BREAKEVEN"

    def test_classify_edge_cases(self):
        """Test edge cases at exactly +/- 10%."""
        # Exactly at boundaries should be breakeven (inclusive)
        assert TradeThresholds.classify_trade(10.0) == "BREAKEVEN"
        assert TradeThresholds.classify_trade(-10.0) == "BREAKEVEN"

        # Just outside boundaries
        assert TradeThresholds.classify_trade(10.001) == "WIN"
        assert TradeThresholds.classify_trade(-10.001) == "LOSS"

    def test_classify_none_returns_unknown(self):
        """Test None gain returns UNKNOWN."""
        assert TradeThresholds.classify_trade(None) == "UNKNOWN"

    def test_thresholds_values(self):
        """Test threshold values are correct."""
        assert TradeThresholds.BREAKEVEN_MIN == -10.0
        assert TradeThresholds.BREAKEVEN_MAX == 10.0


class TestDiscordColors:
    """Tests for Discord color constants."""

    def test_colors_are_valid_hex(self):
        """Test all colors are valid hex values."""
        colors = [
            DiscordColors.TEAL,
            DiscordColors.BLUE,
            DiscordColors.PURPLE,
            DiscordColors.SLATE,
            DiscordColors.SUCCESS,
            DiscordColors.WARNING,
            DiscordColors.DANGER,
            DiscordColors.CYAN,
            DiscordColors.INDIGO,
            DiscordColors.STEEL,
        ]
        for color in colors:
            assert isinstance(color, int)
            assert 0 <= color <= 0xFFFFFF

    def test_teal_is_buy_color(self):
        """Test TEAL is used for BUY/open positions."""
        assert DiscordColors.TEAL == 0x1ABC9C

    def test_blue_is_profit_color(self):
        """Test BLUE is used for profit."""
        assert DiscordColors.BLUE == 0x3498DB

    def test_purple_is_loss_color(self):
        """Test PURPLE is used for loss."""
        assert DiscordColors.PURPLE == 0x9B59B6


class TestExcelStyles:
    """Tests for Excel styling constants."""

    def test_header_colors_are_valid_hex(self):
        """Test header colors are valid hex strings."""
        assert len(ExcelStyles.HEADER_BG_COLOR) == 6
        assert all(c in "0123456789ABCDEFabcdef" for c in ExcelStyles.HEADER_BG_COLOR)

    def test_win_loss_breakeven_colors_defined(self):
        """Test all outcome colors are defined."""
        assert ExcelStyles.WIN_COLOR
        assert ExcelStyles.WIN_FONT
        assert ExcelStyles.LOSS_COLOR
        assert ExcelStyles.LOSS_FONT
        assert ExcelStyles.BREAKEVEN_COLOR
        assert ExcelStyles.BREAKEVEN_FONT
