# Техническая архитектура проекта

## 1. Сбор данных

### 1.1 Источники данных

#### 1.1.1 Blockchain.com API
- **Назначение**: Получение основных метрик блокчейна Bitcoin
- **Метрики**:
  - Рыночные данные (цена, объем, капитализация)
  - Данные сети (транзакции, комиссии)
  - Данные майнинга (доход майнеров, сложность)
- **Периодичность**: Ежедневное обновление
- **Хранение**: CSV файлы в директории data/

#### 1.1.2 Yahoo Finance API
- **Назначение**: Получение данных о связанных активах
- **Метрики**:
  - Акции крипто-компаний (MSTR, COIN, MARA, RIOT)
  - Индексы (SPY, QQQ)
  - Сырьевые товары (GLD)
  - Валюты (UUP)
- **Периодичность**: Ежедневное обновление
- **Хранение**: CSV файлы в директории data/market_data/

#### 1.1.3 LunarCrush API
- **Назначение**: Получение данных о социальных настроениях
- **Метрики**:
  - Социальные метрики (упоминания, настроения)
  - Рыночные метрики
  - Новостные данные
- **Периодичность**: Ежедневное обновление
- **Хранение**: CSV файлы в директории data/lunarcrush/

#### 1.1.4 Fear & Greed Index
- **Назначение**: Индикатор рыночных настроений
- **Метрики**: Индекс страха и жадности (0-100)
- **Периодичность**: Ежедневное обновление
- **Хранение**: CSV файлы в директории data/sentiment/

### 1.2 Система сбора данных

#### 1.2.1 Коллекторы данных
- **BlockchainDataCollector**: Сбор данных с Blockchain.com
- **YahooFinanceCollector**: Сбор данных с Yahoo Finance
- **LunarCrushCollector**: Сбор данных с LunarCrush
- **SentimentDataCollector**: Сбор данных о настроениях

#### 1.2.2 Механизм обновления
```python
class HistoricalDataCollector:
    def __init__(self):
        self.blockchain_collector = BlockchainDataCollector()
        self.yahoo_collector = YahooFinanceCollector()
        self.lunarcrush_collector = LunarCrushCollector()
        self.sentiment_collector = SentimentDataCollector()

    def update_all_data(self):
        # Обновление всех источников данных
        self.blockchain_collector.update_all_metrics()
        self.yahoo_collector.update_all_data()
        self.lunarcrush_collector.update_all_metrics()
        self.sentiment_collector.update_fear_and_greed_index()
```

## 2. Обработка данных

### 2.1 Предобработка
- Очистка пропущенных значений
- Нормализация временных рядов
- Агрегация данных из разных источников

### 2.2 Создание признаков
- Технические индикаторы
- Социальные метрики
- Рыночные корреляции
- Метрики блокчейна

### 2.3 Масштабирование
- MinMaxScaler для числовых данных
- Нормализация временных рядов
- Сохранение скейлеров

## 3. Модели

### 3.1 Ансамбль LSTM
- Краткосрочная модель (1-7 дней)
- Среднесрочная модель (7-30 дней)
- Модель тренда

### 3.2 Валидация
- Проверка реалистичности предсказаний
- Оценка точности
- Мониторинг производительности

## 4. Инфраструктура

### 4.1 Структура проекта
```
project/
├── extended_version/
│   ├── blockchain_data_collector.py
│   ├── yahoo_finance_collector.py
│   ├── lunarcrush_collector.py
│   ├── sentiment_data_collector.py
│   └── historical_data_collector.py
├── model/
│   ├── models/
│   └── preprocessing/
├── data/
│   ├── blockchain/
│   ├── market_data/
│   ├── lunarcrush/
│   └── sentiment/
└── config/
    └── config.py
```

### 4.2 Конфигурация
- API ключи в config.py
- Параметры моделей
- Настройки логирования

### 4.3 Логирование
- Информация о сборе данных
- Ошибки и предупреждения
- Метрики производительности

## 5. Безопасность

### 6.1 Валидация входных данных
- Проверка целостности данных
- Обработка отсутствующих значений
- Проверка форматов данных

### 6.2 Обработка ошибок
- Логирование исключений
- Graceful degradation
