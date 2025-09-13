import pytz
import asyncio
import datetime
from typing import Dict, Optional, List, Tuple
import logging
import aiohttp

from config import bot
from services.price_service import price_service
from services.time_utils import timeframe_manager, time_service, logger, timezone_service
from services.progress_service import progress_service

logger = logging.getLogger(__name__)

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
    
    @property
    def body_mid(self) -> float:
        return (self.open + self.close) / 2
    
    @property
    def range_mid(self) -> float:
        return (self.high + self.low) / 2

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
    
class AnalysisService:
    def __init__(self, price_service, time_service, timeframe_manager):
        self.price_service = price_service
        self.time_service = time_service
        self.timeframe_manager = timeframe_manager
        self.user_tasks: Dict[int, asyncio.Task] = {}
        self.candle_history: Dict[int, Dict[str, List[Candle]]] = {}
        self.active_analyses: Dict[int, bool] = {}
        self.found_imbalances: Dict[int, Dict[str, List[Imbalance]]] = {}

    async def safe_send_message(self, chat_id: int, text: str, parse_mode: Optional[str] = None) -> bool:
        """Безопасная отправка сообщений"""
        try:
            await bot.send_message(chat_id=chat_id, text=text, parse_mode=parse_mode)
            await asyncio.sleep(2)
            return True
        except Exception as e:
            logger.error(f"Ошибка отправки сообщения: {e}")
            return False

    def analyze_order_block(self, prev_candle: Candle, current_candle: Candle) -> Optional[str]:
        """
        Анализирует две свечи на наличие ордерблока по вашим правилам:
        1. Свечи разного цвета
        2. Вторая свеча в 2+ раза больше первой
        """
        if (prev_candle is None or current_candle is None or
            prev_candle.body_size == 0 or current_candle.body_size == 0):
            return None
        
        # Проверяем условия ордерблока
        if (prev_candle.color != current_candle.color and  # Разный цвет
            current_candle.body_size >= prev_candle.body_size * 2):  # В 2+ раза больше
            
            # Определяем тип ордерблока
            if current_candle.color == 'green':
                return 'buy'  # Зеленый ордерблок (бычий)
            else:
                return 'sell' # Красный ордерблок (медвежий)
        
        return None

    def find_imbalance(self, prev_candle: Candle, current_candle: Candle) -> Optional[Imbalance]:
        """
        Находит имбаланс между двумя свечами
        Имбаланс - это разрыв между свечами
        """
        if prev_candle is None or current_candle is None:
            return None
        
        # Бычий имбаланс (зеленая свеча перекрывает красную)
        if (prev_candle.color == 'red' and current_candle.color == 'green' and
            current_candle.low > prev_candle.high):
            return Imbalance(
                high=current_candle.low,
                low=prev_candle.high,
                type='buy'
            )
        
        # Медвежий имбаланс (красная свеча перекрывает зеленую)
        if (prev_candle.color == 'green' and current_candle.color == 'red' and
            current_candle.high < prev_candle.low):
            return Imbalance(
                high=prev_candle.low,
                low=current_candle.high,
                type='sell'
            )
        
        # Имбаланс внутри диапазона (текущая свеча полностью перекрывает предыдущую)
        if (current_candle.low > prev_candle.high or 
            current_candle.high < prev_candle.low):
            
            if current_candle.color == 'green':
                imbalance_type = 'buy'
                imbalance_high = min(current_candle.low, prev_candle.high)
                imbalance_low = max(current_candle.low, prev_candle.high)
            else:
                imbalance_type = 'sell'
                imbalance_high = min(current_candle.high, prev_candle.low)
                imbalance_low = max(current_candle.high, prev_candle.low)
            
            return Imbalance(
                high=imbalance_high,
                low=imbalance_low,
                type=imbalance_type
            )
        
        return None

    def create_order_block_message(self, symbol: str, signal: str, timeframe: str, 
                                 candles: List[Candle], imbalance: Optional[Imbalance] = None) -> str:
        """Создание сообщения об ордерблоке с имбалансом"""
        prev, current = candles
        
        direction = "🟢 ПОКУПКА" if signal == 'buy' else "🔴 ПРОДАЖА"
        block_type = "Бычий ордерблок" if signal == 'buy' else "Медвежий ордерблок"
        size_ratio = current.body_size / prev.body_size
        
        message = (
            f"*{symbol} - {block_type}* \n"
            f"• Сигнал: {direction}\n"
            f"• Таймфрейм: {timeframe}\n"
            f"• Размер свечи 1: {prev.body_size:.2f}\n"
            f"• Размер свечи 2: {current.body_size:.2f} (x{size_ratio:.1f})\n"
            f"• Цвета: {prev.color.upper()} → {current.color.upper()}\n"
            f"• Цена: {current.close:.2f}\n"
            f"• Время: {datetime.datetime.now().strftime('%H:%M:%S')}\n"
            f"• Дата: {datetime.datetime.now().strftime('%d.%m.%Y')}\n"
        )
        
        # Добавляем информацию об имбалансе если есть
        if imbalance:
            message += (
                f"\n*ИМБАЛАНС ОБНАРУЖЕН* \n"
                f"• Тип: {'Бычий' if imbalance.type == 'buy' else 'Медвежий'}\n"
                f"• Диапазон: {imbalance.low:.2f} - {imbalance.high:.2f}\n"
                f"• Размер имбаланса: {imbalance.size:.2f}\n"
                f"• *Рекомендуемая зона лимитного ордера:* {imbalance.mid_price:.2f}\n"
                f"• Стратегия: Лимитный ордер в середине имбаланса\n"
            )
        
        message += (
            f"\n *ВНИМАНИЕ:* Это только сигнал. Проверьте дополнительный анализ!"
        )
        
        return message

    async def get_candle_data(self, symbol: str, timeframe: str) -> Optional[Candle]:
        """Получает данные последней завершенной свечи"""
        try:
            # Используем ваш существующий price_service или Binance API
            ohlc_data = await self.price_service.get_binance_ohlc_async(symbol, timeframe)
            if ohlc_data:
                return Candle(
                    open=float(ohlc_data['open']),
                    high=float(ohlc_data['high']),
                    low=float(ohlc_data['low']),
                    close=float(ohlc_data['close']),
                    volume=float(ohlc_data['volume']),
                    timestamp=ohlc_data['timestamp']
                )
        except Exception as e:
            logger.error(f"Ошибка получения свечи {symbol}: {e}")
        
        return None

    async def initialize_candle_history(self, user_id: int, symbols: List[str], timeframe: str):
        """Инициализирует историю свечей для пользователя"""
        if user_id not in self.candle_history:
            self.candle_history[user_id] = {}
        if user_id not in self.found_imbalances:
            self.found_imbalances[user_id] = {}
        
        for symbol in symbols:
            if symbol not in self.candle_history[user_id]:
                self.candle_history[user_id][symbol] = []
                self.found_imbalances[user_id][symbol] = []
                
                # Загружаем последние 3 свечи для истории
                for _ in range(3):
                    candle = await self.get_candle_data(symbol, timeframe)
                    if candle:
                        self.candle_history[user_id][symbol].append(candle)
                
                logger.info(f"Загружено {len(self.candle_history[user_id][symbol])} свечей для {symbol}")

    async def analyze_candles_with_progress(self, user_id: int):
        """Анализ свечей на ордерблоки и имбалансы с прогресс-баром"""
        try:
            timeframe = self.timeframe_manager.get_timeframe()
            if not timeframe:
                await self.safe_send_message(user_id, "❌ Сначала выбери таймфрейм в настройках!")
                return
            
            symbols = ['BTCUSDT', 'ETHUSDT']
            self.active_analyses[user_id] = True
            
            logger.info(f"🔄 Начинаем анализ ордерблоков и имбалансов для user {user_id}, TF: {timeframe}")
            
            # Инициализируем историю свечей
            await self.initialize_candle_history(user_id, symbols, timeframe)
            
            while self.active_analyses.get(user_id, False):
                if asyncio.current_task().cancelled():
                    break
                
                # Ждем время до закрытия свечи
                wait_time, close_time = await self.time_service.get_time_to_candle_close(timeframe)
                
                if wait_time > 0:
                    logger.info(f"Ждем {wait_time} сек до закрытия свечи {timeframe}")
                    await progress_service.start_progress_animation(
                        user_id, wait_time, timeframe, close_time
                    )
                    await asyncio.sleep(wait_time)
                    await progress_service.stop_progress_animation(user_id)
                
                # Получаем новые свечи после закрытия
                new_candles = {}
                for symbol in symbols:
                    candle = await self.get_candle_data(symbol, timeframe)
                    if candle:
                        new_candles[symbol] = candle
                
                if not new_candles:
                    logger.warning("Не получилось получить данные свечей")
                    await asyncio.sleep(5)
                    continue
                
                # Анализируем каждую пару на ордерблоки и имбалансы
                for symbol in symbols:
                    if symbol in new_candles and symbol in self.candle_history[user_id]:
                        new_candle = new_candles[symbol]
                        history = self.candle_history[user_id][symbol]
                        
                        # Добавляем новую свечу в историю
                        history.append(new_candle)
                        
                        # Держим только последние 3 свечи
                        if len(history) > 3:
                            history = history[-3:]
                            self.candle_history[user_id][symbol] = history
                        
                        # Анализируем если есть минимум 2 свечи
                        if len(history) >= 2:
                            prev_candle, current_candle = history[-2], history[-1]
                            
                            # Ищем ордерблок
                            signal = self.analyze_order_block(prev_candle, current_candle)
                            
                            # Ищем имбаланс
                            imbalance = self.find_imbalance(prev_candle, current_candle)
                            
                            if imbalance:
                                logger.info(f"⚡ Найден имбаланс {symbol}: {imbalance.type}")
                                # Сохраняем найденный имбаланс
                                self.found_imbalances[user_id][symbol].append(imbalance)
                            
                            if signal:
                                logger.info(f"🎯 Найден ордерблок {symbol}: {signal}")
                                
                                # Получаем последний имбаланс для этого символа
                                last_imbalance = None
                                if self.found_imbalances[user_id][symbol]:
                                    last_imbalance = self.found_imbalances[user_id][symbol][-1]
                                
                                message = self.create_order_block_message(
                                    symbol, signal, timeframe, [prev_candle, current_candle], last_imbalance
                                )
                                await self.safe_send_message(user_id, message, parse_mode="Markdown")
                                
                                # Прерываем анализ после нахождения ордерблока
                                self.active_analyses[user_id] = False
                                break
                
                # Небольшая пауза перед следующим циклом
                await asyncio.sleep(2)
                    
        except asyncio.CancelledError:
            logger.info(f"⏹️ Анализ остановлен для user {user_id}")
        except Exception as e:
            logger.error(f"❌ Ошибка в анализе ордерблоков и имбалансов: {e}")
            await self.safe_send_message(user_id, 
                "*Произошла ошибка анализа*\n"
                "Попробуйте запустить анализ снова",
                parse_mode="Markdown"
            )
        finally:
            # Чистим за собой
            if user_id in self.user_tasks:
                del self.user_tasks[user_id]
            if user_id in self.candle_history:
                del self.candle_history[user_id]
            if user_id in self.active_analyses:
                del self.active_analyses[user_id]
            if user_id in self.found_imbalances:
                del self.found_imbalances[user_id]
            await progress_service.stop_progress_animation(user_id)

    def stop_analysis(self, user_id: int):
        """Останавливает анализ для пользователя"""
        self.active_analyses[user_id] = False
        if user_id in self.user_tasks:
            self.user_tasks[user_id].cancel()
        logger.info(f"⏹️ Анализ остановлен по команде для user {user_id}")

    async def get_imbalance_recommendation(self, user_id: int, symbol: str) -> Optional[str]:
        """Возвращает рекомендацию по последнему имбалансу"""
        if (user_id in self.found_imbalances and 
            symbol in self.found_imbalances[user_id] and 
            self.found_imbalances[user_id][symbol]):
            
            last_imbalance = self.found_imbalances[user_id][symbol][-1]
            return (
                f"*Рекомендация по имбалансу {symbol}:*\n"
                f"• Тип: {'Бычий' if last_imbalance.type == 'buy' else 'Медвежий'}\n"
                f"• Диапазон: {last_imbalance.low:.2f} - {last_imbalance.high:.2f}\n"
                f"• *Лимитный ордер:* {last_imbalance.mid_price:.2f}\n"
                f"• Размер имбаланса: {last_imbalance.size:.2f}"
            )
        return None

# Глобальный экземпляр
analysis_service = AnalysisService(price_service, time_service, timeframe_manager)