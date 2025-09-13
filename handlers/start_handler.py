from aiogram.filters import Command, CommandStart
from aiogram import types, Router
import asyncio
import logging

from config import bot, subscribed_users  # Импортируем bot
from services.message_utils import edit_navigation_message  # Импортируем отсюда

import keyboards
from services.trade_calculator import trade_calculator

logger = logging.getLogger(__name__)
start_router = Router()

@start_router.message(CommandStart())
async def handle_start(message: types.Message):
    """Обработка команды /start"""
    try:
        #await message.delete()
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
        
        # Очищаем предыдущие данные
        from services.state_service import state_service
        if user_id in state_service.user_states:
            del state_service.user_states[user_id]
        if user_id in state_service.user_calculation_data:
            del state_service.user_calculation_data[user_id]
        
        # Создаем навигационное сообщение
        nav_message = await message.answer(
            "*КАЛЬКУЛЯТОР ПОЗИЦИИ*\n\n"
            "Выберите направление сделки:",
            reply_markup=keyboards.lot_keyboard(),
            parse_mode="Markdown"
        )
        
        # Сохраняем ID навигационного сообщения
        state_service.set_navigation_id(user_id, nav_message.message_id)
        
        # Удаляем команду
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
    
    # Запускаем задачу с анимацией
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


@start_router.message()
async def handle_trade_inputs(message: types.Message):
    """Обработка ввода данных для расчета позиции"""
    from services.state_service import state_service
    from services.message_utils import edit_navigation_message
    
    user_id = message.from_user.id
    
    # Проверяем, ожидаем ли мы ввод от пользователя
    if user_id not in state_service.user_states:
        return
    
    user_state = state_service.user_states[user_id]
    waiting_for = user_state.get('waiting_for')
    
    if not waiting_for:
        return
    
    try:
        text = message.text.strip()
        
        if waiting_for == 'balance':
            # Обработка ввода баланса
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
            
            # Переходим к цене входа
            direction = state_service.user_calculation_data[user_id].get('direction', 'long')
            
            await edit_navigation_message(
                user_id,
                f"Введите цену входа для {direction.upper()}:",
                keyboards.cancel_keyboard(),
                "Markdown"
            )
            state_service.user_states[user_id] = {'waiting_for': 'entry_price'}
            
        elif waiting_for == 'entry_price':
            # Обработка цены входа
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
            
            # Переходим к стоп-лоссу
            direction = state_service.user_calculation_data[user_id].get('direction', 'long')
            stop_text = "ниже цены входа" if direction == 'long' else "выше цены входа"
            
            await edit_navigation_message(
                user_id,
                f"Введите стоп-лосс ({stop_text}):",
                keyboards.cancel_keyboard(),
                "Markdown"
            )
            state_service.user_states[user_id] = {'waiting_for': 'stop_loss'}
            
        elif waiting_for == 'stop_loss':
            # Обработка стоп-лосса
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
            
            # Валидация стоп-лосса
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
            
            # Переходим к risk/reward ratio
            await edit_navigation_message(
                user_id,
                "Введите соотношение Risk/Reward (например: 1 для 1:1, 2 для 1:2 и т.д.):",
                keyboards.cancel_keyboard(),
                "Markdown"
            )
            state_service.user_states[user_id] = {'waiting_for': 'risk_reward'}
            
        elif waiting_for == 'risk_reward':
            # Обработка risk/reward ratio
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
            
            # Переходим к проценту риска
            await edit_navigation_message(
                user_id,
                "⚠️ Введите процент риска на сделку (например: 2 для 2%, 0.5 для 0.5%):\n"
                "Или нажмите /default для использования значения по умолчанию (0.5%)",
                keyboards.cancel_keyboard(),
                "Markdown"
            )
            state_service.user_states[user_id] = {'waiting_for': 'risk_percent'}
            
        elif waiting_for == 'risk_percent':
            # Обработка процента риска
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
            
            # Все данные собраны, производим расчет
            await calculate_and_show_trade(user_id)
            
        # Удаляем сообщение пользователя
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

@start_router.message(Command("default"))
async def handle_default_risk(message: types.Message):
    """Использование значения риска по умолчанию"""
    from services.state_service import state_service
    
    user_id = message.from_user.id
    
    if user_id not in state_service.user_states:
        return
    
    user_state = state_service.user_states[user_id]
    if user_state.get('waiting_for') != 'risk_percent':
        return
    
    # Используем значение по умолчанию 0.5%
    state_service.user_calculation_data[user_id]['risk_percent'] = 0.005
    
    # Все данные собраны, производим расчет
    await calculate_and_show_trade(user_id)
    
    # Удаляем сообщение с командой
    try:
        asyncio.sleep(2)
        await message.delete()
    except:
        pass

async def calculate_and_show_trade(user_id: int):
    """Выполняет расчет и показывает результаты"""
    from services.state_service import state_service
    from services.message_utils import edit_navigation_message
    
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
        
        # Выполняем расчет
        result = trade_calculator.calculate_trade(user_data)
        
        if 'error' in result:
            await edit_navigation_message(
                user_id,
                f"❌ Ошибка расчета: {result['error']}",
                keyboards.lot_keyboard(),
                "Markdown"
            )
            return
        
        # Сохраняем результат
        state_service.user_calculation_data[user_id]['result'] = result
        
        # Формируем краткое сообщение с результатами
        trade = result['success']
        
        brief_message = (
            f"🎯 *РАСЧЕТ ПОЗИЦИИ ЗАВЕРШЕН*\n\n"
            f"• Направление: {trade.direction.upper()}\n"
            f"• Цена входа: ${trade.entry_price:.2f}\n"
            f"• Стоп-лосс: ${trade.stop_loss:.2f}\n"
            f"• Тейк-профит: ${trade.take_profit:.2f}\n\n"
            f"💡 *РЕКОМЕНДАЦИЯ:*\n"
            f"• Объем: {trade_calculator.format_volume(trade.volume)}\n"
            f"• Плечо: x{trade.required_leverage:.2f}\n"
            f"• Риск: ${trade.risk_money:.2f} ({trade.risk_percent*100:.1f}%)\n\n"
            f"📊 Потенциальная прибыль: ${trade.potential_profit:.2f}"
        )
        
        # Редактируем навигационное сообщение
        await edit_navigation_message(
            user_id,
            brief_message,
            keyboards.trade_details_keyboard(),
            "Markdown"
        )
        
        # Очищаем состояние ожидания
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
        
        # Очищаем состояние в случае ошибки
        if user_id in state_service.user_states:
            del state_service.user_states[user_id]