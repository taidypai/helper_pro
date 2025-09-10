from typing import Dict, Optional
import time
import logging

logger = logging.getLogger(__name__)

class StateService:
    """Сервис для управления состоянием пользователей"""
    
    def __init__(self):
        self.user_navigation_ids: Dict[int, int] = {}
        self.user_states: Dict[int, dict] = {}
        self.user_last_activity: Dict[int, float] = {}
    
    def set_navigation_id(self, user_id: int, message_id: int):
        """Установка ID навигационного сообщения для пользователя"""
        self.user_navigation_ids[user_id] = message_id
        self.user_last_activity[user_id] = time.time()
    
    def get_navigation_id(self, user_id: int) -> Optional[int]:
        """Получение ID навигационного сообщения"""
        self.user_last_activity[user_id] = time.time()
        return self.user_navigation_ids.get(user_id)
    
    def clear_navigation_id(self, user_id: int):
        """Очистка ID навигационного сообщения"""
        if user_id in self.user_navigation_ids:
            del self.user_navigation_ids[user_id]
        if user_id in self.user_last_activity:
            del self.user_last_activity[user_id]
    
    def cleanup_inactive_users(self, inactive_time: int = 3600):
        """Очистка неактивных пользователей"""
        current_time = time.time()
        users_to_remove = [
            user_id for user_id, last_activity in self.user_last_activity.items()
            if current_time - last_activity > inactive_time
        ]
        
        for user_id in users_to_remove:
            self.clear_navigation_id(user_id)
            logger.info(f"Cleaned up inactive user: {user_id}")

# Глобальный экземпляр сервиса состояния
state_service = StateService()