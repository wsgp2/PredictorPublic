"""
Краткосрочная LSTM модель для предсказания цены Bitcoin (1-7 дней)
"""

import numpy as np
import pandas as pd
import yfinance as yf
import tensorflow as tf
from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.models import Sequential, load_model
from tensorflow.keras.layers import LSTM, Dense, Dropout
from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau
from .feature_preparation import prepare_short_term_features
from .sentiment_analysis import SentimentAnalyzer
from .logger import setup_logger
from typing import Tuple
import pickle
import os

logger = setup_logger(__name__)

class ShortTermLSTM:
    """
    Класс для краткосрочного предсказания цены Bitcoin (1-7 дней)
    """
    
    def __init__(self, look_back=30):
        self.look_back = look_back
        self.model = None
        self.scaler = MinMaxScaler()
        
    def _create_model(self):
        """
        Создание архитектуры модели
        """
        try:
            model = Sequential([
                LSTM(units=50, return_sequences=True, input_shape=(self.look_back, 13)),  # 13 признаков
                Dropout(0.2),
                LSTM(units=50, return_sequences=True),
                Dropout(0.2),
                LSTM(units=50),
                Dropout(0.2),
                Dense(30)  # Предсказываем 30 дней
            ])
            
            model.compile(optimizer=tf.keras.optimizers.Adam(learning_rate=0.001),
                        loss='mean_squared_error',
                        metrics=['mae'])
            
            self.model = model
            
        except Exception as e:
            logger.error(f"Ошибка при создании модели: {str(e)}")
            raise
        
    def prepare_data(self, features: pd.DataFrame):
        """
        Подготовка данных для обучения краткосрочной модели
        """
        try:
            # Нормализация данных
            data = self.scaler.fit_transform(features)
            
            X, y = [], []
            for i in range(len(data) - self.look_back - 30):
                X.append(data[i:(i + self.look_back)])
                y.append(data[i + self.look_back:i + self.look_back + 30, 0])  # Берем только цену закрытия для предсказания
                
            return np.array(X), np.array(y)
            
        except Exception as e:
            logger.error(f"Ошибка при подготовке данных: {str(e)}")
            return None, None
        
    def train(self, train_data, val_data=None, test_data=None, epochs=100, batch_size=32):
        """
        Обучение модели
        """
        # Подготовка обучающих данных
        X_train, y_train = self.prepare_data(train_data)
        
        if X_train is None or y_train is None:
            logger.error("Не удалось подготовить обучающие данные")
            return None
        
        # Подготовка валидационных данных
        X_val, y_val = None, None
        if val_data is not None:
            X_val, y_val = self.prepare_data(val_data)
            
        # Подготовка тестовых данных
        X_test, y_test = None, None
        if test_data is not None:
            X_test, y_test = self.prepare_data(test_data)
        
        # Создание модели
        self._create_model()
        
        # Callbacks для обучения
        callbacks = [
            EarlyStopping(patience=20, restore_best_weights=True),
            ReduceLROnPlateau(factor=0.1, patience=10, min_lr=1e-6)
        ]
        
        # Обучение модели
        history = self.model.fit(
            X_train, y_train,
            epochs=epochs,
            batch_size=batch_size,
            validation_data=(X_val, y_val) if X_val is not None else None,
            callbacks=callbacks,
            verbose=1
        )
        
        # Оценка модели
        metrics = {}
        metrics['train_loss'] = self.model.evaluate(X_train, y_train, verbose=0)
        if X_val is not None:
            metrics['val_loss'] = self.model.evaluate(X_val, y_val, verbose=0)
        if X_test is not None:
            metrics['test_loss'] = self.model.evaluate(X_test, y_test, verbose=0)
        
        return metrics
        
    def _prepare_prediction_data(self, features):
        """
        Подготовка данных для предсказания
        
        Args:
            features: DataFrame с входными данными
        """
        # Проверяем, что у нас достаточно данных
        if len(features) < self.look_back:
            logger.error(f"Недостаточно данных для предсказания. Получено {len(features)}, необходимо {self.look_back}")
            return None
            
        # Масштабируем входные данные
        scaled_data = self.scaler.transform(features)
        logger.info(f"Форма нормализованных данных: {scaled_data.shape}")
        
        # Берем последние look_back точек и добавляем размерность батча
        X = scaled_data[-self.look_back:].reshape(1, self.look_back, -1)
        logger.info(f"Форма входных данных для модели: {X.shape}")
        
        return X
        
    def predict(self, features):
        """
        Делает предсказание на основе входных данных
        
        Args:
            features: Входные данные для предсказания
            
        Returns:
            numpy.ndarray: Массив предсказанных значений
        """
        # Проверяем, что у нас достаточно данных
        if len(features) < self.look_back:
            logger.error(f"Недостаточно данных для предсказания. Необходимо минимум {self.look_back} точек")
            return None
        
        # Преобразуем входные данные
        X = self._prepare_prediction_data(features)
        
        if X is None or len(X) == 0:
            logger.error("Не удалось подготовить данные для предсказания")
            return None
        
        # Делаем предсказание
        prediction = self.model.predict(X)
        logger.info(f"Форма предсказания: {prediction.shape}")
        
        # Создаем массив с нулями для всех признаков
        dummy_features = np.zeros((prediction.shape[1], features.shape[1]))
        
        # Заполняем первый столбец (цена) предсказанными значениями
        dummy_features[:, 0] = prediction[0]
        
        # Отменяем масштабирование
        unscaled_prediction = self.scaler.inverse_transform(dummy_features)
        
        # Проверяем реалистичность предсказаний
        current_price = features['close'].iloc[-1]
        price_predictions = unscaled_prediction[:, 0]  # Берем только цены
        
        for i, pred in enumerate(price_predictions):
            if pred < 0 or pred > current_price * 10:
                logger.warning(f"Нереалистичное предсказание на шаг {i}: ${pred:,.2f}")
                # Ограничиваем предсказание диапазоном от 0.1 до 1000% текущей цены
                price_predictions[i] = np.clip(pred, current_price * 0.1, current_price * 10)
        
        # Логируем результаты
        logger.info(f"Текущая цена: ${current_price:,.2f}")
        logger.info(f"Предсказанные цены: {[f'${price:,.2f}' for price in price_predictions]}")
        
        return price_predictions
        
    def save_model(self, filepath: str):
        """
        Сохранение модели в файл
        
        Args:
            filepath: Путь для сохранения модели
        """
        self.model.save(filepath)
        
        # Сохраняем масштабировщик
        scaler_path = filepath.replace('.h5', '_scaler.pkl')
        with open(scaler_path, 'wb') as f:
            pickle.dump(self.scaler, f)
            
    def load_model(self, filepath: str):
        """
        Загрузка модели из файла
        
        Args:
            filepath: Путь к файлу модели
        """
        self.model = load_model(filepath)
        
        # Загружаем масштабировщик
        scaler_path = filepath.replace('.h5', '_scaler.pkl')
        if os.path.exists(scaler_path):
            with open(scaler_path, 'rb') as f:
                self.scaler = pickle.load(f)
                
    def main(self):
        print("Загрузка данных...")
        btc = yf.Ticker("BTC-USD")
        data = btc.history(period="max", interval="1d")  # Получаем дневные данные
        
        print("Подготовка признаков...")
        sentiment_analyzer = SentimentAnalyzer()
        features = prepare_short_term_features(data, sentiment_analyzer)
        
        if features is None:
            print("Ошибка при подготовке признаков")
            return
        
        print(f"Подготовлено признаков: {features.shape[1]}")
        print(f"Количество дней: {len(features)}")
        
        # Подготовка данных
        train_size = int(len(features) * 0.8)
        train_data, val_data = features[:train_size], features[train_size:]
        
        # Обучение модели
        metrics = self.train(train_data, val_data)
        
        # Оценка модели
        print(f"\nРезультаты обучения:")
        print(f"Ошибка на обучающей выборке: {metrics['train_loss']:.4f}")
        print(f"Ошибка на валидационной выборке: {metrics['val_loss']:.4f}")
        
        # Сохранение модели
        self.save_model('short_term_model.h5')
        print("\nМодель сохранена как 'short_term_model.h5'")

if __name__ == "__main__":
    short_term_lstm = ShortTermLSTM()
    short_term_lstm.main()
