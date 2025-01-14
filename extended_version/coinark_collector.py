import os
import logging
import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional
from db import DB
import time

class CoinArkCollector:
    """
    Класс для сбора данных с CoinArk API
    """
    def __init__(self, api_key=None):
        """
        Инициализация коллектора данных
        
        Args:
            api_key (str): API ключ для доступа к CoinArk API
        """
        self.api_key = api_key or '84068f54707949bc8f86e2dd9dcee6ac'
        self.base_url = 'https://open-api.coinank.com/api'
        self.headers = {
            'apikey': self.api_key,
            'accept': 'application/json'
        }
        
        # Настройка логирования
        self.logger = logging.getLogger(__name__)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
            
        # Подключение к базе данных
        self.db = DB()
        self.logger.info("Database connection established")
        
        # Проверка уровня доступа API
        self._check_api_access()
            
    def _check_api_access(self):
        """Проверяет уровень доступа к API"""
        try:
            # Пробуем получить данные funding rate как индикатор доступного уровня
            response = self._make_request('fundingRate/hist', {'symbol': 'BTCUSDT', 'size': '1'})
            
            if not response or (isinstance(response, dict) and not response.get('success')):
                self.logger.warning("У вас базовый уровень доступа к API. Некоторые методы будут недоступны.")
                self.logger.warning("Недоступные методы: Funding Rate, Индикаторы, Market Buy/Sell Volume")
                self.logger.warning("Для доступа к этим методам необходим уровень VIP3 или выше.")
                self.has_vip_access = False
            else:
                self.has_vip_access = True
                
        except Exception as e:
            self.logger.error(f"Ошибка при проверке уровня доступа: {str(e)}")
            self.has_vip_access = False

    def _create_tables(self):
        """Создает необходимые таблицы в базе данных"""
        try:
            # Таблица для индикаторов
            query = """
            CREATE TABLE IF NOT EXISTS coinark_indicators (
                id SERIAL PRIMARY KEY,
                timestamp TIMESTAMP NOT NULL,
                indicator VARCHAR(50) NOT NULL,
                value FLOAT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(timestamp, indicator)
            );
            """
            self.db.execute_query(query)
            
            # Таблица для funding rate
            query = """
            CREATE TABLE IF NOT EXISTS funding_rate_data (
                id SERIAL PRIMARY KEY,
                timestamp TIMESTAMP NOT NULL,
                base_coin VARCHAR(10) NOT NULL,
                exchange VARCHAR(50) NOT NULL,
                rate FLOAT NOT NULL,
                change_24h FLOAT,
                turnover_24h FLOAT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(timestamp, base_coin, exchange)
            );
            """
            self.db.execute_query(query)
            
            # Таблица для ликвидаций
            query = """
            CREATE TABLE IF NOT EXISTS liquidations_data (
                id SERIAL PRIMARY KEY,
                timestamp TIMESTAMP NOT NULL,
                base_coin VARCHAR(10) NOT NULL,
                side VARCHAR(10) NOT NULL,
                price FLOAT NOT NULL,
                quantity FLOAT NOT NULL,
                liquidation_value FLOAT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(timestamp, base_coin, side, price, quantity)
            );
            """
            self.db.execute_query(query)
            
            # Таблица для открытого интереса
            query = """
            CREATE TABLE IF NOT EXISTS open_interest_data (
                id SERIAL PRIMARY KEY,
                timestamp TIMESTAMP NOT NULL,
                base_coin VARCHAR(10) NOT NULL,
                exchange VARCHAR(50) NOT NULL,
                open_interest FLOAT NOT NULL,
                open_interest_value FLOAT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(timestamp, base_coin, exchange)
            );
            """
            self.db.execute_query(query)
            
            # Таблица для соотношения длинных и коротких позиций
            query = """
            CREATE TABLE IF NOT EXISTS long_short_ratio_data (
                id SERIAL PRIMARY KEY,
                timestamp TIMESTAMP NOT NULL,
                base_coin VARCHAR(10) NOT NULL,
                exchange VARCHAR(50) NOT NULL,
                long_short_ratio FLOAT NOT NULL,
                long_account FLOAT NOT NULL,
                short_account FLOAT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(timestamp, base_coin, exchange)
            );
            """
            self.db.execute_query(query)

            # Таблица для книги ордеров
            query = """
            CREATE TABLE IF NOT EXISTS coinark_orderbook (
                id SERIAL PRIMARY KEY,
                timestamp TIMESTAMP NOT NULL,
                symbol VARCHAR(20) NOT NULL,
                exchange VARCHAR(50) NOT NULL,
                product_type VARCHAR(10) NOT NULL,
                rate VARCHAR(10) NOT NULL,
                bid_volume FLOAT NOT NULL,
                bid_count INTEGER NOT NULL,
                ask_volume FLOAT NOT NULL,
                ask_count INTEGER NOT NULL,
                volume_imbalance FLOAT NOT NULL,
                count_imbalance INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(timestamp, symbol, exchange, product_type, rate)
            );
            """
            self.db.execute_query(query)
            
            # Таблица для исторических данных
            query = """
            CREATE TABLE IF NOT EXISTS coinark_historical (
                id SERIAL PRIMARY KEY,
                timestamp TIMESTAMP NOT NULL,
                symbol VARCHAR(20) NOT NULL,
                exchange VARCHAR(50) NOT NULL,
                open_price FLOAT NOT NULL,
                high_price FLOAT NOT NULL,
                low_price FLOAT NOT NULL,
                close_price FLOAT NOT NULL,
                volume FLOAT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(timestamp, symbol, exchange)
            );
            """
            self.db.execute_query(query)
            
            self.logger.info("All tables created successfully")
            
        except Exception as e:
            self.logger.error(f"Error creating tables: {str(e)}")
            raise

    def _make_request(self, endpoint, params=None):
        """Выполняет запрос к API CoinArk"""
        url = f"{self.base_url}/{endpoint}"
        headers = {
            'apikey': self.api_key,
            'accept': 'application/json'
        }
        
        self.logger.info(f"Making request to {url}")
        self.logger.info(f"Headers: {headers}")
        self.logger.info(f"Params: {params}")
        
        try:
            response = requests.get(url, params=params, headers=headers)
            self.logger.info(f"Response status code: {response.status_code}")
            self.logger.info(f"Response content: {response.text[:200]}")  # Логируем только первые 200 символов
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    if isinstance(data, dict) and data.get('success'):
                        return data.get('data')
                    elif isinstance(data, list):
                        return data  # Некоторые эндпоинты возвращают список напрямую
                    else:
                        self.logger.error(f"API returned unexpected format: {data}")
                        return None
                except ValueError as e:
                    self.logger.error(f"Failed to parse JSON response: {str(e)}")
                    return None
            else:
                self.logger.error(f"API request failed with status code {response.status_code}")
                return None
                
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Request failed: {str(e)}")
            return None

    def get_open_interest(self, base_coin='BTC'):
        """
        Получает данные об открытом интересе по всем биржам

        Args:
            base_coin (str): Базовая валюта (например, 'BTC')
        """
        endpoint = '/api/openInterest/all'
        params = {'baseCoin': base_coin}
        
        self.logger.info(f"Getting open interest data for {base_coin}")
        data = self._make_request(endpoint, params)
        
        if data:
            # Преобразуем данные в DataFrame
            df = pd.DataFrame(data)
            
            # Текущее время для всех записей
            current_time = datetime.now()
            
            # Сохраняем данные в базу
            for _, row in df.iterrows():
                query = """
                INSERT INTO open_interest_data 
                (timestamp, base_coin, exchange, open_interest, open_interest_value)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (timestamp, base_coin, exchange) DO NOTHING;
                """
                
                self.db.execute_query(query, (
                    current_time,
                    base_coin,
                    row['exchangeName'],
                    row['coinCount'],
                    row['coinValue']
                ))
            
            return df
        
        return None

    def get_orderbook_by_symbol(self, symbol='BTCUSDT', exchange='Binance', rate='0.01', 
                              product_type='SWAP', interval='1h', end_time=None, size=500):
        """
        Получает разницу бид-аск ордербука для торговой пары по уровню времени и диапазону.
        
        API Endpoint: https://docs.coinank.com/docs/api/version-1.html#/OrderBook/get_api_orderBook_v2_bySymbol
        
        Args:
            symbol (str): Торговая пара (например, 'BTCUSDT')
            exchange (str): Биржа
            rate (str): Диапазон разницы (0.0025, 0.005, 0.0075, 0.01, 0.03, 0.05, 0.1)
            product_type (str): Тип продукта ('SWAP' или 'SPOT')
            interval (str): Интервал времени (1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 8h, 1d)
            end_time (int): Конечное время в миллисекундах
            size (int): Размер выборки (макс. 500)
            
        Returns:
            pandas.DataFrame: DataFrame с данными или None в случае ошибки
        """
        endpoint = 'orderBook/v2/bySymbol'
        params = {
            'symbol': symbol,
            'exchange': exchange,
            'rate': rate,
            'productType': product_type,
            'interval': interval,
            'size': str(min(size, 500))
        }
        
        if end_time:
            params['endTime'] = str(end_time)
            
        self.logger.info(f"Getting orderbook data for {symbol} on {exchange}")
        data = self._make_request(endpoint, params)
        
        if data:
            # Создаем таблицу, если она не существует
            query = """
            CREATE TABLE IF NOT EXISTS orderbook_by_symbol (
                id SERIAL PRIMARY KEY,
                timestamp TIMESTAMP NOT NULL,
                symbol VARCHAR(20) NOT NULL,
                exchange VARCHAR(50) NOT NULL,
                rate FLOAT NOT NULL,
                product_type VARCHAR(10) NOT NULL,
                bid_volume FLOAT NOT NULL,
                bid_count FLOAT NOT NULL,
                ask_volume FLOAT NOT NULL,
                ask_count FLOAT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(timestamp, symbol, exchange, rate, product_type)
            );
            """
            self.db.execute_query(query)
            
            # Преобразуем данные в DataFrame
            df = pd.DataFrame(data, columns=['timestamp', 'bid_volume', 'bid_count', 'ask_volume', 'ask_count'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df['symbol'] = symbol
            df['exchange'] = exchange
            df['rate'] = float(rate)
            df['product_type'] = product_type
            
            # Сохраняем данные в базу
            query = """
            INSERT INTO orderbook_by_symbol 
            (timestamp, symbol, exchange, rate, product_type, bid_volume, bid_count, ask_volume, ask_count)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (timestamp, symbol, exchange, rate, product_type) DO NOTHING;
            """
            
            for _, row in df.iterrows():
                self.db.execute_query(query, (
                    row['timestamp'],
                    row['symbol'],
                    row['exchange'],
                    row['rate'],
                    row['product_type'],
                    row['bid_volume'],
                    row['bid_count'],
                    row['ask_volume'],
                    row['ask_count']
                ))
            
            self.logger.info(f"Saved orderbook by symbol data: {len(df)} records")
            return df
            
        return None

    def get_orderbook_by_exchange(self, base_coin='BTC', product_type='SWAP', interval='1h',
                                end_time=None, size=500, exchanges='Binance', rate_type='0.01'):
        """
        Получает разницу бид-аск ордербука биржи по уровню времени и диапазону.
        
        API Endpoint: https://docs.coinank.com/docs/api/version-1.html#/OrderBook/get_api_orderBook_v2_byExchange
        
        Curl Example:
        ```
        curl -X 'GET' \
          'https://open-api.coinank.com/api/orderBook/v2/byExchange?baseCoin=BTC&productType=SWAP&interval=1h&size=10&exchanges=Binance&endTime=1725965847353&type=0.01' \
          -H 'accept: application/json' \
          -H 'apikey: YOUR_API_KEY'
        ```
        
        Response Format:
        {
            "data": [
                {
                    "timestamp": 1725930000000,
                    "bidVolume": 123.45,
                    "bidCount": 1,
                    "askVolume": 678.9,
                    "askCount": 2
                }
            ]
        }
        
        Args:
            base_coin (str): Базовая монета (например, 'BTC')
            product_type (str): Тип продукта ('SWAP' или 'SPOT')
            interval (str): Интервал времени (1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 8h, 1d)
            end_time (int): Конечное время в миллисекундах
            size (int): Размер выборки (макс. 500)
            exchanges (str): Список бирж через запятую
                           SWAP: Binance,Bybit,OKX,Huobi,Bitfinex
                           SPOT: Binance,Bybit,OKX,Bitfinex,Kraken,Coinbase
            rate_type (str): Тип диапазона (0.0025, 0.005, 0.0075, 0.01, 0.03, 0.05, 0.1)
            
        Returns:
            pandas.DataFrame: DataFrame с данными или None в случае ошибки
        """
        endpoint = 'orderBook/v2/byExchange'
        params = {
            'baseCoin': base_coin,
            'productType': product_type,
            'interval': interval,
            'size': str(min(size, 500)),
            'exchanges': exchanges,
            'type': rate_type
        }
        
        if end_time:
            params['endTime'] = str(end_time)
            
        self.logger.info(f"Getting orderbook data for {base_coin} on exchanges: {exchanges}")
        data = self._make_request(endpoint, params)
        
        if data:
            # Создаем таблицу, если она не существует
            query = """
            CREATE TABLE IF NOT EXISTS orderbook_by_exchange (
                id SERIAL PRIMARY KEY,
                timestamp TIMESTAMP NOT NULL,
                base_coin VARCHAR(10) NOT NULL,
                exchanges VARCHAR(255) NOT NULL,
                rate_type FLOAT NOT NULL,
                product_type VARCHAR(10) NOT NULL,
                bid_volume FLOAT NOT NULL,
                bid_count FLOAT NOT NULL,
                ask_volume FLOAT NOT NULL,
                ask_count FLOAT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(timestamp, base_coin, exchanges, rate_type, product_type)
            );
            """
            self.db.execute_query(query)
            
            # Преобразуем данные в DataFrame
            df = pd.DataFrame(data, columns=['timestamp', 'bid_volume', 'bid_count', 'ask_volume', 'ask_count'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df['base_coin'] = base_coin
            df['exchanges'] = exchanges
            df['rate_type'] = float(rate_type)
            df['product_type'] = product_type
            
            # Сохраняем данные в базу
            query = """
            INSERT INTO orderbook_by_exchange 
            (timestamp, base_coin, exchanges, rate_type, product_type, bid_volume, bid_count, ask_volume, ask_count)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (timestamp, base_coin, exchanges, rate_type, product_type) DO NOTHING;
            """
            
            for _, row in df.iterrows():
                self.db.execute_query(query, (
                    row['timestamp'],
                    row['base_coin'],
                    row['exchanges'],
                    row['rate_type'],
                    row['product_type'],
                    row['bid_volume'],
                    row['bid_count'],
                    row['ask_volume'],
                    row['ask_count']
                ))
            
            self.logger.info(f"Saved orderbook by exchange data: {len(df)} records")
            return df
            
        return None

    def get_kline_data(self, symbol='BTCUSDT', exchange='Binance', interval='1h', 
                     start_time=None, end_time=None, size=500):
        """
        DEPRECATED: Этот метод в настоящее время не работает из-за ошибки API
        Получает исторические данные о ценах

        Args:
            symbol (str): Торговая пара (например, 'BTCUSDT')
            exchange (str): Биржа
            interval (str): Интервал ('1m', '3m', '5m', '15m', '30m', '1h', '2h', '4h', '6h', '8h', '1d')
            start_time (int): Начальное время в миллисекундах
            end_time (int): Конечное время в миллисекундах
            size (int): Количество записей (максимум 500)
        """
        self.logger.warning("This method is currently deprecated due to API issues")
        endpoint = '/kline'
        
        if end_time is None:
            end_time = int(datetime.now().timestamp() * 1000)
            
        params = {
            'symbol': symbol,
            'exchange': exchange,
            'interval': interval,
            'endTime': end_time,
            'size': min(size, 500)
        }
        
        if start_time is not None:
            params['startTime'] = start_time
            
        data = self._make_request(endpoint, params)
        if data:
            df = pd.DataFrame(data)
            return df
        return None

    def get_funding_rate(self, symbol='BTCUSDT', exchange='Binance', margin_type='USDT'):
        """
        DEPRECATED: Этот метод в настоящее время не работает из-за ошибки API
        Получает данные о ставках финансирования

        Args:
            symbol (str): Торговая пара (например, 'BTCUSDT')
            exchange (str): Биржа
            margin_type (str): Тип маржи (USDT или COIN)
        """
        self.logger.warning("This method is currently deprecated due to API issues")
        endpoint = '/fundingRate'
        
        params = {
            'symbol': symbol,
            'exchange': exchange,
            'marginType': margin_type
        }
        
        data = self._make_request(endpoint, params)
        if data:
            df = pd.DataFrame([data])
            return df
        return None

    def get_liquidation_data(self, symbol='BTCUSDT', exchange='Binance', end_time=None, size=500):
        """
        Получает данные о ликвидациях
        
        API Endpoint: https://docs.coinank.com/docs/api/version-1.html#/Liquidation/get_api_liquidation_data
        
        Curl Example:
        ```
        curl -X 'GET' \
          'https://open-api.coinank.com/api/liquidation/data?symbol=BTCUSDT&exchange=Binance&endTime=1725965847353&size=10' \
          -H 'accept: application/json' \
          -H 'apikey: YOUR_API_KEY'
        ```
        
        Response Format:
        {
            "id": "66df9a1b0b45b023e83ee37d",
            "symbol": "BTCUSDT",
            "exchange": "Binance",
            "side": "long",
            "price": 45000.23,
            "quantity": 1.5,
            "liquidationTime": 1725930000000
        }
        
        Args:
            symbol (str): Торговая пара (например, 'BTCUSDT')
            exchange (str): Биржа (Binance, OKX, Huobi)
            end_time (int): Конечное время в миллисекундах
            size (int): Размер выборки (макс. 500)
            
        Returns:
            pandas.DataFrame: DataFrame с данными или None в случае ошибки
            Структура данных:
            - timestamp: Время ликвидации
            - symbol: Торговая пара
            - exchange: Биржа
            - side: Сторона (long/short)
            - price: Цена ликвидации
            - quantity: Объем ликвидации
        """
        if end_time is None:
            end_time = int(datetime.now().timestamp() * 1000)
            
        params = {
            'symbol': symbol,
            'exchange': exchange,
            'endTime': str(end_time),
            'size': str(min(size, 500))
        }
        
        self.logger.info(f"Getting liquidation data for {symbol} on {exchange}")
        data = self._make_request('liquidation/data', params)
        
        if data:
            # Создаем таблицу, если она не существует
            query = """
            CREATE TABLE IF NOT EXISTS liquidation_data (
                id SERIAL PRIMARY KEY,
                timestamp TIMESTAMP NOT NULL,
                symbol VARCHAR(20) NOT NULL,
                exchange VARCHAR(50) NOT NULL,
                side VARCHAR(10) NOT NULL,
                price FLOAT NOT NULL,
                quantity FLOAT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(timestamp, symbol, exchange, side, price, quantity)
            );
            """
            self.db.execute_query(query)
            
            # Преобразуем данные
            rows = []
            for item in data:
                # Пропускаем записи с отсутствующими данными
                if not all(k in item for k in ['liquidationTime', 'symbol', 'exchange', 'side', 'price', 'quantity']):
                    continue
                    
                try:
                    ts = datetime.fromtimestamp(item['liquidationTime'] / 1000)
                    row = {
                        'timestamp': ts,
                        'symbol': item['symbol'],
                        'exchange': item['exchange'],
                        'side': item['side'].lower(),
                        'price': float(item['price']),
                        'quantity': float(item['quantity'])
                    }
                    rows.append(row)
                except (ValueError, TypeError) as e:
                    self.logger.warning(f"Ошибка при обработке записи: {e}")
                    continue
            
            if not rows:
                self.logger.warning("Нет данных для сохранения")
                return None
                
            # Создаем DataFrame
            df = pd.DataFrame(rows)
            
            # Сохраняем данные в базу
            query = """
            INSERT INTO liquidation_data 
            (timestamp, symbol, exchange, side, price, quantity)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (timestamp, symbol, exchange, side, price, quantity) DO NOTHING;
            """
            
            for _, row in df.iterrows():
                self.db.execute_query(query, (
                    row['timestamp'],
                    row['symbol'],
                    row['exchange'],
                    row['side'],
                    row['price'],
                    row['quantity']
                ))
            
            self.logger.info(f"Saved liquidation data for {len(df)} records")
            return df
            
        return None

    def get_longshort_position(self, symbol='BTCUSDT', exchange='Binance', interval='1h', 
                           ls_type='longShortPosition', size=500, end_time=None):
        """
        DEPRECATED: Этот метод в настоящее время не работает из-за ошибки API
        Получает данные о позициях long/short с биржи

        Args:
            symbol (str): Торговая пара (например, 'BTCUSDT')
            exchange (str): Биржа (Binance, Bybit, OKX)
            interval (str): Интервал (5m, 15m, 30m, 1h, 4h, 1d)
            ls_type (str): Тип данных (longShortPosition, longShortAccount, longShortPerson)
            size (int): Размер выборки (максимум 500)
            end_time (int): Временная метка окончания (в миллисекундах)
        """
        self.logger.warning("This method is currently deprecated due to API issues")
        endpoint = 'longShort/v2/history'
        
        if end_time is None:
            end_time = int(datetime.now().timestamp() * 1000)
            
        params = {
            'symbol': symbol,
            'exchange': exchange,
            'interval': interval,
            'type': ls_type,
            'endTime': end_time,
            'size': min(size, 500)
        }
        
        data = self._make_request(endpoint, params)
        if data:
            df = pd.DataFrame(data)
            
            # Создаем таблицу, если она не существует
            query = """
            CREATE TABLE IF NOT EXISTS longshort_data (
                id SERIAL PRIMARY KEY,
                timestamp TIMESTAMP NOT NULL,
                symbol VARCHAR(20) NOT NULL,
                exchange VARCHAR(50) NOT NULL,
                interval VARCHAR(10) NOT NULL,
                ratio_open FLOAT NOT NULL,
                ratio_high FLOAT NOT NULL,
                ratio_low FLOAT NOT NULL,
                ratio_close FLOAT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(timestamp, symbol, exchange, interval)
            );
            """
            self.db.execute_query(query)
            
            # Сохраняем данные в базу
            query = """
            INSERT INTO longshort_data 
            (timestamp, symbol, exchange, interval, ratio_open, ratio_high, ratio_low, ratio_close)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (timestamp, symbol, exchange, interval) DO NOTHING;
            """
            
            for _, row in df.iterrows():
                self.db.execute_query(query, (
                    row['timestamp'], symbol, exchange, interval,
                    row['ratio_open'], row['ratio_high'],
                    row['ratio_low'], row['ratio_close']
                ))
            
            return df
            
        return None

    def get_historical_funding_rate(self, symbol='BTCUSDT', end_time=None, size=500):
        """
        Получает исторические данные о ставках финансирования
        
        API Endpoint: https://docs.coinank.com/docs/api/version-1.html#/FundingRate/get_api_fundingRate_hist
        
        Args:
            symbol (str): Торговая пара (например, 'BTCUSDT')
            end_time (int): Конечное время в миллисекундах
            size (int): Размер выборки (макс. 500)
            
        Returns:
            pandas.DataFrame: DataFrame с данными или None в случае ошибки
            Структура данных:
            - timestamp: Временная метка
            - symbol: Торговая пара
            - exchange: Биржа
            - funding_rate: Ставка финансирования
            - realized_rate: Реализованная ставка (если доступно)
        """
        if self.has_vip_access is False:
            self.logger.warning("Этот метод требует VIP3 или выше")
            return None
        
        endpoint = 'fundingRate/hist'
        params = {
            'symbol': symbol,
            'size': str(min(size, 500))
        }
        
        if end_time:
            params['endTime'] = str(end_time)
            
        self.logger.info(f"Getting funding rate data for {symbol}")
        data = self._make_request(endpoint, params)
        
        if data:
            # Создаем таблицу, если она не существует
            query = """
            CREATE TABLE IF NOT EXISTS funding_rate_history (
                id SERIAL PRIMARY KEY,
                timestamp TIMESTAMP NOT NULL,
                symbol VARCHAR(20) NOT NULL,
                exchange VARCHAR(50) NOT NULL,
                funding_rate FLOAT NOT NULL,
                realized_rate FLOAT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(timestamp, symbol, exchange)
            );
            """
            self.db.execute_query(query)
            
            # Преобразуем данные в плоский формат
            rows = []
            for item in data:
                ts = datetime.fromtimestamp(item['ts'] / 1000)  # конвертируем из миллисекунд
                details = item['details']
                
                for exchange, rates in details.items():
                    row = {
                        'timestamp': ts,
                        'symbol': symbol,
                        'exchange': exchange,
                        'funding_rate': rates.get('fundingRate'),
                        'realized_rate': rates.get('realizedRate')
                    }
                    rows.append(row)
            
            if rows:
                # Создаем DataFrame
                df = pd.DataFrame(rows)
                
                # Сохраняем данные в базу
                query = """
                INSERT INTO funding_rate_history 
                (timestamp, symbol, exchange, funding_rate, realized_rate)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (timestamp, symbol, exchange) DO NOTHING;
                """
                
                for _, row in df.iterrows():
                    self.db.execute_query(query, (
                        row['timestamp'],
                        row['symbol'],
                        row['exchange'],
                        row['funding_rate'],
                        row['realized_rate']
                    ))
                
                self.logger.info(f"Saved funding rate data: {len(df)} records")
                return df
            else:
                self.logger.info("No funding rate data available")
                
        return None

    def get_longshort_ratio(self, base_coin='BTC', interval='5m'):
        """
        Получает соотношение длинных/коротких позиций в реальном времени для всех бирж

        Args:
            base_coin (str): Базовая монета (например, 'BTC')
            interval (str): Интервал (например, '5m')

        Returns:
            pandas.DataFrame: DataFrame с данными или None в случае ошибки
            Колонки:
            - baseCoin: Базовая монета
            - exchangeName: Название биржи
            - sellTradeTurnover: Объем продаж
            - buyTradeTurnover: Объем покупок
            - longRatio: Доля длинных позиций
            - shortRatio: Доля коротких позиций
        """
        endpoint = 'longshort/realtimeAll'
        params = {
            'baseCoin': base_coin,
            'interval': interval
        }
        
        self.logger.info(f"Getting long/short ratio data for {base_coin}")
        data = self._make_request(endpoint, params)
        
        if data:
            # Создаем таблицу, если она не существует
            query = """
            CREATE TABLE IF NOT EXISTS longshort_realtime_data (
                id SERIAL PRIMARY KEY,
                timestamp TIMESTAMP NOT NULL,
                base_coin VARCHAR(10) NOT NULL,
                exchange VARCHAR(50) NOT NULL,
                sell_turnover FLOAT NOT NULL,
                buy_turnover FLOAT NOT NULL,
                long_ratio FLOAT NOT NULL,
                short_ratio FLOAT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(timestamp, base_coin, exchange)
            );
            """
            self.db.execute_query(query)
            
            # Получаем текущее время для всех записей
            current_time = datetime.now()
            
            # Сохраняем данные в базу
            query = """
            INSERT INTO longshort_realtime_data 
            (timestamp, base_coin, exchange, sell_turnover, buy_turnover, long_ratio, short_ratio)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (timestamp, base_coin, exchange) DO NOTHING;
            """
            
            df = pd.DataFrame(data)
            for _, row in df.iterrows():
                self.db.execute_query(query, (
                    current_time,
                    row['baseCoin'],
                    row['exchangeName'],
                    row['sellTradeTurnover'],
                    row['buyTradeTurnover'],
                    row['longRatio'],
                    row['shortRatio']
                ))
            
            self.logger.info(f"Saved long/short ratio data for {len(df)} exchanges")
            return df
            
        return None

    def get_open_interest_kline(self, symbol='BTCUSDT', exchange='Binance', interval='1h', end_time=None, size=500):
        """
        Получает данные K-line об открытом интересе для торговой пары
        
        API Endpoint: https://docs.coinank.com/docs/api/version-1.html#/Open%20Interest/get_api_openInterest_kline
        
        Curl Example:
        ```
        curl -X 'GET' \
          'https://open-api.coinank.com/api/openInterest/kline?exchange=Binance&symbol=BTCUSDT&interval=1h&endTime=1725983462353&size=10' \
          -H 'accept: application/json' \
          -H 'apikey: YOUR_API_KEY'
        ```
        
        Response Format:
        {
            "begin": 1725948000000,
            "open": 86935,
            "close": 86918,
            "low": 86854,
            "high": 86942
        }
        
        Args:
            symbol (str): Торговая пара (например, 'BTCUSDT')
            exchange (str): Биржа (Binance, OKX, Bybit, Bitget, Huobi, Gate)
            interval (str): Интервал (1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 8h, 12h, 1d)
            end_time (int): Конечное время в миллисекундах
            size (int): Размер выборки (макс. 500)
            
        Returns:
            pandas.DataFrame: DataFrame с данными или None в случае ошибки
            Структура данных:
            - timestamp: Временная метка
            - open: Открытие
            - high: Максимум
            - low: Минимум
            - close: Закрытие
        """
        endpoint = 'openInterest/kline'
        
        if end_time is None:
            end_time = int(datetime.now().timestamp() * 1000)
            
        params = {
            'symbol': symbol,
            'exchange': exchange,
            'interval': interval,
            'endTime': str(end_time),
            'size': str(min(size, 500))
        }
            
        self.logger.info(f"Getting open interest kline data for {symbol} on {exchange}")
        data = self._make_request(endpoint, params)
        
        if data:
            # Создаем таблицу, если она не существует
            query = """
            CREATE TABLE IF NOT EXISTS open_interest_kline (
                id SERIAL PRIMARY KEY,
                timestamp TIMESTAMP NOT NULL,
                symbol VARCHAR(20) NOT NULL,
                exchange VARCHAR(50) NOT NULL,
                interval VARCHAR(10) NOT NULL,
                open_value FLOAT NOT NULL,
                high_value FLOAT NOT NULL,
                low_value FLOAT NOT NULL,
                close_value FLOAT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(timestamp, symbol, exchange, interval)
            );
            """
            self.db.execute_query(query)
            
            # Преобразуем данные
            rows = []
            for item in data:
                ts = datetime.fromtimestamp(item['begin'] / 1000)  # конвертируем из миллисекунд
                row = {
                    'timestamp': ts,
                    'symbol': symbol,
                    'exchange': exchange,
                    'interval': interval,
                    'open_value': float(item['open']),
                    'high_value': float(item['high']),
                    'low_value': float(item['low']),
                    'close_value': float(item['close'])
                }
                rows.append(row)
            
            # Создаем DataFrame
            df = pd.DataFrame(rows)
            
            # Сохраняем данные в базу
            query = """
            INSERT INTO open_interest_kline 
            (timestamp, symbol, exchange, interval, open_value, high_value, low_value, close_value)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (timestamp, symbol, exchange, interval) DO NOTHING;
            """
            
            for _, row in df.iterrows():
                self.db.execute_query(query, (
                    row['timestamp'],
                    row['symbol'],
                    row['exchange'],
                    row['interval'],
                    row['open_value'],
                    row['high_value'],
                    row['low_value'],
                    row['close_value']
                ))
            
            self.logger.info(f"Saved open interest kline data for {len(df)} records")
            return df
            
        return None

    def get_longshort_kline(self, symbol='BTCUSDT', exchange='Binance', interval='1h', 
                           ls_type='longShortPerson', end_time=None, size=500):
        """
        Получает исторические данные о соотношении длинных и коротких позиций в формате K-line
        
        API Endpoint: https://docs.coinank.com/docs/api/version-1.html#/Longshort/get_api_longshort_kline
        
        Curl Example:
        ```
        curl -X 'GET' \
          'https://open-api.coinank.com/api/longshort/kline?exchange=Binance&symbol=BTCUSDT&endTime=1725965847353&interval=1h&size=10&type=longShortPerson' \
          -H 'accept: application/json' \
          -H 'apikey: YOUR_API_KEY'
        ```
        
        Response Format:
        {
            "id": "66df9a1b0b45b023e83ee37d",
            "begin": 1725930000000,
            "open": 1.6144,
            "close": 1.5873,
            "low": 1.5873,
            "high": 1.6357
        }

        Args:
            symbol (str): Торговая пара (например, 'BTCUSDT')
            exchange (str): Биржа (Binance, OKX, Huobi)
            interval (str): Интервал (5m, 15m, 30m, 1h, 2h, 4h, 6h, 8h, 1d)
            ls_type (str): Тип данных:
                - longShortPerson: общее соотношение long/short
                - longShortPosition: соотношение по позициям
                - longShortAccount: соотношение по аккаунтам
            end_time (int): Конечное время в миллисекундах
            size (int): Размер выборки (макс. 500)
            
        Returns:
            pandas.DataFrame: DataFrame с данными или None в случае ошибки
            Структура данных:
            - timestamp: Временная метка
            - symbol: Торговая пара
            - exchange: Биржа
            - open_ratio: Открытие
            - high_ratio: Максимум
            - low_ratio: Минимум
            - close_ratio: Закрытие
            - ratio_type: Тип соотношения
        """
        endpoint = 'longshort/kline'
        
        if end_time is None:
            end_time = int(datetime.now().timestamp() * 1000)
            
        params = {
            'symbol': symbol,
            'exchange': exchange,
            'interval': interval,
            'type': ls_type,
            'endTime': str(end_time),
            'size': str(min(size, 500))
        }
        
        self.logger.info(f"Getting long/short kline data for {symbol} on {exchange}")
        data = self._make_request(endpoint, params)
        
        if data:
            # Создаем таблицу, если она не существует
            query = """
            CREATE TABLE IF NOT EXISTS longshort_kline (
                id SERIAL PRIMARY KEY,
                timestamp TIMESTAMP NOT NULL,
                symbol VARCHAR(20) NOT NULL,
                exchange VARCHAR(50) NOT NULL,
                interval VARCHAR(10) NOT NULL,
                ratio_type VARCHAR(20) NOT NULL,
                open_ratio FLOAT NOT NULL,
                high_ratio FLOAT NOT NULL,
                low_ratio FLOAT NOT NULL,
                close_ratio FLOAT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(timestamp, symbol, exchange, interval, ratio_type)
            );
            """
            self.db.execute_query(query)
            
            # Преобразуем данные
            rows = []
            for item in data:
                ts = datetime.fromtimestamp(item['begin'] / 1000)  # конвертируем из миллисекунд
                row = {
                    'timestamp': ts,
                    'symbol': symbol,
                    'exchange': exchange,
                    'interval': interval,
                    'ratio_type': ls_type,
                    'open_ratio': float(item['open']),
                    'high_ratio': float(item['high']),
                    'low_ratio': float(item['low']),
                    'close_ratio': float(item['close'])
                }
                rows.append(row)
            
            # Создаем DataFrame
            df = pd.DataFrame(rows)
            
            # Сохраняем данные в базу
            query = """
            INSERT INTO longshort_kline 
            (timestamp, symbol, exchange, interval, ratio_type, open_ratio, high_ratio, low_ratio, close_ratio)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (timestamp, symbol, exchange, interval, ratio_type) DO NOTHING;
            """
            
            for _, row in df.iterrows():
                self.db.execute_query(query, (
                    row['timestamp'],
                    row['symbol'],
                    row['exchange'],
                    row['interval'],
                    row['ratio_type'],
                    row['open_ratio'],
                    row['high_ratio'],
                    row['low_ratio'],
                    row['close_ratio']
                ))
            
            self.logger.info(f"Saved long/short kline data for {len(df)} records")
            return df
            
        return None

    def get_accumulated_funding_rate(self, type='day'):
        """
        DEPRECATED: Этот метод в настоящее время не работает из-за ошибки API
        Получает накопленную ставку финансирования
        type: day, week, month, year
        """
        self.logger.warning("This method is currently deprecated due to API issues")
        endpoint = 'fundingRate/accumulated'
        params = {'type': type}
        
        data = self._make_request(endpoint, params)
        if data:
            df = pd.DataFrame(data)
            filename = os.path.join(self.data_dir, 'funding_rates', 
                                  f'accumulated_funding_rate_{type}_{datetime.now().strftime("%Y%m%d")}.csv')
            df.to_csv(filename, index=False)
            self.logger.info(f"Saved accumulated funding rate data to {filename}")
            return df
        return None

    def get_indicator_data(self, indicator_type, end_time=None, size=500):
        """
        Получает данные индикатора
        
        API Endpoint: https://docs.coinank.com/docs/api/version-1.html#/Indicator/get_api_indicator_index_charts
        
        Curl Example:
        ```
        curl -X 'GET' \
          'https://open-api.coinank.com/api/indicator/index/charts?type=bitcoin-rainbow-v2&endTime=1725965847353' \
          -H 'accept: application/json' \
          -H 'apikey: YOUR_API_KEY'
        ```
        
        Response Format:
        {
            "timeList": [1725930000000, ...],
            "btcPrice": [45000.23, ...],
            "value1": [42000.1, ...],
            "value2": [43500.5, ...],
            ...
        }
        
        Args:
            indicator_type (str): Тип индикатора:
                - bitcoin-rainbow-v2: Bitcoin Rainbow Chart V2
                - /charts/1-year-hodl-wave/: 1 Year+ HODL Wave
                - /charts/hodl-waves/: HODL Waves
                - /charts/mvrv-zscore/: MVRV Z-Score
                - /charts/relative-unrealized-prof/: Relative Unrealized Profit/Loss
                - /charts/bitcoin-price-prediction/: Bitcoin Price Prediction
                - /charts/reserve-risk/: Reserve Risk
                - /charts/rhodl-ratio/: RHODL Ratio
                - /charts/whale-shadows/: Whale Shadows
            end_time (int): Конечное время в миллисекундах
            size (int): Размер выборки (макс. 500)
            
        Returns:
            pandas.DataFrame: DataFrame с данными или None в случае ошибки
            Структура данных:
            - timestamp: Временная метка
            - btc_price: Цена BTC
            - value_1 ... value_12: Значения индикатора
        """
        if self.has_vip_access is False:
            self.logger.warning("Этот метод требует VIP3 или выше")
            return None
        
        request_type = indicator_type
        if not indicator_type.startswith('/charts/') and indicator_type != 'bitcoin-rainbow-v2':
            request_type = f'/charts/{indicator_type}/'
            
        if end_time is None:
            end_time = int(datetime.now().timestamp() * 1000)
            
        params = {
            'type': request_type,
            'endTime': str(end_time),
            'size': str(min(size, 500))
        }
        
        self.logger.info(f"Getting indicator data for {indicator_type}")
        data = self._make_request('indicator/index/charts', params)
        
        if data:
            # Создаем таблицу, если она не существует
            query = """
            CREATE TABLE IF NOT EXISTS indicator_data (
                id SERIAL PRIMARY KEY,
                timestamp TIMESTAMP NOT NULL,
                indicator_type VARCHAR(50) NOT NULL,
                btc_price FLOAT NOT NULL,
                value_1 FLOAT,
                value_2 FLOAT,
                value_3 FLOAT,
                value_4 FLOAT,
                value_5 FLOAT,
                value_6 FLOAT,
                value_7 FLOAT,
                value_8 FLOAT,
                value_9 FLOAT,
                value_10 FLOAT,
                value_11 FLOAT,
                value_12 FLOAT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(timestamp, indicator_type)
            );
            """
            self.db.execute_query(query)
            
            # Преобразуем данные
            timestamps = [datetime.fromtimestamp(ts / 1000) for ts in data.get('timeList', [])]
            btc_prices = data.get('btcPrice', [])
            
            rows = []
            for i in range(len(timestamps)):
                btc_price = btc_prices[i] if i < len(btc_prices) else None
                if btc_price is None:
                    continue
                    
                row = {
                    'timestamp': timestamps[i],
                    'indicator_type': indicator_type,
                    'btc_price': float(btc_price)
                }
                
                # Добавляем все доступные значения
                for j in range(1, 13):
                    value_key = f'value{j}'
                    values = data.get(value_key, [])
                    value = values[i] if i < len(values) else None
                    row[f'value_{j}'] = float(value) if value is not None else None
                
                rows.append(row)
            
            # Создаем DataFrame
            df = pd.DataFrame(rows)
            
            # Сохраняем данные в базу
            value_placeholders = ', '.join([f'value_{i}' for i in range(1, 13)])
            query = f"""
            INSERT INTO indicator_data 
            (timestamp, indicator_type, btc_price, {value_placeholders})
            VALUES (%s, %s, %s, {', '.join(['%s'] * 12)})
            ON CONFLICT (timestamp, indicator_type) DO NOTHING;
            """
            
            for _, row in df.iterrows():
                values = [
                    row['timestamp'],
                    row['indicator_type'],
                    row['btc_price']
                ]
                values.extend([row.get(f'value_{i}') for i in range(1, 13)])
                self.db.execute_query(query, tuple(values))
            
            self.logger.info(f"Saved indicator data for {len(df)} records")
            return df
            
        return None

    def get_exchange_liquidations(self, base_coin=None):
        """
        Получает статистику ликвидаций по всем биржам
        
        API Endpoint: https://docs.coinank.com/docs/api/version-1.html#/Liquidation/get_api_liquidation_allExchange_intervals
        
        Curl Example:
        ```
        curl -X 'GET' \
          'https://open-api.coinank.com/api/liquidation/allExchange/intervals' \
          -H 'accept: application/json' \
          -H 'apikey: YOUR_API_KEY'
        ```
        
        Response Format:
        {
            "baseCoin": "",
            "totalTurnover": 12621932.51035611,
            "longTurnover": 3878700.78958684,
            "shortTurnover": 8743231.72076927,
            "percentage": 0,
            "longRatio": 0,
            "shortRatio": 0,
            "interval": "1h"
        }
        
        Args:
            base_coin (str, optional): Базовая монета (например, 'BTC')
            
        Returns:
            pandas.DataFrame: DataFrame с данными или None в случае ошибки
            Структура данных:
            - base_coin: Базовая монета
            - interval: Интервал
            - total_turnover: Общий объем ликвидаций
            - long_turnover: Объем ликвидаций длинных позиций
            - short_turnover: Объем ликвидаций коротких позиций
            - percentage: Процент
            - long_ratio: Соотношение длинных позиций
            - short_ratio: Соотношение коротких позиций
            
            Также включает топ ликвидаций:
            - top_symbol: Торговая пара
            - top_side: Сторона (long/short)
            - top_exchange: Биржа
            - top_turnover: Объем
            - top_base_coin: Базовая монета
            - top_timestamp: Время
        """
        params = {}
        if base_coin:
            params['baseCoin'] = base_coin
            
        self.logger.info(f"Getting exchange liquidation statistics{' for ' + base_coin if base_coin else ''}")
        data = self._make_request('liquidation/allExchange/intervals', params)
        
        if data:
            # Создаем таблицу для основных данных, если она не существует
            query = """
            CREATE TABLE IF NOT EXISTS exchange_liquidations (
                id SERIAL PRIMARY KEY,
                base_coin VARCHAR(20),
                interval VARCHAR(10) NOT NULL,
                total_turnover FLOAT NOT NULL,
                long_turnover FLOAT NOT NULL,
                short_turnover FLOAT NOT NULL,
                percentage FLOAT,
                long_ratio FLOAT,
                short_ratio FLOAT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(base_coin, interval)
            );
            """
            self.db.execute_query(query)
            
            # Создаем таблицу для топ ликвидаций
            query = """
            CREATE TABLE IF NOT EXISTS top_liquidations (
                id SERIAL PRIMARY KEY,
                symbol VARCHAR(20) NOT NULL,
                side VARCHAR(10) NOT NULL,
                exchange VARCHAR(50) NOT NULL,
                turnover FLOAT NOT NULL,
                base_coin VARCHAR(20),
                timestamp TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(timestamp, symbol, exchange, side)
            );
            """
            self.db.execute_query(query)
            
            # Преобразуем основные данные
            rows = []
            for item in data:
                row = {
                    'base_coin': item.get('baseCoin'),
                    'interval': item['interval'],
                    'total_turnover': float(item['totalTurnover']),
                    'long_turnover': float(item['longTurnover']),
                    'short_turnover': float(item['shortTurnover']),
                    'percentage': float(item['percentage']),
                    'long_ratio': float(item['longRatio']),
                    'short_ratio': float(item['shortRatio'])
                }
                rows.append(row)
            
            # Создаем DataFrame
            df = pd.DataFrame(rows)
            
            # Сохраняем основные данные
            query = """
            INSERT INTO exchange_liquidations 
            (base_coin, interval, total_turnover, long_turnover, short_turnover, percentage, long_ratio, short_ratio)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (base_coin, interval) DO UPDATE SET
                total_turnover = EXCLUDED.total_turnover,
                long_turnover = EXCLUDED.long_turnover,
                short_turnover = EXCLUDED.short_turnover,
                percentage = EXCLUDED.percentage,
                long_ratio = EXCLUDED.long_ratio,
                short_ratio = EXCLUDED.short_ratio;
            """
            
            for _, row in df.iterrows():
                self.db.execute_query(query, (
                    row['base_coin'],
                    row['interval'],
                    row['total_turnover'],
                    row['long_turnover'],
                    row['short_turnover'],
                    row['percentage'],
                    row['long_ratio'],
                    row['short_ratio']
                ))
            
            # Обрабатываем топ ликвидации
            if 'ext' in data and 'tops' in data['ext']:
                top_rows = []
                for top in data['ext']['tops']:
                    top_row = {
                        'symbol': top['symbol'],
                        'side': top['posSide'],
                        'exchange': top['exchangeName'],
                        'turnover': float(top['tradeTurnover']),
                        'base_coin': top['baseCoin'],
                        'timestamp': datetime.fromtimestamp(top['ts'] / 1000)
                    }
                    top_rows.append(top_row)
                
                # Создаем DataFrame для топ ликвидаций
                top_df = pd.DataFrame(top_rows)
                
                # Сохраняем топ ликвидации
                query = """
                INSERT INTO top_liquidations 
                (symbol, side, exchange, turnover, base_coin, timestamp)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (timestamp, symbol, exchange, side) DO UPDATE SET
                    turnover = EXCLUDED.turnover,
                    base_coin = EXCLUDED.base_coin;
                """
                
                for _, row in top_df.iterrows():
                    self.db.execute_query(query, (
                        row['symbol'],
                        row['side'],
                        row['exchange'],
                        row['turnover'],
                        row['base_coin'],
                        row['timestamp']
                    ))
                
                # Объединяем данные для возврата
                df['top_liquidations'] = [top_df.to_dict('records')] * len(df)
            
            self.logger.info(f"Saved exchange liquidation data: {len(df)} intervals and {len(data['ext']['tops']) if 'ext' in data and 'tops' in data['ext'] else 0} top liquidations")
            return df
            
        return None

    def get_aggregated_liquidations(self, base_coin='BTCUSDT', interval='1h', end_time=None, size=500):
        """
        Получает агрегированные данные о ликвидациях для монеты
        
        API Endpoint: https://docs.coinank.com/docs/api/version-1.html#/Liquidation/get_api_liquidation_aggregated_history
        
        Args:
            base_coin (str): Торговая пара (например, 'BTCUSDT')
            interval (str): Интервал (1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 8h, 12h, 1d)
            end_time (int): Конечное время в миллисекундах
            size (int): Размер выборки (макс. 500)
            
        Returns:
            pandas.DataFrame: DataFrame с данными или None в случае ошибки
            Структура данных:
            - timestamp: Временная метка
            - base_coin: Торговая пара
            - interval: Интервал
            - long_turnover: Объем ликвидаций длинных позиций
            - short_turnover: Объем ликвидаций коротких позиций
            - long_amount: Количество ликвидаций длинных позиций
            - short_amount: Количество ликвидаций коротких позиций
        """
        if end_time is None:
            end_time = int(datetime.now().timestamp() * 1000)
            
        params = {
            'baseCoin': base_coin,
            'interval': interval,
            'endTime': str(end_time),
            'size': str(min(size, 500))
        }
        
        self.logger.info(f"Getting aggregated liquidation data for {base_coin}")
        data = self._make_request('liquidation/aggregated-history', params)
        
        if data:
            # Создаем таблицу, если она не существует
            query = """
            CREATE TABLE IF NOT EXISTS aggregated_liquidations (
                id SERIAL PRIMARY KEY,
                timestamp TIMESTAMP NOT NULL,
                base_coin VARCHAR(20) NOT NULL,
                interval VARCHAR(10) NOT NULL,
                long_turnover FLOAT NOT NULL,
                short_turnover FLOAT NOT NULL,
                long_amount FLOAT NOT NULL,
                short_amount FLOAT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(timestamp, base_coin, interval)
            );
            """
            self.db.execute_query(query)
            
            # Преобразуем данные
            rows = []
            for item in data:
                if 'all' not in item or 'ts' not in item:
                    continue
                    
                try:
                    ts = datetime.fromtimestamp(item['ts'] / 1000)
                    all_data = item['all']
                    row = {
                        'timestamp': ts,
                        'base_coin': base_coin,
                        'interval': interval,
                        'long_turnover': float(all_data['longTurnover']),
                        'short_turnover': float(all_data['shortTurnover']),
                        'long_amount': float(all_data['longAmount']),
                        'short_amount': float(all_data['shortAmount'])
                    }
                    rows.append(row)
                except (ValueError, TypeError, KeyError) as e:
                    self.logger.warning(f"Ошибка при обработке записи: {e}")
                    continue
            
            if not rows:
                self.logger.warning("Нет данных для сохранения")
                return None
                
            # Создаем DataFrame
            df = pd.DataFrame(rows)
            
            # Сохраняем данные в базу
            query = """
            INSERT INTO aggregated_liquidations 
            (timestamp, base_coin, interval, long_turnover, short_turnover, long_amount, short_amount)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (timestamp, base_coin, interval) DO UPDATE SET
                long_turnover = EXCLUDED.long_turnover,
                short_turnover = EXCLUDED.short_turnover,
                long_amount = EXCLUDED.long_amount,
                short_amount = EXCLUDED.short_amount;
            """
            
            for _, row in df.iterrows():
                self.db.execute_query(query, (
                    row['timestamp'],
                    row['base_coin'],
                    row['interval'],
                    row['long_turnover'],
                    row['short_turnover'],
                    row['long_amount'],
                    row['short_amount']
                ))
            
            self.logger.info(f"Saved aggregated liquidation data: {len(df)} records")
            return df
            
        return None

    def get_pair_liquidations(self, symbol='BTCUSDT', exchange='Binance', interval='1h', end_time=None, size=500):
        """
        Получает данные о ликвидациях для конкретной торговой пары
        
        API Endpoint: https://docs.coinank.com/docs/api/version-1.html#/Liquidation/get_api_liquidation_history
        
        Curl Example:
        ```
        curl -X 'GET' \
          'https://open-api.coinank.com/api/liquidation/history?exchange=Binance&symbol=BTCUSDT&interval=1h&endTime=1725972522356&size=10' \
          -H 'accept: application/json' \
          -H 'apikey: YOUR_API_KEY'
        ```
        
        Response Format:
        {
            "symbol": "BTCUSDT",
            "exchangeName": "Binance",
            "ts": 1725937200000,
            "longTurnover": 123431.9085,
            "shortTurnover": 0,
            "shortAmount": 0,
            "longAmount": 0
        }

        Args:
            symbol (str): Торговая пара (например, 'BTCUSDT')
            exchange (str): Биржа (Binance, OKX, Bybit, Gate, Huobi, Bitfinex, Kraken, Deribit, Bitmex)
            interval (str): Интервал (1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 8h, 12h, 1d)
            end_time (int): Конечное время в миллисекундах
            size (int): Размер выборки (макс. 500)
            
        Returns:
            pandas.DataFrame: DataFrame с данными или None в случае ошибки
            Структура данных:
            - timestamp: Временная метка
            - symbol: Торговая пара
            - exchange: Биржа
            - interval: Интервал
            - long_turnover: Объем ликвидаций длинных позиций
            - short_turnover: Объем ликвидаций коротких позиций
            - long_amount: Количество ликвидаций длинных позиций
            - short_amount: Количество ликвидаций коротких позиций
        """
        if end_time is None:
            end_time = int(datetime.now().timestamp() * 1000)
            
        params = {
            'symbol': symbol,
            'exchange': exchange,
            'interval': interval,
            'endTime': str(end_time),
            'size': str(min(size, 500))
        }
        
        self.logger.info(f"Getting pair liquidation data for {symbol} on {exchange}")
        data = self._make_request('liquidation/history', params)
        
        if data:
            # Создаем таблицу, если она не существует
            query = """
            CREATE TABLE IF NOT EXISTS pair_liquidations (
                id SERIAL PRIMARY KEY,
                timestamp TIMESTAMP NOT NULL,
                symbol VARCHAR(20) NOT NULL,
                exchange VARCHAR(50) NOT NULL,
                interval VARCHAR(10) NOT NULL,
                long_turnover FLOAT NOT NULL,
                short_turnover FLOAT NOT NULL,
                long_amount FLOAT NOT NULL,
                short_amount FLOAT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(timestamp, symbol, exchange, interval)
            );
            """
            self.db.execute_query(query)
            
            # Преобразуем данные
            rows = []
            for item in data:
                try:
                    ts = datetime.fromtimestamp(item['ts'] / 1000)
                    row = {
                        'timestamp': ts,
                        'symbol': item.get('symbol', symbol),
                        'exchange': item.get('exchangeName', exchange),
                        'interval': interval,
                        'long_turnover': float(item.get('longTurnover', 0)),
                        'short_turnover': float(item.get('shortTurnover', 0)),
                        'long_amount': float(item.get('longAmount', 0)),
                        'short_amount': float(item.get('shortAmount', 0))
                    }
                    rows.append(row)
                except (ValueError, TypeError, KeyError) as e:
                    self.logger.warning(f"Ошибка при обработке записи: {e}")
                    continue
            
            if not rows:
                self.logger.warning("Нет данных для сохранения")
                return None
                
            # Создаем DataFrame
            df = pd.DataFrame(rows)
            
            # Сохраняем данные в базу
            query = """
            INSERT INTO pair_liquidations 
            (timestamp, symbol, exchange, interval, long_turnover, short_turnover, long_amount, short_amount)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (timestamp, symbol, exchange, interval) DO UPDATE SET
                long_turnover = EXCLUDED.long_turnover,
                short_turnover = EXCLUDED.short_turnover,
                long_amount = EXCLUDED.long_amount,
                short_amount = EXCLUDED.short_amount;
            """
            
            for _, row in df.iterrows():
                self.db.execute_query(query, (
                    row['timestamp'],
                    row['symbol'],
                    row['exchange'],
                    row['interval'],
                    row['long_turnover'],
                    row['short_turnover'],
                    row['long_amount'],
                    row['short_amount']
                ))
            
            self.logger.info(f"Saved pair liquidation data: {len(df)} records")
            return df
            
        return None

    def get_market_buy_sell_volume(self, symbol='BTCUSDT', exchange='Binance', interval='1h', 
                                 product_type='SWAP', end_time=None, size=500):
        """
        Получает объем активных покупок и продаж рыночных ордеров в пределах временного уровня.
        
        API Endpoint: https://docs.coinank.com/docs/api/version-1.html#/Market%20Order%20Statistics/get_api_marketOrder_getBuySellVolume
        
        Args:
            symbol (str): Торговая пара (например, 'BTCUSDT')
            exchange (str): Биржа (Binance, OKX, Bybit, Bitget)
            interval (str): Интервал времени (1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 8h, 1d)
            product_type (str): Тип продукта (SWAP или SPOT)
            end_time (int): Конечное время в миллисекундах
            size (int): Размер выборки (макс. 500)
            
        Returns:
            pandas.DataFrame: DataFrame с данными или None в случае ошибки
        """
        if self.has_vip_access is False:
            self.logger.warning("Этот метод требует VIP3 или выше")
            return None
        
        endpoint = 'marketOrder/getBuySellVolume'
        params = {
            'symbol': symbol,
            'exchange': exchange,
            'interval': interval,
            'productType': product_type,
            'size': min(size, 500)
        }
        
        if end_time:
            params['endTime'] = str(end_time)
            
        self.logger.info(f"Getting market buy/sell volume for {symbol} on {exchange}")
        data = self._make_request(endpoint, params)
        
        if data and 'data' in data and 'data' in data['data']:
            # Создаем таблицу, если она не существует
            query = """
            CREATE TABLE IF NOT EXISTS market_buy_sell_volume (
                id SERIAL PRIMARY KEY,
                timestamp TIMESTAMP NOT NULL,
                symbol VARCHAR(20) NOT NULL,
                exchange VARCHAR(50) NOT NULL,
                product_type VARCHAR(10) NOT NULL,
                buy_volume FLOAT NOT NULL,
                sell_volume FLOAT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(timestamp, symbol, exchange, product_type)
            );
            """
            self.db.execute_query(query)
            
            # Преобразуем данные в DataFrame
            df = pd.DataFrame(data['data']['data'], columns=['timestamp', 'buy_volume', 'sell_volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df['symbol'] = symbol
            df['exchange'] = exchange
            df['product_type'] = product_type
            
            # Сохраняем данные в базу
            query = """
            INSERT INTO market_buy_sell_volume 
            (timestamp, symbol, exchange, product_type, buy_volume, sell_volume)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (timestamp, symbol, exchange, product_type) DO NOTHING;
            """
            
            for _, row in df.iterrows():
                self.db.execute_query(query, (
                    row['timestamp'],
                    row['symbol'],
                    row['exchange'],
                    row['product_type'],
                    row['buy_volume'],
                    row['sell_volume']
                ))
            
            self.logger.info(f"Saved market buy/sell volume data: {len(df)} records")
            return df
            
        return None

    def get_aggregated_market_buy_sell_volume(self, base_coin='BTC', exchanges='Binance', interval='1h',
                                            product_type='SWAP', end_time=None, size=500):
        """
        Получает агрегированный объем активных покупок и продаж рыночных ордеров в пределах временного уровня.
        
        API Endpoint: https://docs.coinank.com/docs/api/version-1.html#/Market%20Order%20Statistics/get_api_marketOrder_getAggBuySellVolume
        
        Args:
            base_coin (str): Базовая монета (например, 'BTC')
            exchanges (str): Список бирж через запятую (Binance,OKX,Bybit,Bitget,Huobi)
            interval (str): Интервал времени (1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 8h, 1d)
            product_type (str): Тип продукта (SWAP или SPOT)
            end_time (int): Конечное время в миллисекундах
            size (int): Размер выборки (макс. 500)
            
        Returns:
            pandas.DataFrame: DataFrame с данными или None в случае ошибки
        """
        if self.has_vip_access is False:
            self.logger.warning("Этот метод требует VIP3 или выше")
            return None
        
        endpoint = 'marketOrder/getAggBuySellVolume'
        params = {
            'baseCoin': base_coin,
            'exchanges': exchanges,
            'interval': interval,
            'productType': product_type,
            'size': min(size, 500)
        }
        
        if end_time:
            params['endTime'] = str(end_time)
            
        self.logger.info(f"Getting aggregated market buy/sell volume for {base_coin} on exchanges: {exchanges}")
        data = self._make_request(endpoint, params)
        
        if data and 'data' in data and 'data' in data['data']:
            # Создаем таблицу, если она не существует
            query = """
            CREATE TABLE IF NOT EXISTS aggregated_market_buy_sell_volume (
                id SERIAL PRIMARY KEY,
                timestamp TIMESTAMP NOT NULL,
                base_coin VARCHAR(10) NOT NULL,
                exchanges VARCHAR(255) NOT NULL,
                product_type VARCHAR(10) NOT NULL,
                buy_volume FLOAT NOT NULL,
                sell_volume FLOAT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(timestamp, base_coin, exchanges, product_type)
            );
            """
            self.db.execute_query(query)
            
            # Преобразуем данные в DataFrame
            df = pd.DataFrame(data['data']['data'], columns=['timestamp', 'buy_volume', 'sell_volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df['base_coin'] = base_coin
            df['exchanges'] = exchanges
            df['product_type'] = product_type
            
            # Сохраняем данные в базу
            query = """
            INSERT INTO aggregated_market_buy_sell_volume 
            (timestamp, base_coin, exchanges, product_type, buy_volume, sell_volume)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (timestamp, base_coin, exchanges, product_type) DO NOTHING;
            """
            
            for _, row in df.iterrows():
                self.db.execute_query(query, (
                    row['timestamp'],
                    row['base_coin'],
                    row['exchanges'],
                    row['product_type'],
                    row['buy_volume'],
                    row['sell_volume']
                ))
            
            self.logger.info(f"Saved aggregated market buy/sell volume data: {len(df)} records")
            return df
            
        return None

    def get_funding_rate_kline(self, symbol='BTCUSDT', exchange='Binance', interval='1h', end_time=None, size=500):
        """
        Получает исторические данные по funding rate в формате kline.
        
        API Endpoint: https://docs.coinank.com/docs/api/version-1.html#/FundingRate/get_api_fundingRate_kline
        
        Args:
            symbol (str): Торговая пара (например, 'BTCUSDT')
            exchange (str): Биржа
            interval (str): Интервал времени (1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 8h, 1d)
            end_time (int): Конечное время в миллисекундах
            size (int): Размер выборки (макс. 500)
            
        Returns:
            pandas.DataFrame: DataFrame с данными или None в случае ошибки
        """
        endpoint = 'fundingRate/kline'
        params = {
            'symbol': symbol,
            'exchange': exchange,
            'interval': interval,
            'size': min(size, 500)
        }
        
        if end_time:
            params['endTime'] = str(end_time)
            
        self.logger.info(f"Getting funding rate kline data for {symbol} on {exchange}")
        data = self._make_request(endpoint, params)
        
        if data:
            # Создаем таблицу, если она не существует
            query = """
            CREATE TABLE IF NOT EXISTS funding_rate_kline (
                id SERIAL PRIMARY KEY,
                timestamp TIMESTAMP NOT NULL,
                symbol VARCHAR(20) NOT NULL,
                exchange VARCHAR(50) NOT NULL,
                funding_rate FLOAT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(timestamp, symbol, exchange)
            );
            """
            self.db.execute_query(query)
            
            # Преобразуем данные в DataFrame
            df = pd.DataFrame(data, columns=['timestamp', 'funding_rate'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df['symbol'] = symbol
            df['exchange'] = exchange
            
            # Сохраняем данные в базу
            query = """
            INSERT INTO funding_rate_kline 
            (timestamp, symbol, exchange, funding_rate)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (timestamp, symbol, exchange) DO NOTHING;
            """
            
            for _, row in df.iterrows():
                self.db.execute_query(query, (
                    row['timestamp'],
                    row['symbol'],
                    row['exchange'],
                    row['funding_rate']
                ))
            
            self.logger.info(f"Saved funding rate kline data: {len(df)} records")
            return df
            
        return None

    def get_funding_rate_accumulated(self, symbol='BTCUSDT', exchange='Binance', end_time=None, size=500):
        """
        Получает накопленные данные по funding rate.
        
        API Endpoint: https://docs.coinank.com/docs/api/version-1.html#/FundingRate/get_api_fundingRate_accumulated
        
        Args:
            symbol (str): Торговая пара (например, 'BTCUSDT')
            exchange (str): Биржа
            end_time (int): Конечное время в миллисекундах
            size (int): Размер выборки (макс. 500)
            
        Returns:
            pandas.DataFrame: DataFrame с данными или None в случае ошибки
        """
        endpoint = 'fundingRate/accumulated'
        params = {
            'symbol': symbol,
            'exchange': exchange,
            'size': min(size, 500)
        }
        
        if end_time:
            params['endTime'] = str(end_time)
            
        self.logger.info(f"Getting accumulated funding rate data for {symbol} on {exchange}")
        data = self._make_request(endpoint, params)
        
        if data:
            # Создаем таблицу, если она не существует
            query = """
            CREATE TABLE IF NOT EXISTS funding_rate_accumulated (
                id SERIAL PRIMARY KEY,
                timestamp TIMESTAMP NOT NULL,
                symbol VARCHAR(20) NOT NULL,
                exchange VARCHAR(50) NOT NULL,
                accumulated_rate FLOAT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(timestamp, symbol, exchange)
            );
            """
            self.db.execute_query(query)
            
            # Преобразуем данные в DataFrame
            df = pd.DataFrame(data, columns=['timestamp', 'accumulated_rate'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df['symbol'] = symbol
            df['exchange'] = exchange
            
            # Сохраняем данные в базу
            query = """
            INSERT INTO funding_rate_accumulated 
            (timestamp, symbol, exchange, accumulated_rate)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (timestamp, symbol, exchange) DO NOTHING;
            """
            
            for _, row in df.iterrows():
                self.db.execute_query(query, (
                    row['timestamp'],
                    row['symbol'],
                    row['exchange'],
                    row['accumulated_rate']
                ))
            
            self.logger.info(f"Saved accumulated funding rate data: {len(df)} records")
            return df
            
        return None

    def get_historical_data(self, symbol='BTCUSDT', exchange='Binance', interval='1d', 
                          start_time=None, end_time=None, limit=1000):
        """
        Получает исторические данные
        
        Args:
            symbol (str): Торговая пара
            exchange (str): Биржа
            interval (str): Интервал времени (1m, 5m, 15m, 30m, 1h, 4h, 1d, 1w, 1M)
            start_time (datetime): Время начала
            end_time (datetime): Время окончания
            limit (int): Количество записей
        """
        try:
            # Проверяем последнюю запись в базе данных
            if not start_time:
                query = """
                    SELECT MAX(timestamp) as last_timestamp 
                    FROM coinark_historical 
                    WHERE symbol = %s AND exchange = %s
                """
                result = self.db.execute_query(query, (symbol, exchange))
                last_timestamp = result[0][0] if result and result[0][0] else None
                
                if last_timestamp:
                    start_time = last_timestamp
                else:
                    # По умолчанию берем данные за последние 2 года
                    start_time = datetime.now() - timedelta(days=730)
            
            # Получаем данные
            params = {
                'symbol': symbol,
                'exchange': exchange,
                'interval': interval,
                'limit': limit
            }
            if start_time:
                params['startTime'] = int(start_time.timestamp() * 1000)
            if end_time:
                params['endTime'] = int(end_time.timestamp() * 1000)
            
            data = self._make_request('kline', params)
            
            if not data:
                self.logger.warning(f"No historical data received for {symbol} on {exchange}")
                return
            
            # Сохраняем данные
            for item in data:
                timestamp = datetime.fromtimestamp(item[0] / 1000)
                
                query = """
                    INSERT INTO coinark_historical 
                    (timestamp, symbol, exchange, open_price, high_price, 
                     low_price, close_price, volume)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (timestamp, symbol, exchange) DO UPDATE SET
                        open_price = EXCLUDED.open_price,
                        high_price = EXCLUDED.high_price,
                        low_price = EXCLUDED.low_price,
                        close_price = EXCLUDED.close_price,
                        volume = EXCLUDED.volume;
                """
                self.db.execute_query(
                    query,
                    (timestamp, symbol, exchange, item[1], item[2], 
                     item[3], item[4], item[5])
                )
            
            self.logger.info(f"Successfully collected historical data for {symbol} on {exchange}")
            
        except Exception as e:
            self.logger.error(f"Error collecting historical data: {str(e)}")

    def update_all_data(self, symbols=None, exchanges=None):
        """
        Обновляет все данные
        
        Args:
            symbols (list): Список торговых пар
            exchanges (list): Список бирж
        """
        if not symbols:
            symbols = ['BTCUSDT']
        if not exchanges:
            exchanges = ['Binance']
            
        self.logger.info("Начинаем обновление всех данных")
        
        # Создаем таблицы если они не существуют
        self._create_tables()
        
        # Собираем исторические данные для каждой пары
        for symbol in symbols:
            for exchange in exchanges:
                # Получаем исторические данные
                self.get_historical_data(symbol=symbol, exchange=exchange)
                # Получаем данные книги ордеров
                self.get_orderbook(symbol=symbol, exchange=exchange)
        
        self.logger.info("Обновление всех данных завершено")

    def get_orderbook(self, symbol='BTCUSDT', exchange='Binance', product_type='Swap', limit=1000):
        """
        Получает данные книги ордеров
        
        Args:
            symbol (str): Торговая пара
            exchange (str): Биржа
            product_type (str): Тип продукта (Spot, Swap, Future)
            limit (int): Количество записей
        """
        try:
            # Получаем данные
            params = {
                'symbol': symbol,
                'exchange': exchange,
                'productType': product_type,
                'limit': limit
            }
            data = self._make_request('depth', params)
            
            if not data:
                self.logger.warning(f"No orderbook data received for {symbol} on {exchange}")
                return
            
            timestamp = datetime.now()
            
            # Обрабатываем каждый уровень цены
            for rate, bid_data in data.get('bids', {}).items():
                bid_volume = float(bid_data.get('volume', 0))
                bid_count = int(bid_data.get('count', 0))
                
                ask_data = data.get('asks', {}).get(rate, {})
                ask_volume = float(ask_data.get('volume', 0))
                ask_count = int(ask_data.get('count', 0))
                
                # Вычисляем дисбаланс
                volume_imbalance = bid_volume - ask_volume
                count_imbalance = bid_count - ask_count
                
                # Сохраняем в базу данных
                query = """
                    INSERT INTO coinark_orderbook 
                    (timestamp, symbol, exchange, product_type, rate, 
                     bid_volume, bid_count, ask_volume, ask_count,
                     volume_imbalance, count_imbalance)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (timestamp, symbol, exchange, product_type, rate) 
                    DO UPDATE SET
                        bid_volume = EXCLUDED.bid_volume,
                        bid_count = EXCLUDED.bid_count,
                        ask_volume = EXCLUDED.ask_volume,
                        ask_count = EXCLUDED.ask_count,
                        volume_imbalance = EXCLUDED.volume_imbalance,
                        count_imbalance = EXCLUDED.count_imbalance;
                """
                self.db.execute_query(
                    query,
                    (timestamp, symbol, exchange, product_type, rate,
                     bid_volume, bid_count, ask_volume, ask_count,
                     volume_imbalance, count_imbalance)
                )
            
            self.logger.info(f"Successfully collected orderbook data for {symbol} on {exchange}")
            
        except Exception as e:
            self.logger.error(f"Error collecting orderbook data: {str(e)}")

    def collect_full_history(self, start_date=None, symbol='BTCUSDT', exchange='Binance', interval='1h', force_full=False):
        """
        Собирает все доступные исторические данные с проверкой уже собранных данных в базе.
        
        Args:
            start_date (datetime): Начальная дата для сбора данных
            symbol (str): Торговая пара
            exchange (str): Биржа
            interval (str): Интервал времени
            force_full (bool): Если True, собирает все данные заново
        """
        if not start_date:
            # По умолчанию берем данные за последние 2 года
            start_date = datetime.now() - timedelta(days=730)
            
        self.logger.info(f"Начинаем сбор исторических данных с {start_date}")
        
        # Разбиваем symbol на base_coin
        base_coin = symbol.replace('USDT', '') if isinstance(symbol, str) else 'BTC'
        
        # Создаем все необходимые таблицы
        self._create_tables()
        
        # Собираем все типы данных
        if self.has_vip_access:
            self.collect_funding_rates(start_date, force_full)
            self.collect_open_interest(start_date, force_full)
            self.collect_long_short_ratio(start_date, force_full)
            self.collect_liquidation_data(start_date, force_full)
            self.collect_indicators(start_date, force_full)
        else:
            self.logger.info("Пропускаем сбор расширенных данных из-за базового уровня доступа")
        
        self.logger.info("Обновление всех данных завершено")

    def update_all_data(self, start_date: Optional[datetime] = None, force_full: bool = False):
        """
        Обновляет все данные
        
        Args:
            start_date (datetime, optional): Дата начала сбора данных
            force_full (bool): Принудительно собрать все данные, игнорируя существующие записи
        """
        self.logger.info("Начинаем обновление всех данных")
        
        # Создаем таблицы если они не существуют
        self._create_tables()
        
        # Собираем все типы данных
        self.collect_full_history(start_date, force_full)
        
        if self.has_vip_access:
            self.collect_indicators(start_date, force_full)
        else:
            self.logger.info("Пропускаем сбор индикаторов из-за базового уровня доступа")
        
        self.logger.info("Обновление всех данных завершено")

    def collect_indicators(self, start_date=None, force_full=False):
        """
        Собирает данные индикаторов с CoinArk API
        
        Args:
            start_date (datetime): Начальная дата для сбора данных
            force_full (bool): Если True, собирает все данные заново
        """
        indicators = [
            'mvrv-zscore',
            '1-year-hodl-wave',
            'hodl-waves',
            'relative-unrealized-prof',
            'bitcoin-price-prediction',
            'reserve-risk',
            'rhodl-ratio',
            'whale-shadows',
            'bitcoin-rainbow-v2'
        ]
        
        for indicator in indicators:
            self.logger.info(f"Collecting data for indicator: {indicator}")
            try:
                # Формируем URL для индикатора
                if indicator == 'bitcoin-rainbow-v2':
                    params = {'type': indicator}
                else:
                    params = {'type': f'/charts/{indicator}/'}
                
                # Получаем данные
                response_data = self._make_request('indicator/index/charts', params)
                
                if response_data and isinstance(response_data, dict):
                    # Извлекаем значения
                    values = response_data.get('data', {}).get('value6', [])
                    
                    if values and not all(v is None for v in values):
                        # Создаем временные метки
                        # Предположим, что данные идут с интервалом в 1 день, начиная с сегодня
                        end_date = datetime.now()
                        dates = [end_date - timedelta(days=i) for i in range(len(values)-1, -1, -1)]
                        
                        # Создаем DataFrame
                        df = pd.DataFrame({
                            'timestamp': dates,
                            'value': values
                        }).dropna()  # Удаляем строки с null значениями
                        
                        if not df.empty:
                            # Сохраняем в базу данных
                            for _, row in df.iterrows():
                                query = """
                                INSERT INTO coinark_indicators (timestamp, indicator, value)
                                VALUES (%s, %s, %s)
                                ON CONFLICT (timestamp, indicator) DO UPDATE 
                                SET value = EXCLUDED.value;
                                """
                                self.db.execute_query(query, (row['timestamp'], indicator, row['value']))
                            
                            self.logger.info(f"Successfully saved {len(df)} records for {indicator}")
                        else:
                            self.logger.warning(f"No valid data received for {indicator}")
                    else:
                        self.logger.warning(f"No valid values received for {indicator}")
                else:
                    self.logger.warning(f"No data received for {indicator}")
                    
            except Exception as e:
                self.logger.error(f"Error collecting data for indicator {indicator}: {str(e)}")
                continue

    def collect_funding_rates(self, start_date=None, force_full=False):
        """
        Собирает данные funding rate
        
        Args:
            start_date (datetime): Начальная дата для сбора данных
            force_full (bool): Если True, собирает все данные заново
        """
        try:
            # Получаем данные
            data = self._make_request('fundingRate/hist', {'symbol': 'BTCUSDT', 'size': '1000'})
            
            if not data:
                self.logger.warning("No funding rate data received")
                return
            
            # Сохраняем данные
            for item in data:
                timestamp = datetime.fromtimestamp(item['timestamp'] / 1000)
                base_coin = item['symbol'].split('USDT')[0]
                
                query = """
                    INSERT INTO funding_rate_data 
                    (timestamp, base_coin, exchange, rate, change_24h, turnover_24h)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (timestamp, base_coin, exchange) DO UPDATE SET
                        rate = EXCLUDED.rate,
                        change_24h = EXCLUDED.change_24h,
                        turnover_24h = EXCLUDED.turnover_24h;
                """
                self.db.execute_query(
                    query,
                    (timestamp, base_coin, item['exchange'], 
                     item['rate'], item['change24h'], item['turnover24h'])
                )
            
            self.logger.info(f"Successfully collected funding rate data: {len(data)} records")
            
        except Exception as e:
            self.logger.error(f"Error collecting funding rate data: {str(e)}")

    def collect_open_interest(self, start_date=None, force_full=False):
        """
        Собирает данные по открытому интересу
        
        Args:
            start_date (datetime): Начальная дата для сбора данных
            force_full (bool): Если True, собирает все данные заново
        """
        try:
            # Получаем данные
            data = self._make_request('openInterest/hist', {'symbol': 'BTCUSDT', 'size': '1000'})
            
            if not data:
                self.logger.warning("No open interest data received")
                return
            
            # Сохраняем данные
            for item in data:
                timestamp = datetime.fromtimestamp(item['timestamp'] / 1000)
                base_coin = item['symbol'].split('USDT')[0]
                
                query = """
                    INSERT INTO open_interest_data 
                    (timestamp, base_coin, exchange, open_interest, open_interest_value)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (timestamp, base_coin, exchange) DO UPDATE SET
                        open_interest = EXCLUDED.open_interest,
                        open_interest_value = EXCLUDED.open_interest_value;
                """
                self.db.execute_query(
                    query,
                    (timestamp, base_coin, item['exchange'], 
                     item['openInterest'], item['openInterestValue'])
                )
            
            self.logger.info(f"Successfully collected open interest data: {len(data)} records")
            
        except Exception as e:
            self.logger.error(f"Error collecting open interest data: {str(e)}")

    def collect_long_short_ratio(self, start_date=None, force_full=False):
        """
        Собирает данные по соотношению длинных и коротких позиций
        
        Args:
            start_date (datetime): Начальная дата для сбора данных
            force_full (bool): Если True, собирает все данные заново
        """
        try:
            # Получаем данные
            data = self._make_request('longShortRatio/hist', {'symbol': 'BTCUSDT', 'size': '1000'})
            
            if not data:
                self.logger.warning("No long/short ratio data received")
                return
            
            # Сохраняем данные
            for item in data:
                timestamp = datetime.fromtimestamp(item['timestamp'] / 1000)
                base_coin = item['symbol'].split('USDT')[0]
                
                query = """
                    INSERT INTO long_short_ratio_data 
                    (timestamp, base_coin, exchange, long_short_ratio, long_account, short_account)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (timestamp, base_coin, exchange) DO UPDATE SET
                        long_short_ratio = EXCLUDED.long_short_ratio,
                        long_account = EXCLUDED.long_account,
                        short_account = EXCLUDED.short_account;
                """
                self.db.execute_query(
                    query,
                    (timestamp, base_coin, item['exchange'], 
                     item['longShortRatio'], item['longAccount'], item['shortAccount'])
                )
            
            self.logger.info(f"Successfully collected long/short ratio data: {len(data)} records")
            
        except Exception as e:
            self.logger.error(f"Error collecting long/short ratio data: {str(e)}")

    def collect_liquidation_data(self, start_date=None, force_full=False):
        """
        Собирает данные по ликвидациям
        
        Args:
            start_date (datetime): Начальная дата для сбора данных
            force_full (bool): Если True, собирает все данные заново
        """
        try:
            # Получаем данные
            data = self._make_request('liquidation/hist', {'symbol': 'BTCUSDT', 'size': '1000'})
            
            if not data:
                self.logger.warning("No liquidation data received")
                return
            
            # Сохраняем данные
            for item in data:
                timestamp = datetime.fromtimestamp(item['timestamp'] / 1000)
                base_coin = item['symbol'].split('USDT')[0]
                
                query = """
                    INSERT INTO liquidations_data 
                    (timestamp, base_coin, side, price, quantity, liquidation_value)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (timestamp, base_coin, side, price, quantity) DO UPDATE SET
                        liquidation_value = EXCLUDED.liquidation_value;
                """
                self.db.execute_query(
                    query,
                    (timestamp, base_coin, item['side'], 
                     item['price'], item['quantity'], item['liquidationValue'])
                )
            
            self.logger.info(f"Successfully collected liquidation data: {len(data)} records")
            
        except Exception as e:
            self.logger.error(f"Error collecting liquidation data: {str(e)}")

    def collect_basic_data(self, start_date=None, symbol='BTCUSDT', exchange='Binance', interval='1h', force_full=False):
        """
        Собирает базовые данные, доступные с базовым уровнем доступа
        
        Args:
            start_date (datetime): Начальная дата для сбора данных
            symbol (str): Торговая пара
            exchange (str): Биржа
            interval (str): Интервал времени
            force_full (bool): Если True, собирает все данные заново
        """
        if not start_date:
            # По умолчанию берем данные за последние 2 года
            start_date = datetime.now() - timedelta(days=730)
            
        self.logger.info(f"Начинаем сбор базовых данных с {start_date}")
        
        # Разбиваем symbol на base_coin
        base_coin = symbol.replace('USDT', '') if isinstance(symbol, str) else 'BTC'
        
        # Создаем все необходимые таблицы
        self._create_tables()
        
        # Собираем базовые данные
        self.collect_historical_data(start_date, symbol, exchange, interval, force_full)
        self.collect_orderbook_data(symbol, exchange)
        
        self.logger.info("Сбор базовых данных завершен")

    def collect_historical_data(self, start_date=None, symbol='BTCUSDT', exchange='Binance', interval='1h', force_full=False):
        """
        Собирает исторические данные о ценах
        
        Args:
            start_date (datetime): Начальная дата для сбора данных
            symbol (str): Торговая пара
            exchange (str): Биржа
            interval (str): Интервал времени
            force_full (bool): Если True, собирает все данные заново
        """
        try:
            # Получаем данные
            params = {
                'symbol': symbol,
                'exchange': exchange,
                'interval': interval,
                'limit': 1000
            }
            
            if start_date:
                params['startTime'] = int(start_date.timestamp() * 1000)
            
            data = self._make_request('kline', params)
            
            if not data:
                self.logger.warning("No historical data received")
                return
            
            # Сохраняем данные
            for item in data:
                timestamp = datetime.fromtimestamp(item[0] / 1000)
                
                query = """
                    INSERT INTO coinark_historical 
                    (timestamp, symbol, exchange, open_price, high_price, low_price, close_price, volume)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (timestamp, symbol, exchange) DO UPDATE SET
                        open_price = EXCLUDED.open_price,
                        high_price = EXCLUDED.high_price,
                        low_price = EXCLUDED.low_price,
                        close_price = EXCLUDED.close_price,
                        volume = EXCLUDED.volume;
                """
                self.db.execute_query(
                    query,
                    (timestamp, symbol, exchange, 
                     float(item[1]), float(item[2]), float(item[3]), float(item[4]), float(item[5]))
                )
            
            self.logger.info(f"Successfully collected historical data: {len(data)} records")
            
        except Exception as e:
            self.logger.error(f"Error collecting historical data: {str(e)}")

    def update_all_data(self, start_date: Optional[datetime] = None, force_full: bool = False):
        """
        Обновляет все данные
        
        Args:
            start_date (datetime, optional): Дата начала сбора данных
            force_full (bool): Принудительно собрать все данные, игнорируя существующие записи
        """
        self.logger.info("Начинаем обновление всех данных")
        
        # Создаем таблицы если они не существуют
        self._create_tables()
        
        # Собираем базовые данные
        self.collect_basic_data(start_date, force_full=force_full)
        
        # Собираем расширенные данные если есть доступ
        if self.has_vip_access:
            self.collect_full_history(start_date, force_full)
            self.collect_indicators(start_date, force_full)
        else:
            self.logger.info("Пропускаем сбор расширенных данных из-за базового уровня доступа")
        
        self.logger.info("Обновление всех данных завершено")

if __name__ == "__main__":
    collector = CoinArkCollector()
    collector.update_all_data()
