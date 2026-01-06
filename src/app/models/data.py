from dataclasses import dataclass

@dataclass
class Trade:
    symbol: str
    price: float
    volume: int



