"""
Тесты для ансамбля моделей
"""

import unittest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from model.ensemble import BitcoinEnsemble

class TestBitcoinEnsemble(unittest.TestCase):
    def setUp(self):
        """Подготовка данных для тестов"""
        self.ensemble = BitcoinEnsemble()
        
        # Создаем тестовые данные на 90 дней
        dates = pd.date_range(start='2025-01-01', end='2025-04-01', freq='D')
        
        # Генерируем 20 признаков
        features = {
            'price': np.random.normal(45000, 1000, len(dates)),
            'volume': np.random.normal(1000000, 100000, len(dates)),
            'sentiment': np.random.normal(0.2, 0.1, len(dates)),
            'ma_5': np.random.normal(45000, 500, len(dates)),
            'ma_10': np.random.normal(45000, 400, len(dates)),
            'ma_20': np.random.normal(45000, 300, len(dates)),
            'rsi': np.random.uniform(30, 70, len(dates)),
            'macd': np.random.normal(0, 100, len(dates)),
            'macd_signal': np.random.normal(0, 90, len(dates)),
            'macd_hist': np.random.normal(0, 10, len(dates)),
            'bb_upper': np.random.normal(46000, 200, len(dates)),
            'bb_middle': np.random.normal(45000, 100, len(dates)),
            'bb_lower': np.random.normal(44000, 200, len(dates)),
            'stoch_k': np.random.uniform(20, 80, len(dates)),
            'stoch_d': np.random.uniform(20, 80, len(dates)),
            'adx': np.random.uniform(15, 45, len(dates)),
            'cci': np.random.normal(0, 100, len(dates)),
            'mfi': np.random.uniform(30, 70, len(dates)),
            'obv': np.random.normal(1000000, 100000, len(dates)),
            'vwap': np.random.normal(45000, 500, len(dates))
        }
        
        self.test_data = pd.DataFrame(features, index=dates)
        
    def test_analyze_market_state(self):
        """Тест анализа состояния рынка"""
        # Создаем данные для разных состояний рынка
        
        # Волатильный рынок (стандартное отклонение > 0.2)
        volatile_data = self.test_data.copy()
        # Симулируем высокую волатильность в предсказаниях тренда
        def mock_volatile_predict(data):
            return np.random.normal(0, 0.3, 7)  # std > 0.2
        self.ensemble.trend_model.predict = mock_volatile_predict
        state = self.ensemble.analyze_market_state(volatile_data)
        self.assertEqual(state, 'volatile')
        
        # Бычий рынок (среднее > 0.1)
        bull_data = self.test_data.copy()
        def mock_bull_predict(data):
            return np.array([0.15] * 7)  # Устойчивый положительный тренд
        self.ensemble.trend_model.predict = mock_bull_predict
        state = self.ensemble.analyze_market_state(bull_data)
        self.assertEqual(state, 'bull')
        
        # Медвежий рынок (среднее < -0.1)
        bear_data = self.test_data.copy()
        def mock_bear_predict(data):
            return np.array([-0.15] * 7)  # Устойчивый отрицательный тренд
        self.ensemble.trend_model.predict = mock_bear_predict
        state = self.ensemble.analyze_market_state(bear_data)
        self.assertEqual(state, 'bear')
        
        # Боковой рынок (-0.1 <= среднее <= 0.1)
        sideways_data = self.test_data.copy()
        def mock_sideways_predict(data):
            return np.array([0.05] * 7)  # Слабый тренд
        self.ensemble.trend_model.predict = mock_sideways_predict
        state = self.ensemble.analyze_market_state(sideways_data)
        self.assertEqual(state, 'sideways')
        
    def test_adjust_weights(self):
        """Тест корректировки весов"""
        # Проверяем корректировку весов для разных состояний
        self.ensemble.adjust_weights('volatile')
        self.assertEqual(self.ensemble.current_weights['short_term'], 0.5)
        
        self.ensemble.adjust_weights('bull')
        self.assertEqual(self.ensemble.current_weights['trend'], 0.4)
        
        self.ensemble.adjust_weights('sideways')
        self.assertEqual(self.ensemble.current_weights, self.ensemble.default_weights)
        
    def test_predict(self):
        """Тест предсказания"""
        # Мокаем предсказания моделей
        def mock_short_term_predict(data):
            return np.array([45000] * 7)
        self.ensemble.short_term_model.predict = mock_short_term_predict
        
        def mock_medium_term_predict(data):
            return np.array([46000] * 7)
        self.ensemble.medium_term_model.predict = mock_medium_term_predict
        
        def mock_trend_predict(data):
            return np.array([0.05] * 7)  # Слабый положительный тренд
        self.ensemble.trend_model.predict = mock_trend_predict
        
        # Тест предсказания с интервалами
        result = self.ensemble.predict(self.test_data, days=7, with_intervals=True)
        
        self.assertIn('prediction', result)
        self.assertIn('lower_bound', result)
        self.assertIn('upper_bound', result)
        
        # Проверяем, что нижняя граница меньше предсказания
        self.assertTrue(np.all(result['lower_bound'] <= result['prediction']))
        
        # Проверяем, что верхняя граница больше предсказания
        self.assertTrue(np.all(result['prediction'] <= result['upper_bound']))
        
        # Проверяем размерность предсказаний
        self.assertEqual(len(result['prediction']), 7)
        self.assertEqual(len(result['lower_bound']), 7)
        self.assertEqual(len(result['upper_bound']), 7)
        
    def test_train(self):
        """Тест обучения"""
        # Разделяем данные на выборки
        train_size = int(len(self.test_data) * 0.6)
        val_size = int(len(self.test_data) * 0.2)
        
        train_data = self.test_data[:train_size]
        val_data = self.test_data[train_size:train_size + val_size]
        test_data = self.test_data[train_size + val_size:]
        
        # Обучаем модели
        metrics = self.ensemble.train(train_data, val_data, test_data)
        
        # Проверяем, что получили метрики для каждой модели
        self.assertIn('short_term', metrics)
        self.assertIn('medium_term', metrics)
        self.assertIn('trend', metrics)

if __name__ == '__main__':
    unittest.main()
