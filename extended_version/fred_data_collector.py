import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
import os
from typing import Dict, List, Optional, Tuple
import psycopg2
from psycopg2.extras import execute_batch

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class FREDDataCollector:
    """Коллектор данных из FRED API с поддержкой исторических данных и инкрементальных обновлений"""
    
    def __init__(self, api_key: str):
        """
        Инициализация коллектора
        
        Args:
            api_key: FRED API ключ
        """
        self.api_key = api_key
        self.base_url = "https://api.stlouisfed.org/fred"
        self.data_dir = 'data/fred'
        
        # Создаем директорию для данных если её нет
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
            
        # Подключение к базе данных
        self.conn = psycopg2.connect(
            dbname='bitcoin_predictor',
            user='postgres',
            password='postgres',
            host='localhost',
            port='5432'
        )
        self.cur = self.conn.cursor()
        
        # Определяем все серии данных которые будем собирать
        self.series_config = {
            # Инфляционные показатели
            'CPIAUCSL': {'name': 'Consumer Price Index', 'frequency': 'Monthly'},
            'CPILFESL': {'name': 'Core CPI', 'frequency': 'Monthly'},
            'PPIACO': {'name': 'Producer Price Index', 'frequency': 'Monthly'},
            'PCE': {'name': 'Personal Consumption Expenditures', 'frequency': 'Monthly'},
            'PCEPILFE': {'name': 'Core PCE Price Index', 'frequency': 'Monthly'},
            
            # Денежная масса
            'M1SL': {'name': 'M1 Money Supply', 'frequency': 'Monthly'},
            'M2SL': {'name': 'M2 Money Supply', 'frequency': 'Monthly'},
            'M2V': {'name': 'M2 Velocity', 'frequency': 'Quarterly'},
            'BOGMBASE': {'name': 'Monetary Base', 'frequency': 'Monthly'},
            
            # Процентные ставки
            'FEDFUNDS': {'name': 'Federal Funds Rate', 'frequency': 'Monthly'},
            'DGS10': {'name': '10-Year Treasury Rate', 'frequency': 'Daily'},
            'DGS2': {'name': '2-Year Treasury Rate', 'frequency': 'Daily'},
            'T10Y2Y': {'name': '10-Year Treasury Minus 2-Year Treasury', 'frequency': 'Daily'},
            'MORTGAGE30US': {'name': '30-Year Fixed Rate Mortgage', 'frequency': 'Weekly'},
            
            # Экономическая активность
            'GDPC1': {'name': 'Real GDP', 'frequency': 'Quarterly'},
            'INDPRO': {'name': 'Industrial Production Index', 'frequency': 'Monthly'},
            'UNRATE': {'name': 'Unemployment Rate', 'frequency': 'Monthly'},
            'PAYEMS': {'name': 'Total Nonfarm Payrolls', 'frequency': 'Monthly'},
            'TCU': {'name': 'Capacity Utilization', 'frequency': 'Monthly'},
            
            # Индексы доллара и валюты
            'DTWEXBGS': {'name': 'Trade Weighted U.S. Dollar Index', 'frequency': 'Daily'},
            'DEXUSEU': {'name': 'USD/EUR Exchange Rate', 'frequency': 'Daily'},
            'DEXCHUS': {'name': 'USD/CNY Exchange Rate', 'frequency': 'Daily'},
            
            # Рыночные индикаторы
            'SP500': {'name': 'S&P 500', 'frequency': 'Daily'},
            'VIXCLS': {'name': 'VIX', 'frequency': 'Daily'},
            'GFDEBTN': {'name': 'Federal Debt', 'frequency': 'Quarterly'},
            'BAMLH0A0HYM2': {'name': 'ICE BofA High Yield Index', 'frequency': 'Daily'},
            
            # Индикаторы настроений
            'UMCSENT': {'name': 'Consumer Sentiment', 'frequency': 'Monthly'},
            'CSCICP03USM665S': {'name': 'Consumer Confidence', 'frequency': 'Monthly'}
        }

    def __del__(self):
        """Закрытие соединения с базой данных при уничтожении объекта"""
        if hasattr(self, 'cur') and self.cur:
            self.cur.close()
        if hasattr(self, 'conn') and self.conn:
            self.conn.close()
            
    def get_series_info(self, series_id: str) -> dict:
        """Получение информации о серии данных"""
        try:
            response = requests.get(
                f"{self.base_url}/series",
                params={
                    'series_id': series_id,
                    'api_key': self.api_key,
                    'file_type': 'json'
                }
            )
            response.raise_for_status()
            return response.json()['seriess'][0]
        except Exception as e:
            logger.error(f"Ошибка при получении информации о серии {series_id}: {str(e)}")
            return None

    def get_series_data(self, series_id: str, start_date: Optional[str] = None, end_date: Optional[str] = None) -> pd.DataFrame:
        """
        Получение данных серии за указанный период
        
        Args:
            series_id: ID серии данных
            start_date: Начальная дата в формате YYYY-MM-DD
            end_date: Конечная дата в формате YYYY-MM-DD
        """
        try:
            params = {
                'series_id': series_id,
                'api_key': self.api_key,
                'file_type': 'json'
            }
            
            if start_date:
                params['observation_start'] = start_date
            if end_date:
                params['observation_end'] = end_date
                
            response = requests.get(
                f"{self.base_url}/series/observations",
                params=params
            )
            response.raise_for_status()
            
            data = response.json()
            if 'observations' in data:
                df = pd.DataFrame(data['observations'])
                df['date'] = pd.to_datetime(df['date'])
                df = df[['date', 'value']]  # Оставляем только нужные колонки
                df.set_index('date', inplace=True)
                return df
                
            return pd.DataFrame()
            
        except Exception as e:
            logger.error(f"Ошибка при получении данных серии {series_id}: {str(e)}")
            return pd.DataFrame()

    def save_to_database(self, df: pd.DataFrame, indicator_code: str):
        """Сохранение данных в базу данных"""
        try:
            # Подготовка данных для вставки
            data = []
            for idx, row in df.iterrows():
                # Преобразуем значение в float, если возможно
                try:
                    value = float(row['value']) if not pd.isna(row['value']) and row['value'] != '.' else None
                except (ValueError, TypeError):
                    value = None
                    
                data.append((
                    idx,  # timestamp (уже datetime из индекса)
                    indicator_code,
                    value
                ))
            
            # SQL для вставки данных
            sql = """
                INSERT INTO fred_economic_data 
                (timestamp, indicator_code, value)
                VALUES (%s, %s, %s)
                ON CONFLICT (timestamp, indicator_code) DO UPDATE SET
                    value = EXCLUDED.value;
            """
            
            # Пакетная вставка данных
            execute_batch(self.cur, sql, data, page_size=1000)
            self.conn.commit()
            
            logger.info(f"Saved {len(data)} records to database for {indicator_code}")
            
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Error saving data to database for {indicator_code}: {str(e)}")

    def get_latest_from_database(self, indicator_code: str) -> Optional[datetime]:
        """Получение последней временной метки из базы данных"""
        try:
            self.cur.execute("""
                SELECT MAX(timestamp)
                FROM fred_economic_data
                WHERE indicator_code = %s;
            """, (indicator_code,))
            result = self.cur.fetchone()
            return result[0] if result and result[0] else None
        except Exception as e:
            logger.error(f"Error getting latest timestamp for {indicator_code}: {str(e)}")
            return None

    def collect_series_data(self, series_id: str) -> None:
        """Сбор данных для конкретной серии"""
        try:
            # Получаем информацию о серии
            series_info = self.get_series_info(series_id)
            if not series_info:
                return
                
            # Получаем последнюю дату из базы данных
            latest_timestamp = self.get_latest_from_database(series_id)
            
            # Определяем период сбора данных
            if latest_timestamp:
                start_date = (latest_timestamp + timedelta(days=1)).strftime('%Y-%m-%d')
                if datetime.strptime(start_date, '%Y-%m-%d') >= datetime.now():
                    logger.info(f"{series_id}: Already up to date")
                    return
            else:
                # Если данных нет, берем с 2010 года
                start_date = '2010-01-01'
                
            end_date = datetime.now().strftime('%Y-%m-%d')
            
            # Получаем данные
            df = self.get_series_data(series_id, start_date, end_date)
            if df is not None and not df.empty:
                # Сохраняем в базу данных
                self.save_to_database(df, series_id)
                
                logger.info(f"{series_id} ({self.series_config[series_id]['name']}): ✅ {len(df)} records from {df.index[0].strftime('%Y-%m-%d')} to {df.index[-1].strftime('%Y-%m-%d')}")
            else:
                logger.warning(f"{series_id}: No new data available")
                
        except Exception as e:
            logger.error(f"Error collecting data for {series_id}: {str(e)}")

    def update_all_series(self):
        """
        Обновление всех серий данных
        """
        for series_id, config in self.series_config.items():
            logger.info(f"\nОбновление {config['name']} ({series_id})")
            self.collect_series_data(series_id)

def main():
    api_key = 'bb08bba3969b795cb832f4c1eb721494'
    collector = FREDDataCollector(api_key)
    
    # При первом запуске или для полного обновления используйте force_full_update=True
    collector.update_all_series()

if __name__ == "__main__":
    main()
