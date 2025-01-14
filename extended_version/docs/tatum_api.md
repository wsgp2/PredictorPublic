# Документация Tatum API для предсказания цены Bitcoin

## 1. Доступные эндпоинты

### 1.1 Rate API (Цены)
```
GET https://api.tatum.io/v3/tatum/rate/BTC?basePair=USD
```
- ✅ Текущая цена BTC/USD
- ✅ Источник данных (CoinGecko)
- ✅ Временная метка

### 1.2 Bitcoin RPC API

#### Информация о сети (getnetworkinfo)
```
POST https://api.tatum.io/v3/bitcoin/node
```
- ✅ Количество соединений
- ✅ Версия протокола
- ✅ Состояние сети

#### Информация о блокчейне (getblockchaininfo)
- ✅ Количество блоков
- ✅ Сложность сети
- ✅ Время последнего блока
- ✅ Размер блокчейна

#### Информация о мемпуле (getmempoolinfo)
- ✅ Количество транзакций в мемпуле
- ✅ Размер мемпула в байтах
- ✅ Общая комиссия
- ✅ Минимальная комиссия

#### Информация о майнинге (getmininginfo)
- ✅ Текущий хэшрейт сети
- ✅ Сложность
- ✅ Количество транзакций в пуле

#### Информация о блоке (getblock)
- ✅ Хэш блока
- ✅ Количество транзакций
- ✅ Размер блока
- ✅ Вес блока
- ✅ Время создания

## 2. Анализ доступности данных по плану

### 2.1 Доступные данные

#### Ончейн-метрики:
- ✅ Хэшрейт сети
- ✅ Количество транзакций (в блоке и мемпуле)
- ✅ Сложность сети
- ❌ Активные адреса
- ❌ Доля монет на биржах

#### Рыночные данные:
- ✅ Текущая цена BTC/USD
- ❌ Объем торгов
- ❌ Рыночная капитализация
- ❌ Спреды и ликвидность

### 2.2 Недоступные данные (нужны дополнительные API)

1. **Ончейн-метрики:**
   - Количество активных адресов
   - Распределение монет по адресам
   - Балансы бирж

2. **Рыночные данные:**
   - Объем торгов по биржам
   - Данные о ликвидности
   - Спреды

3. **Сентимент и социальные данные:**
   - Твиты и социальные упоминания
   - Поисковые запросы
   - Активность на форумах

4. **Технические индикаторы:**
   - RSI
   - MACD
   - Скользящие средние

5. **Макроэкономические показатели:**
   - Индекс доллара (DXY)
   - Процентные ставки
   - Инфляция

6. **Данные деривативов:**
   - Открытый интерес
   - Фьючерсные цены
   - Опционные данные

## 3. Рекомендации по сбору данных

### 3.1 Частота сбора:
- Цена BTC/USD: каждую минуту
- Блокчейн метрики: каждые 10 минут
- Мемпул: каждые 5 минут

### 3.2 Формат хранения:
```json
{
    "timestamp": "unix_timestamp",
    "price_usd": "float",
    "network": {
        "hashrate": "float",
        "difficulty": "float",
        "connections": "int"
    },
    "mempool": {
        "tx_count": "int",
        "size_bytes": "int",
        "total_fee": "float"
    },
    "latest_block": {
        "height": "int",
        "tx_count": "int",
        "size": "int",
        "time": "unix_timestamp"
    }
}

```

## 4. CCXT API (Биржевые данные)

### 4.1 Установка и инициализация
```bash
pip install ccxt
```

```python
import ccxt

# Инициализация бирж
exchanges = {
    'binance': ccxt.binance(),
    'kraken': ccxt.kraken(),
    'coinbase': ccxt.coinbasepro()
}
```

### 4.2 Доступные методы

