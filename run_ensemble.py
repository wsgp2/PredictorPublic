"""
Запуск ансамбля моделей для предсказания цены Bitcoin
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import yfinance as yf
from model.short_term import ShortTermLSTM
from model.medium_term import MediumTermLSTM
from model.trend_model import TrendLSTM
from model.ensemble import BitcoinEnsemble
from model.logger import setup_logger
from model.feature_preparation import prepare_trend_features
from model.technical_indicators import add_technical_indicators
import matplotlib.pyplot as plt
import tensorflow as tf
import os

logger = setup_logger(__name__)

def load_data():
    """
    Загрузка и подготовка данных
    """
    try:
        # Получаем исторические данные за последние 5 лет
        end_date = datetime.now()
        start_date = end_date - timedelta(days=1825)  # 5 лет
        
        logger.info(f"Загрузка данных с {start_date.date()} по {end_date.date()}")
        
        # Загружаем данные через yfinance
        btc = yf.download('BTC-USD', start=start_date, end=end_date, interval='1d')
        
        if btc.empty:
            logger.error("Не удалось загрузить данные о цене биткойна")
            return pd.DataFrame()
        
        # Убираем мультииндекс из столбцов
        btc.columns = btc.columns.droplevel('Ticker')
        
        logger.info(f"Текущая цена биткойна: ${btc['Close'].iloc[-1]:.2f}")
        logger.info(f"Количество дней в наборе данных: {len(btc)}")
        logger.info(f"Диапазон дат: с {btc.index.min()} по {btc.index.max()}")
        
        # Переименовываем столбцы для совместимости
        btc = btc.rename(columns={
            'Open': 'open',
            'High': 'high',
            'Low': 'low',
            'Close': 'close',
            'Volume': 'volume'
        })
        
        # Добавляем технические индикаторы
        btc = add_technical_indicators(btc)
        
        # Подготавливаем признаки для модели тренда
        btc = prepare_trend_features(btc)
        
        # Удаляем строки с NaN значениями
        btc = btc.dropna()
        
        logger.info(f"Количество дней после обработки: {len(btc)}")
        logger.info(f"Количество признаков: {len(btc.columns)}")
        
        return btc
        
    except Exception as e:
        logger.error(f"Ошибка при загрузке данных: {str(e)}")
        return pd.DataFrame()

def plot_predictions(historical_data: pd.DataFrame, predictions: pd.DataFrame, 
                    output_file: str = 'predictions.png'):
    """
    Строит график исторических данных и предсказаний
    
    Args:
        historical_data: DataFrame с историческими данными
        predictions: DataFrame с предсказаниями
        output_file: путь для сохранения графика
    """
    plt.figure(figsize=(15, 7))
    
    # Исторические данные
    plt.plot(historical_data.index[-90:], historical_data['close'].tail(90), 
             label='Исторические данные', color='blue')
    
    # Предсказания
    plt.plot(predictions.index, predictions['prediction'], 
             label='Предсказания', color='red', linestyle='--')
    
    plt.title('Цена Bitcoin: история и прогноз')
    plt.xlabel('Дата')
    plt.ylabel('Цена (USD)')
    plt.legend()
    plt.grid(True)
    
    # Поворачиваем метки дат для лучшей читаемости
    plt.xticks(rotation=45)
    
    # Сохраняем график
    plt.tight_layout()
    plt.savefig(output_file)
    plt.close()

def main():
    """
    Основная функция
    """
    logger.info("Запуск программы")
    
    try:
        # Загрузка исторических данных
        end_date = datetime.now()
        start_date = end_date - timedelta(days=5*365)
        logger.info(f"Загрузка данных с {start_date.date()} по {end_date.date()}")
        
        # Пробуем загрузить данные несколько раз в случае ошибки
        max_retries = 3
        for attempt in range(max_retries):
            try:
                btc = yf.download('BTC-USD', start=start_date, end=end_date, timeout=30)
                if not btc.empty:
                    break
            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(f"Попытка {attempt + 1} не удалась: {str(e)}. Пробуем снова...")
                    continue
                else:
                    raise Exception(f"Не удалось загрузить данные после {max_retries} попыток: {str(e)}")
        
        if btc.empty:
            raise Exception("Загруженный DataFrame пуст")
            
        # Сбрасываем мультииндекс в столбцах
        btc.columns = btc.columns.get_level_values(0)
        
        # Выводим текущую цену
        current_price = float(btc['Close'].iloc[-1])
        logger.info(f"Текущая цена биткойна: ${current_price:,.2f}")
        
        # Выводим информацию о данных
        logger.info(f"Количество дней в наборе данных: {len(btc)}")
        logger.info(f"Диапазон дат: с {btc.index[0]} по {btc.index[-1]}")
        
        # Добавляем технические индикаторы
        print("Columns before:", btc.columns)  # Отладочный вывод
        btc = add_technical_indicators(btc)
        print("Columns after:", btc.columns)   # Отладочный вывод
        
        # Создаем и обучаем модель
        ensemble = BitcoinEnsemble()
        
        # Загружаем сохраненные модели
        logger.info("Загружаем сохраненные модели...")
        ensemble.load_models()
        
        # Получаем последние 90 дней данных для предсказания
        last_90_days = btc.tail(90)
        
        # Делаем предсказание на следующие 30 дней
        logger.info("Выполняем предсказание на следующие 30 дней")
        predictions = ensemble.predict(30, last_90_days)
        
        # Выводим результаты
        logger.info("Результаты предсказания:")
        if isinstance(predictions, pd.DataFrame) and 'prediction' in predictions.columns:
            last_prediction = predictions['prediction'].iloc[-1]
            if isinstance(last_prediction, (np.ndarray, list)):
                last_prediction = last_prediction[0]  # Берем первое значение из массива
            logger.info("Предсказанная цена через 30 дней: $%.2f", float(last_prediction))
        else:
            logger.error("Некорректный формат предсказаний")
        
        # Строим график
        plot_predictions(btc, predictions, 'prediction_results.png')
        
    except Exception as e:
        logger.error("Ошибка в основном процессе: %s", str(e))
        raise

if __name__ == "__main__":
    # Закрываем все предыдущие процессы python
    try:
        import os
        import signal
        import psutil
        
        # Получаем текущий PID
        current_pid = os.getpid()
        
        # Находим и закрываем все процессы python, кроме текущего
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                if proc.info['name'] == 'python' and proc.pid != current_pid:
                    os.kill(proc.pid, signal.SIGTERM)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
    except Exception as e:
        logger.warning(f"Не удалось закрыть предыдущие процессы: {e}")
    
    # Запускаем основной код
    main()
