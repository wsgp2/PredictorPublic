"""
Среднесрочная LSTM модель для предсказания цены Bitcoin (7-30 дней)
"""

import numpy as np
import pandas as pd
import yfinance as yf
from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.models import Sequential, load_model
from tensorflow.keras.layers import LSTM, Dense, Dropout, BatchNormalization
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau
from .feature_preparation import prepare_medium_term_features
from .sentiment_analysis import SentimentAnalyzer
from .logger import setup_logger
import tensorflow as tf
import pickle
import os

logger = setup_logger(__name__)

class MediumTermLSTM:
    """
    Класс для среднесрочного предсказания цены Bitcoin (7-30 дней)
    """
    
    def __init__(self, look_back=60):
        self.look_back = look_back
        self.model = None
        self.scaler = MinMaxScaler()
        
    def create_model(self, input_shape=(60, 7)):
        """
        Создание архитектуры модели

        Args:
            input_shape: Размерность входных данных (timesteps, features)
        """
        self.model = Sequential([
            LSTM(100, input_shape=input_shape, return_sequences=True),
            Dropout(0.2),
            LSTM(50),
            Dropout(0.2),
            Dense(25, activation='relu'),
            Dense(1)
        ])
        
        self.compile_model()
        return self.model
        
    def compile_model(self):
        """Компиляция модели с оптимизатором и функцией потерь"""
        self.model.compile(
            optimizer=Adam(),
            loss='mean_squared_error',
            metrics=['mae']
        )
        
    def prepare_data(self, features):
        """
        Подготовка данных для обучения модели
        """
        # Масштабирование данных
        scaled_data = self.scaler.fit_transform(features)
        
        X, y = [], []
        for i in range(self.look_back, len(scaled_data)):
            X.append(scaled_data[i-self.look_back:i])
            y.append(scaled_data[i, features.columns.get_loc('close')])
        
        X = np.array(X)
        y = np.array(y)
        
        return X, y
        
    def train(self, train_data, val_data=None, test_data=None, epochs=100, batch_size=32):
        """
        Обучение модели
        """
        # Подготовка обучающих данных
        X_train, y_train = self.prepare_data(train_data)
        
        # Подготовка валидационных данных
        X_val, y_val = None, None
        if val_data is not None:
            X_val, y_val = self.prepare_data(val_data)
            
        # Подготовка тестовых данных
        X_test, y_test = None, None
        if test_data is not None:
            X_test, y_test = self.prepare_data(test_data)
        
        # Создание модели если еще не создана
        if self.model is None:
            self.create_model(input_shape=(X_train.shape[1], X_train.shape[2]))
        
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
        
    def predict(self, features):
        """
        Делает предсказание на основе входных данных
        
        Args:
            features: Входные данные для предсказания
            
        Returns:
            float: Предсказанное значение
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
        
        # Создаем массив с нулями для всех признаков
        dummy_features = np.zeros((len(prediction), features.shape[1]))
        
        # Заполняем первый столбец (цена) предсказанными значениями
        dummy_features[:, features.columns.get_loc('close')] = prediction.flatten()
        
        # Отменяем масштабирование
        unscaled_prediction = self.scaler.inverse_transform(dummy_features)
        
        # Проверяем реалистичность предсказаний
        current_price = features['close'].iloc[-1]
        price_predictions = unscaled_prediction[:, features.columns.get_loc('close')]  # Берем только цены
        
        for i, pred in enumerate(price_predictions):
            if pred < 0 or pred > current_price * 10:
                logger.warning(f"Нереалистичное предсказание на шаг {i}: ${pred:,.2f}")
                # Ограничиваем предсказание диапазоном от 0.1 до 1000% текущей цены
                price_predictions[i] = np.clip(pred, current_price * 0.1, current_price * 10)
        
        # Логируем результаты
        logger.info(f"Текущая цена: ${current_price:,.2f}")
        logger.info(f"Предсказанная цена: ${price_predictions[0]:,.2f}")
        
        return price_predictions
        
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
        features = prepare_medium_term_features(data, sentiment_analyzer)
        
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
        self.save_model('medium_term_model.h5')
        print("\nМодель сохранена как 'medium_term_model.h5'")

if __name__ == "__main__":
    medium_term_lstm = MediumTermLSTM()
    medium_term_lstm.main()
