from aiogram import Router
from aiogram.filters import Command
import asyncio
import logging

from services.state_service import state_service
from services.message_utils import edit_navigation_message
from services.trade_calculator import trade_calculator

import keyboards
logger = logging.getLogger(__name__)
message_router = Router()
@message_router.message()
async def handle_trade_inputs(message):
    """Обработка ввода данных для расчета позиции"""
    user_id = message.from_user.id
    
    if user_id not in state_service.user_states:
        return
    
    user_state = state_service.user_states[user_id]
    waiting_for = user_state.get('waiting_for')
    
    if not waiting_for:
        return
    
    try:
        text = message.text.strip()
        
        if waiting_for == 'balance':
            await _handle_balance_input(user_id, text)
        elif waiting_for == 'entry_price':
            await _handle_entry_price_input(user_id, text)
        elif waiting_for == 'stop_loss':
            await _handle_stop_loss_input(user_id, text)
        elif waiting_for == 'risk_reward':
            await _handle_risk_reward_input(user_id, text)
        elif waiting_for == 'risk_percent':
            await _handle_risk_percent_input(user_id, text)
            
        try:
            await message.delete()
        except:
            pass
            
    except ValueError:
        await edit_navigation_message(
            user_id,
            "❌ Пожалуйста, введите корректное число\n\n"
            f"Текущий шаг: {waiting_for}",
            keyboards.cancel_keyboard(),
            "Markdown"
        )
    except Exception as e:
        logger.error(f"Error processing trade input: {e}")
        await edit_navigation_message(
            user_id,
            "❌ Произошла ошибка при обработке данных\n\n"
            "Попробуйте еще раз:",
            keyboards.cancel_keyboard(),
            "Markdown"
        )

async def _handle_balance_input(user_id: int, text: str):
    """Обработка ввода баланса"""
    balance = float(text)
    if balance <= 0:
        await edit_navigation_message(
            user_id,
            "❌ Баланс должен быть положительным числом\n\n"
            "Введите ваш баланс в USDT:",
            keyboards.cancel_keyboard(),
            "Markdown"
        )
        return
    
    state_service.user_calculation_data[user_id]['balance'] = balance
    direction = state_service.user_calculation_data[user_id].get('direction', 'long')
    
    await edit_navigation_message(
        user_id,
        f"Введите цену входа для {direction.upper()}:",
        keyboards.cancel_keyboard(),
        "Markdown"
    )
    state_service.user_states[user_id] = {'waiting_for': 'entry_price'}

async def _handle_entry_price_input(user_id: int, text: str):
    """Обработка цены входа"""
    entry_price = float(text)
    if entry_price <= 0:
        await edit_navigation_message(
            user_id,
            "Цена входа должна быть положительной\n\n"
            f"Введите цену входа:",
            keyboards.cancel_keyboard(),
            "Markdown"
        )
        return
    
    state_service.user_calculation_data[user_id]['entry_price'] = entry_price
    direction = state_service.user_calculation_data[user_id].get('direction', 'long')
    stop_text = "ниже цены входа" if direction == 'long' else "выше цены входа"
    
    await edit_navigation_message(
        user_id,
        f"Введите стоп-лосс ({stop_text}):",
        keyboards.cancel_keyboard(),
        "Markdown"
    )
    state_service.user_states[user_id] = {'waiting_for': 'stop_loss'}

async def _handle_stop_loss_input(user_id: int, text: str):
    """Обработка стоп-лосса"""
    stop_loss = float(text)
    if stop_loss <= 0:
        await edit_navigation_message(
            user_id,
            "Стоп-лосс должен быть положительным\n\n"
            f"Введите стоп-лосс:",
            keyboards.cancel_keyboard(),
            "Markdown"
        )
        return
    
    user_data = state_service.user_calculation_data[user_id]
    direction = user_data.get('direction', 'long')
    entry_price = user_data.get('entry_price')
    
    if direction == 'long' and stop_loss >= entry_price:
        await edit_navigation_message(
            user_id,
            "Для LONG стоп-лосс должен быть НИЖЕ цены входа\n\n"
            f"Введите стоп-лосс:",
            keyboards.cancel_keyboard(),
            "Markdown"
        )
        return
    elif direction == 'short' and stop_loss <= entry_price:
        await edit_navigation_message(
            user_id,
            "Для SHORT стоп-лосс должен быть ВЫШЕ цены входа\n\n"
            f"Введите стоп-лосс:",
            keyboards.cancel_keyboard(),
            "Markdown"
        )
        return
    
    state_service.user_calculation_data[user_id]['stop_loss'] = stop_loss
    
    await edit_navigation_message(
        user_id,
        "Введите соотношение Risk/Reward (например: 1 для 1:1, 2 для 1:2 и т.д.):",
        keyboards.cancel_keyboard(),
        "Markdown"
    )
    state_service.user_states[user_id] = {'waiting_for': 'risk_reward'}

async def _handle_risk_reward_input(user_id: int, text: str):
    """Обработка risk/reward ratio"""
    risk_reward = float(text)
    if risk_reward <= 0:
        await edit_navigation_message(
            user_id,
            "Соотношение должно быть положительным\n\n"
            f"Введите соотношение Risk/Reward:",
            keyboards.cancel_keyboard(),
            "Markdown"
        )
        return
    
    state_service.user_calculation_data[user_id]['risk_reward'] = risk_reward
    
    await edit_navigation_message(
        user_id,
        "⚠️ Введите процент риска на сделку (например: 2 для 2%, 0.5 для 0.5%):\n"
        "Или нажмите /default для использования значения по умолчанию (0.5%)",
        keyboards.cancel_keyboard(),
        "Markdown"
    )
    state_service.user_states[user_id] = {'waiting_for': 'risk_percent'}

async def _handle_risk_percent_input(user_id: int, text: str):
    """Обработка процента риска"""
    risk_percent = float(text)
    if risk_percent <= 0 or risk_percent > 10:
        await edit_navigation_message(
            user_id,
            "❌ Процент риска должен быть от 0.1% до 10%\n\n"
            f"Введите процент риска:",
            keyboards.cancel_keyboard(),
            "Markdown"
        )
        return
    
    risk_percent_decimal = risk_percent / 100
    state_service.user_calculation_data[user_id]['risk_percent'] = risk_percent_decimal
    
    await calculate_and_show_trade(user_id)

async def calculate_and_show_trade(user_id: int):
    """Выполняет расчет и показывает результаты"""
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