from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

def main_keyboard() -> InlineKeyboardMarkup:
    """Основная клавиатура"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="Лот", callback_data="lot"),
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
        InlineKeyboardButton(text="5M", callback_data=" 5m"),
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

def progress_keyboard(progress: int) -> InlineKeyboardMarkup:
    """Клавиатура прогресса"""
    builder = InlineKeyboardBuilder()
    builder.button(text=f"$ Загрузка {progress}%", callback_data="progress")
    return builder.as_markup()