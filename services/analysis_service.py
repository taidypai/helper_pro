# analysis_service.py
import asyncio
from typing import Dict, Optional, List
import logging

from config import bot
from services.price_service import price_service
from services.time_utils import timeframe_manager, time_service, logger, timezone_service
from services.progress_service import progress_service
from .models import Candle

logger = logging.getLogger(__name__)
    
class AnalysisService:
    def __init__(self, price_service, time_service, timeframe_manager):
        self.price_service = price_service
        self.time_service = time_service
        self.timeframe_manager = timeframe_manager
        self.user_tasks: Dict[int, asyncio.Task] = {}
        self.candle_history: Dict[int, Dict[str, List[Candle]]] = {}
        self.active_analyses: Dict[int, bool] = {}
        self.last_prices: Dict[int, float] = {}
        self.analysis_tasks: Dict[int, Dict[str, asyncio.Task]] = {}
        self.progress_managers: Dict[int, asyncio.Task] = {}

    async def safe_send_message(self, chat_id: int, text: str, parse_mode: Optional[str] = None) -> bool:
        """Безопасная отправка сообщений"""
        try:
            await bot.send_message(chat_id=chat_id, text=text, parse_mode=parse_mode)
            await asyncio.sleep(1)
            return True
        except Exception as e:
            logger.error(f"Ошибка отправки сообщения: {e}")
            return False

    def analyze_order_block(self, prev_candle: Candle, current_candle: Candle) -> Optional[str]:
        """
        Анализирует две свечи на наличие ордерблока:
        1. Свечи разного цвета
        2. Вторая свеча в 2+ раза больше первой по телу
        """
        if (prev_candle is None or current_candle is None or
            prev_candle.body_size == 0 or current_candle.body_size == 0):
            return None
        
        # Определяем цвет свечей через свойства
        prev_color = prev_candle.color
        current_color = current_candle.color
        
        # Проверяем условия ордерблока
        if (prev_color != current_color and  # Разный цвет
            current_candle.body_size >= prev_candle.body_size * 2):  # В 2+ раза больше
            
            # Определяем тип ордерблока
            if current_color == 'green':
                return 'buy'  # Зеленый ордерблок (бычий)
            else:
                return 'sell' # Красный ордерблок (медвежий)
        
        return None

    def create_order_block_message(self, symbol: str, signal: str, timeframe: str, 
                         candles: List[Candle]) -> str:
        """Создание сообщения об ордерблоке"""
        from services.message_utils import escape_markdown
        
        prev, current = candles
        
        # Используем свойства для получения цвета и размера
        prev_color = prev.color
        current_color = current.color
        size_ratio = current.body_size / prev.body_size
        
        direction = "🟢 LONG" if signal == 'buy' else "🔴 SHORT"
        block_type = "Бычий ордерблок" if signal == 'buy' else "Медвежий ордерблок"
        
        # Экранируем все специальные символы
        symbol_escaped = escape_markdown(symbol)
        timeframe_escaped = escape_markdown(timeframe)
        direction_escaped = escape_markdown(direction)
        block_type_escaped = escape_markdown(block_type)
        
        message = (
            f"*{symbol_escaped} - {block_type_escaped}* (x{size_ratio:.1f}) \n"
            f"• Сигнал: {direction_escaped}\n"
            f"• Таймфрейм: {timeframe_escaped}\n"
            f"• Цвета: {escape_markdown(prev_color.upper())} → {escape_markdown(current_color.upper())}\n"
            f"• Закрытие: {current.close:.2f}\n"
            f"\n*ВНИМАНИЕ:* Это только сигнал. Проверьте дополнительный анализ!"
        )
        
        return message

    async def get_candle_data(self, symbol: str, timeframe: str) -> Optional[Candle]:
        """Получает данные последней завершенной свечи"""
        try:
            if symbol == 'IMOEX':
                # Для IMOEX используем специальный метод
                imoex_data = await self.price_service.get_imoex_data()
                if imoex_data:
                    return Candle(
                        open=float(imoex_data['open']),
                        high=float(imoex_data['high']),
                        low=float(imoex_data['low']),
                        close=float(imoex_data['close']),
                        volume=float(imoex_data['volume']),
                        timestamp=imoex_data['timestamp']
                    )
            else:
                # Для крипты используем Binance
                async with self.price_service as ps:  # Используем контекстный менеджер
                    ohlc_data = await ps.get_binance_ohlc_async(symbol, timeframe)
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
        
        for symbol in symbols:
            if symbol not in self.candle_history[user_id]:
                self.candle_history[user_id][symbol] = []
                
                for _ in range(2):
                    candle = await self.get_candle_data(symbol, timeframe)
                    if candle:
                        self.candle_history[user_id][symbol].append(candle)
                
                logger.info(f"Загружено {len(self.candle_history[user_id][symbol])} свечей для {symbol}")

    async def manage_progress(self, user_id: int, timeframe: str):
        """Управление прогресс-баром (отправляется один раз)"""
        try:
            while self.active_analyses.get(user_id, False):
                wait_time, close_time = await self.time_service.get_time_to_candle_close(timeframe)
                
                if wait_time > 0:
                    logger.info(f"Ждем {wait_time} сек до закрытия свечи {timeframe}")
                    await progress_service.start_progress_animation(
                        user_id, wait_time, timeframe, close_time
                    )
                    await asyncio.sleep(wait_time)
                    await progress_service.stop_progress_animation(user_id)
                
                await asyncio.sleep(1)
                    
        except asyncio.CancelledError:
            logger.info(f"⏹️ Управление прогрессом остановлено для user {user_id}")
        except Exception as e:
            logger.error(f"❌ Ошибка в управлении прогрессом: {e}")

    async def analyze_symbol(self, user_id: int, symbol: str, timeframe: str):
        """Анализ отдельного символа (только после закрытия свечи)"""
        try:
            logger.info(f"🔄 Начинаем анализ {symbol} для user {user_id}")
            
            # Инициализируем историю для этого символа
            if user_id not in self.candle_history:
                self.candle_history[user_id] = {}
            if symbol not in self.candle_history[user_id]:
                self.candle_history[user_id][symbol] = []
                # Загружаем 2 последние завершенные свечи
                for _ in range(2):
                    candle = await self.get_candle_data(symbol, timeframe)
                    if candle:
                        self.candle_history[user_id][symbol].append(candle)
            
            # Основной цикл анализа
            while self.active_analyses.get(user_id, False):
                if asyncio.current_task().cancelled():
                    break
                
                # Ждем до закрытия следующей свечи
                wait_time, close_time = await self.time_service.get_time_to_candle_close(timeframe)
                if wait_time > 0:
                    logger.info(f"Ждем {wait_time} сек до закрытия свечи {timeframe}")
                    await asyncio.sleep(wait_time)
                
                # Получаем новую завершенную свечу
                new_candle = await self.get_candle_data(symbol, timeframe)
                
                if not new_candle:
                    logger.warning(f"{symbol}: Не получилось получить данные свечи")
                    continue
                
                # Обновляем историю (добавляем новую, удаляем старую)
                history = self.candle_history[user_id][symbol]
                history.append(new_candle)
                
                # Держим только последние 2 свечи
                if len(history) > 2:
                    history.pop(0)
                
                # Анализируем если есть минимум 2 свечи
                if len(history) >= 2:
                    prev_candle, current_candle = history[-2], history[-1]
                    
                    # Проверяем, что свечи разные (не дубликаты)
                    if prev_candle.timestamp != current_candle.timestamp:
                        # Ищем ордерблок
                        signal = self.analyze_order_block(prev_candle, current_candle)
                        
                        if signal:
                            logger.info(f"Найден ордерблок {symbol}: {signal}")
                            
                            message = self.create_order_block_message(
                                symbol, signal, timeframe, [prev_candle, current_candle]
                            )
                            await self.safe_send_message(user_id, message, parse_mode="Markdown")
                    
        except asyncio.CancelledError:
            logger.info(f"⏹️ Анализ {symbol} остановлен для user {user_id}")
        except Exception as e:
            logger.error(f"❌ Ошибка в анализе {symbol}: {e}")

    async def analyze_candles_with_progress(self, user_id: int):
        """Запуск анализа (работает до команды stop)"""
        try:
            timeframe = self.timeframe_manager.get_timeframe()
            if not timeframe:
                await self.safe_send_message(user_id, "Сначала выбери таймфрейм в настройках!")
                return
            
            symbols = ['BTCUSDT', 'ETHUSDT', 'IMOEX']
            self.active_analyses[user_id] = True
            
            logger.info(f"🔄 Начинаем бесконечный анализ ордерблоков для user {user_id}, TF: {timeframe}")
            
            # Запускаем задачу управления прогрессом
            self.progress_managers[user_id] = asyncio.create_task(
                self.manage_progress(user_id, timeframe)
            )
            
            # Создаем отдельные задачи для каждого символа
            self.analysis_tasks[user_id] = {}
            for symbol in symbols:
                task = asyncio.create_task(self.analyze_symbol(user_id, symbol, timeframe))
                self.analysis_tasks[user_id][symbol] = task
            
            # Бесконечно ждем, пока не будет остановлено
            while self.active_analyses.get(user_id, False):
                await asyncio.sleep(1)
                    
        except asyncio.CancelledError:
            logger.info(f"⏹️ Анализ остановлен для user {user_id}")
        except Exception as e:
            logger.error(f"❌ Ошибка в анализе ордерблоков: {e}")
            await self.safe_send_message(user_id, 
                "*Произошла ошибка анализа*\n"
                "Попробуйте запустить анализ снова",
                parse_mode="Markdown"
            )
        finally:
            # Останавливаем все задачи
            if user_id in self.progress_managers:
                self.progress_managers[user_id].cancel()
                try:
                    await self.progress_managers[user_id]
                except:
                    pass
                del self.progress_managers[user_id]
            
            if user_id in self.analysis_tasks:
                for task in self.analysis_tasks[user_id].values():
                    task.cancel()
                del self.analysis_tasks[user_id]
            
            # Чистим за собой
            if user_id in self.candle_history:
                del self.candle_history[user_id]
            if user_id in self.active_analyses:
                del self.active_analyses[user_id]
            await progress_service.stop_progress_animation(user_id)

    def stop_analysis(self, user_id: int):
        """Останавливает анализ для пользователя"""
        if user_id in self.active_analyses:
            self.active_analyses[user_id] = False
            logger.info(f"⏹️ Анализ остановлен по команде для user {user_id}")

# Глобальный экземпляр
analysis_service = AnalysisService(price_service, time_service, timeframe_manager)