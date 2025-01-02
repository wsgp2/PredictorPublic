import numpy as np
import pandas as pd
import yfinance as yf
from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout, MultiHeadAttention, LayerNormalization
from tensorflow.keras.regularizers import L2
from tensorflow.keras.optimizers import Adam
import matplotlib.pyplot as plt
import os
import requests
from datetime import datetime, timedelta
import tensorflow as tf

def get_fear_and_greed_index(start_date):
    """Получение исторических данных индекса страха и жадности"""
    print("Загружаем данные индекса страха и жадности...")
    url = "https://api.alternative.me/fng/"
    params = {
        "limit": 0,  # Получаем все доступные данные
        "format": "json"
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        # Преобразуем данные в DataFrame
        fng_data = pd.DataFrame(data['data'])
        fng_data['timestamp'] = pd.to_datetime(fng_data['timestamp'].astype(int), unit='s', utc=True)
        fng_data['value'] = fng_data['value'].astype(float)
        fng_data.set_index('timestamp', inplace=True)
        fng_data = fng_data.sort_index()
        
        # Приводим к ежедневным данным с заполнением пропусков
        if isinstance(start_date, str):
            start_date = pd.to_datetime(start_date, utc=True)
        elif not start_date.tzinfo:
            start_date = start_date.tz_localize('UTC')
            
        end_date = pd.Timestamp.now(tz='UTC')
        date_range = pd.date_range(start=start_date, end=end_date, freq='D', tz='UTC')
        
        # Переиндексируем и заполняем пропуски
        fng_data = fng_data['value'].reindex(date_range)
        fng_data = fng_data.ffill().bfill()
        
        return fng_data
    except Exception as e:
        print(f"Ошибка при получении индекса страха и жадности: {e}")
        return None

def get_bitcoin_data():
    print("Загружаем данные о цене биткойна...")
    btc = yf.Ticker("BTC-USD")
    data = btc.history(period="2y")
    
    # Создаем DataFrame для признаков
    features = pd.DataFrame()
    features['Close'] = data['Close']
    features['Volume'] = data['Volume']
    features['High'] = data['High']
    features['Low'] = data['Low']
    
    # Получаем индекс страха и жадности
    fng_index = get_fear_and_greed_index(data.index[0])
    if fng_index is not None:
        features['FNG'] = fng_index
        print(f"Индекс страха и жадности добавлен, диапазон: {fng_index.min():.2f} - {fng_index.max():.2f}")
    
    # Добавляем технические индикаторы
    features = add_technical_indicators(features)
    print(f"\nИспользуемые признаки: {', '.join(features.columns)}")
    
    # Заполняем пропущенные значения
    features = features.ffill().bfill()
    
    return features

def add_volume_indicators(data):
    # Volume Rate of Change (VROC)
    data['VROC'] = data['Volume'].pct_change(periods=14) * 100
    
    # Price Volume Trend (PVT)
    data['PVT'] = (data['Close'].pct_change() * data['Volume']).cumsum()
    
    # On-Balance Volume (OBV)
    data['OBV'] = (data['Volume'] * (~data['Close'].diff().le(0) * 2 - 1)).cumsum()
    
    return data

def add_technical_indicators(data):
    # RSI
    delta = data['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    data['RSI'] = 100 - (100 / (1 + rs))
    
    # MACD
    exp1 = data['Close'].ewm(span=12, adjust=False).mean()
    exp2 = data['Close'].ewm(span=26, adjust=False).mean()
    data['MACD'] = exp1 - exp2
    data['Signal_Line'] = data['MACD'].ewm(span=9, adjust=False).mean()
    
    # Bollinger Bands
    data['BB_middle'] = data['Close'].rolling(window=20).mean()
    data['BB_upper'] = data['BB_middle'] + 2 * data['Close'].rolling(window=20).std()
    data['BB_lower'] = data['BB_middle'] - 2 * data['Close'].rolling(window=20).std()
    
    # Добавляем индикаторы объема
    data = add_volume_indicators(data)
    
    # ATR (Average True Range)
    data['ATR'] = calculate_atr(data, period=14)
    
    # Stochastic Oscillator
    stoch = calculate_stochastic(data, k_period=14, d_period=3)
    data['Stoch_K'] = stoch['K']
    data['Stoch_D'] = stoch['D']
    
    # EMA (разные периоды)
    data['EMA_9'] = calculate_ema(data['Close'], period=9)
    data['EMA_21'] = calculate_ema(data['Close'], period=21)
    
    # CMF (Chaikin Money Flow)
    data['CMF'] = calculate_cmf(data, period=20)
    
    # ADX (Average Directional Index)
    data['ADX'] = calculate_adx(data, period=14)
    
    # Удаляем NaN значения
    data = data.dropna()
    
    return data

def calculate_atr(data, period=14):
    """Вычисляет Average True Range"""
    high = data['High']
    low = data['Low']
    close = data['Close']
    
    tr1 = abs(high - low)
    tr2 = abs(high - close.shift())
    tr3 = abs(low - close.shift())
    
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=period).mean()
    return atr

def calculate_stochastic(data, k_period=14, d_period=3):
    """Вычисляет Stochastic Oscillator"""
    low_min = data['Low'].rolling(window=k_period).min()
    high_max = data['High'].rolling(window=k_period).max()
    
    k = 100 * ((data['Close'] - low_min) / (high_max - low_min))
    d = k.rolling(window=d_period).mean()
    
    return {'K': k, 'D': d}

def calculate_ema(series, period):
    """Вычисляет Exponential Moving Average"""
    return series.ewm(span=period, adjust=False).mean()

def calculate_cmf(data, period=20):
    """Вычисляет Chaikin Money Flow"""
    mfm = ((data['Close'] - data['Low']) - (data['High'] - data['Close'])) / (data['High'] - data['Low'])
    mfv = mfm * data['Volume']
    cmf = mfv.rolling(window=period).sum() / data['Volume'].rolling(window=period).sum()
    return cmf

def calculate_adx(data, period=14):
    """Вычисляет Average Directional Index"""
    plus_dm = data['High'].diff()
    minus_dm = data['Low'].diff()
    plus_dm[plus_dm < 0] = 0
    minus_dm[minus_dm > 0] = 0
    
    tr1 = abs(data['High'] - data['Low'])
    tr2 = abs(data['High'] - data['Close'].shift())
    tr3 = abs(data['Low'] - data['Close'].shift())
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    
    atr = tr.rolling(window=period).mean()
    
    plus_di = 100 * (plus_dm.rolling(window=period).mean() / atr)
    minus_di = 100 * (minus_dm.rolling(window=period).mean() / atr)
    
    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
    adx = dx.rolling(window=period).mean()
    return adx

class AttentionBlock(tf.keras.layers.Layer):
    """
    Блок внимания с self-attention
    """
    def __init__(self, num_heads=2, key_dim=32):
        super().__init__()
        self.attention = MultiHeadAttention(num_heads=num_heads, key_dim=key_dim)
        self.layernorm = LayerNormalization()
    
    def call(self, inputs):
        # Self-attention: используем один и тот же вход для query, key и value
        attention_output = self.attention(inputs, inputs, inputs)
        # Добавляем residual connection и нормализацию
        return self.layernorm(inputs + attention_output)

def create_model(input_shape):
    model = Sequential([
        LSTM(128, return_sequences=True, input_shape=input_shape, kernel_regularizer=L2(0.01)),
        Dropout(0.2),
        LSTM(64, return_sequences=True),
        Dropout(0.2),
        LSTM(32),
        Dropout(0.1),
        Dense(16, activation='relu'),
        Dense(1)
    ])
    
    optimizer = Adam(learning_rate=0.001)
    model.compile(optimizer=optimizer, loss='mse')
    return model

def prepare_data(data, look_back=30):
    """
    Подготовка данных для обучения модели
    """
    features = [
        'Close', 'Volume', 'FNG', 
        'RSI', 'MACD', 'Signal_Line', 
        'BB_middle', 'BB_upper', 'BB_lower', 
        'VROC', 'PVT', 'OBV',
        'ATR', 'Stoch_K', 'Stoch_D', 
        'EMA_9', 'EMA_21', 'CMF', 'ADX'
    ]
    
    # Создаем скейлеры для разных групп признаков
    price_scaler = MinMaxScaler(feature_range=(0, 1))
    close_scaler = MinMaxScaler(feature_range=(0, 1))  # Отдельный скейлер для цены закрытия
    volume_scaler = MinMaxScaler(feature_range=(0, 1))
    indicator_scaler = MinMaxScaler(feature_range=(0, 1))
    
    # Разделяем признаки на группы
    close_price = data[['Close']].values  # Только цена закрытия
    price_features = data[['BB_middle', 'BB_upper', 'BB_lower']].values
    volume_features = data[['Volume', 'PVT', 'OBV']].values
    indicator_features = data[['FNG', 'RSI', 'MACD', 'Signal_Line', 'VROC', 
                             'ATR', 'Stoch_K', 'Stoch_D', 'EMA_9', 'EMA_21', 'CMF', 'ADX']].values
    
    # Масштабируем каждую группу отдельно
    scaled_close = close_scaler.fit_transform(close_price)
    scaled_prices = price_scaler.fit_transform(price_features)
    scaled_volumes = volume_scaler.fit_transform(volume_features)
    scaled_indicators = indicator_scaler.fit_transform(indicator_features)
    
    # Собираем масштабированные данные обратно
    scaled_data = np.zeros((len(data), len(features)))
    scaled_data[:, 0] = scaled_close.reshape(-1)  # Close
    scaled_data[:, 1] = scaled_volumes[:, 0]  # Volume
    scaled_data[:, 2:6] = scaled_indicators[:, :4]  # FNG, RSI, MACD, Signal_Line
    scaled_data[:, 6:9] = scaled_prices  # BB_middle, BB_upper, BB_lower
    scaled_data[:, 9] = scaled_indicators[:, 4]  # VROC
    scaled_data[:, 10:12] = scaled_volumes[:, 1:]  # PVT, OBV
    scaled_data[:, 12:] = scaled_indicators[:, 5:]  # ATR, Stoch_K, Stoch_D, EMA_9, EMA_21, CMF, ADX
    
    X, y = [], []
    for i in range(look_back, len(scaled_data)):
        X.append(scaled_data[i-look_back:i])
        y.append(scaled_data[i, 0])  # Прогнозируем только цену закрытия
    
    X, y = np.array(X), np.array(y)
    
    # Разделение на обучающую и тестовую выборки (80/20)
    train_size = int(len(X) * 0.8)
    train_X, test_X = X[:train_size], X[train_size:]
    train_y, test_y = y[:train_size], y[train_size:]
    
    return train_X, train_y, test_X, test_y, close_scaler, price_scaler, volume_scaler, indicator_scaler, scaled_data[-look_back:]

def train_model(model, train_X, train_y, test_X, test_y):
    """
    Обучает модель с использованием early stopping и reduce learning rate
    """
    # Настраиваем callbacks
    early_stopping = tf.keras.callbacks.EarlyStopping(
        monitor='val_loss',
        patience=10,
        restore_best_weights=True,
        mode='min'
    )
    
    reduce_lr = tf.keras.callbacks.ReduceLROnPlateau(
        monitor='val_loss',
        factor=0.2,
        patience=5,
        min_lr=0.0001,
        mode='min'
    )
    
    # Обучаем модель
    history = model.fit(
        train_X, train_y,
        epochs=100,
        batch_size=32,
        validation_data=(test_X, test_y),
        callbacks=[early_stopping, reduce_lr],
        verbose=1
    )
    
    return history

def predict_future(model, last_data, look_back, num_days=30, scaler=None):
    """
    Предсказание цены на будущие дни с обновлением всех признаков
    """
    if scaler is None:
        return None
        
    # Создаем копию последних данных
    current_data = last_data.copy()
    predictions = []
    
    for _ in range(num_days):
        # Проверяем размерность входных данных
        if current_data.shape != (1, look_back, 19):  
            print(f"Неверная размерность входных данных: {current_data.shape}, ожидается: (1, {look_back}, 19)")
            return None
            
        # Получаем предсказание на следующий день
        predicted = model.predict(current_data, verbose=0)
        
        # Преобразуем предсказание обратно в реальную цену
        predicted_price = scaler.inverse_transform(predicted.reshape(-1, 1))
        predictions.append(predicted_price[0][0])
        
        # Обновляем входные данные для следующего предсказания
        # Сдвигаем все значения на один шаг назад
        current_data = np.roll(current_data, -1, axis=1)
        
        # Обновляем последнее значение цены закрытия
        current_data[0, -1, 0] = predicted
        
        # Обновляем технические индикаторы (используем последние известные значения)
        current_data[0, -1, 1:] = current_data[0, -2, 1:]
    
    return predictions

def save_model(model, model_path='model'):
    """Сохраняет модель в указанную директорию"""
    if not os.path.exists(model_path):
        os.makedirs(model_path)
    model.save(f'{model_path}/bitcoin_prediction_model.h5')
    print(f"Модель сохранена в {model_path}/bitcoin_prediction_model.h5")

def plot_results(close_prices, train_predict, test_predict, look_back, history):
    # Создаем массив индексов для построения графика
    train_size = len(train_predict)
    all_size = len(close_prices)
    
    # Создаем индексы для тренировочных и тестовых данных
    train_index = range(look_back, train_size + look_back)
    test_index = range(train_size + look_back, all_size)
    
    # Создаем график
    plt.figure(figsize=(12, 6))
    
    # Строим график реальных цен
    plt.plot(close_prices, label='Реальная цена')
    
    # Строим график предсказаний на тренировочных данных
    plt.plot(train_index, train_predict, label='Предсказание на тренировочных данных')
    
    # Строим график предсказаний на тестовых данных
    plt.plot(test_index, test_predict, label='Предсказание на тестовых данных')
    
    plt.title('Предсказание цены Bitcoin')
    plt.xlabel('Время')
    plt.ylabel('Цена (USD)')
    plt.legend()
    plt.grid(True)
    plt.savefig('bitcoin_prediction_plot.png')
    plt.close()
    
    # Строим график функции потерь
    plt.figure(figsize=(12, 6))
    plt.plot(history.history['loss'], label='Ошибка на обучающей выборке')
    plt.plot(history.history['val_loss'], label='Ошибка на проверочной выборке')
    plt.title('График функции потерь')
    plt.xlabel('Эпоха')
    plt.ylabel('Значение функции потерь')
    plt.legend()
    plt.grid(True)
    plt.savefig('loss_plot.png')
    plt.close()

def main():
    """
    Основная функция
    """
    print("Загружаем данные о цене биткойна...")
    data = get_bitcoin_data()
    
    print("Загружаем данные индекса страха и жадности...")
    fng_data = get_fear_and_greed_index(data.index[0])
    data['FNG'] = fng_data
    print(f"Индекс страха и жадности добавлен, диапазон: {data['FNG'].min():.2f} - {data['FNG'].max():.2f}\n")
    
    # Добавляем технические индикаторы
    data = add_technical_indicators(data)
    
    print("Используемые признаки:", ", ".join([
        'Close', 'Volume', 'FNG', 
        'RSI', 'MACD', 'Signal_Line', 
        'BB_middle', 'BB_upper', 'BB_lower', 
        'VROC', 'PVT', 'OBV',
        'ATR', 'Stoch_K', 'Stoch_D', 
        'EMA_9', 'EMA_21', 'CMF', 'ADX'
    ]))
    
    print(f"\nПоследняя известная цена биткойна: ${data['Close'].iloc[-1]:,.2f}")
    
    # Подготовка данных для обучения
    look_back = 30
    train_X, train_y, test_X, test_y, close_scaler, price_scaler, volume_scaler, indicator_scaler, last_data = prepare_data(data, look_back)
    
    # Создание и обучение модели
    model = create_model(input_shape=(look_back, train_X.shape[2]))
    history = train_model(model, train_X, train_y, test_X, test_y)
    save_model(model)
    
    # Получение последних данных для прогноза
    features = [
        'Close', 'Volume', 'FNG', 
        'RSI', 'MACD', 'Signal_Line', 
        'BB_middle', 'BB_upper', 'BB_lower', 
        'VROC', 'PVT', 'OBV',
        'ATR', 'Stoch_K', 'Stoch_D', 
        'EMA_9', 'EMA_21', 'CMF', 'ADX'
    ]
    last_data = data.iloc[-look_back:][features].values
    
    # Масштабируем данные по группам
    close_price = last_data[:, [0]]  # Только цена закрытия
    price_features = last_data[:, [6, 7, 8]]  # BB_middle, BB_upper, BB_lower
    volume_features = last_data[:, [1, 10, 11]]  # Volume, PVT, OBV
    indicator_features = last_data[:, [2, 3, 4, 5, 9, 12, 13, 14, 15, 16, 17, 18]]  # FNG, RSI, MACD, Signal_Line, VROC, ATR, Stoch_K, Stoch_D, EMA_9, EMA_21, CMF, ADX
    
    # Масштабируем каждую группу отдельно
    scaled_close = close_scaler.transform(close_price)
    scaled_prices = price_scaler.transform(price_features)
    scaled_volumes = volume_scaler.transform(volume_features)
    scaled_indicators = indicator_scaler.transform(indicator_features)
    
    # Собираем масштабированные данные обратно
    last_data_scaled = np.zeros_like(last_data)
    last_data_scaled[:, 0] = scaled_close.reshape(-1)  # Close
    last_data_scaled[:, 1] = scaled_volumes[:, 0]  # Volume
    last_data_scaled[:, 2:6] = scaled_indicators[:, :4]  # FNG, RSI, MACD, Signal_Line
    last_data_scaled[:, 6:9] = scaled_prices  # BB_middle, BB_upper, BB_lower
    last_data_scaled[:, 9] = scaled_indicators[:, 4]  # VROC
    last_data_scaled[:, 10:12] = scaled_volumes[:, 1:]  # PVT, OBV
    last_data_scaled[:, 12:] = scaled_indicators[:, 5:]  # ATR, Stoch_K, Stoch_D, EMA_9, EMA_21, CMF, ADX
    
    last_data_reshaped = last_data_scaled.reshape((1, look_back, len(features)))
    
    # Прогноз на следующие 30 дней
    print("\nПрогноз цены биткойна на следующие 30 дней:")
    future_prices = predict_future(model, last_data_reshaped, look_back, num_days=30, scaler=close_scaler)
    
    if future_prices is not None:
        for i, price in enumerate(future_prices, 1):
            print(f"День {i}: ${price:,.2f}")
    
    # Построение графиков
    plot_results(data['Close'].values, train_y, test_y, look_back, history)

if __name__ == "__main__":
    main()
