from aiogram import Router, F
from aiogram.types import CallbackQuery
import asyncio
import logging

from services.message_utils import edit_navigation_message
from services.state_service import state_service
from services.time_utils import time_service, timeframe_manager, timezone_service
import keyboards

logger = logging.getLogger(__name__)
time_router = Router()

@time_router.callback_query(F.data.in_(['MSK', 'UTC', 'EST', 'CET', 'GMT']))
async def handle_timezone_callback(callback: CallbackQuery):
    """Обработка выбора временной зоны"""
    try:
        user_id = callback.from_user.id
        
        state_service.set_navigation_id(user_id, callback.message.message_id)
        
        abbr = callback.data
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
        
        await edit_navigation_message(
            user_id,
            'Выберите таймфрейм',
            keyboards.settings_keyboard(),
            None
        )
            
    except Exception as e:
        logger.error(f"Error in timezone callback: {e}")
        await callback.answer("Произошла ошибка при выборе временной зоны")

@time_router.callback_query(F.data.in_(["1d", "4h", "1h", "30m", "15m", "5m"]))
async def handle_timeframe(callback: CallbackQuery):
    await handle_timeframe_selection(callback, callback.data)

async def handle_timeframe_selection(callback: CallbackQuery, timeframe: str):
    """Общая функция обработки выбора таймфрейма"""
    try:
        user_id = callback.from_user.id
        
        state_service.set_navigation_id(user_id, callback.message.message_id)
        
        await time_service.sync_binance_time()
        timeframe_manager.set_timeframe(timeframe)
        
        await callback.answer(f"Синхронизировано с Binance", show_alert=True)
        
        await asyncio.sleep(3)
        await edit_navigation_message(
            user_id,
            '||Запуск анализа → /trade||',
            keyboards.main_keyboard(),
            "MarkdownV2"
        )
    except Exception as e:
        logger.error(f"Error in timeframe selection {timeframe}: {e}")
        await callback.answer("Произошла ошибка при выборе таймфрейма")

@time_router.callback_query(F.data == "progress")
async def handle_progress_callback(callback: CallbackQuery):
    """Обработка нажатия на кнопку прогресса"""
    user_id = callback.message.from_user.id

    get_timeframe = timeframe_manager.get_timeframe()
    # Исправлено: используем напрямую timeframe или добавляем функцию get_timeframe_text
    timeframe = get_timeframe  # или timeframe_manager.get_timeframe_text(get_timeframe) если функция существует
    current_time = time_service.get_binance_time()
    user_timezone = timezone_service.get_user_timezone(user_id)
    text_analizmessage = (
        f"Ваша зона {user_timezone}\n"
        f"Таймфрейм {timeframe}\n"
        f"Binance {current_time.strftime('%H:%M:%S UTC')}"
    )

    await callback.answer(text_analizmessage, show_alert=True)