#### 4.2.1 Получение тикера (Цена и объем)
```python
# Получение текущей цены и объема торгов
ticker = exchange.fetch_ticker('BTC/USDT')
{
    'last': float,      # Последняя цена
    'bid': float,       # Лучшая цена покупки
    'ask': float,       # Лучшая цена продажи
    'baseVolume': float # Объем в базовой валюте
}
```

#### 4.2.2 Книга ордеров
```python
# Получение книги ордеров
orderbook = exchange.fetch_order_book('BTC/USDT')
{
    'bids': [[price, volume], ...],  # Ордера на покупку
    'asks': [[price, volume], ...],  # Ордера на продажу
    'timestamp': int                 # Временная метка
}
```

#### 4.2.3 OHLCV данные
```python
# Получение исторических свечей
ohlcv = exchange.fetch_ohlcv('BTC/USDT', '1h', limit=10)
# Каждая свеча: [timestamp, open, high, low, close, volume]
```

### 4.3 Частота обновления данных
- Тикер: каждую минуту
- Книга ордеров: каждые 5 секунд
- OHLCV: каждый час

### 4.4 Ограничения
- Разные биржи имеют разные лимиты запросов
- Некоторые методы могут быть недоступны на определенных биржах
- Требуется обработка ошибок и повторные попытки

### 4.5 Формат хранения данных
```json
{
    "timestamp": "ISO-8601",
    "exchange_data": {
        "binance": {
            "ticker": {
                "last": float,
                "volume": float
            },
            "orderbook": {
                "bids_count": int,
                "asks_count": int
            }
        },
        "kraken": {
            // Аналогичная структура
        }
    }
}

```

## 5. CCXT (Биржевые данные)

### 5.1 Установка и базовая настройка
```bash
pip install ccxt pandas
```

### 5.2 Доступные данные

#### 5.2.1 Текущие рыночные данные
- Тикер (цена, объем)
- Книга ордеров
- Последние сделки
- OHLCV данные

#### 5.2.2 Поддерживаемые биржи
- Binance
- Kraken
- Coinbase
- И многие другие (100+ бирж)

### 5.3 Примеры использования

#### 5.3.1 Получение текущей цены
```python
import ccxt

exchange = ccxt.binance()
ticker = exchange.fetch_ticker('BTC/USDT')
print(f"Цена BTC: {ticker['last']}")
```

#### 5.3.2 Получение исторических данных
```python
ohlcv = exchange.fetch_ohlcv('BTC/USDT', '1h')
# Формат: [timestamp, open, high, low, close, volume]
```

#### 5.3.3 Получение книги ордеров
```python
orderbook = exchange.fetch_order_book('BTC/USDT')
print(f"Лучшая цена покупки: {orderbook['bids'][0][0]}")
print(f"Лучшая цена продажи: {orderbook['asks'][0][0]}")
```

### 5.4 Ограничения и рекомендации

#### 5.4.1 Лимиты запросов
- Binance: 1200 запросов в минуту
- Kraken: 15 запросов в секунду
- Coinbase: 3 запросов в секунду

#### 5.4.2 Рекомендуемая частота сбора
- Тикер: каждую минуту
- Книга ордеров: каждые 5 секунд
- OHLCV: каждый час

#### 5.4.3 Обработка ошибок
```python
try:
    data = exchange.fetch_ticker('BTC/USDT')
except ccxt.NetworkError as e:
    print(f"Ошибка сети: {str(e)}")
except ccxt.ExchangeError as e:
    print(f"Ошибка биржи: {str(e)}")
```

### 5.5 Формат хранения данных
```json
{
    "timestamp": "ISO-8601",
    "exchange": "binance",
    "symbol": "BTC/USDT",
    "ticker": {
        "last": float,
        "bid": float,
        "ask": float,
        "volume": float
    },
    "orderbook": {
        "bids": [[price, volume], ...],
        "asks": [[price, volume], ...]
    },
    "ohlcv": {
        "timestamp": int,
        "open": float,
        "high": float,
        "low": float,
        "close": float,
        "volume": float
    }
}
