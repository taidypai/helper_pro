from aiogram import Router
from .settings_handlers import settings_router
from .trade_handlers import trade_router
from .time_handlers import time_router
from .navigation_handlers import navigation_router

callback_router = Router()
callback_router.include_router(settings_router)
callback_router.include_router(trade_router)
callback_router.include_router(time_router)
callback_router.include_router(navigation_router)


__all__ = ['callback_router']