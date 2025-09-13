from binance.client import Client
from binance.exceptions import BinanceAPIException
import aiohttp
import asyncio
from typing import Optional, Dict, Tuple
import logging
import time
from functools import wraps

logger = logging.getLogger(__name__)

def retry(max_retries: int = 3, delay: float = 1.0):
    """Декоратор для повторных попыток"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_error = e
                    if attempt < max_retries - 1:
                        await asyncio.sleep(delay * (attempt + 1))
                    logger.warning(f"Attempt {attempt + 1} failed: {e}")
            raise last_error
        return wrapper
    return decorator

class PriceService:
    def __init__(self):
        self.client = Client()
        self.session: Optional[aiohttp.ClientSession] = None
        self.price_cache: Dict[str, Tuple[float, float]] = {}
        self.cache_timeout = 30
    
    async def initialize(self):
        """Инициализация асинхронной сессии"""
        self.session = aiohttp.ClientSession()
    
    async def close(self):
        """Закрытие сессии"""
        if self.session:
            await self.session.close()
    
    def get_cached_price(self, symbol: str) -> Optional[float]:
        """Получение цены из кэша"""
        if symbol in self.price_cache:
            price, timestamp = self.price_cache[symbol]
            if time.time() - timestamp < self.cache_timeout:
                return price
        return None
    
    def set_cached_price(self, symbol: str, price: float):
        """Сохранение цены в кэш"""
        self.price_cache[symbol] = (price, time.time())
    
    @retry(max_retries=3, delay=1.0)
    async def get_binance_ohlc_async(self, symbol: str, timeframe: str) -> Optional[dict]:
        """
        Получает последнюю завершенную свечу с Binance
        """
        try:
            # Конвертируем таймфрейм в формат Binance
            tf_mapping = {
                '1m': '1m', '5m': '5m', '15m': '15m',
                '30m': '30m', '1h': '1h', '4h': '4h',
                '1d': '1d', '1w': '1w'
            }
            
            binance_tf = tf_mapping.get(timeframe, '1h')
            url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={binance_tf}&limit=1"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data and len(data) > 0:
                            kline = data[0]
                            return {
                                'open': float(kline[1]),
                                'high': float(kline[2]),
                                'low': float(kline[3]),
                                'close': float(kline[4]),
                                'volume': float(kline[5]),
                                'timestamp': kline[0]
                            }
        except Exception as e:
            logger.error(f"Ошибка получения OHLC данных: {e}")
        
        return None
    async def get_binance_price_async(self, symbol: str) -> Optional[float]:
        """Асинхронное получение цены с кэшированием"""
        cached_price = self.get_cached_price(symbol)
        if cached_price is not None:
            return cached_price
        
        try:
            url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
            if self.session is None:
                await self.initialize()
            
            async with self.session.get(url, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    price = float(data['price'])
                    self.set_cached_price(symbol, price)
                    return price
                else:
                    logger.error(f"HTTP error: {response.status}")
                    return None
        except asyncio.TimeoutError:
            logger.error(f"Timeout getting price for {symbol}")
            return None
        except Exception as e:
            logger.error(f"Async price error: {e}")
            return self.get_binance_price_sync(symbol)
    
    def get_binance_price_sync(self, symbol: str) -> Optional[float]:
        """Синхронное получение цены с Binance"""
        try:
            ticker = self.client.get_symbol_ticker(symbol=symbol)
            price = float(ticker['price'])
            self.set_cached_price(symbol, price)
            return price
        except BinanceAPIException as e:
            logger.error(f"Binance API error: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return None

# Глобальный экземпляр сервиса
price_service = PriceService()