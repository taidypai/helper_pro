import pytz
import asyncio
import datetime
from typing import Dict, Optional, Tuple
import logging

from config import bot
from services.price_service import price_service
from services.time_utils import timeframe_manager, time_service, logger, timezone_service
from services.progress_service import progress_service

logger = logging.getLogger(__name__)

class AnalysisService:
    def __init__(self, price_service, time_service, timeframe_manager):
        self.price_service = price_service
        self.time_service = time_service
        self.timeframe_manager = timeframe_manager
        self.user_tasks: Dict[int, asyncio.Task] = {}
        self.last_prices: Dict[int, dict] = {}
        self.analysis_threshold = 0.01  # 1% изменение для сигнала

    async def safe_send_message(self, chat_id: int, text: str, parse_mode: Optional[str] = None) -> bool:
        """Безопасная отправка сообщений"""
        try:
            await bot.send_message(chat_id=chat_id, text=text, parse_mode=parse_mode)
            return True
        except Exception as e:
            logger.error(f"Ошибка отправки сообщения: {e}")
            return False

    def analyze_price_change(self, old_price: float, new_price: float) -> Optional[str]:
        """Анализ изменения цены с порогом"""
        if old_price == 0 or new_price == 0:
            return None
            
        change_percent = (new_price - old_price) / old_price
        
        if change_percent >= self.analysis_threshold:
            return 'green'
        elif change_percent <= -self.analysis_threshold:
            return 'red'
        return None

    def create_message(self, symbol: str, old_price: float, new_price: float, signal: str, timeframe: str) -> str:
        """Создание сообщения о сигнале"""
        change_percent = ((new_price - old_price) / old_price) * 100
        direction = "Зеленый" if signal == 'green' else "Красный"
        
        return (
            f"*{symbol} - {direction} ордер-блок*\n"
            f"• Таймфрейм: {timeframe}\n"
            f"• Изменение: {change_percent:+.2f}%\n"
            f"• Цена: {old_price:.2f} → {new_price:.2f}\n"
            f"• Время: {datetime.datetime.now().strftime('%H:%M:%S')}\n"
            f"• Дата: {datetime.datetime.now().strftime('%d.%m.%Y')}"
        )

    async def analyze_candles_with_progress(self, user_id: int):
        """Анализ с красивой анимацией прогресса"""
        try:
            timeframe = self.timeframe_manager.get_timeframe()
            if not timeframe:
                await self.safe_send_message(user_id, "Сначала выбери таймфрейм в настройках!")
                return
            
            logger.info(f"🔄 Начинаем анализ для user {user_id}, TF: {timeframe}")
            
            # Получаем начальные цены
            btc_price = await self.price_service.get_binance_price_async('BTCUSDT')
            eth_price = await self.price_service.get_binance_price_async('ETHUSDT')
            
            if btc_price is None or eth_price is None:
                await self.safe_send_message(user_id, "Не могу получить цены с Binance")
                return
            
            self.last_prices[user_id] = {'BTCUSDT': btc_price, 'ETHUSDT': eth_price}
            
            while True:
                if asyncio.current_task().cancelled():
                    break
                
                # Ждем время до закрытия свечи с анимацией
                wait_time, close_time = await self.time_service.get_time_to_candle_close(timeframe)
                
                if wait_time > 0:
                    logger.info(f"Ждем {wait_time} сек до закрытия свечи")
                    await progress_service.start_progress_animation(
                        user_id, wait_time, timeframe, close_time
                    )
                    await asyncio.sleep(wait_time)
                    await progress_service.stop_progress_animation(user_id)
                
                # Получаем новые цены
                new_btc = await self.price_service.get_binance_price_async('BTCUSDT')
                new_eth = await self.price_service.get_binance_price_async('ETHUSDT')
                
                if new_btc is None or new_eth is None:
                    logger.warning("Не получилось получить цены, пробуем снова")
                    await asyncio.sleep(5)
                    continue
                
                # Анализируем изменения
                old_btc = self.last_prices[user_id]['BTCUSDT']
                old_eth = self.last_prices[user_id]['ETHUSDT']
                
                btc_signal = self.analyze_price_change(old_btc, new_btc)
                eth_signal = self.analyze_price_change(old_eth, new_eth)
                
                # Обновляем последние цены
                self.last_prices[user_id] = {'BTCUSDT': new_btc, 'ETHUSDT': new_eth}
                
                # Отправляем сигналы если есть
                if btc_signal:
                    message = self.create_message('BTC', old_btc, new_btc, btc_signal, timeframe)
                    await self.safe_send_message(user_id, message, parse_mode="Markdown")
                
                if eth_signal:
                    message = self.create_message('ETH', old_eth, new_eth, eth_signal, timeframe)
                    await self.safe_send_message(user_id, message, parse_mode="Markdown")
                
                # Если были сигналы - прерываем анализ
                if btc_signal or eth_signal:
                    break
                    
                # Небольшая пауза перед следующим циклом
                await asyncio.sleep(2)
                    
        except asyncio.CancelledError:
            logger.info(f"⏹️ Анализ остановлен для user {user_id}")
            await progress_service.stop_progress_animation(user_id)
        except Exception as e:
            logger.error(f"❌ Ошибка в анализе: {e}")
            await progress_service.stop_progress_animation(user_id)
            await self.safe_send_message(user_id, 
                "*Произошла ошибка*\n"
                "Попробуйте запустить анализ снова",
                parse_mode="Markdown"
            )
        finally:
            # Чистим за собой
            if user_id in self.user_tasks:
                del self.user_tasks[user_id]
            if user_id in self.last_prices:
                del self.last_prices[user_id]
            await progress_service.stop_progress_animation(user_id)

# Глобальный экземпляр (будет переделано в DI)
analysis_service = AnalysisService(price_service, time_service, timeframe_manager)