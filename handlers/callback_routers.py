from aiogram import Router, F
from aiogram.types import CallbackQuery
import asyncio
import logging

from services.state_service import state_service
import keyboards
from services.trade_calculator import trade_calculator
from services.message_utils import edit_navigation_message

logger = logging.getLogger(__name__)
callback_router = Router()


@callback_router.callback_query(F.data == "settings")
async def handle_settings_callback(callback: CallbackQuery):
    """Обработка callback с данными 'settings'"""
    try:
        user_id = callback.from_user.id
        from services.state_service import state_service

        # Сохраняем ID навигационного сообщения
        state_service.set_navigation_id(user_id, callback.message.message_id)

        await edit_navigation_message(
            user_id,
            'Выберите временную зону:',
            keyboards.timezone_keyboard(),
            None
        )
    except Exception as e:
        logger.error(f"Error in settings callback: {e}")
        await callback.answer("Произошла ошибка")

@callback_router.callback_query(F.data == "go")
async def instruction_callback(callback: CallbackQuery):
    try:
        #await message.delete()
        user_id = callback.message.from_user.id
        novigation_message = await callback.message.edit_text(f'Перейдите в настройки', reply_markup=keyboards.main_keyboard())
        state_service.set_navigation_id(user_id, novigation_message.message_id)
        await asyncio.sleep(2)

    except Exception as e:
        logger.error(f"Error in start handler: {e}")
        await callback.message.answer("Произошла ошибка при запуске основной функции")

@callback_router.callback_query(F.data.in_(['MSK', 'UTC', 'EST', 'CET', 'GMT']))
async def handle_timezone_callback(callback: CallbackQuery):
    """Обработка выбора временной зоны"""
    try:
        user_id = callback.from_user.id
        from services.state_service import state_service

        # Сохраняем ID навигационного сообщения
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
        from services.time_utils import timezone_service
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

@callback_router.callback_query(F.data == "back")
async def handle_back_callback(callback: CallbackQuery):
    """Обработка callback с данными 'back'"""
    try:
        user_id = callback.from_user.id
        from services.state_service import state_service

        # Сохраняем ID навигационного сообщения
        state_service.set_navigation_id(user_id, callback.message.message_id)

        # Если мы в процессе расчета - очищаем состояние
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

@callback_router.callback_query(F.data.in_(["1d", "4h", "1h", "30m", "15m", "5m"]))
async def handle_timeframe(callback: CallbackQuery):
    await handle_timeframe_selection(callback, callback.data)

async def handle_timeframe_selection(callback: CallbackQuery, timeframe: str):
    """Общая функция обработки выбора таймфрейма"""
    try:
        user_id = callback.from_user.id
        from services.state_service import state_service

        # Сохраняем ID навигационного сообщения
        state_service.set_navigation_id(user_id, callback.message.message_id)

        from services.time_utils import time_service, timeframe_manager
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

@callback_router.callback_query(F.data == "progress")
async def handle_progress_callback(callback: CallbackQuery):
    from services.time_utils import timezone_service, time_service, timeframe_manager
    user_id = callback.message.from_user.id

    """Обработка нажатия на кнопку прогресса"""

    get_timeframe = timeframe_manager.get_timeframe()
    timeframe = timeframe_manager.get_timeframe_text(get_timeframe)
    current_time = time_service.get_binance_time()
    user_timezone = timezone_service.get_user_timezone(user_id)
    text_analizmessage = (
        f"Ваша зона {user_timezone}\n"
        f"Таймфрейм {timeframe}\n"
        f"Binance {current_time.strftime('%H:%M:%S UTC')}"
    )

    await callback.answer(text_analizmessage, show_alert=True)

@callback_router.callback_query(F.data == "lot")
async def handle_lot_callback(callback: CallbackQuery):
    try:
        user_id = callback.from_user.id

        # Сохраняем ID навигационного сообщения
        from services.state_service import state_service
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

@callback_router.callback_query(F.data.in_(["long", "short"]))
async def handle_direction_selection(callback: CallbackQuery):
    """Обработка выбора направления сделки"""
    try:
        user_id = callback.from_user.id
        direction = callback.data

        # Сохраняем ID навигационного сообщения (на случай если его еще нет)
        from services.state_service import state_service
        state_service.set_navigation_id(user_id, callback.message.message_id)

        # Сохраняем направление
        if user_id not in state_service.user_calculation_data:
            state_service.user_calculation_data[user_id] = {}
        state_service.user_calculation_data[user_id]['direction'] = direction

        # Устанавливаем состояние ожидания ввода баланса
        state_service.user_states[user_id] = {'waiting_for': 'balance'}

        await edit_navigation_message(
            user_id,
            f"*Расчет позиции - {direction.upper()}*\n\n"
            f"Введите ваш баланс в USDT:",
            keyboards.cancel_keyboard(),
            "Markdown"
        )

    except Exception as e:
        logger.error(f"Error in direction selection: {e}")
        await callback.answer("Произошла ошибка")

@callback_router.callback_query(F.data == "cancel_trade")
async def handle_cancel_trade(callback: CallbackQuery):
    """Обработка отмены расчета"""
    try:
        user_id = callback.from_user.id

        # Очищаем состояние
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

@callback_router.callback_query(F.data == "trade_details")
async def handle_trade_details(callback: CallbackQuery):
    """Показать детальную информацию о сделке"""
    try:
        user_id = callback.from_user.id
        from services.state_service import state_service

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
            f"• Объем: {trade_calculator.format_volume(trade.volume)}\n"
            f"• Стоимость позиции: ${trade.position_value:.2f}\n"
            f"• Плечо: x{trade.required_leverage:.2f}\n"
            f"• Дистанция риска: {trade.risk_distance_percent:.2f}%\n\n"
            f"*ПОТЕНЦИАЛ:*\n"
            f"• Потенциальный убыток: ${trade.potential_loss:.2f}\n"
            f"• Потенциальная прибыль: ${trade.potential_profit:.2f}\n\n"
            f"*ВНИМАНИЕ:* Все расчеты приблизительные"
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

@callback_router.callback_query(F.data == "trade_brief")
async def handle_trade_brief(callback: CallbackQuery):
    """Вернуться к краткому виду"""
    try:
        user_id = callback.from_user.id
        from services.state_service import state_service

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

@callback_router.callback_query(F.data == "new_trade")
async def handle_new_trade(callback: CallbackQuery):
    """Начать новый расчет"""
    try:
        user_id = callback.from_user.id
        from services.state_service import state_service

        # Очищаем данные
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

@callback_router.callback_query(F.data == "back_to_main")
async def handle_back_to_main(callback: CallbackQuery):
    """Вернуться в главное меню"""
    try:
        user_id = callback.from_user.id
        from services.state_service import state_service

        # Очищаем данные
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