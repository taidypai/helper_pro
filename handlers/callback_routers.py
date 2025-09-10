from aiogram import Router, F
from aiogram.types import CallbackQuery
import asyncio
import logging

from config import bot
from services.state_service import state_service
from services.time_utils import timeframe_manager, time_service, timezone_service
import keyboards

logger = logging.getLogger(__name__)
callback_router = Router()

async def edit_navigation_message(callback: CallbackQuery, text: str, reply_markup=None, parse_mode=None):
    """Утилита для редактирования навигационного сообщения"""
    try:
        user_id = callback.from_user.id
        navigation_id = state_service.get_navigation_id(user_id)
        message_id = navigation_id if navigation_id else callback.message.message_id
        
        await bot.edit_message_text(
            chat_id=callback.message.chat.id,
            message_id=message_id,
            text=text,
            reply_markup=reply_markup,
            parse_mode=parse_mode
        )
        return True
    except Exception as e:
        logger.error(f"Error editing navigation message: {e}")
        await callback.answer("Произошла ошибка")
        return False

@callback_router.callback_query(F.data == "settings")
async def handle_settings_callback(callback: CallbackQuery):
    """Обработка callback с данными 'settings'"""
    try:
        await edit_navigation_message(
            callback,
            'Выберите временную зону.',
            keyboards.timezone_keyboard()
        )
    except Exception as e:
        logger.error(f"Error in settings callback: {e}")
        await callback.answer("Произошла ошибка")

@callback_router.callback_query(F.data.in_(['MSK', 'UTC', 'EST', 'CET', 'GMT']))
async def handle_timezone_callback(callback: CallbackQuery):
    """Обработка выбора временной зоны"""
    try:
        abbr = callback.data
        user_id = callback.from_user.id
        
        timezone_mapping = {
            'MSK': 'Europe/Moscow',
            'UTC': 'UTC', 
            'EST': 'America/New_York',
            'CET': 'Europe/Paris',
            'GMT': 'Europe/London'
        }
        
        if abbr not in timezone_mapping:
            await callback.answer("Неизвестная временная зона")
            return
        
        full_timezone = timezone_mapping[abbr]
        timezone_service.set_user_timezone(user_id, full_timezone)
        
        await callback.answer(f"Установлена временная зона: {abbr}", show_alert=True)
        
        await asyncio.sleep(2)
        
        await callback.message.edit_text(
            text='Выберите таймфрейм',
            reply_markup=keyboards.settings_keyboard()
        )
            
    except Exception as e:
        logger.error(f"Error in timezone callback: {e}")
        await callback.answer("Произошла ошибка при выборе временной зоны")

@callback_router.callback_query(F.data == "back")
async def handle_back_callback(callback: CallbackQuery):
    """Обработка callback с данными 'back'"""
    try:
        await edit_navigation_message(
            callback,
            '||Запуск анализа /trade||',
            keyboards.main_keyboard(),
            parse_mode="MarkdownV2"
        )
    except Exception as e:
        logger.error(f"Error in back callback: {e}")
        await callback.answer("Произошла ошибка")

@callback_router.callback_query(F.data.in_(["1d", "4h", "1h", "30m", "15m", "5m"]))
async def handle_timeframe(callback: CallbackQuery):
    await handle_timeframe_selection(callback, callback.data)

async def handle_timeframe_selection(callback: CallbackQuery, timeframe: str):
    """Общая функция обработки выбора таймфрейма"""
    try:
        await time_service.sync_binance_time()
        timeframe_manager.set_timeframe(timeframe)
        
        await callback.answer(f"Синхронизировано с Binance", show_alert=True)
        
        await asyncio.sleep(3)
        await edit_navigation_message(
            callback,
            '||Запуск анализа /trade||',
            keyboards.main_keyboard(),
            parse_mode="MarkdownV2"
        )
    except Exception as e:
        logger.error(f"Error in timeframe selection {timeframe}: {e}")
        await callback.answer("Произошла ошибка при выборе таймфрейма")

@callback_router.callback_query(F.data == "progress")
async def handle_progress_callback(callback: CallbackQuery):
    """Обработка нажатия на кнопку прогресса"""
    await callback.answer("Идет анализ...", show_alert=True)