from __future__ import annotations
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class FillTrade:
    # matching key foundation
    account_number: str
    instrument_id: int

    # identity
    order_id: int
    leg_id: Optional[int]
    execution_time: str  # from executionLegs[].time

    # instrument/details
    symbol: str
    asset_type: str
    instruction: str
    position_effect: Optional[str]  # OPENING/CLOSING

    # fill facts
    fill_quantity: float
    fill_price: Optional[float]

    # optional context
    status: Optional[str] = None
    description: Optional[str] = None
    entered_time: Optional[str] = None
    close_time: Optional[str] = None

    # ---- compatibility with your existing template builder ----
    @property
    def quantity(self) -> float:
        return self.fill_quantity

    @property
    def filled_quantity(self) -> float:
        return self.fill_quantity

    @property
    def remaining_quantity(self):
        return None

    @property
    def price(self):
        return self.fill_price
