import unittest
from datetime import datetime, timedelta
import pandas as pd
import sys
import os

# Добавляем путь к корневой директории проекта
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from collectors.google_trends_collector import GoogleTrendsCollector

class TestGoogleTrendsCollector(unittest.TestCase):
    def setUp(self):
        """Инициализация перед каждым тестом"""
        self.collector = GoogleTrendsCollector()
        self.test_keywords = ['bitcoin', 'btc', 'crypto']
        self.end_date = datetime.now()
        self.start_date = self.end_date - timedelta(days=7)

    def test_initialization(self):
        """Тест инициализации коллектора"""
        self.assertIsNotNone(self.collector)
        self.assertTrue(os.path.exists(self.collector.data_dir))

    def test_get_trends_data(self):
        """Тест получения данных трендов"""
        df = self.collector.get_trends_data(
            keywords=self.test_keywords,
            start_date=self.start_date,
            end_date=self.end_date
        )
        
        # Проверяем структуру данных
        self.assertIsInstance(df, pd.DataFrame)
        self.assertIn('timestamp', df.columns)
        for keyword in self.test_keywords:
            self.assertIn(keyword, df.columns)

    def test_data_freshness(self):
        """Тест свежести данных"""
        df = self.collector.get_trends_data(
            keywords=self.test_keywords,
            start_date=self.start_date,
            end_date=self.end_date
        )
        
        latest_date = pd.to_datetime(df['timestamp']).max()
        self.assertGreaterEqual(
            self.end_date.timestamp(),
            latest_date.timestamp()
        )

    def test_data_completeness(self):
        """Тест полноты данных"""
        df = self.collector.get_trends_data(
            keywords=self.test_keywords,
            start_date=self.start_date,
            end_date=self.end_date
        )
        
        # Проверяем, что нет пропущенных значений
        self.assertFalse(df.isnull().any().any())
        
        # Проверяем, что все значения в допустимом диапазоне (0-100)
        for keyword in self.test_keywords:
            self.assertTrue((df[keyword] >= 0).all())
            self.assertTrue((df[keyword] <= 100).all())

    def test_error_handling(self):
        """Тест обработки ошибок"""
        # Тест с некорректными датами
        with self.assertRaises(ValueError):
            self.collector.get_trends_data(
                keywords=self.test_keywords,
                start_date=self.end_date,
                end_date=self.start_date
            )
        
        # Тест с пустым списком ключевых слов
        with self.assertRaises(ValueError):
            self.collector.get_trends_data(
                keywords=[],
                start_date=self.start_date,
                end_date=self.end_date
            )

    def test_save_and_load(self):
        """Тест сохранения и загрузки данных"""
        # Получаем и сохраняем данные
        df_original = self.collector.get_trends_data(
            keywords=self.test_keywords,
            start_date=self.start_date,
            end_date=self.end_date
        )
        
        filename = f"trends_data_{datetime.now().strftime('%Y%m%d')}.csv"
        self.collector.save_data(df_original, filename)
        
        # Загружаем сохраненные данные
        df_loaded = self.collector.load_historical_data(filename)
        
        # Проверяем идентичность данных
        pd.testing.assert_frame_equal(df_original, df_loaded)

if __name__ == '__main__':
    unittest.main()
