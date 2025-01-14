"""
Ансамбль моделей для предсказания цены Bitcoin
"""

import numpy as np
import pandas as pd
import os
from typing import Dict, List, Optional, Tuple
from .short_term import ShortTermLSTM
from .medium_term import MediumTermLSTM
from .trend_model import TrendLSTM
from .logger import setup_logger

logger = setup_logger(__name__)

class BitcoinEnsemble:
    def __init__(self):
        """
        Инициализация ансамбля моделей
        """
        logger.info("Инициализация ансамбля моделей")
        
        # Инициализация моделей
        self.short_term_model = ShortTermLSTM()  # 1-7 дней
        self.medium_term_model = MediumTermLSTM()  # 7-30 дней
        self.trend_model = TrendLSTM()  # определение тренда
        
        # Базовые веса для каждой модели
        self.default_weights = {
            'short_term': 0.4,
            'medium_term': 0.3,
            'trend': 0.3
        }
        
        # Текущие веса (могут динамически меняться)
        self.current_weights = self.default_weights.copy()
        
        # Параметры для контроля изменений
        self.max_daily_change = 0.1  # максимальное изменение за день (10%)
        self.max_deviation = 0.2  # максимальное отклонение между моделями (20%)
        
    def analyze_market_state(self, data: pd.DataFrame) -> str:
        """
        Анализирует текущее состояние рынка на основе предсказаний моделей
        
        Args:
            data: DataFrame с данными для анализа
            
        Returns:
            str: Состояние рынка ('uptrend', 'downtrend', 'sideways')
        """
        logger.info("Анализ состояния рынка")
        
        # Получаем предсказание тренда
        trend_pred = self.trend_model.predict(data)
        trend_value = float(trend_pred[0])  # Берем только первое значение
        
        # Определяем состояние рынка на основе предсказания
        if trend_value > 0.6:  # Сильный восходящий тренд
            return 'uptrend'
        elif trend_value < 0.4:  # Сильный нисходящий тренд
            return 'downtrend'
        else:  # Боковой тренд
            return 'sideways'
            
    def adjust_weights(self, market_state: str) -> None:
        """
        Корректировка весов моделей в зависимости от состояния рынка

        Args:
            market_state: Текущее состояние рынка
        """
        logger.info(f"Корректировка весов моделей. Состояние рынка: {market_state}")
        
        if market_state == 'uptrend':
            # В восходящем рынке сильно увеличиваем вес краткосрочной модели
            self.current_weights = {
                'short_term': 0.6,  
                'medium_term': 0.2,  
                'trend': 0.2
            }
        elif market_state == 'downtrend':
            # В нисходящем рынке увеличиваем вес среднесрочной модели
            self.current_weights = {
                'short_term': 0.3,
                'medium_term': 0.4,
                'trend': 0.3
            }
        else:  # sideways
            # В боковом рынке используем базовые веса
            self.current_weights = self.default_weights.copy()

    def harmonize_predictions(self, predictions: Dict[str, np.ndarray], current_price: float) -> Dict[str, np.ndarray]:
        """
        Согласование предсказаний разных моделей
        
        Args:
            predictions: Словарь с предсказаниями каждой модели
            current_price: Текущая цена
            
        Returns:
            Dict с согласованными предсказаниями
        """
        logger.info("Согласование предсказаний моделей")
        
        harmonized = predictions.copy()
        
        # Для каждого дня предсказания
        for i in range(len(next(iter(predictions.values())))):
            # Получаем предсказания всех моделей на этот день
            day_predictions = {model: preds[i] for model, preds in predictions.items()}
            
            # Рассчитываем среднее и стандартное отклонение
            mean_pred = np.mean(list(day_predictions.values()))
            std_pred = np.std(list(day_predictions.values()))
            
            # Если разброс предсказаний слишком большой
            if std_pred > mean_pred * self.max_deviation:
                logger.warning(f"Большой разброс предсказаний на день {i+1}: ${std_pred:,.2f}")
                
                # Приближаем экстремальные значения к среднему
                for model in day_predictions:
                    if abs(day_predictions[model] - mean_pred) > std_pred:
                        harmonized[model][i] = (day_predictions[model] + mean_pred) / 2
                        logger.info(f"Скорректировано предсказание {model} на день {i+1}: "
                                  f"${day_predictions[model]:,.2f} -> ${harmonized[model][i]:,.2f}")
            
            # Проверяем реалистичность изменений
            for model in harmonized:
                # Определяем предыдущую цену
                if i == 0:
                    prev_price = current_price
                else:
                    prev_price = harmonized[model][i-1]
                
                # Максимально допустимое изменение
                max_change = prev_price * self.max_daily_change
                
                # Если изменение слишком большое
                if abs(harmonized[model][i] - prev_price) > max_change:
                    old_price = harmonized[model][i]
                    harmonized[model][i] = np.clip(
                        harmonized[model][i],
                        prev_price - max_change,
                        prev_price + max_change
                    )
                    logger.warning(f"Большое изменение цены для {model} на день {i+1}. "
                                 f"Корректировка: ${old_price:,.2f} -> ${harmonized[model][i]:,.2f}")
            
            # Проверяем общие границы реалистичности
            for model in harmonized:
                if harmonized[model][i] < current_price * 0.5 or harmonized[model][i] > current_price * 1.5:
                    logger.warning(f"Нереалистичное предсказание {model} на день {i+1}: ${harmonized[model][i]:,.2f}")
                    harmonized[model][i] = np.clip(harmonized[model][i], 
                                                 current_price * 0.5, 
                                                 current_price * 1.5)
        
        return harmonized
            
    def predict(self, days: int, data: pd.DataFrame) -> pd.DataFrame:
        """
        Делает предсказание на указанное количество дней
        
        Args:
            days: Количество дней для предсказания
            data: DataFrame с последними данными
            
        Returns:
            DataFrame с предсказаниями
        """
        logger.info("Предсказание цены на %d дней", days)
        
        # Анализируем текущее состояние рынка
        market_state = self.analyze_market_state(data)
        
        # Корректируем веса моделей
        self.adjust_weights(market_state)
        
        # Получаем предсказания от каждой модели
        model_predictions = {
            'short_term': self.short_term_model.predict(data),
            'medium_term': self.medium_term_model.predict(data),
            'trend': self.trend_model.predict(data)
        }
        
        # Проверяем и обрабатываем предсказания
        for model_name, preds in model_predictions.items():
            if isinstance(preds, np.ndarray):
                if len(preds) < days:
                    # Если предсказаний меньше чем нужно, повторяем последнее значение
                    preds = np.append(preds, [preds[-1]] * (days - len(preds)))
                elif len(preds) > days:
                    # Если предсказаний больше, берем только нужное количество
                    preds = preds[:days]
            else:
                # Если получили скаляр, создаем массив нужной длины
                preds = np.array([float(preds)] * days)
            model_predictions[model_name] = preds
            
        # Текущая цена для проверки реалистичности
        current_price = data['close'].iloc[-1]
        
        # Согласование предсказаний
        harmonized_predictions = self.harmonize_predictions(model_predictions, current_price)
        
        # Комбинируем предсказания с учетом весов для каждого дня
        final_predictions = (
            harmonized_predictions['short_term'] * self.current_weights['short_term'] +
            harmonized_predictions['medium_term'] * self.current_weights['medium_term'] +
            harmonized_predictions['trend'] * self.current_weights['trend']
        )
        
        # Сглаживание предсказаний
        window_size = 3
        final_predictions = pd.Series(final_predictions).rolling(window=window_size, min_periods=1).mean().values
        
        # Создаем DataFrame с предсказаниями
        last_date = data.index[-1]
        future_dates = pd.date_range(start=last_date, periods=days + 1)[1:]
        
        predictions_df = pd.DataFrame({
            'prediction': final_predictions,
            'market_state': [market_state] * days,
            'short_term_pred': harmonized_predictions['short_term'],
            'medium_term_pred': harmonized_predictions['medium_term'],
            'trend_pred': harmonized_predictions['trend']
        }, index=future_dates)
        
        # Логируем результаты
        logger.info(f"Текущая цена: ${current_price:,.2f}")
        logger.info(f"Предсказания на {days} дней:")
        for i in range(min(5, days)):  # Показываем первые 5 предсказаний
            logger.info(f"День {i+1}: ${final_predictions[i]:,.2f}")
            logger.info(f"  - ShortTerm: ${harmonized_predictions['short_term'][i]:,.2f}")
            logger.info(f"  - MediumTerm: ${harmonized_predictions['medium_term'][i]:,.2f}")
            logger.info(f"  - Trend: ${harmonized_predictions['trend'][i]:,.2f}")
        if days > 5:
            logger.info("...")
            logger.info(f"День {days}: ${final_predictions[-1]:,.2f}")
        
        return predictions_df
    
    def _update_features(self, features: float) -> None:
        """
        Обновление признаков с учетом нового предсказания
        
        Args:
            features: Новое предсказанное значение цены
            
        Returns:
            None
        """
        # TODO: Добавить обновление признаков
        pass
        
    def train(self, train_data: pd.DataFrame, 
              val_data: pd.DataFrame,
              test_data: pd.DataFrame) -> Dict[str, float]:
        """
        Обучение всех моделей в ансамбле

        Args:
            train_data: Данные для обучения
            val_data: Данные для валидации
            test_data: Данные для тестирования

        Returns:
            Dict с метриками качества для каждой модели
        """
        logger.info("Обучение ансамбля моделей")
        
        metrics = {}
        
        # Обучаем каждую модель
        metrics['short_term'] = self.short_term_model.train(
            train_data, val_data, test_data
        )
        
        metrics['medium_term'] = self.medium_term_model.train(
            train_data, val_data, test_data
        )
        
        metrics['trend'] = self.trend_model.train(
            train_data, val_data, test_data
        )
        
        return metrics
        
    def save_models(self, path: str) -> None:
        """
        Сохранение всех моделей
        
        Args:
            path: Путь для сохранения моделей
        """
        logger.info(f"Сохранение моделей в {path}")
        
        os.makedirs(path, exist_ok=True)
        
        self.short_term_model.save_model(os.path.join(path, 'short_term.h5'))
        self.medium_term_model.save_model(os.path.join(path, 'medium_term.h5'))
        self.trend_model.save_model(os.path.join(path, 'trend.h5'))
        
    def load_models(self, path: str = 'models/') -> None:
        """
        Загрузка моделей из файлов
        
        Args:
            path: Путь к директории с моделями
        """
        logger.info(f"Загрузка моделей из {path}")
        
        self.short_term_model.load_model(os.path.join(path, 'short_term.h5'))
        self.medium_term_model.load_model(os.path.join(path, 'medium_term.h5'))
        self.trend_model.load_model(os.path.join(path, 'trend.h5'))
