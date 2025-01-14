"""
Технические индикаторы для анализа цены Bitcoin
"""

import pandas as pd
import numpy as np
from typing import Dict
import ta

def calculate_rsi(data: pd.DataFrame, period: int = 14) -> pd.Series:
    """Расчет RSI"""
    return ta.momentum.RSIIndicator(data['price'], window=period).rsi()

def calculate_macd(data: pd.DataFrame) -> pd.DataFrame:
    """Расчет MACD"""
    macd = ta.trend.MACD(data['price'])
    return pd.DataFrame({
        'macd': macd.macd(),
        'macd_signal': macd.macd_signal(),
        'macd_diff': macd.macd_diff()
    })

def calculate_bollinger_bands(data: pd.DataFrame, window: int = 20) -> pd.DataFrame:
    """Расчет Bollinger Bands"""
    bollinger = ta.volatility.BollingerBands(data['price'], window=window)
    return pd.DataFrame({
        'bb_high': bollinger.bollinger_hband(),
        'bb_mid': bollinger.bollinger_mavg(),
        'bb_low': bollinger.bollinger_lband()
    })

def calculate_atr(data: pd.DataFrame, period: int = 14) -> pd.Series:
    """Расчет Average True Range"""
    return ta.volatility.AverageTrueRange(
        high=data['high'],
        low=data['low'],
        close=data['price'],
        window=period
    ).average_true_range()

def calculate_stochastic(data: pd.DataFrame) -> pd.DataFrame:
    """Расчет Stochastic Oscillator"""
    stoch = ta.momentum.StochasticOscillator(
        high=data['high'],
        low=data['low'],
        close=data['price']
    )
    return pd.DataFrame({
        'stoch_k': stoch.stoch(),
        'stoch_d': stoch.stoch_signal()
    })

def calculate_cmf(data: pd.DataFrame) -> pd.Series:
    """Расчет Chaikin Money Flow"""
    return ta.volume.ChaikinMoneyFlowIndicator(
        high=data['high'],
        low=data['low'],
        close=data['price'],
        volume=data['volume']
    ).chaikin_money_flow()

def calculate_adx(data: pd.DataFrame) -> pd.Series:
    """Расчет Average Directional Index"""
    return ta.trend.ADXIndicator(
        high=data['high'],
        low=data['low'],
        close=data['price']
    ).adx()

def calculate_obv(data: pd.DataFrame) -> pd.Series:
    """Расчет On-Balance Volume"""
    return ta.volume.OnBalanceVolumeIndicator(
        close=data['price'],
        volume=data['volume']
    ).on_balance_volume()

def calculate_volatility(data: pd.DataFrame, window: int = 20) -> pd.Series:
    """Расчет волатильности"""
    return data['price'].pct_change().rolling(window=window).std()

def calculate_indicators(data: pd.DataFrame) -> pd.DataFrame:
    """
    Расчет всех технических индикаторов
    
    Args:
        data: DataFrame с ценовыми данными
        
    Returns:
        DataFrame с техническими индикаторами
    """
    indicators = pd.DataFrame()
    
    # Momentum indicators
    indicators['rsi'] = calculate_rsi(data)
    indicators = pd.concat([indicators, calculate_macd(data)], axis=1)
    indicators = pd.concat([indicators, calculate_stochastic(data)], axis=1)
    
    # Trend indicators
    indicators = pd.concat([indicators, calculate_bollinger_bands(data)], axis=1)
    indicators['adx'] = calculate_adx(data)
    
    # Volume indicators
    indicators['obv'] = calculate_obv(data)
    indicators['cmf'] = calculate_cmf(data)
    
    # Volatility indicators
    indicators['atr'] = calculate_atr(data)
    indicators['volatility'] = calculate_volatility(data)
    
    return indicators

