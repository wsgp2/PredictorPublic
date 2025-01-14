import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
import tensorflow as tf
from tensorflow.keras.models import load_model
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import yfinance as yf
from technical_indicators import add_technical_indicators, calculate_technical_indicators
import requests
import time
from google_trends import get_google_trends, normalize_trends

def load_and_prepare_data():
    """Загрузка и подготовка данных"""
    print("\nЗагружаем данные о цене биткойна...")
    
    # Загружаем данные о цене биткойна
    max_attempts = 3
    for attempt in range(max_attempts):
        try:
            btc = yf.download('BTC-USD', start='2023-01-01', end=None)
            break
        except Exception as e:
            if attempt < max_attempts - 1:
                print(f"Попытка {attempt + 1} не удалась. Пробуем снова через 5 секунд...")
                time.sleep(5)
            else:
                raise Exception("Не удалось загрузить данные после нескольких попыток")

    # Получаем индекс страха и жадности
    fng = get_fng_index()
    
    # Получаем данные из Google Trends
    trends_df = get_google_trends()
    
    # Приводим индексы к одному часовому поясу
    btc.index = btc.index.tz_localize(None)
    fng.index = fng.index.tz_localize(None)
    if trends_df is not None:
        trends_df.index = trends_df.index.tz_localize(None)
    
    # Создаем общий индекс дат
    all_indices = [btc.index, fng.index]
    if trends_df is not None:
        all_indices.append(trends_df.index)
    
    common_dates = pd.date_range(
        start=min(idx.min() for idx in all_indices),
        end=max(idx.max() for idx in all_indices),
        freq='D'
    )
    
    # Приводим данные к общему индексу
    btc = btc.reindex(common_dates)
    fng = fng.reindex(common_dates)
    if trends_df is not None:
        trends_df = trends_df.reindex(common_dates)
    
    # Заполняем пропущенные значения
    btc = btc.ffill().bfill()
    fng = fng.ffill().bfill()
    if trends_df is not None:
        trends_df = trends_df.ffill().bfill()
        
    # Рассчитываем технические индикаторы
    btc = calculate_technical_indicators(btc)
    
    # Добавляем индекс страха и жадности
    btc['FNG'] = fng['FNG']
    
    # Добавляем тренды, если они доступны
    if trends_df is not None:
        btc['buy_trend'] = trends_df['buy_trend']
        btc['sell_trend'] = trends_df['sell_trend']
    
    # Выбираем нужные колонки для предсказания
    base_features = ['Close', 'Volume', 'High', 'Low', 'FNG', 
                    'RSI', 'MACD', 'Signal_Line',
                    'BB_middle', 'BB_upper', 'BB_lower', 'VROC', 
                    'PVT', 'OBV', 'ATR', 'Stoch_K', 'Stoch_D',
                    'EMA_9', 'EMA_21']  # Исходные 19 признаков
    
    # Добавляем тренды, если они доступны
    if trends_df is not None:
        base_features.extend(['buy_trend', 'sell_trend'])  # Добавляем 2 новых признака
    
    return btc[base_features]

