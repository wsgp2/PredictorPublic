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

class BlockchainAPITester:
    def __init__(self):
        self.base_url = 'https://api.blockchain.info/charts'
        self.metrics = {
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
        
    def create_test_tables(self, conn):
        """Создание тестовых таблиц для каждой метрики"""
        cur = conn.cursor()
        
        for metric_name in self.metrics.keys():
            table_name = f'test_{metric_name}'
            cur.execute(f"""
                CREATE TABLE IF NOT EXISTS {table_name} (
                    timestamp TIMESTAMP PRIMARY KEY,
                    value FLOAT
                )
            """)
        
        conn.commit()
        cur.close()
        
    def fetch_historical_data(self, metric, timespan='all'):
        """Получение исторических данных для метрики"""
        url = f'{self.base_url}/{self.metrics[metric]}'
        params = {
            'timespan': timespan,
            'format': 'json',
            'sampled': 'false'  # Получаем все точки данных
        }
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            if 'values' in data:
                df = pd.DataFrame(data['values'])
                df['timestamp'] = pd.to_datetime(df['x'], unit='s')
                df = df.rename(columns={'y': 'value'})
                df = df[['timestamp', 'value']]
                return df
            
            return None
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка при получении данных для {metric}: {str(e)}")
            return None
            
    def save_to_database(self, conn, metric_name, df):
        """Сохранение данных в тестовую таблицу"""
        if df is None or df.empty:
            return 0
            
        cur = conn.cursor()
        table_name = f'test_{metric_name}'
        
        inserted = 0
        for _, row in df.iterrows():
            try:
                cur.execute(f"""
                    INSERT INTO {table_name} (timestamp, value)
                    VALUES (%s, %s)
                    ON CONFLICT (timestamp) DO NOTHING
                """, (row['timestamp'], row['value']))
                inserted += 1
            except Exception as e:
                logger.error(f"Ошибка при сохранении записи {row['timestamp']}: {str(e)}")
                continue
        
        conn.commit()
        cur.close()
        return inserted

    def analyze_data(self, conn, metric_name):
        """Анализ собранных данных"""
        cur = conn.cursor()
        table_name = f'test_{metric_name}'
        
        cur.execute(f"""
            SELECT 
                COUNT(*) as total_records,
                MIN(timestamp) as first_record,
                MAX(timestamp) as last_record,
                AVG(value) as avg_value
            FROM {table_name}
        """)
        
        stats = cur.fetchone()
        cur.close()
        
        logger.info(f"\nАнализ данных для {metric_name}:")
        logger.info(f"Всего записей: {stats[0]}")
        logger.info(f"Период: с {stats[1]} по {stats[2]}")
        logger.info(f"Среднее значение: {stats[3]:.2f}")
        
        return stats

def main():
    try:
        logger.info("Начало тестирования Blockchain.com API...")
        tester = BlockchainAPITester()
        conn = psycopg2.connect(**DB_CONFIG)
        
        # Создаем тестовые таблицы
        tester.create_test_tables(conn)
        
        # Собираем данные по каждой метрике
        for metric_name in tester.metrics.keys():
            logger.info(f"\nСбор данных для метрики: {metric_name}")
            
            # Получаем исторические данные
            df = tester.fetch_historical_data(metric_name)
            
            if df is not None:
                # Сохраняем в базу
                inserted = tester.save_to_database(conn, metric_name, df)
                logger.info(f"Сохранено {inserted} новых записей")
                
                # Анализируем результаты
                tester.analyze_data(conn, metric_name)
            else:
                logger.error(f"Не удалось получить данные для {metric_name}")
            
            # Небольшая пауза между запросами
            time.sleep(1)
        
        logger.info("\nТестирование завершено")
        
    except Exception as e:
        logger.error(f"Ошибка при выполнении теста: {str(e)}")
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    main()
