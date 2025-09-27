# analysis_service.py
import asyncio
from typing import Dict, Optional, List
import logging

import time
from config import bot
from services.price_service import crypto_service, forex_service
from services.time_utils import timeframe_manager, time_service, logger, timezone_service
from services.progress_service import progress_service
from .models import Candle

logger = logging.getLogger(__name__)

class AnalysisService:
    def __init__(self, crypto_service, forex_service, time_service, timeframe_manager):
        self.crypto_service = crypto_service
        self.forex_service = forex_service
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
                # Для IMOEX используем новый метод из price_service
                imoex_candles = await self.price_service.get_imoex_ohlc(
                    timeframe=timeframe,
                    num_candles=1
                )

                if imoex_candles and len(imoex_candles) > 0:
                    candle_data = imoex_candles[0]
                    return Candle(
                        open=float(candle_data['open']),
                        high=float(candle_data['high']),
                        low=float(candle_data['low']),
                        close=float(candle_data['close']),
                        volume=0.0,  # Для IMOEX объем не используется
                        timestamp=candle_data['end'].timestamp() * 1000  # Конвертируем в миллисекунды
                    )
            else:
                # Для крипты используем Binance
                pass
        except Exception as e:
            logger.error(f"Ошибка получения свечи {symbol} {timeframe}: {e}")

        return None

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
            logger.info(f"🔄 Начинаем анализ {symbol} для user {user_id} на TF: {timeframe}")

            # Инициализируем историю для символа
            if user_id not in self.candle_history:
                self.candle_history[user_id] = {}
            if symbol not in self.candle_history[user_id]:
                self.candle_history[user_id][symbol] = []

            while self.active_analyses.get(user_id, False):
                if asyncio.current_task().cancelled():
                    break

                # Ждем до закрытия следующей свечи
                wait_time, close_time = await self.time_service.get_time_to_candle_close(timeframe)
                if wait_time > 0:
                    logger.info(f"Ждем {wait_time} сек до закрытия свечи {timeframe}")
                    await asyncio.sleep(wait_time)

                # Получаем новые данные
                analysis_data = None
                if symbol in ['BTCUSDT', 'ETHUSDT']:
                    analysis_data = await self.crypto_service.get_price(symbol)
                elif symbol in ['EURUSD', 'GBPUSD']:
                    analysis_data = await self.forex_service.get_price(symbol)

                if not analysis_data:
                    logger.warning(f"{symbol}: Не получилось получить данные")
                    continue

                # Создаем объект Candle из полученных данных
                indicators = analysis_data.indicators
                new_candle = Candle(
                    open=float(indicators.get('open', 0)),
                    high=float(indicators.get('high', 0)),
                    low=float(indicators.get('low', 0)),
                    close=float(indicators.get('close', 0)),
                    volume=float(indicators.get('volume', 0)),
                    timestamp=int(time.time() * 1000)  # Текущее время в миллисекундах
                )

                print(f'{symbol}: Close = {new_candle.close}')

                # Обновляем историю
                history = self.candle_history[user_id][symbol]
                history.append(new_candle)

                # Держим только последние 2 свечи
                if len(history) > 2:
                    history.pop(0)

                logger.info(f"📊 {symbol} {timeframe}: обновлена история свечей ({len(history)} шт)")

                # Анализируем если есть минимум 2 свечи
                if len(history) >= 2:
                    prev_candle, current_candle = history[-2], history[-1]

                    # Проверяем, что свечи разные (по времени)
                    if prev_candle.timestamp != current_candle.timestamp:
                        # Ищем ордерблок
                        signal = self.analyze_order_block(prev_candle, current_candle)

                        if signal:
                            logger.info(f"🎯 Найден ордерблок {symbol} {timeframe}: {signal}")

                            message = self.create_order_block_message(
                                symbol, signal, timeframe, [prev_candle, current_candle]
                            )
                            await self.safe_send_message(user_id, message, parse_mode="Markdown")
                        else:
                            logger.debug(f"{symbol} {timeframe}: ордерблок не найден")
                else:
                    logger.info(f"📊 {symbol}: накопление истории ({len(history)}/2)")

        except asyncio.CancelledError:
            logger.info(f"⏹️ Анализ {symbol} остановлен для user {user_id}")
        except Exception as e:
            logger.error(f"❌ Ошибка в анализе {symbol} {timeframe}: {e}")

    async def analyze_candles_with_progress(self, user_id: int):
        """Запуск анализа (работает до команды stop)"""
        try:
            timeframe = self.timeframe_manager.get_timeframe()
            if not timeframe:
                await self.safe_send_message(user_id, "Сначала выбери таймфрейм в настройках!")
                return

            symbols = ['BTCUSDT', 'ETHUSDT', 'EURUSD', 'GBPUSD']
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
            await self.cleanup_user_analysis(user_id)

    async def cleanup_user_analysis(self, user_id: int):
        """Очистка ресурсов анализа для пользователя"""
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
                try:
                    await task
                except:
                    pass
            del self.analysis_tasks[user_id]

        # Чистим за собой
        if user_id in self.candle_history:
            del self.candle_history[user_id]
        if user_id in self.active_analyses:
            del self.active_analyses[user_id]

        await progress_service.stop_progress_animation(user_id)
        logger.info(f"🧹 Ресурсы анализа очищены для user {user_id}")

    def stop_analysis(self, user_id: int):
        """Останавливает анализ для пользователя"""
        if user_id in self.active_analyses:
            self.active_analyses[user_id] = False
            logger.info(f"⏹️ Анализ остановлен по команде для user {user_id}")

    async def get_imoex_current_price(self) -> Optional[float]:
        """Получить текущую цену IMOEX"""
        try:
            return await self.price_service.get_imoex_index()
        except Exception as e:
            logger.error(f"Ошибка получения цены IMOEX: {e}")
            return None

# Глобальный экземпляр
analysis_service = AnalysisService(crypto_service, forex_service, time_service, timeframe_manager)