def validate_model(data, look_back=30, validation_start='2024-01-01'):
    print("\nЗагружаем модель...")
    model = load_model('model/bitcoin_prediction_model.h5')
    
    # Подготавливаем данные
    scaler = MinMaxScaler(feature_range=(0, 1))
    scaled_data = scaler.fit_transform(data)
    
    # Создаем массивы для валидации
    validation_mask = data.index >= validation_start
    validation_data = data[validation_mask]
    validation_start_idx = len(data) - len(validation_data)
    
    if validation_start_idx < look_back:
        raise ValueError("Недостаточно исторических данных для валидации")
    
    scaled_validation = scaled_data[validation_start_idx-look_back:]
    
    X_val, y_val = [], []
    for i in range(look_back, len(scaled_validation)-30):
        X_val.append(scaled_validation[i-look_back:i])
        y_val.append(scaled_validation[i:i+30, 0])  # Берем только цену закрытия
    
    if not X_val:
        raise ValueError("Недостаточно данных для создания валидационного набора")
    
    X_val = np.array(X_val)
    y_val = np.array(y_val)
    
    # Делаем предсказания
    print("\nДелаем предсказания...")
    predictions = []
    actual_values = []
    dates = []
    
    for i in range(len(X_val)):
        pred = model.predict(X_val[i:i+1], verbose=0)
        # Преобразуем предсказания обратно в исходный масштаб
        zeros = np.zeros((pred.shape[0], data.shape[1]-1))
        pred_reshaped = np.hstack((pred, zeros))
        actual_reshaped = np.hstack((y_val[i:i+1, 0:1], zeros))
        
        pred_price = scaler.inverse_transform(pred_reshaped)[0, 0]
        actual_price = scaler.inverse_transform(actual_reshaped)[0, 0]
        
        predictions.append(pred_price)
        actual_values.append(actual_price)
        dates.append(validation_data.index[i])
    
    # Вычисляем метрики ошибок
    mse = np.mean((np.array(predictions) - np.array(actual_values))**2)
    rmse = np.sqrt(mse)
    mae = np.mean(np.abs(np.array(predictions) - np.array(actual_values)))
    mape = np.mean(np.abs((np.array(actual_values) - np.array(predictions)) / np.array(actual_values))) * 100
    
    # Визуализация результатов
    plt.figure(figsize=(15, 7))
    plt.plot(dates, actual_values, label='Реальные значения', color='blue')
    plt.plot(dates, predictions, label='Предсказания', color='red', linestyle='--')
    plt.title('Сравнение предсказаний с реальными значениями')
    plt.xlabel('Дата')
    plt.ylabel('Цена BTC (USD)')
    plt.legend()
    plt.grid(True)
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    return {
        'MSE': mse,
        'RMSE': rmse,
        'MAE': mae,
        'MAPE': mape
    }

def get_fng_index():
    max_attempts = 3
    for attempt in range(max_attempts):
        try:
            url = "https://api.alternative.me/fng/?limit=0"
            response = requests.get(url)
            data = response.json()
            
            # Создаем DataFrame с индексом в виде даты
            df = pd.DataFrame([{
                'date': datetime.fromtimestamp(int(item['timestamp'])).strftime('%Y-%m-%d'),
                'value': int(item['value'])
            } for item in data['data']])
            
            df['date'] = pd.to_datetime(df['date'])
            df = df.set_index('date')
            df = df.rename(columns={'value': 'FNG'})
            df = df.sort_index()
            
            return df
        except Exception as e:
            if attempt < max_attempts - 1:
                print(f"Попытка {attempt + 1} получить FNG не удалась. Пробуем снова через 5 секунд...")
                time.sleep(5)
            else:
                print("Не удалось получить индекс страха и жадности. Используем случайные значения.")
                dates = pd.date_range(start='2020-01-01', end='2024-12-31')
                df = pd.DataFrame({
                    'FNG': np.random.randint(0, 100, size=len(dates))
                }, index=dates)
                return df

if __name__ == "__main__":
    try:
        # Загружаем данные
        data = load_and_prepare_data()
        
        # Тестируем на разных периодах
        periods = [
            ('2024-01-01', 'Январь 2024'),
            ('2023-07-01', 'Второе полугодие 2023'),
            ('2023-01-01', 'Весь 2023 год')
        ]
        
        for validation_start, period_name in periods:
            print(f"\nТестирование за период: {period_name}")
            print("-" * 50)
            
            # Проводим валидацию
            metrics = validate_model(data, look_back=30, validation_start=validation_start)
            
            # Выводим результаты
            print(f"\nРезультаты валидации:")
            print(f"Средняя квадратичная ошибка (MSE): ${metrics['MSE']:,.2f}")
            print(f"Корень из средней квадратичной ошибки (RMSE): ${metrics['RMSE']:,.2f}")
            print(f"Средняя абсолютная ошибка (MAE): ${metrics['MAE']:,.2f}")
            print(f"Средняя абсолютная процентная ошибка (MAPE): {metrics['MAPE']:.2f}%")
            
            # Сохраняем график с указанием периода
            plt.savefig(f'validation_results_{validation_start}.png')
            plt.close()
            
            print(f"\nГрафик сохранен в файл 'validation_results_{validation_start}.png'")
            
    except Exception as e:
        print(f"\nОшибка при выполнении валидации: {str(e)}")
