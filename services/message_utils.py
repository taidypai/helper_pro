import asyncio
from aiogram.types import Message
import logging
import re
logger = logging.getLogger(__name__)

async def delete_messages_range(chat_id: int, start_id: int, end_id: int, 
                              bot, delay: float = 0.1):
    """Удаление диапазона сообщений"""
    for message_id in range(start_id, end_id + 1):
        try:
            await bot.delete_message(chat_id=chat_id, message_id=message_id)
            await asyncio.sleep(delay)
        except Exception as e:
            logger.debug(f"Не получилось удалить сообщение {message_id}: {e}")
            continue

async def edit_navigation_message(user_id: int, text: str, reply_markup=None, 
                                parse_mode=None) -> bool:
    """Утилита для редактирования навигационного сообщения"""
    try:
        from services.state_service import state_service
        from config import bot  # Импортируем бота напрямую
        
        navigation_id = state_service.get_navigation_id(user_id)
        
        if not navigation_id:
            logger.error(f"No navigation message found for user {user_id}")
            return False
            
        await bot.edit_message_text(
            chat_id=user_id,
            message_id=navigation_id,
            text=text,
            reply_markup=reply_markup,
            parse_mode=parse_mode
        )
        return True
    except Exception as e:
        logger.error(f"Error editing navigation message: {e}")
        return False
def escape_markdown(text: str) -> str:
    """Экранирование специальных символов для Markdown"""
    escape_chars = r'\_*[]()~`>#+-=|{}.!'
    return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', text)