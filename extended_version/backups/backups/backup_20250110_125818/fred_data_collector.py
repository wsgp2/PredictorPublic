import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
import os
from typing import Dict, List, Optional, Tuple

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
            
            # Создаем DataFrame
            df = pd.DataFrame(data['observations'])
            if not df.empty:
                df['date'] = pd.to_datetime(df['date'])
                df['value'] = pd.to_numeric(df['value'], errors='coerce')
                df = df[['date', 'value']].rename(columns={'value': series_id})
                df.set_index('date', inplace=True)
            
            return df
            
        except Exception as e:
            logger.error(f"Ошибка при получении данных серии {series_id}: {str(e)}")
            return pd.DataFrame()

    def load_historical_data(self, filename: str) -> pd.DataFrame:
        """Загрузка исторических данных из файла"""
        try:
            filepath = os.path.join(self.data_dir, filename)
            if os.path.exists(filepath):
                df = pd.read_csv(filepath)
                df['date'] = pd.to_datetime(df['date'])
                df.set_index('date', inplace=True)
                return df
            return pd.DataFrame()
        except Exception as e:
            logger.error(f"Ошибка при загрузке исторических данных из {filename}: {str(e)}")
            return pd.DataFrame()

    def save_data(self, df: pd.DataFrame, filename: str):
        """Сохранение данных в файл"""
        try:
            filepath = os.path.join(self.data_dir, filename)
            df.to_csv(filepath)
            logger.info(f"Данные сохранены в {filepath}")
        except Exception as e:
            logger.error(f"Ошибка при сохранении данных в {filename}: {str(e)}")

    def update_series_data(self, series_id: str, force_full_update: bool = False) -> pd.DataFrame:
        """
        Обновление данных для конкретной серии
        
        Args:
            series_id: ID серии данных
            force_full_update: Принудительное обновление всех исторических данных
        """
        filename = f"{series_id}.csv"
        historical_df = self.load_historical_data(filename) if not force_full_update else pd.DataFrame()
        
        if historical_df.empty or force_full_update:
            logger.info(f"Загрузка полных исторических данных для {series_id}")
            new_df = self.get_series_data(series_id)
        else:
            last_date = historical_df.index.max()
            logger.info(f"Загрузка новых данных для {series_id} с {last_date}")
            new_df = self.get_series_data(series_id, start_date=last_date.strftime('%Y-%m-%d'))
        
        if not new_df.empty:
            # Объединяем старые и новые данные
            df = pd.concat([historical_df, new_df])
            df = df[~df.index.duplicated(keep='last')].sort_index()
            self.save_data(df, filename)
            return df
        return historical_df

    def update_all_series(self, force_full_update: bool = False):
        """
        Обновление всех серий данных
        
        Args:
            force_full_update: Принудительное обновление всех исторических данных
        """
        results = {}
        for series_id, config in self.series_config.items():
            logger.info(f"\nОбновление {config['name']} ({series_id})")
            df = self.update_series_data(series_id, force_full_update)
            if not df.empty:
                results[series_id] = {
                    'name': config['name'],
                    'frequency': config['frequency'],
                    'start_date': df.index.min(),
                    'end_date': df.index.max(),
                    'records': len(df)
                }
        
        # Выводим сводную информацию
        logger.info("\nСводка обновления данных:")
        for series_id, info in results.items():
            logger.info(f"{info['name']} ({series_id}):")
            logger.info(f"  Частота: {info['frequency']}")
            logger.info(f"  Период: с {info['start_date'].date()} по {info['end_date'].date()}")
            logger.info(f"  Количество записей: {info['records']}")

def main():
    api_key = 'bb08bba3969b795cb832f4c1eb721494'
    collector = FREDDataCollector(api_key)
    
    # При первом запуске или для полного обновления используйте force_full_update=True
    collector.update_all_series(force_full_update=True)

if __name__ == "__main__":
    main()
