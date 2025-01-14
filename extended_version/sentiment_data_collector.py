import os
import logging
import requests
import pandas as pd
from datetime import datetime, timedelta
import psycopg2
from psycopg2.extras import execute_values

# Настройка подключения к базе данных
DB_NAME = "bitcoin_predictor"
DB_USER = "postgres"
DB_PASSWORD = "postgres"
DB_HOST = "localhost"
DB_PORT = "5432"

# Настройка логирования
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SentimentDataCollector:
    def __init__(self):
        """Инициализация коллектора данных о настроениях рынка"""
        # Подключение к базе данных
        self.conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )

    def __del__(self):
        """Закрытие соединения с базой данных"""
        if hasattr(self, 'conn'):
            self.conn.close()

    def save_to_db(self, df):
        """
        Сохранение данных в базу данных
        
        Args:
            df (pd.DataFrame): DataFrame с данными
        """
        try:
            # Подготовка данных
            data = [(index, row['value'], row['classification']) 
                   for index, row in df.iterrows()]
            
            # Вставка данных
            with self.conn.cursor() as cur:
                execute_values(cur,
                    """
                    INSERT INTO fear_and_greed_index (timestamp, value, classification)
                    VALUES %s
                    ON CONFLICT (timestamp) DO UPDATE 
                    SET value = EXCLUDED.value,
                        classification = EXCLUDED.classification
                    """,
                    data
                )
            self.conn.commit()
            logger.info(f"Saved {len(df)} records to database")
        except Exception as e:
            logger.error(f"Error saving to database: {str(e)}")
            self.conn.rollback()

    def get_latest_timestamp(self):
        """
        Получение последней временной метки из базы данных
        
        Returns:
            datetime: Последняя временная метка или None
        """
        try:
            with self.conn.cursor() as cur:
                cur.execute("SELECT MAX(timestamp) FROM fear_and_greed_index")
                result = cur.fetchone()
                return result[0] if result and result[0] else None
        except Exception as e:
            logger.error(f"Error getting latest timestamp: {str(e)}")
            return None

    def get_fear_and_greed_index(self, start_date=None):
        """Получение исторических данных индекса страха и жадности"""
        logger.info("Loading Fear and Greed Index data...")
        url = "https://api.alternative.me/fng/"
        params = {
            "limit": 0,  # Получаем все доступные данные
            "format": "json"
        }
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            # Преобразуем данные в DataFrame
            fng_data = pd.DataFrame(data['data'])
            fng_data['timestamp'] = pd.to_datetime(fng_data['timestamp'].astype(int), unit='s')
            fng_data['value'] = fng_data['value'].astype(float)
            fng_data['classification'] = fng_data['value_classification']
            
            # Устанавливаем индекс и сортируем
            fng_data.set_index('timestamp', inplace=True)
            fng_data = fng_data.sort_index()
            
            # Если start_date не указан, берем самую раннюю дату
            if start_date is None:
                start_date = fng_data.index.min()
            
            if isinstance(start_date, str):
                start_date = pd.to_datetime(start_date)
                
            end_date = pd.Timestamp.now()
            date_range = pd.date_range(start=start_date, end=end_date, freq='D')
            
            # Переиндексируем и заполняем пропуски
            fng_data = fng_data.reindex(date_range)
            fng_data = fng_data.ffill().bfill()
            
            return fng_data
            
        except Exception as e:
            logger.error(f"Error getting Fear and Greed Index: {str(e)}")
            return None

    def update_fear_and_greed_index(self):
        """Обновление индекса страха и жадности"""
        # Получаем последнюю дату из базы данных
        last_date = self.get_latest_timestamp()
        
        if last_date is not None:
            # Получаем последнюю дату и добавляем 1 день
            last_date = last_date + timedelta(days=1)
            logger.info(f"Fetching new data since {last_date}...")
        else:
            logger.info("No historical data found. Fetching all historical data...")
        
        # Получаем новые данные
        new_data = self.get_fear_and_greed_index(start_date=last_date)
        
        if new_data is not None:
            # Сохраняем данные в базу
            self.save_to_db(new_data)
            logger.info("Fear and Greed Index updated successfully")

def main():
    """Основная функция для запуска коллектора"""
    try:
        collector = SentimentDataCollector()
        collector.update_fear_and_greed_index()
    except Exception as e:
        logger.error(f"Error in main: {str(e)}")

if __name__ == "__main__":
    main()
