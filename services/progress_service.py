import asyncio
import logging
from typing import Dict
from aiogram.utils.keyboard import InlineKeyboardBuilder
from config import bot
import datetime
from services.time_utils import timezone_service
logger = logging.getLogger(__name__)

class ProgressService:
    def __init__(self):
        self.progress_tasks: Dict[int, asyncio.Task] = {}
        self.progress_messages: Dict[int, int] = {}

    async def format_time_remaining(self, seconds: int) -> str:
        """Форматирование времени в читаемый вид с часами и минутами"""
        if seconds >= 3600:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            secs = seconds % 60
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        elif seconds >= 60:
            minutes = seconds // 60
            secs = seconds % 60
            return f"{minutes:02d}:{secs:02d}"
        else:
            return f"00:{seconds:02d}"

    async def start_progress_animation(self, user_id: int, wait_time: int, 
                                    timeframe: str, close_time: datetime.datetime):
        """Запуск неблокирующей анимации прогресса с часами и минутами"""
        # Останавливаем предыдущую анимацию если была
        await self.stop_progress_animation(user_id)
        
        try:
            
            close_time_str = timezone_service.format_time_for_user(user_id, close_time)
            initial_time_str = await self.format_time_remaining(wait_time)
            
            builder = InlineKeyboardBuilder()
            builder.button(text=f"$", callback_data="progress")
            
            message_text = (f"*Новая свеча*\n"
                            f"Закрытие: {close_time_str}\n")
            
            message = await bot.send_message(
                chat_id=user_id,
                text=message_text,
                reply_markup=builder.as_markup(),
                parse_mode="Markdown"
            )
            
            self.progress_messages[user_id] = message.message_id
            
            # Запускаем анимацию в ОТДЕЛЬНОЙ задаче
            self.progress_tasks[user_id] = asyncio.create_task(
                self._animate_progress(user_id, wait_time, timeframe, close_time_str)
            )
            
        except Exception as e:
            logger.error(f"Error starting progress: {e}")
            
    async def _animate_progress(self, user_id: int, total_time: int, 
                                timeframe: str, close_time_str: str):
            """Анимация прогресса с обновлением времени"""
            try:
                
                progress_emojis = ['$', '€', '£', '₽', '¥', '₿', 'Ƀ', 'Ł', 'Ð']
                
                start_time = asyncio.get_event_loop().time()
                
                while user_id in self.progress_messages:
                    elapsed = asyncio.get_event_loop().time() - start_time
                    remaining = max(0, total_time - int(elapsed))
                    
                    if remaining <= 0:
                        break
                    
                    # Форматируем оставшееся время
                    time_str = await self.format_time_remaining(remaining)
                    emoji_index = (int(elapsed) // 10) % len(progress_emojis)  # Меняем каждые 10 секунд
                    current_emoji = progress_emojis[emoji_index]
                    
                    # Создаем клавиатуру с текущим временем
                    builder = InlineKeyboardBuilder()
                    builder.button(text=f"{current_emoji} {time_str}", callback_data="progress")
                    
                    # Обновляем текст сообщения
                    message_text = (f"*Новая свеча*\n"
                                f"Закрытие: {close_time_str}\n")
                    
                    try:
                        # Обновляем и текст и клавиатуру
                        await bot.edit_message_text(
                            chat_id=user_id,
                            message_id=self.progress_messages[user_id],
                            text=message_text,
                            reply_markup=builder.as_markup(),
                            parse_mode="Markdown"
                        )
                    except Exception as e:
                        logger.debug(f"Progress update error: {e}")
                        break
                    
                    await asyncio.sleep(5)  # Обновляем каждую секунду
                    
            except Exception as e:
                logger.error(f"Error in progress animation: {e}")
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