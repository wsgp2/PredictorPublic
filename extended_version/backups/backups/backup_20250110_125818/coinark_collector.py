import requests
import pandas as pd
import os
from datetime import datetime, timedelta
import logging
import time
from typing import Optional

class CoinArkCollector:
    """
    Коллектор данных с CoinArk API для получения данных о деривативах и фьючерсах
    """
    
    def __init__(self, api_key='84068f54707949bc8f86e2dd9dcee6ac'):
        self.api_key = api_key
        self.base_url = 'https://open-api.coinank.com/api'
        self.headers = {
            'apikey': self.api_key,
            'accept': 'application/json'
        }
        
        # Создаем директории для хранения данных
        self.data_dir = 'data/coinark'
        subdirs = [
            'open_interest', 'liquidations', 'funding_rates', 'klines',
            'longshort', 'indicators', 'historical', 'orderbook'
        ]
        for subdir in subdirs:
            os.makedirs(os.path.join(self.data_dir, subdir), exist_ok=True)
        
        # Настройка логирования
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

    def _make_request(self, endpoint, params=None):
        """Выполняет запрос к API"""
        # Формируем URL с параметрами
        url = f"{self.base_url}/{endpoint}"
        if params:
            query_params = '&'.join([f"{k}={v}" for k, v in params.items()])
            url = f"{url}?{query_params}"
            
        headers = {
            'accept': 'application/json',
            'apikey': self.api_key
        }
        
        try:
            self.logger.info(f"Making request to {url}")
            self.logger.info(f"Headers: {headers}")
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    return data.get('data')
                else:
                    self.logger.error(f"API Error for {endpoint}. Code: {data.get('code')}, Message: {data.get('msg')}")
                    self.logger.error(f"Full response: {data}")
            else:
                self.logger.error(f"HTTP Error for {endpoint}: {response.status_code} {response.reason} for url: {response.url}")
                self.logger.error(f"Response content: {response.text}")
                
                # Повторяем запрос при ошибках
                if response.status_code in [429, 500, 502, 503, 504]:
                    for attempt in range(3):
                        self.logger.info(f"Retrying in 5 seconds... (Attempt {attempt + 1}/3)")
                        time.sleep(5)
                        response = requests.get(url, headers=headers)
                        if response.status_code == 200:
                            data = response.json()
                            if data.get('success'):
                                return data.get('data')
                            
        except Exception as e:
            self.logger.error(f"Error making request to {endpoint}: {str(e)}")
            
        return None

    def get_funding_rate(self, type='current'):
        """
        Получает данные о ставках финансирования
        type: current, day, week, month, year
        """
        endpoint = 'fundingRate/current'
        params = {'type': type}
        
        data = self._make_request(endpoint, params)
        if data:
            records = []
            for item in data:
                symbol = item['symbol']
                if item.get('cmap'):
                    for exchange, exchange_data in item['cmap'].items():
                        exchange_data['symbol'] = symbol
                        exchange_data['margin_type'] = 'COIN'
                        records.append(exchange_data)
                if item.get('umap'):
                    for exchange, exchange_data in item['umap'].items():
                        exchange_data['symbol'] = symbol
                        exchange_data['margin_type'] = 'USDT'
                        records.append(exchange_data)
            
            df = pd.DataFrame(records)
            filename = os.path.join(self.data_dir, 'funding_rates', f'funding_rate_{type}_{datetime.now().strftime("%Y%m%d")}.csv')
            df.to_csv(filename, index=False)
            self.logger.info(f"Saved funding rate data to {filename}")
            return df
        return None

    def get_historical_funding_rate(self, base_coin, exchange_type, end_time=None, size=500):
        """
        Получает исторические данные о ставках финансирования
        
        Args:
            base_coin: Базовая монета (например, 'BTC')
            exchange_type: Тип контракта ('USDT' или 'COIN')
            end_time: Конечное время в миллисекундах
            size: Размер выборки (макс. 500)
        """
        params = {
            'baseCoin': base_coin,
            'exchangeType': exchange_type,
            'size': str(size)
        }
        
        if end_time:
            params['endTime'] = str(end_time)
            
        self.logger.info(f"Getting funding rate data for {base_coin}{exchange_type}")
        data = self._make_request('fundingRate/hist', params)
        
        if data:
            # Создаем директорию, если она не существует
            os.makedirs(os.path.join(self.data_dir, 'funding_rate'), exist_ok=True)
            
            # Преобразуем данные в DataFrame
            rows = []
            for item in data:
                ts = item['ts']
                details = item['details']
                
                row = {'timestamp': ts}
                for exchange, rates in details.items():
                    row[f'{exchange}_fundingRate'] = rates.get('fundingRate')
                    if 'realizedRate' in rates:
                        row[f'{exchange}_realizedRate'] = rates.get('realizedRate')
                rows.append(row)
                
            df = pd.DataFrame(rows)
            
            # Сохраняем данные в CSV
            filename = os.path.join(self.data_dir, 'funding_rate', 
                                  f'funding_rate_{base_coin}{exchange_type}_{datetime.now().strftime("%Y%m%d")}.csv')
            df.to_csv(filename, index=False)
            self.logger.info(f'Saved funding rate data to {filename}')
            return df
        return None

    def get_accumulated_funding_rate(self, type='day'):
        """
        Получает накопленную ставку финансирования
        type: day, week, month, year
        """
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

    def get_open_interest(self, base_coin: str, interval: str = '1h', size: int = 500, 
                         type: str = 'USD', end_time: Optional[int] = None) -> pd.DataFrame:
        """
        Получает данные об открытом интересе

        Args:
            base_coin: Базовая монета (например, 'BTC')
            interval: Интервал времени ('1h', '4h', '1d')
            size: Количество записей (максимум 500)
            type: Тип данных ('USD' или 'COIN')
            end_time: Конечное время в миллисекундах

        Returns:
            pd.DataFrame: Данные об открытом интересе
        """
        params = {
            'baseCoin': base_coin,
            'interval': interval,
            'size': size,
            'type': type
        }
        if end_time is not None:
            params['endTime'] = end_time

        response = self._make_request('openInterest/kline', params)
        if response and 'data' in response:
            data = response['data']
            if not data:
                return pd.DataFrame()

            df = pd.DataFrame(data)
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            return df
        return pd.DataFrame()

    def get_open_interest_kline(self, symbol, exchange, interval, start_time=None, end_time=None):
        """
        Получает исторические данные об открытом интересе
        
        Args:
            symbol: Торговая пара (например, 'BTCUSDT')
            exchange: Биржа
            interval: Интервал
            start_time: Начальное время в миллисекундах
            end_time: Конечное время в миллисекундах
        """
        params = {
            'symbol': symbol,
            'exchange': exchange,
            'interval': interval,
            'productType': 'SWAP'
        }
        
        if start_time:
            params['startTime'] = start_time
        if end_time:
            params['endTime'] = end_time
            
        data = self._make_request('openInterest/kline', params)
        if data:
            # Создаем директорию, если она не существует
            os.makedirs(os.path.join(self.data_dir, 'open_interest'), exist_ok=True)
            
            # Сохраняем данные в CSV
            filename = os.path.join(self.data_dir, 'open_interest', 
                                  f'open_interest_kline_{symbol}_{exchange}_{interval}_{datetime.now().strftime("%Y%m%d")}.csv')
            
            df = pd.DataFrame(data)
            df.to_csv(filename, index=False)
            self.logger.info(f'Saved open interest kline data to {filename}')
            return df
        return None
        
    def get_liquidations(self, base_coin: str, interval: str = '1h', size: int = 500, end_time: Optional[int] = None) -> pd.DataFrame:
        """
        Получает данные о ликвидациях

        Args:
            base_coin: Базовая монета (например, 'BTC')
            interval: Интервал времени ('1h', '4h', '1d')
            size: Количество записей (максимум 500)
            end_time: Конечное время в миллисекундах

        Returns:
            pd.DataFrame: Данные о ликвидациях
        """
        params = {
            'baseCoin': base_coin,
            'interval': interval,
            'size': size
        }
        if end_time is not None:
            params['endTime'] = end_time

        response = self._make_request('liquidation/kline', params)
        if response and 'data' in response:
            data = response['data']
            if not data:
                return pd.DataFrame()

            df = pd.DataFrame(data)
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            return df
        return pd.DataFrame()

    def get_historical_liquidations(self, symbol, exchange, interval, start_time=None, end_time=None):
        """
        Получает исторические данные о ликвидациях
        
        Args:
            symbol: Торговая пара
            exchange: Биржа
            interval: Интервал
            start_time: Начальное время в миллисекундах
            end_time: Конечное время в миллисекундах
        """
        params = {
            'symbol': symbol,
            'exchange': exchange,
            'interval': interval,
            'productType': 'SWAP'
        }
        
        if start_time:
            params['startTime'] = start_time
        if end_time:
            params['endTime'] = end_time
            
        data = self._make_request('liquidation/history', params)
        if data:
            # Создаем директорию, если она не существует
            os.makedirs(os.path.join(self.data_dir, 'liquidations'), exist_ok=True)
            
            # Сохраняем данные в CSV
            filename = os.path.join(self.data_dir, 'liquidations', 
                                  f'liquidations_{symbol}_{exchange}_{interval}_{datetime.now().strftime("%Y%m%d")}.csv')
            
            df = pd.DataFrame(data)
            df.to_csv(filename, index=False)
            self.logger.info(f'Saved liquidation data to {filename}')
            return df
        return None
        
    def get_longshort_kline(self, symbol='BTCUSDT', exchange='Binance', interval='1h', 
                           ls_type='longShortPerson', end_time=None, size=500):
        """
        Получает исторические данные о соотношении длинных и коротких позиций в формате K-line

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
        """
        endpoint = 'longshort/kline'
        
        # Если end_time не указан, используем текущее время
        if end_time is None:
            end_time = int(datetime.now().timestamp() * 1000)
            
        params = {
            'symbol': symbol,
            'exchange': exchange,
            'interval': interval,
            'endTime': end_time,
            'size': min(size, 500),  # Ограничиваем максимальный размер
            'type': ls_type
        }
        
        data = self._make_request(endpoint, params)
        if data:
            # Преобразуем данные в DataFrame
            df = pd.DataFrame(data)
            
            # Переименовываем колонки для лучшей читаемости
            df = df.rename(columns={
                'begin': 'timestamp',
                'open': 'ratio_open',
                'high': 'ratio_high',
                'low': 'ratio_low',
                'close': 'ratio_close'
            })
            
            # Преобразуем timestamp в datetime
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            # Сохраняем данные в CSV
            filename = f"{symbol}_{exchange}_{interval}_{ls_type}_longshort.csv"
            filepath = os.path.join(self.data_dir, 'longshort', filename)
            df.to_csv(filepath, index=False)
            self.logger.info(f"Long/Short ratio data saved to {filepath}")
            
            return df
            
        return None

    def get_kline_data(self, symbol='BTCUSDT', exchange='Binance', interval='1h', 
                      product_type='SWAP', size=500, end_time=None):
        """
        Получение исторических данных свечного графика (K-line)
        
        Args:
            symbol (str): Торговая пара (например, 'BTCUSDT')
            exchange (str): Биржа (Binance, OKX, Bybit, Huobi, Bitmex, Bitget, Gate)
            interval (str): Интервал (1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 8h, 1d)
            product_type (str): Тип продукта (SWAP или SPOT)
            size (int): Количество записей (максимум 500)
            end_time (int): Временная метка окончания (в миллисекундах)
        
        Returns:
            pandas.DataFrame: DataFrame с данными K-line или None в случае ошибки
        """
        endpoint = 'kline/lists'
        
        # Если end_time не указан, используем текущее время
        if end_time is None:
            end_time = int(datetime.now().timestamp() * 1000)
            
        params = {
            'symbol': symbol,
            'exchange': exchange,
            'interval': interval,
            'endTime': end_time,
            'size': min(size, 500),  # Ограничиваем максимальный размер
            'productType': product_type
        }
        
        data = self._make_request(endpoint, params)
        if data:
            # Выводим структуру первой записи для отладки
            if data:
                self.logger.info(f"First record structure: {data[0]}")
                self.logger.info(f"Number of elements in first record: {len(data[0])}")
            
            # Преобразуем данные в DataFrame с правильными колонками
            df = pd.DataFrame(data, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 
                'volume', 'close_time', 'quote_volume', 'trades'
            ])
            
            # Преобразуем timestamp в datetime
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df['close_time'] = pd.to_datetime(df['close_time'], unit='ms')
            
            # Сохраняем данные в CSV
            filename = f"{symbol}_{exchange}_{interval}_{product_type}_kline.csv"
            filepath = os.path.join(self.data_dir, 'klines', filename)
            df.to_csv(filepath, index=False)
            self.logger.info(f"Kline data saved to {filepath}")
            
            return df
            
        return None

    def get_longshort_ratio(self, base_coin='BTC', interval='1h'):
        """
        Получает соотношение длинных/коротких позиций в реальном времени
        """
        params = {
            'baseCoin': base_coin,
            'interval': interval
        }
        
        data = self._make_request('longshort/realtimeAll', params)
        if data:
            # Создаем директорию, если она не существует
            os.makedirs(os.path.join(self.data_dir, 'longshort'), exist_ok=True)
            
            # Сохраняем данные в CSV
            filename = os.path.join(self.data_dir, 'longshort', f'longshort_ratio_{params["baseCoin"]}_{params["interval"]}_{datetime.now().strftime("%Y%m%d")}.csv')
            
            # Преобразуем данные в DataFrame
            df = pd.DataFrame(data)
            df.to_csv(filename, index=False)
            self.logger.info(f'Saved long/short ratio data to {filename}')
            return df
        return None

    def get_longshort_position(self, exchange='Binance', symbol='BTCUSDT', interval='1h'):
        """
        Получает соотношение позиций long/short от топ-трейдеров
        """
        params = {
            'exchange': exchange,
            'symbol': symbol,
            'interval': interval,
            'size': '500',
            'endTime': int(time.time() * 1000)  # Текущее время в миллисекундах
        }
        
        data = self._make_request('longshort/position', params)
        if data:
            # Создаем директорию, если она не существует
            os.makedirs(os.path.join(self.data_dir, 'longshort'), exist_ok=True)
            
            # Сохраняем данные в CSV
            filename = os.path.join(self.data_dir, 'longshort', 
                                  f'longshort_position_{exchange}_{symbol}_{interval}_{datetime.now().strftime("%Y%m%d")}.csv')
            
            # Преобразуем данные в DataFrame
            df = pd.DataFrame(data)
            df.to_csv(filename, index=False)
            self.logger.info(f'Saved long/short position data to {filename}')
            return df
        return None

    def get_indicator_data(self, indicator_type):
        """
        Получает данные индикатора
        
        Args:
            indicator_type: Тип индикатора:
                - bitcoin-rainbow-v2
                - /charts/1-year-hodl-wave/
                - /charts/hodl-waves/
                - /charts/mvrv-zscore/
                - /charts/relative-unrealized-prof/
                - /charts/bitcoin-price-prediction/
                - /charts/reserve-risk/
                - /charts/rhodl-ratio/
                - /charts/whale-shadows/
        """
        # Для bitcoin-rainbow-v2 используем как есть, для остальных добавляем /charts/ в начало
        request_type = indicator_type
        if not indicator_type.startswith('/charts/') and indicator_type != 'bitcoin-rainbow-v2':
            request_type = f'/charts/{indicator_type}/'
            
        params = {
            'type': request_type,
            'endTime': int(time.time() * 1000)  # Текущее время в миллисекундах
        }
        
        self.logger.info(f"Getting indicator data for {indicator_type}")
        data = self._make_request('indicator/index/charts', params)
        if data:
            # Создаем директорию, если она не существует
            os.makedirs(os.path.join(self.data_dir, 'indicators'), exist_ok=True)
            
            # Сохраняем данные в CSV
            # Убираем слеши из имени файла для безопасности
            safe_type = indicator_type.replace('/', '_').strip('_')
            filename = os.path.join(self.data_dir, 'indicators', 
                                  f'indicator_{safe_type}_{datetime.now().strftime("%Y%m%d")}.csv')
            
            # Преобразуем данные в DataFrame
            df_data = {
                'timestamp': data.get('timeList', []),
                'btc_price': data.get('btcPrice', [])
            }
            
            # Добавляем все доступные значения
            for i in range(1, 13):  # Максимум 12 значений в ответе
                value_key = f'value{i}'
                if value_key in data:
                    values = data[value_key]
                    # Убедимся, что длина массива совпадает с timeList
                    if len(values) == len(df_data['timestamp']):
                        df_data[f'value_{i}'] = values
            
            df = pd.DataFrame(df_data)
            df.to_csv(filename, index=False)
            self.logger.info(f'Saved indicator data to {filename}')
            return df
        return None

    def check_api_status(self):
        """
        Проверяет статус API ключа
        """
        try:
            # Используем простой эндпоинт для проверки
            response = requests.get(f"{self.base_url}/fundingRate/current", 
                                 headers=self.headers, 
                                 params={'type': 'current'})
            
            if response.status_code == 401:
                self.logger.error("API ключ недействителен или истек")
                return False
                
            data = response.json()
            if not data.get('success'):
                error_code = data.get('code')
                error_msg = data.get('msg')
                self.logger.error(f"Ошибка API. Код: {error_code}, Сообщение: {error_msg}")
                self.logger.error(f"Full response: {data}")
                return False
                
            return True
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Ошибка при проверке статуса API: {str(e)}")
            return False
            
    def update_all_data(self):
        """
        Обновляет все данные
        """
        # Проверяем статус API перед запуском
        if not self.check_api_status():
            self.logger.error("Невозможно продолжить: проблема с API ключом")
            return False
            
        # Получаем текущую ставку финансирования
        self.get_funding_rate(type='current')
        self.get_funding_rate(type='day')
        
        # Получаем данные для BTC и ETH
        for symbol in ['BTC', 'ETH']:
            # Получаем данные для разных временных интервалов
            for interval in ['1h', '4h', '1d']:
                # Получаем OHLCV данные
                self.get_kline_data(f"{symbol}USDT", 'Binance', interval)
                
                # Получаем данные об открытом интересе
                self.get_open_interest_data(symbol, interval)
                self.get_open_interest_kline(f"{symbol}USDT", 'Binance', interval)
                
                # Получаем данные о ликвидациях
                self.get_liquidation_data(symbol, interval)
                self.get_historical_liquidations(f"{symbol}USDT", 'Binance', interval)
                
                # Получаем исторические ставки финансирования
                self.get_historical_funding_rate(symbol, 'USDT', interval)
                
                # Получаем данные о соотношении long/short позиций
                self.get_longshort_ratio(symbol, interval)
                self.get_longshort_position(f"{symbol}USDT", 'Binance', interval)
                
                # Получаем данные о long/short позициях разных типов
                for ls_type in ['longShortPerson', 'longShortPosition', 'longShortAccount']:
                    self.get_longshort_kline(f"{symbol}USDT", 'Binance', interval, ls_type)
        
        # Получаем данные индикаторов
        indicators = [
            'bitcoin-rainbow-v2',
            '1-year-hodl-wave',
            'hodl-waves',
            'mvrv-zscore',
            'relative-unrealized-prof',
            'bitcoin-price-prediction',
            'reserve-risk',
            'rhodl-ratio',
            'whale-shadows'
        ]
        
        for indicator in indicators:
            self.get_indicator_data(indicator)
            
        return True

    def _collect_paginated_data(self, data_method, filename_prefix, **kwargs):
        """
        Собирает данные с пагинацией по времени
        
        Args:
            data_method: Метод для сбора данных
            filename_prefix: Префикс для имени файла
            **kwargs: Параметры для метода
        """
        all_data = []
        current_end_time = int(datetime.now().timestamp() * 1000)
        start_time = int((datetime.now() - timedelta(days=365*3)).timestamp() * 1000)  # За 3 года
        
        while current_end_time > start_time:
            self.logger.info(f"Получаем данные до {datetime.fromtimestamp(current_end_time/1000)}")
            
            # Получаем порцию данных
            kwargs['end_time'] = current_end_time
            kwargs['size'] = 500
            
            df = data_method(**kwargs)
            if df is None or df.empty:
                break
                
            all_data.append(df)
            
            # Получаем самую раннюю временную метку из текущей порции
            min_timestamp = df['timestamp'].min()
            if pd.isna(min_timestamp) or min_timestamp.timestamp() * 1000 >= current_end_time:
                break
                
            # Обновляем end_time для следующей итерации
            current_end_time = int(min_timestamp.timestamp() * 1000)
            
        if all_data:
            # Объединяем все данные
            final_df = pd.concat(all_data)
            # Удаляем дубликаты
            final_df = final_df.drop_duplicates(subset=['timestamp'])
            # Сортируем по времени
            final_df = final_df.sort_values('timestamp')
            
            # Сохраняем объединенные данные
            filename = f"{filename_prefix}_{datetime.now().strftime('%Y%m%d')}_full.csv"
            filepath = os.path.join(self.data_dir, filename)
            final_df.to_csv(filepath, index=False)
            self.logger.info(f"Сохранено {len(final_df)} записей в {filepath}")
            
            return final_df
        return None

    def collect_historical_data(self, start_time=None):
        """
        Собирает исторические данные за весь доступный период
        
        Args:
            start_time (int): Начальное время в Unix timestamp (ms). 
                           Если None, берет данные за последние 3 года
        """
        self.logger.info("Начинаем сбор исторических данных...")
        
        # 1. K-line данные
        self.logger.info("Сбор K-line данных...")
        intervals = ['1h', '4h', '1d']
        for interval in intervals:
            self._collect_paginated_data(
                self.get_kline_data,
                os.path.join('klines', f'BTCUSDT_Binance_{interval}_SWAP'),
                symbol='BTCUSDT',
                exchange='Binance',
                interval=interval,
                product_type='SWAP'
            )
            
        # 2. Данные ордербука
        self.logger.info("Сбор данных ордербука...")
        rates = ['0.01', '0.05']
        for rate in rates:
            self._collect_paginated_data(
                self.get_orderbook_by_symbol,
                os.path.join('orderbook', f'BTCUSDT_Binance_1h_{rate}_SWAP'),
                symbol='BTCUSDT',
                exchange='Binance',
                rate=rate,
                product_type='SWAP',
                interval='1h'
            )
            
        # 3. Данные о позициях Long/Short
        self.logger.info("Сбор данных о позициях Long/Short...")
        ls_types = ['longShortPerson', 'longShortPosition', 'longShortAccount']
        for ls_type in ls_types:
            self._collect_paginated_data(
                self.get_longshort_kline,
                os.path.join('longshort', f'BTCUSDT_Binance_1h_{ls_type}'),
                symbol='BTCUSDT',
                exchange='Binance',
                interval='1h',
                ls_type=ls_type
            )
            
        # 4. Данные о ликвидациях
        self.logger.info("Сбор данных о ликвидациях...")
        self._collect_paginated_data(
            self.get_liquidations,
            os.path.join('liquidations', 'BTC_1h'),
            base_coin='BTC',
            interval='1h'
        )
        
        # 5. Данные о ставках финансирования
        self.logger.info("Сбор данных о ставках финансирования...")
        self._collect_paginated_data(
            self.get_historical_funding_rate,
            os.path.join('funding_rates', 'BTC_USDT'),
            base_coin='BTC',
            exchange_type='USDT'
        )
        
        # 6. Данные об открытом интересе
        self.logger.info("Сбор данных об открытом интересе...")
        self._collect_paginated_data(
            self.get_open_interest,
            os.path.join('open_interest', 'BTC_USD_1h'),
            base_coin='BTC',
            interval='1h',
            type='USD'
        )
        
        self.logger.info("Сбор исторических данных завершен")
        return True

    def get_orderbook_by_symbol(self, symbol='BTCUSDT', exchange='Binance', rate='0.01',
                              product_type='SWAP', interval='1h', size=500, end_time=None):
        """
        Получает разницу между ордерами на покупку и продажу для конкретной торговой пары

        Args:
            symbol (str): Торговая пара (например, 'BTCUSDT')
            exchange (str): Биржа (SWAP: Binance,Bybit,Okex,Huobi,Bitfinex; 
                          SPOT: Binance,Bybit,Okex,Bitfinex,Kraken,Coinbase)
            rate (str): Диапазон цен (0.0025, 0.005, 0.0075, 0.01, 0.03, 0.05, 0.1)
            product_type (str): Тип продукта (SWAP или SPOT)
            interval (str): Интервал (1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 8h, 1d)
            size (int): Размер выборки (максимум 500)
            end_time (int): Временная метка окончания (в миллисекундах)

        Returns:
            pandas.DataFrame: DataFrame с данными ордербука или None в случае ошибки
        """
        endpoint = 'orderBook/v2/bySymbol'
        
        # Если end_time не указан, используем текущее время
        if end_time is None:
            end_time = int(datetime.now().timestamp() * 1000)
            
        params = {
            'symbol': symbol,
            'exchange': exchange,
            'rate': rate,
            'productType': product_type,
            'interval': interval,
            'endTime': end_time,
            'size': min(size, 500)
        }
        
        data = self._make_request(endpoint, params)
        if data:
            # Преобразуем данные в DataFrame
            df = pd.DataFrame(data, columns=[
                'timestamp', 'bid_volume', 'bid_count', 
                'ask_volume', 'ask_count'
            ])
            
            # Преобразуем timestamp в datetime
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            # Добавляем дополнительные метрики
            df['volume_imbalance'] = df['bid_volume'] - df['ask_volume']
            df['count_imbalance'] = df['bid_count'] - df['ask_count']
            
            # Сохраняем данные в CSV
            filename = f"{symbol}_{exchange}_{interval}_{rate}_{product_type}_orderbook.csv"
            filepath = os.path.join(self.data_dir, 'orderbook', filename)
            df.to_csv(filepath, index=False)
            self.logger.info(f"Orderbook data saved to {filepath}")
            
            return df
            
        return None

    def get_orderbook_by_exchange(self, base_coin='BTC', exchanges='Binance', type='0.01',
                                product_type='SWAP', interval='1h', size=500, end_time=None):
        """
        Получает разницу ордербука по бирже

        Args:
            base_coin (str): Базовая монета (например, 'BTC')
            exchanges (str): Список бирж через запятую
                           SWAP: Binance,Bybit,OKX,Huobi,Bitfinex
                           SPOT: Binance,Bybit,OKX,Bitfinex,Kraken,Coinbase
            type (str): Диапазон цен (0.0025, 0.005, 0.0075, 0.01, 0.03, 0.05, 0.1)
            product_type (str): Тип продукта (SWAP или SPOT)
            interval (str): Интервал (1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 8h, 1d)
            size (int): Размер выборки (максимум 500)
            end_time (int): Временная метка окончания (в миллисекундах)

        Returns:
            pandas.DataFrame: DataFrame с данными ордербука или None в случае ошибки
        """
        endpoint = 'orderBook/v2/byExchange'
        
        # Если end_time не указан, используем текущее время
        if end_time is None:
            end_time = int(datetime.now().timestamp() * 1000)
            
        params = {
            'baseCoin': base_coin,
            'exchanges': exchanges,
            'type': type,
            'productType': product_type,
            'interval': interval,
            'endTime': end_time,
            'size': min(size, 500)
        }
        
        data = self._make_request(endpoint, params)
        if data:
            # Преобразуем данные в DataFrame
            df = pd.DataFrame(data, columns=[
                'timestamp', 'bid_volume', 'bid_count', 
                'ask_volume', 'ask_count'
            ])
            
            # Преобразуем timestamp в datetime
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            # Добавляем дополнительные метрики
            df['volume_imbalance'] = df['bid_volume'] - df['ask_volume']
            df['count_imbalance'] = df['bid_count'] - df['ask_count']
            
            # Сохраняем данные в CSV
            filename = f"{base_coin}_{exchanges}_{interval}_{type}_{product_type}_exchange_orderbook.csv"
            filepath = os.path.join(self.data_dir, 'orderbook', filename)
            df.to_csv(filepath, index=False)
            self.logger.info(f"Exchange orderbook data saved to {filepath}")
            
            return df
            
        return None

if __name__ == "__main__":
    collector = CoinArkCollector()
    collector.update_all_data()