def add_technical_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Добавляет технические индикаторы к DataFrame
    
    Args:
        df: DataFrame с данными
        
    Returns:
        DataFrame с добавленными индикаторами
    """
    # Копируем DataFrame чтобы не изменять оригинал
    df = df.copy()
    
    # Приводим названия столбцов к нижнему регистру
    df.columns = df.columns.str.lower()
    
    # Базовые ценовые признаки
    df = df[['close', 'volume']]  # Оставляем только нужные столбцы
    
    # Долгосрочные технические индикаторы
    close_series = pd.Series(df['close'].values.squeeze(), index=df.index)
    
    # 1. Долгосрочный RSI (90 дней)
    df['long_term_rsi'] = ta.momentum.rsi(close_series, window=90)
    
    # 2. Долгосрочная волатильность (90 дней)
    close_pct_change = close_series.pct_change()
    df['long_term_volatility'] = close_pct_change.rolling(window=90).std()
    
    # 3. Долгосрочная SMA (90 дней)
    df['long_term_sma'] = ta.trend.sma_indicator(close_series, window=90)
    
    # 4. Долгосрочный MACD (26, 12, 9)
    macd = ta.trend.MACD(close_series)
    df['macd'] = macd.macd()
    df['macd_signal'] = macd.macd_signal()
    df['macd_diff'] = macd.macd_diff()
    
    # 5. Долгосрочные уровни Bollinger (90 дней)
    bollinger = ta.volatility.BollingerBands(close_series, window=90)
    df['bollinger_high'] = bollinger.bollinger_hband()
    df['bollinger_low'] = bollinger.bollinger_lband()
    df['bollinger_middle'] = bollinger.bollinger_mavg()
    
    # 6. Объемные индикаторы
    volume_series = pd.Series(df['volume'].values.squeeze(), index=df.index)
    df['volume_sma'] = ta.trend.sma_indicator(volume_series, window=90)
    df['volume_ema'] = ta.trend.ema_indicator(volume_series, window=90)
    
    # Заполняем пропущенные значения
    df = df.ffill().bfill()
    
    # Нормализация
    for column in df.columns:
        if column not in ['close', 'volume']:  # Не нормализуем базовые признаки
            df[column] = (df[column] - df[column].mean()) / df[column].std()
    
    return df

def calculate_technical_indicators(data):
    # Создаем копию данных
    df = data.copy()
    
    # Рассчитываем технические индикаторы
    df['SMA_5'] = df['Close'].rolling(window=5).mean()
    df['SMA_20'] = df['Close'].rolling(window=20).mean()
    
    # Momentum
    df['Momentum'] = df['Close'] - df['Close'].shift(4)
    
    # Stochastic K%
    df['Stoch K'] = (df['Close'] - df['Low'].rolling(window=14).min()) / \
                  (df['High'].rolling(window=14).max() - df['Low'].rolling(window=14).min()) * 100
    
    # Stochastic D%
    df['Stoch D'] = df['Stoch K'].rolling(window=3).mean()
    
    # ROC
    df['ROC'] = ((df['Close'] - df['Close'].shift(12)) / (df['Close'].shift(12))) * 100
    
    # Williams %R
    df['R%'] = (df['High'].rolling(window=14).max() - df['Close']) / (df['High'].rolling(window=14).max() - df['Low'].rolling(window=14).min()) * -100
    
    # A/D Oscillator
    df['HL'] = df['High'] - df['Low']
    df['HC'] = abs(df['High'] - df['Close'].shift())
    df['LC'] = abs(df['Low'] - df['Close'].shift())
    df['TR'] = df[['HL', 'HC', 'LC']].max(axis=1)
    df['DMPlus'] = ((df['High'] - df['High'].shift()) > (df['Low'].shift() - df['Low'])) & (df['High'] - df['High'].shift() > 0) 
    df['DMMinus'] = ((df['Low'].shift() - df['Low']) > (df['High'] - df['High'].shift())) & (df['Low'].shift() - df['Low'] > 0)
    
    # Преобразуем булевы значения в числовые
    df['DMPlus'] = df['DMPlus'].astype(int)
    df['DMMinus'] = df['DMMinus'].astype(int)
    
    # Умножаем на TR
    df['DMPlus'] = df['DMPlus'] * df['TR']
    df['DMMinus'] = df['DMMinus'] * df['TR']
    
    # Рассчитываем ADX
    df['DIPlus'] = df['DMPlus'].rolling(window=14).mean() / df['TR'].rolling(window=14).mean() * 100
    df['DIMinus'] = df['DMMinus'].rolling(window=14).mean() / df['TR'].rolling(window=14).mean() * 100
    df['DIDiff'] = abs(df['DIPlus'] - df['DIMinus'])
    df['DISum'] = df['DIPlus'] + df['DIMinus']
    df['DX'] = df['DIDiff'] / df['DISum'] * 100
    df['ADX'] = df['DX'].rolling(window=14).mean()
    
    # CCI 
    df['TP'] = (df['High'] + df['Low'] + df['Close']) / 3
    df['TPSMA'] = df['TP'].rolling(window=20).mean()
    df['TPMAD'] = df['TP'].rolling(window=20).apply(lambda x: abs(x - x.mean()).mean())
    df['CCI'] = (df['TP'] - df['TPSMA']) / (0.015 * df['TPMAD'])
    
    # Bollinger Bands
    bb_middle, bb_upper, bb_lower = calculate_bollinger_bands(df)
    df['BB_Middle'] = bb_middle
    df['BB_Upper'] = bb_upper
    df['BB_Lower'] = bb_lower
    
    # RSI
    df['Diff'] = df['Close'].diff()
    df['Gain'] = df['Diff'].clip(lower=0)
    df['Loss'] = -df['Diff'].clip(upper=0)
    df['MAgain'] = df['Gain'].rolling(14).mean()
    df['MALoss'] = df['Loss'].rolling(14).mean()
    df['RS'] = df['MAgain'] / df['MALoss']
    df['RSI'] = 100 - (100 / (1 + df['RS']))
    
    # Удаляем промежуточные колонки
    columns_to_drop = ['L14', 'H14', 'HL', 'HC', 'LC', 'TR', 'DMPlus', 'DMMinus', 
                      'DIPlus', 'DIMinus', 'DIDiff', 'DISum', 'DX', 'TP', 'TPSMA', 
                      'TPMAD', 'Diff', 'Gain', 'Loss', 'MAgain', 'MALoss', 'RS']
    df.drop(columns=columns_to_drop, inplace=True, errors='ignore')
    
    return df
