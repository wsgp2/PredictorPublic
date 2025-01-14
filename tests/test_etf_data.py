"""
Тестирование сбора данных ETF
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
from institutional_data import ETFDataCollector
import pandas as pd

def test_etf_data_collection():
    # Инициализация коллектора
    collector = ETFDataCollector()
    
    # Тестовый период (последние 30 дней)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    print(f"\nТестирование сбора данных ETF за период: {start_date.date()} - {end_date.date()}")
    
    # Получение данных
    data = collector.get_etf_data(start_date, end_date)
    
    # Проверка результатов
    print("\nПолученные данные:")
    print(f"Количество дней: {len(data)}")
    print("\nДоступные метрики:")
    for column in data.columns:
        print(f"- {column}")
    
    print("\nПример данных:")
    print(data.head())
    
    # Проверка на пропущенные значения
    nulls = data.isnull().sum()
    if nulls.any():
        print("\nПропущенные значения:")
        print(nulls[nulls > 0])
    else:
        print("\nПропущенные значения отсутствуют")

if __name__ == "__main__":
    test_etf_data_collection()
