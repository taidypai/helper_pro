import asyncio
import logging
from aiogram import Dispatcher

from config import bot, storage
from handlers import start_router, message_router, callback_router  # Изменен импорт
from services.price_service import price_service
from services.state_service import state_service
from services.time_utils import time_service
from services.analysis_service import analysis_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def on_startup():
    """Действия при запуске бота"""
    logger.info("Бот запущен...")
    await price_service.initialize()
    await time_service.sync_binance_time()
    logger.info("Binance time synced successfully")

async def on_shutdown():
    """Действия при остановке бота"""
    logger.info("Бот остановлен...")
    await price_service.close()
    await bot.session.close()

async def cleanup_task():
    """Задача для очистки неактивных пользователей"""
    while True:
        await asyncio.sleep(3600*24*7)  # Каждые 7 дней
        state_service.cleanup_inactive_users()

async def main():
    """Основная функция запуска бота"""
    dp = Dispatcher(storage=storage)
    
    dp.include_router(start_router)
    dp.include_router(message_router)
    dp.include_router(callback_router)  # Добавлен callback_router
    
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    
    cleanup_task_instance = asyncio.create_task(cleanup_task())
    
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Ошибка в боте: {e}")
    finally:
        cleanup_task_instance.cancel()
        await on_shutdown()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")