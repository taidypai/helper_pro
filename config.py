import os
from aiogram import Bot
from aiogram.fsm.storage.memory import MemoryStorage

# Конфигурация из переменных окружения
#TOKEN = '8213569469:AAExbtP6wQaKky-4Y4TQ9E807j184QSH6hY' #бэк Тест
TOKEN = '8442684870:AAEwtD81q4QbQSL5D7fnGUYY7wiOkODAHGM' # Основной

# Инициализация бота и хранилища
bot = Bot(token=TOKEN)
storage = MemoryStorage()

# Глобальные состояния
subscribed_users = set()
running_analyses = {}
