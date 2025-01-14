import requests
import pandas as pd
import logging
from datetime import datetime, timedelta
import psycopg2
from config.config import DB_CONFIG
import time

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class BlockchainDataCollector:
    def __init__(self):
        """Инициализация коллектора данных"""
        self.conn = psycopg2.connect(**DB_CONFIG)
        self.setup_tables()

    def setup_tables(self):
        """Создание необходимых таблиц"""
        metrics = [
            'trade_volume', 'miners_revenue', 'estimated_transaction_volume_usd',
            'market_price', 'total_bitcoins', 'market_cap', 'hash_rate',
            'difficulty', 'transaction_fees', 'n_unique_addresses', 'n_transactions'
        ]
        
        cur = self.conn.cursor()
        
        for metric in metrics:
            table_name = f"blockchain_{metric}"
            cur.execute(f"""
                CREATE TABLE IF NOT EXISTS {table_name} (
                    timestamp TIMESTAMP PRIMARY KEY,
                    value FLOAT NOT NULL
                )
            """)
        
        self.conn.commit()
        cur.close()

    def get_blockchain_data(self, endpoint, timespan='all'):
        """Получение данных с blockchain.info API"""
        base_url = 'https://api.blockchain.info/charts'
        
        # Маппинг эндпоинтов на новые имена
        endpoint_mapping = {
            'trade_volume': 'trade-volume',
            'miners_revenue': 'miners-revenue',
            'estimated_transaction_volume_usd': 'estimated-transaction-volume-usd',
            'market_price': 'market-price',
            'total_bitcoins': 'total-bitcoins',
            'market_cap': 'market-cap',
            'hash_rate': 'hash-rate',
            'difficulty': 'difficulty',
            'transaction_fees': 'transaction-fees',
            'n_unique_addresses': 'n-unique-addresses',
            'n_transactions': 'n-transactions'
        }
        
        # Получаем правильное имя эндпоинта
        api_endpoint = endpoint_mapping.get(endpoint, endpoint)
        url = f'{base_url}/{api_endpoint}'
        
        params = {
            'timespan': timespan,
            'format': 'json',
            'cors': 'true',
            'sampled': 'false'
        }
        
        try:
            # Добавляем заголовки для API
            headers = {
                'Accept': 'application/json',
                'User-Agent': 'Mozilla/5.0'
            }
            
            response = requests.get(url, params=params, headers=headers)
            response.raise_for_status()
            
            # Выводим URL для отладки
            logger.debug(f"API URL: {response.url}")
            
            data = response.json()
            
            if 'values' in data:
                df = pd.DataFrame(data['values'])
                df['timestamp'] = pd.to_datetime(df['x'], unit='s')
                df['value'] = df['y']
                return df[['timestamp', 'value']]
            
            return None
        except Exception as e:
            logger.error(f"Error getting data for {endpoint}: {str(e)}")
            if hasattr(response, 'text'):
                logger.error(f"Response text: {response.text[:200]}")  # Показываем первые 200 символов ответа
            return None

    def fill_gaps(self, df, metric_name):
        """Заполнение пропусков в данных"""
        if df is None or df.empty:
            return df
            
        # Создаем полный диапазон дат с шагом 8 часов
        full_range = pd.date_range(start=df['timestamp'].min(),
                                 end=df['timestamp'].max(),
                                 freq='8H')
        
        # Переиндексируем DataFrame
        df.set_index('timestamp', inplace=True)
        df = df.reindex(full_range)
        
        # Для метрик, которые должны монотонно возрастать
        monotonic_metrics = ['total_bitcoins', 'market_cap']
        if metric_name in monotonic_metrics:
            df['value'] = df['value'].fillna(method='ffill')
        else:
            # Для остальных метрик используем интерполяцию
            df['value'] = df['value'].interpolate(method='time')
        
        df.reset_index(inplace=True)
        df.rename(columns={'index': 'timestamp'}, inplace=True)
        
        return df

    def update_metric(self, metric_name):
        """Обновление метрики с заполнением пропусков"""
        table_name = f"blockchain_{metric_name}"
        
        # Получаем текущие данные из базы
        cur = self.conn.cursor()
        cur.execute(f"SELECT timestamp, value FROM {table_name} ORDER BY timestamp")
        existing_data = pd.DataFrame(cur.fetchall(), columns=['timestamp', 'value'])
        
        # Получаем все исторические данные
        logger.info(f"Запрашиваем все исторические данные для {metric_name}")
        new_data = self.get_blockchain_data(metric_name)
        
        if new_data is not None:
            # Заполняем пропуски
            filled_data = self.fill_gaps(new_data, metric_name)
            
            if not filled_data.empty:
                # Удаляем старые данные
                cur.execute(f"DELETE FROM {table_name}")
                
                # Вставляем новые данные с заполненными пропусками
                records = [tuple(x) for x in filled_data.values]
                cur.executemany(
                    f"INSERT INTO {table_name} (timestamp, value) VALUES (%s, %s)",
                    records
                )
                
                self.conn.commit()
                logger.info(f"Обновлено {len(filled_data)} записей для {metric_name}")
                
                # Проверяем пропуски после заполнения
                self.check_data_gaps(filled_data, metric_name)
        
        cur.close()

    def check_data_gaps(self, df, metric_name):
        """Проверка пропусков в данных"""
        if df is None or df.empty:
            return
            
        # Проверяем интервалы между записями
        df = df.sort_values('timestamp')
        time_diff = df['timestamp'].diff()
        gaps = time_diff[time_diff > pd.Timedelta(hours=9)]  # Ищем пропуски больше 9 часов
        
        if not gaps.empty:
            logger.info(f"Проверка пропусков в данных {metric_name}:")
            for idx in gaps.index:
                gap_start = df['timestamp'][idx - 1]
                gap_end = df['timestamp'][idx]
                gap_duration = gap_end - gap_start
                logger.info(f"  Пропуск с {gap_start} по {gap_end} ({gap_duration})")

    def update_blockchain_metrics(self):
        """Обновление метрик из blockchain.info"""
        metrics = {
            'trade_volume': 'trade-volume',
            'miners_revenue': 'miners-revenue',
            'estimated_transaction_volume_usd': 'estimated-transaction-volume-usd',
            'market_price': 'market-price',
            'total_bitcoins': 'total-bitcoins',
            'market_cap': 'market-cap',
            'hash_rate': 'hash-rate',
            'difficulty': 'difficulty',
            'transaction_fees': 'transaction-fees',
            'n_unique_addresses': 'n-unique-addresses',
            'n_transactions': 'n-transactions'
        }
        
        for metric_name, endpoint in metrics.items():
            try:
                self.update_metric(metric_name)
            except Exception as e:
                logger.error(f"Ошибка при обновлении {metric_name}: {str(e)}")
                continue

    def close(self):
        """Закрытие соединения с базой данных"""
        if self.conn:
            self.conn.close()

def main():
    collector = BlockchainDataCollector()
    try:
        collector.update_blockchain_metrics()
    finally:
        collector.close()

if __name__ == "__main__":
    main()
