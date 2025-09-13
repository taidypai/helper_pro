from aiogram import Router, F
from aiogram.types import CallbackQuery
import asyncio
import logging

from services.message_utils import edit_navigation_message
from services.state_service import state_service
from services.time_utils import timezone_service
import keyboards

logger = logging.getLogger(__name__)
settings_router = Router()

@settings_router.callback_query(F.data == "settings")
async def handle_settings_callback(callback: CallbackQuery):
    """Обработка callback с данными 'settings'"""
    try:
        user_id = callback.from_user.id
        
        state_service.set_navigation_id(user_id, callback.message.message_id)
        
        await edit_navigation_message(
            user_id,
            'Выберите временную зону',
            keyboards.timezone_keyboard(),
            None
        )
    except Exception as e:
        logger.error(f"Error in settings callback: {e}")
        await callback.answer("Произошла ошибка")

@settings_router.callback_query(F.data == "go")
async def instruction_callback(callback: CallbackQuery):
    try:
        user_id = callback.message.from_user.id
        novigation_message = await callback.message.edit_text('Перейдите в настройки', reply_markup=keyboards.main_keyboard())
        state_service.set_navigation_id(user_id, novigation_message.message_id)
        await asyncio.sleep(2)

    except Exception as e:
        logger.error(f"Error in start handler: {e}")
        await callback.message.answer("Произошла ошибка при запуске основной функции")