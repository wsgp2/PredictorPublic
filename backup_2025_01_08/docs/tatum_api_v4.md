# Документация Tatum API v4

## Общая информация

- Base URL: `https://api.tatum.io/v4`
- Необходимые заголовки:
  - `accept: application/json`
  - `x-api-key: ваш_api_ключ`

## Доступные эндпоинты

### 1. Токены (/data/tokens)

Получение информации о токенах на различных блокчейнах.

#### Параметры запроса:
- `chain` (обязательный): Блокчейн
  - Поддерживаемые сети: ethereum, polygon, binance-smart-chain, и др.
- `tokenAddress`: Адрес конкретного токена
- `pageSize`: Размер страницы (по умолчанию 50)
- `offset`: Смещение для пагинации
- `tokenTypes`: Тип токена
  - FUNGIBLE: Взаимозаменяемые токены (ERC-20)
  - MULTITOKEN: Мульти-токены (ERC-1155)
  - NFT: Невзаимозаменяемые токены (ERC-721)

#### Пример запроса:
```bash
curl --request GET \
     --url 'https://api.tatum.io/v4/data/tokens?chain=ethereum' \
     --header 'accept: application/json' \
     --header 'x-api-key: ваш_api_ключ'
```

### 2. Кошельки (/data/wallets/{address}/balance/time)

История баланса кошелька с течением времени.

#### Параметры запроса:
- `address` (обязательный): Адрес кошелька
- `chain` (обязательный): Блокчейн
- `from`: Начальное время (Unix timestamp)
- `to`: Конечное время (Unix timestamp)
- `pageSize`: Размер страницы
- `offset`: Смещение

#### Пример запроса:
```bash
curl --request GET \
     --url 'https://api.tatum.io/v4/data/wallets/0x123.../balance/time?chain=ethereum' \
     --header 'accept: application/json' \
     --header 'x-api-key: ваш_api_ключ'
```

### 3. NFT (/data/collections)

Информация о NFT коллекциях.

#### Параметры запроса:
- `chain`: Блокчейн
- `collectionAddress`: Адрес коллекции
- `pageSize`: Размер страницы
- `offset`: Смещение
- `includeMetadata`: Включать метаданные (true/false)

#### Пример запроса:
```bash
curl --request GET \
     --url 'https://api.tatum.io/v4/data/collections?chain=ethereum' \
     --header 'accept: application/json' \
     --header 'x-api-key: ваш_api_ключ'
```

### 4. Транзакции (/data/transactions)

История транзакций.

#### Параметры запроса:
- `chain`: Блокчейн
- `addresses`: Список адресов (можно указать несколько)
- `transactionTypes`: Типы транзакций
  - INCOMING: Входящие
  - OUTGOING: Исходящие
  - CONTRACT_INTERACTION: Взаимодействие с контрактом
- `from`: Начальное время
- `to`: Конечное время
- `pageSize`: Размер страницы
- `offset`: Смещение

#### Пример запроса:
```bash
curl --request GET \
     --url 'https://api.tatum.io/v4/data/transactions?chain=ethereum&addresses=0x123...' \
     --header 'accept: application/json' \
     --header 'x-api-key: ваш_api_ключ'
```

## Ограничения и лимиты

1. Rate Limits:
   - Зависят от типа подписки
   - Рекомендуется использовать пагинацию для больших наборов данных

2. Поддерживаемые блокчейны:
   - Ethereum
   - Polygon
   - Binance Smart Chain
   - Solana
   - Tron
   И другие (полный список в документации)

## Рекомендации по использованию

1. Всегда используйте пагинацию для больших наборов данных
2. Кэшируйте часто запрашиваемые данные
3. Обрабатывайте ошибки и повторяйте запросы при необходимости
4. Следите за rate limits
5. Используйте фильтры для уменьшения объема данных

## Примеры ответов

### Токены
```json
{
  "tokens": [
    {
      "chain": "ethereum",
      "address": "0x...",
      "name": "Token Name",
      "symbol": "TKN",
      "decimals": 18,
      "type": "FUNGIBLE",
      "totalSupply": "1000000000000000000000000"
    }
  ],
  "next": {
    "offset": 50
  }
}
```

### Баланс кошелька
```json
{
  "balances": [
    {
      "timestamp": 1641234567,
      "balance": "1000000000000000000",
      "tokenAddress": "0x...",
      "tokenName": "Token Name",
      "tokenSymbol": "TKN"
    }
  ],
  "next": {
    "offset": 50
  }
}
```

### NFT Коллекции
```json
{
  "collections": [
    {
      "chain": "ethereum",
      "address": "0x...",
      "name": "Collection Name",
      "symbol": "CNFT",
      "type": "NFT",
      "totalSupply": "10000"
    }
  ],
  "next": {
    "offset": 50
  }
}
```

### Транзакции
```json
{
  "transactions": [
    {
      "chain": "ethereum",
      "hash": "0x...",
      "from": "0x...",
      "to": "0x...",
      "value": "1000000000000000000",
      "type": "INCOMING",
      "timestamp": 1641234567
    }
  ],
  "next": {
    "offset": 50
  }
}
```
