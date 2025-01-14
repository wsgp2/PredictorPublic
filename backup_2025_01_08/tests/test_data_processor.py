"""
Тесты для модуля обработки данных
"""

import unittest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from data_processor import DataProcessor

class TestDataProcessor(unittest.TestCase):
    def setUp(self):
        """Подготовка данных для тестов"""
        self.processor = DataProcessor()
        
        # Создаем тестовые данные
        dates = pd.date_range(start='2025-01-01', end='2025-01-07', freq='D')
        
        # Ценовые данные
        self.price_data = pd.DataFrame({
            'price': [45000, 46000, 47000, 46500, 46800, 47200, 47500]
        }, index=dates)
        
        # Данные о настроениях
        self.sentiment_data = pd.DataFrame({
            'Reddit_Sentiment_Mean': [0.2, 0.3, np.nan, 0.1, 0.4, 0.2, 0.3],
            'Reddit_Activity_Score': [0.5, 0.6, 0.7, np.nan, 0.8, 0.9, 0.7]
        }, index=dates)
        
        # Технические индикаторы
        self.technical_data = pd.DataFrame({
            'RSI': [60, 65, np.nan, 55, 58, 62, 65],
            'MACD': [100, 110, 120, np.nan, 130, 125, 128]
        }, index=dates)
        
    def test_merge_features(self):
        """Тест объединения признаков"""
        merged = self.processor.merge_features(
            self.price_data,
            self.sentiment_data,
            self.technical_data
        )
        
        # Проверяем, что все колонки присутствуют
        expected_columns = ['price', 'Reddit_Sentiment_Mean', 
                          'Reddit_Activity_Score', 'RSI', 'MACD']
        self.assertEqual(set(merged.columns), set(expected_columns))
        
        # Проверяем, что пропущенные значения обработаны
        self.assertFalse(merged.isnull().any().any())
        
    def test_prepare_sequences(self):
        """Тест подготовки последовательностей"""
        data = pd.DataFrame({
            'price': [100, 101, 102, 103, 104],
            'feature1': [1, 2, 3, 4, 5]
        })
        
        X, y = self.processor.prepare_sequences(data, sequence_length=2)
        
        # Проверяем размерности
        self.assertEqual(X.shape, (3, 2, 2))  # 3 последовательности, длина 2, 2 признака
        self.assertEqual(y.shape, (3,))  # 3 целевых значения
        
        # Проверяем значения
        expected_y = np.array([102, 103, 104])
        np.testing.assert_array_equal(y, expected_y)
        
    def test_split_data(self):
        """Тест разделения данных"""
        X = np.array(range(100)).reshape(50, 2)
        y = np.array(range(50))
        
        X_train, X_val, X_test, y_train, y_val, y_test = \
            self.processor.split_data(X, y, train_ratio=0.6, val_ratio=0.2)
            
        # Проверяем размеры выборок
        self.assertEqual(len(X_train), 30)  # 60% данных
        self.assertEqual(len(X_val), 10)    # 20% данных
        self.assertEqual(len(X_test), 10)   # 20% данных

if __name__ == '__main__':
    unittest.main()
