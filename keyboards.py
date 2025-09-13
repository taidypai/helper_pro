from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

def start_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="Иснтрукция", url="https://telegra.ph/MInstrukciya-09-13"),\
        InlineKeyboardButton(text="Trade & Brain", url="t.me/trade_and_brain"),
    )
    builder.row(
        InlineKeyboardButton(text="Начать работу", callback_data="go"),
    )
    return builder.as_markup()

def main_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="Сделка", callback_data="lot"),
        InlineKeyboardButton(text="Настройки", callback_data="settings")
    )
    return builder.as_markup()

def settings_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура настроек таймфреймов"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="1D", callback_data="1d"),
        InlineKeyboardButton(text="4H", callback_data="4h"),
        InlineKeyboardButton(text="1H", callback_data="1h"),
        width=3
    )
    
    builder.row(
        InlineKeyboardButton(text="30M", callback_data="30m"),
        InlineKeyboardButton(text="5M", callback_data="5m"),
        width=2
    )
    
    builder.row(
        InlineKeyboardButton(text="← Назад", callback_data="back"),
        width=1
    )
    
    return builder.as_markup()

def timezone_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора временной зоны"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="UTC", callback_data="UTC"),
        InlineKeyboardButton(text="MSK", callback_data="MSK"),
        InlineKeyboardButton(text="EST", callback_data="EST"),
        width=3
    )

    builder.row(
        InlineKeyboardButton(text="CET", callback_data="CET"),
        InlineKeyboardButton(text="GMT", callback_data="GMT"),
        width=2
    )
    
    builder.row(
        InlineKeyboardButton(text="← Назад", callback_data="back"),
        width=1
    )

    return builder.as_markup()

def lot_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура настроек таймфреймов"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="LONG", callback_data="long"),
        InlineKeyboardButton(text="SHORT", callback_data="short"),
        width=2
    )
    builder.row(
        InlineKeyboardButton(text="← Назад", callback_data="back"),
        width=1
    )
    return builder.as_markup()

def trade_details_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для деталей сделки"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="Подробнее", callback_data="trade_details"),
        InlineKeyboardButton(text="Новый расчет", callback_data="new_trade")
    )
    builder.row(
        InlineKeyboardButton(text="← Назад", callback_data="back_to_main")
    )
    return builder.as_markup()

def back_to_trade_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для возврата к основному виду"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="Кратко", callback_data="trade_brief"),
        InlineKeyboardButton(text="Новый расчет", callback_data="new_trade")
    )
    builder.row(
        InlineKeyboardButton(text="← Назад", callback_data="back_to_main")
    )
    return builder.as_markup()

def cancel_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура отмены"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="Отмена", callback_data="cancel_trade")
    )
    return builder.as_markup()

def progress_keyboard(progress: int) -> InlineKeyboardMarkup:
    """Клавиатура прогресса"""
    builder = InlineKeyboardBuilder()
    builder.button(text=f"Ожидайте", callback_data="progress")
    return builder.as_markup()
