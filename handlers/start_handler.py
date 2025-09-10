from aiogram.filters import Command
from aiogram import types, Router
import asyncio
import logging

from config import bot, subscribed_users
from services.state_service import state_service
from services.message_utils import typewriter_effect
import keyboards
from services.time_utils import time_service

logger = logging.getLogger(__name__)
start_router = Router()

@start_router.message(Command('start'))
async def handle_start(message: types.Message):
    """Обработка команды /start"""
    try:
        #await message.delete()
        user_id = message.from_user.id
        subscribed_users.add(user_id)

        welcome_text = "Приветствую!"
        sent_message = await typewriter_effect(message, welcome_text)
        
        await asyncio.sleep(2)

        start_list_1 = []
        for i in start_list_1:
            await sent_message.edit_text(i)
            await asyncio.sleep(3)
            
        navigation_msg = await message.answer('Перейдите в настройки', reply_markup=keyboards.main_keyboard())
        state_service.set_navigation_id(user_id, navigation_msg.message_id)

    except Exception as e:
        logger.error(f"Error in start handler: {e}")
        await message.answer("Произошла ошибка при запуске бота")

@start_router.message(Command("trade"))
async def start_analysis_command(message: types.Message):
    """Запуск анализа с красивой анимацией"""
    from config import running_analyses
    from services.analysis_service import analysis_service
    from services.time_utils import timeframe_manager
    
    user_id = message.from_user.id
    
    if user_id in running_analyses:
        await message.answer("⚠️ Анализ уже запущен! /stop чтобы остановить")
        return
    
    timeframe = timeframe_manager.get_timeframe()
    if not timeframe:
        await message.answer("⚠️ Сначала выбери таймфрейм в настройках!")
        return
    
    # Запускаем задачу с анимацией
    task = asyncio.create_task(analysis_service.analyze_candles_with_progress(user_id))
    running_analyses[user_id] = task
    analysis_service.user_tasks[user_id] = task
    from services.time_utils import timezone_service, time_service
    
    user_id = message.from_user.id
    current_time = time_service.get_binance_time()
    user_timezone = timezone_service.get_user_timezone(user_id)
    
    formatted_time = timezone_service.format_time_for_user(user_id, current_time)
    
    text_analizmessage = (
        f"*Ваше текущее время:*\n"
        f"• Ваша зона: {user_timezone}\n"
        f"• Время запуска: {formatted_time}\n"
        f"• Binance: {current_time.strftime('%H:%M:%S UTC')}\n"
    )
    await message.answer(
         text_analizmessage+
        "||Остановка → /stop||",
        parse_mode="MarkdownV2"
        )
    await asyncio.sleep(1)

@start_router.message(Command("stop"))
async def stop_analysis(message: types.Message):
    """Простая остановка"""
    from config import running_analyses
    from services.analysis_service import analysis_service
    
    user_id = message.from_user.id
    
    if user_id in running_analyses:
        running_analyses[user_id].cancel()
        try:
            await running_analyses[user_id]
        except:
            pass
        del running_analyses[user_id]
        
        # Также очищаем из analysis_service
        if user_id in analysis_service.user_tasks:
            del analysis_service.user_tasks[user_id]
        if user_id in analysis_service.last_prices:
            del analysis_service.last_prices[user_id]
        
        await message.answer("Анализ остановлен")
    else:
        await message.answer("Анализ не запущен")