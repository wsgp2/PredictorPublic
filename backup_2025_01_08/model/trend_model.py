"""
Долгосрочная LSTM модель для предсказания тренда Bitcoin (30+ дней)
"""

import numpy as np
import pandas as pd
import yfinance as yf
import tensorflow as tf
from typing import Tuple, Dict
from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.models import Sequential, load_model
from tensorflow.keras.layers import LSTM, Dense, Dropout, BatchNormalization, Input
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau, ModelCheckpoint
from .feature_preparation import prepare_trend_features
from .sentiment_analysis import SentimentAnalyzer
from .logger import setup_logger
import pickle
import os

logger = setup_logger(__name__)

class TrendLSTM:
    """
    Класс для долгосрочного предсказания тренда Bitcoin (30+ дней)
    """
    
    def __init__(self, look_back=90, sequence_length=30, n_features=13):
        """
        Инициализация модели тренда
        
        Args:
            look_back: количество дней для анализа (90 дней для долгосрочного тренда)
            sequence_length: количество дней для предсказания (30 дней)
            n_features: количество признаков (временно 13, будет расширено до 20)
        """
        self.look_back = look_back
        self.sequence_length = sequence_length
        self.n_features = n_features
        self.model = None
        self.scaler = MinMaxScaler()
        self.feature_columns = None

    def _build_model(self):
        """
        Создание архитектуры модели тренда для долгосрочного прогнозирования
        """
        logger.info("Создание архитектуры модели тренда")
        
        inputs = tf.keras.layers.Input(shape=(self.look_back, self.n_features))
        
        # Входной LSTM слой с большим количеством нейронов для обработки длинных последовательностей
        x = tf.keras.layers.LSTM(256, return_sequences=True)(inputs)
        x = tf.keras.layers.BatchNormalization()(x)
        x = tf.keras.layers.Dropout(0.3)(x)
        
        # Второй LSTM слой
        x = tf.keras.layers.LSTM(128, return_sequences=True)(x)
        x = tf.keras.layers.BatchNormalization()(x)
        x = tf.keras.layers.Dropout(0.3)(x)
        
        # Третий LSTM слой
        x = tf.keras.layers.LSTM(64, return_sequences=False)(x)
        x = tf.keras.layers.BatchNormalization()(x)
        x = tf.keras.layers.Dropout(0.2)(x)
        
        # Полносвязные слои
        x = tf.keras.layers.Dense(32, activation='relu')(x)
        x = tf.keras.layers.BatchNormalization()(x)
        x = tf.keras.layers.Dropout(0.2)(x)
        
        # Выходной слой
        outputs = tf.keras.layers.Dense(self.sequence_length * self.n_features)(x)
        outputs = tf.keras.layers.Reshape((self.sequence_length, self.n_features))(outputs)
        
        model = tf.keras.Model(inputs=inputs, outputs=outputs)
        
        model.compile(
            optimizer=tf.keras.optimizers.Adam(learning_rate=0.001),
            loss='mean_squared_error',
            metrics=['mae']
        )
        
        logger.info(f"Архитектура модели:\n{model.summary()}")
        return model
    
    def prepare_data(self, data: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """
        Подготовка данных для модели тренда
        """
        logger.info("Предобработка данных для модели тренда")
        
        logger.info(f"Исходная форма данных: {data.shape}")
        logger.info(f"Столбцы данных: {data.columns.tolist()}")
        
        # Проверяем наличие NaN значений
        nan_columns = data.columns[data.isna().any()].tolist()
        if nan_columns:
            logger.warning(f"Найдены NaN значения в столбцах: {nan_columns}")
            
        # Обработка NaN значений
        data = data.fillna(method='ffill')  # Заполняем пропуски предыдущими значениями
        data = data.fillna(method='bfill')  # Если в начале есть пропуски, заполняем их следующими значениями
        data = data.fillna(0)  # Если всё ещё остались пропуски, заполняем их нулями
        
        # Проверяем, остались ли NaN значения
        if data.isna().any().any():
            logger.error("После обработки всё ещё остались NaN значения")
            return np.array([]), np.array([])
        
        # Нормализуем данные
        scaled_data = self.scaler.fit_transform(data)
        logger.info(f"Форма нормализованных данных: {scaled_data.shape}")
        
        # Проверяем длину данных
        if len(scaled_data) <= self.look_back + self.sequence_length:
            logger.error(f"Недостаточно данных для создания последовательностей. Необходимо минимум {self.look_back + self.sequence_length} точек, имеется {len(scaled_data)}")
            return np.array([]), np.array([])
        
        X, y = [], []
        for i in range(len(scaled_data) - self.look_back - self.sequence_length + 1):
            # Входные данные - окно размером look_back
            X.append(scaled_data[i:(i + self.look_back)])
            
            # Выходные данные - следующие sequence_length значений всех признаков
            y.append(scaled_data[i + self.look_back:i + self.look_back + self.sequence_length])
        
        # Проверяем, что у нас есть данные после подготовки
        if not X or not y:
            logger.error("Не удалось подготовить последовательности данных")
            return np.array([]), np.array([])
        
        X = np.array(X)
        y = np.array(y)
        
        # Проверяем размерности
        logger.info(f"Размерность входных данных: {X.shape}")
        logger.info(f"Размерность выходных данных: {y.shape}")
        
        return X, y
    
    def train(self, 
             train_data: pd.DataFrame,
             val_data: pd.DataFrame,
             test_data: pd.DataFrame,
             epochs: int = 100,
             batch_size: int = 32,
             verbose: int = 1) -> Dict:
        """
        Обучение модели тренда
        """
        logger.info("Начало обучения модели тренда")
        
        # Сохраняем названия столбцов
        self.feature_columns = train_data.columns.tolist()
        
        # Подготовка данных
        X_train, y_train = self.prepare_data(train_data)
        X_val, y_val = self.prepare_data(val_data)
        X_test, y_test = self.prepare_data(test_data)
        
        # Callbacks для обучения
        callbacks = [
            tf.keras.callbacks.EarlyStopping(
                monitor='val_loss',
                patience=10,
                restore_best_weights=True,
                verbose=1
            ),
            tf.keras.callbacks.ReduceLROnPlateau(
                monitor='val_loss',
                factor=0.5,
                patience=5,
                min_lr=1e-6,
                verbose=1
            ),
            tf.keras.callbacks.ModelCheckpoint(
                filepath='trend_model_best.keras',  # Обновлено расширение на .keras
                monitor='val_loss',
                save_best_only=True,
                verbose=1
            )
        ]
        
        # Создаем модель если её нет
        if self.model is None:
            self.model = self._build_model()
        
        # Обучение модели
        history = self.model.fit(
            X_train, y_train,
            validation_data=(X_val, y_val),
            epochs=epochs,
            batch_size=batch_size,
            callbacks=callbacks,
            verbose=verbose
        )
        
        # Оценка на тестовых данных
        if len(X_test) > 0:
            test_loss = self.model.evaluate(X_test, y_test, verbose=0)
            logger.info(f"Тестовая ошибка (MSE): {test_loss[0]:.4f}")
            logger.info(f"Тестовая ошибка (MAE): {test_loss[1]:.4f}")
        
        return history.history
    
    def predict(self, features: pd.DataFrame) -> np.ndarray:
        """
        Делает предсказание на основе входных данных
        
        Args:
            features: DataFrame с признаками
            
        Returns:
            numpy.ndarray с предсказанными значениями
        """
        logger.info("Предсказание модели тренда")
        
        if len(features) < self.look_back:
            logger.error(f"Недостаточно данных для предсказания. Необходимо минимум {self.look_back} точек")
            return np.array([])
            
        X = self._prepare_prediction_data(features)
        prediction = self.model.predict(X)
        
        # Разворачиваем предсказания в 2D массив
        prediction_reshaped = prediction.reshape(-1, self.n_features)
        
        # Отменяем масштабирование для всех признаков
        prediction_unscaled = self.scaler.inverse_transform(prediction_reshaped)
        
        # Возвращаем только предсказания цены (первый столбец)
        price_predictions = prediction_unscaled[:, 0]
        
        # Проверяем реалистичность предсказаний
        current_price = features['close'].iloc[-1]
        for i, pred in enumerate(price_predictions):
            if pred < 0 or pred > current_price * 10:
                logger.warning(f"Нереалистичное предсказание на шаг {i}: ${pred:,.2f}")
                # Ограничиваем предсказание диапазоном от 0.1 до 1000% текущей цены
                price_predictions[i] = np.clip(pred, current_price * 0.1, current_price * 10)
        
        return price_predictions
    
    def _prepare_prediction_data(self, features):
        """
        Подготовка данных для предсказания
        
        Args:
            features: DataFrame с признаками
        """
        # Проверяем, что у нас достаточно данных
        if len(features) < self.look_back:
            logger.error(f"Недостаточно данных для предсказания. Получено {len(features)}, необходимо {self.look_back}")
            return np.array([])
        
        # Нормализуем данные
        scaled_features = self.scaler.transform(features)
        logger.info(f"Форма нормализованных данных: {scaled_features.shape}")
        
        # Берем последние look_back точек и добавляем размерность батча
        X = scaled_features[-self.look_back:].reshape(1, self.look_back, -1)
        logger.info(f"Форма входных данных для модели: {X.shape}")
        
        return X
    
    def save_model(self, path):
        """
        Сохраняет модель и масштабировщик
        
        Args:
            path: Путь для сохранения модели
        """
        logger.info("Сохранение модели в %s", path)
        self.model.save(path)
        
        # Сохраняем масштабировщик и названия столбцов отдельно
        scaler_path = path.replace('.h5', '_scaler.pkl')
        with open(scaler_path, 'wb') as f:
            pickle.dump(self.scaler, f)
            
        columns_path = path.replace('.h5', '_columns.pkl')
        with open(columns_path, 'wb') as f:
            pickle.dump(self.feature_columns, f)
    
    def load_model(self, path):
        """
        Загружает модель и масштабировщик
        
        Args:
            path: Путь к сохраненной модели
        """
        logger.info("Загрузка модели из %s", path)
        self.model = load_model(path)
        
        # Загружаем масштабировщик и названия столбцов из отдельных файлов
        scaler_path = path.replace('.h5', '_scaler.pkl')
        if os.path.exists(scaler_path):
            with open(scaler_path, 'rb') as f:
                self.scaler = pickle.load(f)
                
        columns_path = path.replace('.h5', '_columns.pkl')
        if os.path.exists(columns_path):
            with open(columns_path, 'rb') as f:
                self.feature_columns = pickle.load(f)
                
    def save(self, path: str) -> None:
        """
        Сохранение модели
        
        Args:
            path: Путь для сохранения
        """
        logger.info(f"Сохранение модели в {path}")
        self.model.save(path)
        
    def load(self, path: str) -> None:
        """
        Загрузка модели
        
        Args:
            path: Путь к сохраненной модели
        """
        logger.info(f"Загрузка модели из {path}")
        self.model = load_model(path)
