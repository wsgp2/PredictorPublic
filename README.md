# Bitcoin Price Predictor

Комплексная система для предсказания цены Bitcoin, использующая данные из различных источников, включая блокчейн-метрики, рыночные показатели, социальные настроения и макроэкономические индикаторы.

## Основные возможности

### 1. Сбор данных
- **Blockchain.com**: Метрики блокчейна, рыночные данные
- **Yahoo Finance**: Корреляции с традиционным рынком
- **LunarCrush**: Социальные метрики и настроения
- **Fear & Greed Index**: Индикатор рыночных настроений
- **FRED API**: Макроэкономические показатели (инфляция, ставки, ВВП и др.)
- **CoinArk API**: Данные о деривативах и фьючерсах (открытый интерес, ликвидации)

### 2. Анализ данных
- Технические индикаторы
- Метрики блокчейна
- Социальные настроения
- Корреляции с традиционными активами
- Макроэкономические индикаторы

### 3. Предсказание
- Краткосрочные прогнозы (1-7 дней)
- Среднесрочные прогнозы (7-30 дней)
- Анализ тренда

## Установка

### Требования
- Python 3.8+
- pip

### Зависимости
```
numpy==1.24.3
pandas==2.0.3
scikit-learn>=0.24.0
tensorflow>=2.4.0
yfinance>=0.1.63
requests>=2.25.1
pytz>=2021.1
python-dateutil>=2.8.1
ta>=0.7.0
keras>=2.13.1
```

### Шаги установки

1. Клонируйте репозиторий:
```bash
git clone https://github.com/yourusername/Bitcoin-Price-Prediction.git
cd Bitcoin-Price-Prediction
```

2. Установите зависимости:
```bash
pip install -r requirements.txt
```

3. Настройте конфигурацию:
   - Скопируйте `config.example.py` в `config.py`
   - Добавьте необходимые API ключи:
     - Blockchain.com API
     - LunarCrush API
     - FRED API
     - CoinArk API

## Использование

### Сбор данных

```python
from extended_version.historical_data_collector import HistoricalDataCollector

# Инициализация коллектора
collector = HistoricalDataCollector()

# Сбор всех данных
collector.update_all_data()
```

### Структура проекта
```
project/
├── extended_version/          # Сборщики данных
│   ├── blockchain_data_collector.py
│   ├── yahoo_finance_collector.py
│   ├── lunarcrush_collector.py
│   ├── sentiment_data_collector.py
│   ├── fred_data_collector.py
│   ├── coinark_collector.py
│   └── historical_data_collector.py
├── model/                     # Модели и препроцессинг
│   ├── models/
│   └── preprocessing/
├── data/                      # Собранные данные
│   ├── blockchain/
│   ├── market_data/
│   ├── lunarcrush/
│   ├── sentiment/
│   ├── fred/
│   └── coinark/
└── config/                    # Конфигурация
    └── config.py
```

## Документация
- [Архитектура](ARCHITECTURE.md)
- [История изменений](CHANGELOG.md)

## Безопасность
- API ключи хранятся в отдельном конфиг-файле
- Валидация входных данных
- Обработка ошибок API

## Разработка

### Тестирование
```bash
python -m pytest tests/
```

### Форматирование кода
```bash
black .
```

## Лицензия
MIT License
