import asyncio
import logging
from typing import Dict
from aiogram.utils.keyboard import InlineKeyboardBuilder
from config import bot
import datetime
from services.time_utils import timezone_service
from aiogram.exceptions import TelegramAPIError

logger = logging.getLogger(__name__)

class ProgressService:
    def __init__(self):
        self.progress_tasks: Dict[int, asyncio.Task] = {}
        self.progress_messages: Dict[int, int] = {}

    async def start_progress_animation(self, user_id: int, wait_time: int, 
                                    timeframe: str, close_time: datetime.datetime):
        """Запуск сообщения ожидания с кнопкой"""
        # Останавливаем предыдущую анимацию если была
        await self.stop_progress_animation(user_id)
        
        try:
            close_time_str = timezone_service.format_time_for_user(user_id, close_time)
            
            builder = InlineKeyboardBuilder()
            builder.button(text="Ожидайте", callback_data="progress")
            
            message_text = (f"*Анализ свечи*\n"
                          f"Закрытие: {close_time_str}\n")
            
            message = await bot.send_message(
                chat_id=user_id,
                text=message_text,
                reply_markup=builder.as_markup(),
                parse_mode="Markdown"
            )
            
            self.progress_messages[user_id] = message.message_id
            
            # Запускаем задачу ожидания
            self.progress_tasks[user_id] = asyncio.create_task(
                self._wait_and_cleanup(user_id, wait_time)
            )
            
        except Exception as e:
            logger.error(f"Error starting progress: {e}")
            
    async def _wait_and_cleanup(self, user_id: int, wait_time: int):
        """Просто ждем и очищаем сообщение"""
        try:
            await asyncio.sleep(wait_time)
        except asyncio.CancelledError:
            pass
        finally:
            await self.cleanup_progress(user_id)
            
    async def stop_progress_animation(self, user_id: int):
        """Остановка анимации прогресса"""
        if user_id in self.progress_tasks:
            self.progress_tasks[user_id].cancel()
            try:
                await self.progress_tasks[user_id]
            except:
                pass
            del self.progress_tasks[user_id]
        
        await self.cleanup_progress(user_id)

    async def cleanup_progress(self, user_id: int):
        """Очистка сообщения прогресса"""
        if user_id in self.progress_messages:
            try:
                await bot.delete_message(
                    chat_id=user_id,
                    message_id=self.progress_messages[user_id]
                )
            except Exception:
                pass
            finally:
                if user_id in self.progress_messages:
                    del self.progress_messages[user_id]

# Глобальный экземпляр
progress_service = ProgressService()