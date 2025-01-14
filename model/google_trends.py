"""
Модуль для получения данных из Google Trends
"""

import pandas as pd
from pytrends.request import TrendReq
from datetime import datetime, timedelta
import time
from typing import Optional
from .logger import setup_logger

logger = setup_logger(__name__)

def get_google_trends():
    """Получение данных из Google Trends"""
    try:
        # Инициализация клиента
        pytrends = TrendReq(hl='en-US', tz=360)
        
        # Получаем текущую дату
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365)  # Данные за последний год
        
        # Формируем временной период
        timeframe = f'{start_date.strftime("%Y-%m-%d")} {end_date.strftime("%Y-%m-%d")}'
        
        # Ключевые слова для поиска
        kw_list = ['buy bitcoin', 'sell bitcoin']
        
        # Получаем данные
        pytrends.build_payload(kw_list, timeframe=timeframe)
        trends_df = pytrends.interest_over_time()
        
        if trends_df.empty:
            return None
            
        # Переименовываем колонки
        trends_df = trends_df.rename(columns={
            'buy bitcoin': 'buy_trend',
            'sell bitcoin': 'sell_trend'
        })
        
        # Удаляем колонку isPartial
        trends_df = trends_df.drop('isPartial', axis=1)
        
        # Заполняем пропущенные значения
        trends_df = trends_df.resample('D').ffill().bfill()
        
        return trends_df
        
    except Exception as e:
        logger.error(f"Ошибка при получении данных из Google Trends: {str(e)}")
        return None

def normalize_trends(df):
    """Нормализация данных трендов"""
    for col in ['buy_trend', 'sell_trend']:
        if col in df.columns:
            df[col] = (df[col] - df[col].min()) / (df[col].max() - df[col].min())
    return df
