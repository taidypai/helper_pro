from aiogram.filters import Command, CommandStart
from aiogram import types, Router
import asyncio
import logging

from config import bot, subscribed_users
from services.message_utils import edit_navigation_message
import keyboards
from services.trade_calculator import trade_calculator
from services.state_service import state_service

logger = logging.getLogger(__name__)
start_router = Router()

@start_router.message(CommandStart())
async def handle_start(message: types.Message):
    """Обработка команды /start"""
    try:
        user_id = message.from_user.id
        subscribed_users.add(user_id)

        welcome_text = "Добро пожаловать в экосистему *Trade & Brain*!"
        await message.answer(welcome_text, reply_markup=keyboards.start_keyboard(), parse_mode='Markdown')
        await asyncio.sleep(2)

    except Exception as e:
        logger.error(f"Error in start handler: {e}")
        await message.answer("Произошла ошибка при запуске бота")

@start_router.message(Command("calculate"))
async def start_calculation_command(message: types.Message):
    """Запуск калькулятора позиции"""
    try:
        user_id = message.from_user.id
        
        if user_id in state_service.user_states:
            del state_service.user_states[user_id]
        if user_id in state_service.user_calculation_data:
            del state_service.user_calculation_data[user_id]
        
        nav_message = await message.answer(
            "*КАЛЬКУЛЯТОР ПОЗИЦИИ*\n\n"
            "Выберите направление сделки:",
            reply_markup=keyboards.lot_keyboard(),
            parse_mode="Markdown"
        )
        
        state_service.set_navigation_id(user_id, nav_message.message_id)
        
        try:
            await message.delete()
        except:
            pass
            
    except Exception as e:
        logger.error(f"Error starting calculation: {e}")
        await message.answer("❌ Произошла ошибка при запуске калькулятора")

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
    
    task = asyncio.create_task(analysis_service.analyze_candles_with_progress(user_id))
    running_analyses[user_id] = task
    analysis_service.user_tasks[user_id] = task
    await message.answer(
        "||Остановка анализа → /stop||",
        parse_mode="MarkdownV2"
    )
    await asyncio.sleep(1)

@start_router.message(Command("stop"))
async def stop_analysis(message: types.Message):
    """Провая остановка"""
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
        
        if user_id in analysis_service.user_tasks:
            del analysis_service.user_tasks[user_id]
        if user_id in analysis_service.last_prices:
            del analysis_service.last_prices[user_id]
        
        await message.answer("Анализ остановлен")
    else:
        await message.answer("Анализ не запущен")

@start_router.message(Command("default"))
async def handle_default_risk(message: types.Message):
    """Использование значения риска по умолчанию"""
    user_id = message.from_user.id
    
    if user_id not in state_service.user_states:
        return
    
    user_state = state_service.user_states[user_id]
    if user_state.get('waiting_for') != 'risk_percent':
        return
    
    state_service.user_calculation_data[user_id]['risk_percent'] = 0.005
    
    # Создаем отдельную функцию чтобы избежать циклического импорта
    await _calculate_and_show_trade(user_id)
    
    try:
        await asyncio.sleep(2)
        await message.delete()
    except:
        pass

async def _calculate_and_show_trade(user_id: int):
    """Вспомогательная функция для расчета сделки"""
    from services.message_utils import edit_navigation_message
    import keyboards
    
    try:
        user_data = state_service.user_calculation_data.get(user_id, {})
        
        if not all(key in user_data for key in ['direction', 'balance', 'entry_price', 'stop_loss', 'risk_reward', 'risk_percent']):
            await edit_navigation_message(
                user_id,
                "❌ Не все данные получены. Начните заново.",
                keyboards.lot_keyboard(),
                "Markdown"
            )
            return
        
        result = trade_calculator.calculate_trade(user_data)
        
        if 'error' in result:
            await edit_navigation_message(
                user_id,
                f"❌ Ошибка расчета: {result['error']}",
                keyboards.lot_keyboard(),
                "Markdown"
            )
            return
        
        state_service.user_calculation_data[user_id]['result'] = result
        trade = result['success']
        
        brief_message = (
            f"*РАСЧЕТ ПОЗИЦИИ ЗАВЕРШЕН*\n\n"
            f"• Направление: {trade.direction.upper()}\n"
            f"• Цена входа: ${trade.entry_price:.2f}\n"
            f"• Стоп-лосс: ${trade.stop_loss:.2f}\n"
            f"• Тейк-профит: ${trade.take_profit:.2f}\n\n"
            f"💡 *РЕКОМЕНДАЦИЯ:*\n"
            f"• Объем: {trade_calculator.format_volume(trade.volume)}\n"
            f"• Плечо: x{trade.required_leverage:.2f}\n"
            f"• Риск: ${trade.risk_money:.2f} ({trade.risk_percent*100:.1f}%)\n\n"
            f"Потенциальная прибыль: ${trade.potential_profit:.2f}"
        )
        
        await edit_navigation_message(
            user_id,
            brief_message,
            keyboards.trade_details_keyboard(),
            "Markdown"
        )
        
        if user_id in state_service.user_states:
            del state_service.user_states[user_id]
            
    except Exception as e:
        logger.error(f"Error calculating trade: {e}")
        await edit_navigation_message(
            user_id,
            "❌ Произошла ошибка при расчете позиции",
            keyboards.lot_keyboard(),
            "Markdown"
        )
        
        if user_id in state_service.user_states:
            del state_service.user_states[user_id]