from aiogram import Router, F
from aiogram.types import CallbackQuery
import logging

from services.message_utils import edit_navigation_message
from services.state_service import state_service
from services.trade_calculator import trade_calculator
import keyboards

logger = logging.getLogger(__name__)
trade_router = Router()

@trade_router.callback_query(F.data == "lot")
async def handle_lot_callback(callback: CallbackQuery):
    try:
        user_id = callback.from_user.id
        
        state_service.set_navigation_id(user_id, callback.message.message_id)
        
        await edit_navigation_message(
            user_id,
            'Выберите направление',
            keyboards.lot_keyboard(),
            None
        )
        
    except Exception as e:
        logger.error(f"Error in lot callback: {e}")
        await callback.answer("Произошла ошибка при запуске калькулятора")

@trade_router.callback_query(F.data.in_(["long", "short"]))
async def handle_direction_selection(callback: CallbackQuery):
    """Обработка выбора направления сделки"""
    try:
        user_id = callback.from_user.id
        direction = callback.data
        
        state_service.set_navigation_id(user_id, callback.message.message_id)
        
        if user_id not in state_service.user_calculation_data:
            state_service.user_calculation_data[user_id] = {}
        state_service.user_calculation_data[user_id]['direction'] = direction
        
        state_service.user_states[user_id] = {'waiting_for': 'balance'}
        
        await edit_navigation_message(
            user_id,
            f"📊 *Расчет позиции - {direction.upper()}*\n\n"
            f"Введите ваш баланс в USDT:",
            keyboards.cancel_keyboard(),
            "Markdown"
        )
        
    except Exception as e:
        logger.error(f"Error in direction selection: {e}")
        await callback.answer("Произошла ошибка")

@trade_router.callback_query(F.data == "cancel_trade")
async def handle_cancel_trade(callback: CallbackQuery):
    """Обработка отмены расчета"""
    try:
        user_id = callback.from_user.id
        
        if user_id in state_service.user_states:
            del state_service.user_states[user_id]
        if user_id in state_service.user_calculation_data:
            del state_service.user_calculation_data[user_id]
        
        await edit_navigation_message(
            user_id,
            'Выберите направление',
            keyboards.lot_keyboard(),
            None
        )
        
    except Exception as e:
        logger.error(f"Error canceling trade: {e}")
        await callback.answer("Произошла ошибка")

@trade_router.callback_query(F.data == "trade_details")
async def handle_trade_details(callback: CallbackQuery):
    """Показать детальную информацию о сделке"""
    try:
        user_id = callback.from_user.id
        
        user_data = state_service.user_calculation_data.get(user_id, {})
        if 'result' not in user_data:
            await callback.answer("Данные не найдены", show_alert=True)
            return
        
        result = user_data['result']
        trade = result['success']
        
        detailed_message = (
            f"*ДЕТАЛЬНЫЙ РАСЧЕТ ПОЗИЦИИ*\n\n"
            f"• Направление: {trade.direction.upper()}\n"
            f"• Баланс: ${trade.balance:.2f}\n"
            f"• Цена входа: ${trade.entry_price:.2f}\n"
            f"• Стоп-лосс: ${trade.stop_loss:.2f}\n"
            f"• Тейк-профит: ${trade.take_profit:.2f}\n"
            f"• Риск/Прибыль: 1:{trade.risk_reward_ratio}\n"
            f"• Риск на сделку: {trade.risk_percent*100:.1f}% (${trade.risk_money:.2f})\n\n"
            f"*ПАРАМЕТРЫ ПОЗИЦИИ:*\n"
            f"• Идеальный объем: {trade_calculator.format_volume(trade.volume)}\n"
            f"• Фактический объем: {trade_calculator.format_volume(trade.adjusted_volume)}\n"
            f"• Стоимость позиции: ${trade.position_value:.2f}\n"
            f"• Плечо: x{trade_calculator.format_leverage(trade.adjusted_leverage)}\n"
            f"• Дистанция риска: {trade.risk_distance_percent:.2f}%\n\n"
            f"*ПОТЕНЦИАЛ:*\n"
            f"• Потенциальный убыток: ${trade.potential_loss:.2f}\n"
            f"• Потенциальная прибыль: ${trade.potential_profit:.2f}\n\n"
            f"*ВНИМАНИЕ:* Объем округлен до 4 знаков после запятой"
        )
        
        await edit_navigation_message(
            user_id,
            detailed_message,
            keyboards.back_to_trade_keyboard(),
            "Markdown"
        )
        
    except Exception as e:
        logger.error(f"Error showing trade details: {e}")
        await callback.answer("Произошла ошибка")

@trade_router.callback_query(F.data == "trade_brief")
async def handle_trade_brief(callback: CallbackQuery):
    """Вернуться к краткому виду"""
    try:
        user_id = callback.from_user.id
        
        user_data = state_service.user_calculation_data.get(user_id, {})
        if 'result' not in user_data:
            await callback.answer("Данные не найдены", show_alert=True)
            return
        
        result = user_data['result']
        trade = result['success']
        
        brief_message = (
            f"*РАСЧЕТ ПОЗИЦИИ ЗАВЕРШЕН*\n\n"
            f"• Направление: {trade.direction.upper()}\n"
            f"• Цена входа: ${trade.entry_price:.2f}\n"
            f"• Стоп-лосс: ${trade.stop_loss:.2f}\n"
            f"• Тейк-профит: ${trade.take_profit:.2f}\n\n"
            f"*РЕКОМЕНДАЦИЯ:*\n"
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
        
    except Exception as e:
        logger.error(f"Error showing trade brief: {e}")
        await callback.answer("Произошла ошибка")

@trade_router.callback_query(F.data == "new_trade")
async def handle_new_trade(callback: CallbackQuery):
    """Начать новый расчет"""
    try:
        user_id = callback.from_user.id
        
        if user_id in state_service.user_calculation_data:
            del state_service.user_calculation_data[user_id]
        if user_id in state_service.user_states:
            del state_service.user_states[user_id]
        
        await edit_navigation_message(
            user_id,
            "*КАЛЬКУЛЯТОР ПОЗИЦИИ*\n\n"
            "Выберите направление сделки:",
            keyboards.lot_keyboard(),
            "Markdown"
        )
        
    except Exception as e:
        logger.error(f"Error starting new trade: {e}")
        await callback.answer("Произошла ошибка")