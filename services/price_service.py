import asyncio
import time
from tradingview_ta import TA_Handler
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PriceService:
    def __init__(self, screener, exchange):
        self.screener = screener
        self.exchange = exchange
        self.interval = '1d'
        self.cache = {}
        self.cache_ttl = 300

    def _get_cache_key(self, symbol):
        return f"{self.screener}:{self.exchange}:{symbol}"

    def _get_from_cache(self, symbol):
        cache_key = self._get_cache_key(symbol)
        if cache_key in self.cache:
            data, timestamp = self.cache[cache_key]
            if time.time() - timestamp < self.cache_ttl:
                logger.info(f"✓ Данные из кэша для {symbol}")
                return data
        return None

    def _save_to_cache(self, symbol, price):
        cache_key = self._get_cache_key(symbol)
        self.cache[cache_key] = (price, time.time())
        logger.info(f"✓ Данные сохранены в кэш для {symbol}")

    def _get_price_from_api(self, symbol):
        """Синхронный метод для работы с TradingView TA"""
        try:
            price = TA_Handler(
                symbol=symbol,
                screener=self.screener,
                exchange=self.exchange,
                interval=self.interval
            )
            price_data = price.get_analysis()
            return price_data
        except Exception as e:
            logger.error(f"Ошибка API для {symbol}: {e}")
            return None

    async def get_price(self, symbol):
        """Асинхронная версия получения цены"""
        cached_price = self._get_from_cache(symbol)
        if cached_price is not None:
            return cached_price

        try:
            logger.info(f"🔄 Запрос к API для {symbol}...")
            loop = asyncio.get_event_loop()
            current_price = await loop.run_in_executor(None, self._get_price_from_api, symbol)

            if current_price is not None:
                self._save_to_cache(symbol, current_price)
                return current_price
            return None

        except Exception as e:
            logger.error(f"Ошибка в get_price для {symbol}: {e}")
            return None

# Глобальные экземпляры сервисов
crypto_service = PriceService('crypto', 'BINANCE')
forex_service = PriceService('forex', 'FX_IDC')

# ✅ ПРАВИЛЬНО: асинхронная main функция
async def main():
    data = await crypto_service.get_price('BTCUSDT')
    if data:
        print("✅ Данные получены успешно!")
        print(f"Цена закрытия: {data.indicators.get('close')}")
    else:
        print("❌ Не удалось получить данные")

if __name__ == '__main__':
    # Запускаем асинхронную функцию
    asyncio.run(main())