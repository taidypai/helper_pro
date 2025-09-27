from aiogram import Router, F
from aiogram.types import CallbackQuery
import logging

from services.message_utils import edit_navigation_message
from services.state_service import state_service
import keyboards

logger = logging.getLogger(__name__)
navigation_router = Router()

@navigation_router.callback_query(F.data == "back")
async def handle_back_callback(callback: CallbackQuery):
    """Обработка callback с данными 'back'"""
    try:
        user_id = callback.from_user.id

        state_service.set_navigation_id(user_id, callback.message.message_id)

        if user_id in state_service.user_states:
            del state_service.user_states[user_id]
        if user_id in state_service.user_calculation_data:
            del state_service.user_calculation_data[user_id]

        await edit_navigation_message(
            user_id,
            '||Запуск анализа → /trade||',
            keyboards.main_keyboard(),
            "MarkdownV2"
        )
    except Exception as e:
        logger.error(f"Error in back callback: {e}")
        await callback.answer("Произошла ошибка")

@navigation_router.callback_query(F.data == "back_to_main")
async def handle_back_to_main(callback: CallbackQuery):
    """Вернуться в главное меню"""
    try:
        user_id = callback.from_user.id

        if user_id in state_service.user_calculation_data:
            del state_service.user_calculation_data[user_id]
        if user_id in state_service.user_states:
            del state_service.user_states[user_id]

        await edit_navigation_message(
            user_id,
            '||Запуск анализа → /trade||',
            keyboards.main_keyboard(),
            "MarkdownV2"
        )

    except Exception as e:
        logger.error(f"Error going back to main: {e}")
        await callback.answer("Произошла ошибка")