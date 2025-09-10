def calculate_position_size():
    """
    Рассчитывает объем позиции на основе баланса, цен и уровня риска.
    """
    try:
        # Шаг 1: Получение входных данных
        print("=== Калькулятор размера позиции ===")
        balance = float(input("Введите текущий баланс депозита: "))
        entry_price = float(input("Введите цену входа: "))
        stop_loss = float(input("Введите цену стоп-лосса: "))
        take_profit = float(input("Введите цену тейк-профита: "))
        risk_percent = 0.02
        
        # Проверка корректности данных
        if balance <= 0 or entry_price <= 0 or stop_loss <= 0 or take_profit <= 0:
            raise ValueError("Все значения должны быть положительными числами")
        
        if entry_price == stop_loss:
            raise ValueError("Цена входа не может быть равна стоп-лоссу")
        
        # Шаг 2: Расчет суммы риска
        risk_money = balance * risk_percent
        print(f"\nСумма риска на сделку: ${risk_money:.2f}")
        
        # Шаг 3: Расчет риска на единицу актива
        risk_per_unit = abs(entry_price - stop_loss)
        
        # Шаг 4: Расчет объема позиции
        volume = risk_money / risk_per_unit
        
        # Расчет стоимости позиции
        position_value = volume * entry_price
        
        # Расчет необходимого кредитного плеча
        if position_value > balance:
            required_leverage = position_value / balance
            print(f"⚠️  ТРЕБУЕТСЯ КРЕДИТНОЕ ПЛЕЧО: {required_leverage:.2f}:1")
            print(f"   Стоимость позиции: ${position_value:.2f}")
            print(f"   Ваш баланс: ${balance:.2f}")
        else:
            required_leverage = 1
            print(f"✅ Кредитное плечо не требуется")
            print(f"   Стоимость позиции: ${position_value:.2f}")
        
        # Шаг 5: Расчет соотношения риск/доходность
        potential_profit = abs(entry_price - take_profit)
        reward_ratio = potential_profit / risk_per_unit
        
        # Шаг 6: Вывод результатов
        print("\n=== РЕЗУЛЬТАТЫ РАСЧЕТА ===")
        print(f"Объем позиции: {volume:.6f} единиц актива")
        print(f"Необходимое плечо: {required_leverage:.2f}")
        print(f"Соотношение R/R: {reward_ratio:.2f}")
        
        # Дополнительная информация
        print(f"\nПри достижении стоп-лосса убыток: ${risk_money:.2f} ({risk_percent*100}% от депозита)")
        print(f"При достижении тейк-профита прибыль: ${volume * potential_profit:.2f}")
        
    except ValueError as e:
        print(f"\n❌ Ошибка ввода данных: {e}")
    except ZeroDivisionError:
        print(f"\n❌ Ошибка: Деление на ноль. Проверьте цены входа и стоп-лосса")
    except Exception as e:
        print(f"\n❌ Неожиданная ошибка: {e}")

# Запуск программы
if __name__ == "__main__":
    calculate_position_size()