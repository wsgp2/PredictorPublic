"""
Тестирование анализа балансов крупных холдеров
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
from institutional_data import WhaleAnalyzer
import pandas as pd

def test_whale_metrics():
    # Инициализация анализатора
    analyzer = WhaleAnalyzer()
    
    # Тестовый период (последние 30 дней)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    print(f"\nТестирование анализа китов за период: {start_date.date()} - {end_date.date()}")
    
    # Получение метрик
    metrics = analyzer.get_whale_metrics(start_date, end_date)
    
    if not metrics.empty:
        print("\nДоступные метрики:")
        for column in metrics.columns:
            print(f"- {column}")
            
        print("\nПример данных:")
        print(metrics.head())
        
        # Анализ статистик
        print("\nСтатистика по метрикам:")
        print(metrics.describe())
        
        # Проверка на пропущенные значения
        nulls = metrics.isnull().sum()
        if nulls.any():
            print("\nПропущенные значения:")
            print(nulls[nulls > 0])
        else:
            print("\nПропущенные значения отсутствуют")
            
        # Проверка корреляций
        print("\nКорреляции между метриками:")
        print(metrics.corr().round(2))
    else:
        print("Не удалось получить метрики китов")

if __name__ == "__main__":
    test_whale_metrics()
