"""
Тестирование сбора институциональных метрик
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
from institutional_data import InstitutionalMetricsCollector
import pandas as pd

def test_institutional_metrics():
    # Инициализация коллектора
    collector = InstitutionalMetricsCollector()
    
    # Тестовый период (последние 30 дней)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    print(f"\nТестирование сбора институциональных метрик за период: {start_date.date()} - {end_date.date()}")
    
    # Получение данных фьючерсов
    print("\nПолучение данных фьючерсов CME...")
    futures_data = collector.get_cme_data(start_date, end_date)
    
    if not futures_data.empty:
        print("\nМетрики фьючерсов:")
        for column in futures_data.columns:
            print(f"- {column}")
        print("\nПример данных фьючерсов:")
        print(futures_data.head())
    else:
        print("Не удалось получить данные фьючерсов")
    
    # Получение всех институциональных метрик
    print("\nПолучение всех институциональных метрик...")
    metrics = collector.get_institutional_metrics(start_date, end_date)
    
    if not metrics.empty:
        print("\nВсе доступные метрики:")
        for column in metrics.columns:
            print(f"- {column}")
        print("\nПример данных:")
        print(metrics.head())
        
        # Проверка на пропущенные значения
        nulls = metrics.isnull().sum()
        if nulls.any():
            print("\nПропущенные значения:")
            print(nulls[nulls > 0])
        else:
            print("\nПропущенные значения отсутствуют")
    else:
        print("Не удалось получить институциональные метрики")

if __name__ == "__main__":
    test_institutional_metrics()
