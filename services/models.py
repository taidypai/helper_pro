# models.py
from dataclasses import dataclass
from typing import Optional

@dataclass
# models.py
class Candle:
    def __init__(self, open: float, high: float, low: float, close: float, volume: float, timestamp: int):
        self.open = open
        self.high = high
        self.low = low
        self.close = close
        self.volume = volume
        self.timestamp = timestamp
    
    @property
    def body_size(self) -> float:
        """Вычисляет размер тела свечи"""
        return abs(self.close - self.open)
    
    @property
    def color(self) -> str:
        """Определяет цвет свечи"""
        return 'green' if self.close >= self.open else 'red'

@dataclass
class Imbalance:
    high: float
    low: float
    type: str  # 'buy' or 'sell'
    
    @property
    def size(self) -> float:
        return self.high - self.low
    
    @property
    def mid_price(self) -> float:
        return (self.high + self.low) / 2
    
    @property
    def recommendation(self) -> str:
        return f"Лимитный ордер в зоне: {self.mid_price:.2f}"
