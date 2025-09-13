Структура проэкта


your_bot_project/
├──  run_bot.py               # Главный файл запуска \n


├──  config.py                # Конфигурация бота\n

├──  requirements.txt         # Зависимости (желательно создать)

│
├── 📁 services/               # Папка с сервисами

│   ├──  __init__.py          # Инициализация сервисов
│   ├──  analysis_service.py  # Анализ цен
│   ├──  price_service.py     # Работа с Binance API
│   ├──  time_utils.py        # Время и таймфреймы
│   ├──  state_service.py     # Состояние пользователей
│   ├──  message_utils.py     # Утилиты сообщений
│   ├──  progress_service.py  # Анимация прогресса
│   ├──  models.py
│   └──  trade_calculator.py  # Счетчик позиции
│
│
├──  handlers/                # Папка с обработчиками
│   ├──  __init__.py          # Инициализация обработчиков
│   ├──  start_handler.py     # Обработка /start
│   └──  callback_routers.py  # Обработка callback кнопок
│
└──  keyboards.py             # Клавиатуры бота
