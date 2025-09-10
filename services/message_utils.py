import asyncio
from aiogram.types import Message
import logging

logger = logging.getLogger(__name__)

async def typewriter_effect(message: Message, text: str, delay: float = 0.05) -> Message:
    """Эффект печатания текста"""
    try:
        sent_message = await message.answer("▌")
        full_message = ""
        
        for letter in text:
            full_message += letter
            await sent_message.edit_text(full_message + " ▌")
            await asyncio.sleep(delay)
        
        await sent_message.edit_text(full_message)
        return sent_message
    except Exception as e:
        logger.error(f"Error in typewriter effect: {e}")
        # Fallback: просто отправляем сообщение без эффекта
        return await message.answer(text)

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