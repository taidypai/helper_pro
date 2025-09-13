# models.py
from dataclasses import dataclass
from typing import Optional

@dataclass
class Candle:
    open: float
    high: float
    low: float
    close: float
    volume: float
    timestamp: int
    
    @property
    def color(self) -> str:
        return 'green' if self.close > self.open else 'red'
    
    @property
    def body_size(self) -> float:
        return abs(self.close - self.open)
    
    @property
    def total_size(self) -> float:
        return self.high - self.low
    
    @property
    def upper_wick(self) -> float:
        return self.high - max(self.open, self.close)
    
    @property
    def lower_wick(self) -> float:
        return min(self.open, self.close) - self.low