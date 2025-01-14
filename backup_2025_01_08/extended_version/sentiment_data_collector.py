import os
import logging
import requests
import pandas as pd
from datetime import datetime, timedelta

# Настройка логирования
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SentimentDataCollector:
    def __init__(self):
        """Инициализация коллектора данных о настроениях рынка"""
        self.data_dir = 'data/sentiment'
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)

    def save_data(self, df, filename):
        """Сохранение DataFrame в CSV файл"""
        filepath = os.path.join(self.data_dir, filename)
        df.to_csv(filepath)
        logger.info(f"Data saved to {filename}")

    def load_data(self, filename):
        """Загрузка данных из CSV файла"""
        filepath = os.path.join(self.data_dir, filename)
        if os.path.exists(filepath):
            return pd.read_csv(filepath, index_col=0, parse_dates=True)
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
        filename = 'fear_and_greed_index.csv'
        
        # Загружаем существующие данные
        existing_data = self.load_data(filename)
        
        if existing_data is not None:
            # Получаем последнюю дату и добавляем 1 день
            last_date = pd.to_datetime(existing_data.index.max()) + timedelta(days=1)
            logger.info(f"Fetching {(pd.Timestamp.now() - last_date).days} days of new data for Fear and Greed Index...")
        else:
            last_date = None
            logger.info("No historical data found for Fear and Greed Index. Fetching all historical data...")
        
        # Получаем новые данные
        new_data = self.get_fear_and_greed_index(start_date=last_date)
        
        if new_data is not None:
            if existing_data is not None:
                # Объединяем старые и новые данные
                updated_data = pd.concat([existing_data, new_data[new_data.index > existing_data.index.max()]])
            else:
                updated_data = new_data
            
            # Сохраняем обновленные данные
            self.save_data(updated_data, filename)
            logger.info(f"Fear and Greed Index records: {len(updated_data)}")
            return updated_data
        
        return existing_data
