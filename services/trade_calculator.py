# trade_calculator.py
import logging
from typing import Dict, Optional
from dataclasses import dataclass
import math

logger = logging.getLogger(__name__)

@dataclass
class TradeParameters:
    """Дата-класс для хранения результатов расчета сделки"""
    entry_price: float
    direction: str
    stop_loss: float
    take_profit: float
    risk_reward_ratio: float
    balance: float
    risk_percent: float
    risk_money: float
    volume: float
    adjusted_volume: float  # Объем с учетом ограничений биржи
    position_value: float
    required_leverage: float
    adjusted_leverage: float  # Плечо с учетом ограничений объема
    potential_loss: float
    potential_profit: float
    risk_per_unit: float
    risk_distance_percent: float

class TradeCalculator:
    def __init__(self):
        self.default_risk_percent = 0.005  # 0.5% по умолчанию
        self.user_data: Dict[int, Dict] = {}  # Хранение данных пользователей
        self.max_decimal_places = 4  # Максимум 4 знака после запятой

    def save_user_data(self, user_id: int, data: Dict):
        """Сохраняет данные пользователя"""
        if user_id not in self.user_data:
            self.user_data[user_id] = {}
        self.user_data[user_id].update(data)

    def get_user_data(self, user_id: int) -> Optional[Dict]:
        """Получает данные пользователя"""
        return self.user_data.get(user_id)

    def clear_user_data(self, user_id: int):
        """Очищает данные пользователя"""
        if user_id in self.user_data:
            del self.user_data[user_id]

    def adjust_volume_to_precision(self, volume: float) -> float:
        """Округляет объем до 4 знаков после запятой"""
        return round(volume, self.max_decimal_places)

    def calculate_required_leverage(self, position_value: float, balance: float) -> float:
        """Рассчитывает необходимое кредитное плечо"""
        if balance <= 0:
            return 1.0
        leverage = position_value / balance
        return max(1.0, round(leverage, 2))

    def calculate_trade(self, user_data: Dict) -> Dict:
        """
        Рассчитывает параметры сделки с учетом ограничений биржи.
        """
        try:
            # Извлекаем данные
            entry_price = user_data['entry_price']
            direction = user_data['direction']
            stop_loss = user_data['stop_loss']
            risk_reward_ratio = user_data['risk_reward']
            balance = user_data['balance']
            risk_percent = user_data.get('risk_percent', self.default_risk_percent)
            
            # Валидация входных данных
            validation_error = self._validate_inputs(
                entry_price, direction, stop_loss, 
                risk_reward_ratio, balance, risk_percent
            )
            if validation_error:
                return {'error': validation_error}
            
            # Основные расчеты
            risk_per_unit = abs(entry_price - stop_loss)
            risk_distance_percent = (risk_per_unit / entry_price) * 100
            
            take_profit = self._calculate_take_profit(
                entry_price, direction, risk_per_unit, risk_reward_ratio
            )
            
            risk_money = balance * risk_percent
            
            # Расчет идеального объема
            ideal_volume = risk_money / risk_per_unit
            
            # Корректируем объем под ограничения биржи
            adjusted_volume = self.adjust_volume_to_precision(ideal_volume)
            
            # Пересчитываем сумму риска с учетом скорректированного объема
            actual_risk_money = adjusted_volume * risk_per_unit
            actual_risk_percent = (actual_risk_money / balance) * 100 if balance > 0 else 0
            
            # Расчет стоимости позиции и плеча
            position_value = adjusted_volume * entry_price
            required_leverage = self.calculate_required_leverage(position_value, balance)
            
            # Корректируем плечо (максимум 2 знака после запятой)
            adjusted_leverage = round(required_leverage, 2)
            
            potential_loss, potential_profit = self._calculate_potentials(
                direction, adjusted_volume, entry_price, stop_loss, take_profit
            )
            
            # Возвращаем результат
            trade_params = TradeParameters(
                entry_price=entry_price,
                direction=direction,
                stop_loss=stop_loss,
                take_profit=take_profit,
                risk_reward_ratio=risk_reward_ratio,
                balance=balance,
                risk_percent=risk_percent,
                risk_money=risk_money,
                volume=ideal_volume,
                adjusted_volume=adjusted_volume,
                position_value=position_value,
                required_leverage=required_leverage,
                adjusted_leverage=adjusted_leverage,
                potential_loss=potential_loss,
                potential_profit=potential_profit,
                risk_per_unit=risk_per_unit,
                risk_distance_percent=risk_distance_percent
            )
            
            return {'success': trade_params}
            
        except KeyError as e:
            return {'error': f'Отсутствует обязательное поле: {e}'}
        except Exception as e:
            logger.error(f"Unexpected error in trade calculation: {e}")
            return {'error': f'Неожиданная ошибка: {str(e)}'}

    def _validate_inputs(self, entry_price, direction, stop_loss, 
                        risk_reward_ratio, balance, risk_percent):
        """Валидация входных параметров"""
        if any(val <= 0 for val in [balance, entry_price, stop_loss, risk_reward_ratio]):
            return 'Все значения должны быть положительными числами'
        
        if entry_price == stop_loss:
            return 'Цена входа не может быть равна стоп-лоссу'
        
        if direction.lower() not in ['long', 'short']:
            return "Направление должно быть 'long' или 'short'"
        
        if risk_percent <= 0 or risk_percent > 0.1:  # Максимум 10% риска
            return 'Процент риска должен быть между 0.1% и 10%'
        
        # Проверка для long: стоп должен быть ниже цены входа
        if direction.lower() == 'long' and stop_loss >= entry_price:
            return 'Для LONG стоп-лосс должен быть ниже цены входа'
        
        # Проверка для short: стоп должен быть выше цены входа
        if direction.lower() == 'short' and stop_loss <= entry_price:
            return 'Для SHORT стоп-лосс должен быть выше цены входа'
        
        return None

    def _calculate_take_profit(self, entry_price, direction, risk_per_unit, risk_reward_ratio):
        """Расчет тейк-профита"""
        if direction.lower() == 'long':
            return entry_price + (risk_per_unit * risk_reward_ratio)
        else:
            return entry_price - (risk_per_unit * risk_reward_ratio)

    def _calculate_potentials(self, direction, volume, entry_price, stop_loss, take_profit):
        """Расчет потенциальной прибыли/убытка"""
        if direction.lower() == 'long':
            potential_loss = volume * (entry_price - stop_loss)
            potential_profit = volume * (take_profit - entry_price)
        else:
            potential_loss = volume * (stop_loss - entry_price)
            potential_profit = volume * (entry_price - take_profit)
        
        return potential_loss, potential_profit

    def format_volume(self, volume: float) -> str:
        """Форматирование объема для вывода"""
        return f"{volume:.{self.max_decimal_places}f}"

    def format_leverage(self, leverage: float) -> str:
        """Форматирование плеча для вывода"""
        return f"{leverage:.2f}"

# Глобальный экземпляр калькулятора
trade_calculator = TradeCalculator()