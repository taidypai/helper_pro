import pytz
import datetime
import asyncio
import aiohttp
import logging
from typing import Dict, Tuple, Optional

logger = logging.getLogger(__name__)

class TimeService:
    def __init__(self):
        self.timeframe_minutes = {
            '5m': 5, '15m': 15, '30m': 30, 
            '1h': 60, '4h': 240, '1d': 1440
        }
        self.binance_server_time_diff = 0
        self.last_sync_time = 0
    
    async def sync_binance_time(self):
        """Синхронизация времени с Binance API"""
        try:
            url = "https://api.binance.com/api/v3/time"
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        binance_server_time = data['serverTime'] / 1000
                        local_time = datetime.datetime.now().timestamp()
                        self.binance_server_time_diff = binance_server_time - local_time
                        self.last_sync_time = local_time
                        logger.info(f"Synced with Binance time. Diff: {self.binance_server_time_diff:.2f}s")
                    else:
                        logger.warning("Failed to sync with Binance time")
        except Exception as e:
            logger.error(f"Error syncing with Binance: {e}")
    
    def get_binance_time(self) -> datetime.datetime:
        """Получение текущего времени по Binance"""
        local_time = datetime.datetime.now().timestamp()
        if local_time - self.last_sync_time > 3600:
            asyncio.create_task(self.sync_binance_time())
        
        binance_timestamp = local_time + self.binance_server_time_diff
        return datetime.datetime.fromtimestamp(binance_timestamp, pytz.UTC)
    
    async def get_time_to_candle_close(self, timeframe: str) -> Tuple[int, datetime.datetime]:
        """Простой расчет времени до закрытия свечи"""
        now = self.get_binance_time()
        
        if timeframe not in self.timeframe_minutes:
            return 0, now
        
        minutes = self.timeframe_minutes[timeframe]
        total_minutes = now.hour * 60 + now.minute
        remainder = total_minutes % minutes
        minutes_remaining = minutes - remainder
        
        close_time = now.replace(second=0, microsecond=0) + datetime.timedelta(
            minutes=minutes_remaining
        )
        
        seconds_remaining = max(0, int((close_time - now).total_seconds()))
        return seconds_remaining, close_time
    
    @staticmethod
    async def format_time_remaining(seconds: int) -> str:
        """Форматирование времени в читаемый вид"""
        if seconds >= 3600:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            return f"{hours}ч {minutes}м"
        elif seconds >= 60:
            minutes = seconds // 60
            seconds_remaining = seconds % 60
            return f"{minutes}м {seconds_remaining}с"
        else:
            return f"{seconds}с"

class TimeframeManager:
    def __init__(self):
        self.current_timeframe: Optional[str] = None
        self.timeframe_texts = {
            '1d': "1 день (дневные свечи)",
            '4h': "4 часа (4-часовые свечи)", 
            '1h': "1 час (часовые свечи)",
            '30m': "30 минут (30-минутные свечи)",
            '15m': "15 минут (15-минутные свечи)",
            '5m': "5 минут (5-минутные свечи)"
        }
    
    def set_timeframe(self, timeframe: str):
        """Установка текущего таймфрейма"""
        valid_timeframes = ['1d', '4h', '1h', '30m', '15m', '5m']
        if timeframe in valid_timeframes:
            self.current_timeframe = timeframe
            logger.info(f"Timeframe set to {timeframe}")
        else:
            logger.warning(f"Invalid timeframe attempt: {timeframe}")
    
    def get_timeframe(self) -> Optional[str]:
        """Получение текущего таймфрейма"""
        return self.current_timeframe
    
    def get_timeframe_text(self, timeframe: str) -> str:
        """Получение текстового описания таймфрейма"""
        return self.timeframe_texts.get(timeframe, timeframe)

class TimezoneService:
    def __init__(self):
        self.user_timezones: Dict[int, str] = {}
        self.common_timezones = {
            'MSK': 'Europe/Moscow',
            'UTC': 'UTC',
            'EST': 'America/New_York', 
            'PST': 'America/Los_Angeles',
            'CET': 'Europe/Paris',
            'GMT': 'Europe/London',
            'IST': 'Asia/Kolkata',
            'CST': 'Asia/Shanghai',
            'JST': 'Asia/Tokyo',
            'AEST': 'Australia/Sydney'
        }
    
    def set_user_timezone(self, user_id: int, timezone: str):
        """Установка временной зоны пользователя"""
        if timezone in self.common_timezones.values() or timezone in pytz.all_timezones:
            self.user_timezones[user_id] = timezone
            logger.info(f"User {user_id} timezone set to {timezone}")
        else:
            raise ValueError(f"Invalid timezone: {timezone}")
    
    def get_user_timezone(self, user_id: int) -> str:
        """Получение временной зоны пользователя"""
        return self.user_timezones.get(user_id, 'Europe/Moscow')
    
    def format_time_for_user(self, user_id: int, dt: datetime.datetime) -> str:
        """Форматирование времени для пользователя"""
        timezone = self.get_user_timezone(user_id)
        try:
            user_tz = pytz.timezone(timezone)
            user_time = dt.astimezone(user_tz)
            
            tz_abbr = self.get_timezone_abbreviation(timezone)
            
            return user_time.strftime(f"%H:%M {tz_abbr}")
        except Exception as e:
            logger.error(f"Error formatting time for user {user_id}: {e}")
            return dt.strftime("%H:%M UTC")
    
    def get_timezone_abbreviation(self, timezone: str) -> str:
        """Получение аббревиатуры временной зоны"""
        for abbr, tz in self.common_timezones.items():
            if tz == timezone:
                return abbr
        return timezone.split('/')[-1]
    
    def get_available_timezones(self) -> Dict[str, str]:
        """Получение списка доступных временных зон"""
        return self.common_timezones

time_service = TimeService()
timeframe_manager = TimeframeManager()
timezone_service = TimezoneService()