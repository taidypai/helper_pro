import os
from aiogram import Bot
from aiogram.fsm.storage.memory import MemoryStorage

# Конфигурация из переменных окружения
TOKEN = 'YOUR_BOT_TOKEN_HERE'

# Инициализация бота и хранилища
bot = Bot(token=TOKEN)
storage = MemoryStorage()

# Глобальные состояния
subscribed_users = set()
running_analyses = {}
