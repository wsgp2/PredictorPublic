"""
Подготовка признаков для разных моделей ансамбля
"""

import logging
from datetime import datetime, timedelta
import pytz
import pandas as pd
import numpy as np
import yfinance as yf
import requests
import ta
from .technical_indicators import add_technical_indicators
from .sentiment_analysis import SentimentAnalyzer
from .google_trends import get_google_trends
from .institutional_data import (
    ETFDataCollector,
    WhaleAnalyzer,
    InstitutionalMetricsCollector
)
from .logger import setup_logger
from typing import List, Dict, Optional, Tuple, Union
import io
import os

# Настраиваем логгер
logger = setup_logger(__name__)

def prepare_short_term_features(data: pd.DataFrame, sentiment_analyzer: SentimentAnalyzer = None) -> pd.DataFrame:
    """
    Подготовка 10 признаков для краткосрочной модели (1-7 дней)
    Требуется минимум 37 дней данных:
    - 30 дней для исторического контекста
    - 7 дней для прогноза
    """
    try:
        # Проверяем наличие необходимых колонок
        required_columns = ['open', 'high', 'low', 'close', 'volume']
        missing_columns = [col for col in required_columns if col not in data.columns]
        if missing_columns:
            logger.error(f"Отсутствуют необходимые колонки: {missing_columns}")
            return None
            
        # Проверяем количество записей (минимум 37 дней)
        if len(data) < 37:
            logger.error(f"Недостаточно данных для обработки. Требуется минимум 37 записей")
            return None
            
        # Убеждаемся, что индекс в UTC
        if not isinstance(data.index, pd.DatetimeIndex):
            data.index = pd.to_datetime(data.index)
        if data.index.tz is None:
            data.index = data.index.tz_localize('UTC')
        elif str(data.index.tz) != 'UTC':
            data.index = data.index.tz_convert('UTC')
            
        features = pd.DataFrame(index=data.index)
        
        # 1-4. Цены (4 признака)
        features['open'] = data['open']
        features['high'] = data['high']
        features['low'] = data['low']
        features['close'] = data['close']
        
        # 5. Объем (1 признак)
        features['volume'] = data['volume']
        
        # 6. RSI (1 признак)
        close_series = pd.Series(data['close'].values.squeeze(), index=data.index)
        features['rsi'] = ta.momentum.rsi(close_series, window=14)
        
        # 7. MACD (1 признак)
        macd = ta.trend.MACD(close_series)
        features['macd'] = macd.macd()
        
        # 8-9. Reddit настроение и индекс страха и жадности (2 признака)
        if sentiment_analyzer is not None:
            sentiment_features = sentiment_analyzer.prepare_sentiment_features(
                data.index[0].to_pydatetime(), 
                data.index[-1].to_pydatetime()
            )
            if not sentiment_features.empty:
                features['reddit_sentiment'] = sentiment_features['sentiment']
                features['fear_greed_index'] = sentiment_features['fear_greed_index']
            else:
                features['reddit_sentiment'] = 0.0
                features['fear_greed_index'] = 0.0
        else:
            features['reddit_sentiment'] = 0.0
            features['fear_greed_index'] = 0.0
            
        # 10. Волатильность (1 признак)
        close_pct_change = pd.Series(data['close'].values.squeeze(), index=data.index).pct_change()
        features['volatility'] = close_pct_change.rolling(window=7).std()
        
        # Заполняем пропущенные значения
        features = features.ffill().bfill()
        
        # Убеждаемся, что у нас ровно 10 признаков
        expected_columns = [
            'open', 'high', 'low', 'close',  # 4 признака цены
            'volume',  # 1 признак объема
            'rsi',  # 1 признак RSI
            'macd',  # 1 признак MACD
            'reddit_sentiment', 'fear_greed_index',  # 2 признака настроений
            'volatility'  # 1 признак волатильности
        ]
        
        # Проверяем наличие всех признаков
        for col in expected_columns:
            if col not in features.columns:
                features[col] = 0  # Заполняем нулями отсутствующие признаки
        
        return features
        
    except Exception as e:
        logger.error(f"Ошибка при подготовке краткосрочных признаков: {str(e)}")
        return None

def prepare_medium_term_features(data: pd.DataFrame, sentiment_analyzer: SentimentAnalyzer = None) -> pd.DataFrame:
    """
    Подготовка 15 признаков для среднесрочной модели (7-30 дней)
    Требуется минимум 60 дней данных:
    - 30 дней для исторического контекста
    - 30 дней для прогноза
    """
    try:
        # Проверяем наличие необходимых колонок
        required_columns = ['open', 'high', 'low', 'close', 'volume']
        missing_columns = [col for col in required_columns if col not in data.columns]
        if missing_columns:
            logger.error(f"Отсутствуют необходимые колонки: {missing_columns}")
            return None
            
        # Проверяем количество записей (минимум 60 дней)
        if len(data) < 60:
            logger.error(f"Недостаточно данных для обработки. Требуется минимум 60 записей")
            return None
            
        features = pd.DataFrame(index=data.index)
        
        # 1-4. Цены (4 признака)
        features['open'] = data['open']
        features['high'] = data['high']
        features['low'] = data['low']
        features['close'] = data['close']
        
        # 5. Объем (1 признак)
        features['volume'] = data['volume']
        
        # 6. RSI (1 признак)
        close_series = pd.Series(data['close'].values.squeeze(), index=data.index)
        features['rsi'] = ta.momentum.rsi(close_series, window=14)
        
        # 7. MACD (1 признак)
        macd = ta.trend.MACD(close_series)
        features['macd'] = macd.macd()
        
        # 8-9. Reddit настроение и индекс страха и жадности (2 признака)
        if sentiment_analyzer is not None:
            sentiment_features = sentiment_analyzer.prepare_sentiment_features(
                data.index[0].to_pydatetime(), 
                data.index[-1].to_pydatetime()
            )
            if not sentiment_features.empty:
                features['reddit_sentiment'] = sentiment_features['sentiment']
                features['fear_greed_index'] = sentiment_features['fear_greed_index']
            else:
                features['reddit_sentiment'] = 0.0
                features['fear_greed_index'] = 0.0
        else:
            features['reddit_sentiment'] = 0.0
            features['fear_greed_index'] = 0.0
            
        # 10. Волатильность (1 признак)
        close_pct_change = pd.Series(data['close'].values.squeeze(), index=data.index).pct_change()
        features['volatility'] = close_pct_change.rolling(window=7).std()
            
        # 11. Bollinger Bands (1 признак)
        bb = ta.volatility.BollingerBands(close_series, window=20)
        features['bb_width'] = (bb.bollinger_hband() - bb.bollinger_lband()) / close_series
        
        # 12. S&P 500 корреляция (1 признак)
        try:
            sp500_features = prepare_sp500_features(data)
            if not sp500_features.empty:
                features['sp500_corr'] = sp500_features['sp500_correlation']
            else:
                features['sp500_corr'] = 0.0
        except Exception as e:
            logger.error(f"Ошибка при получении данных S&P 500: {e}")
            features['sp500_corr'] = 0.0
            
        # 13-14. ETF метрики (2 признака)
        try:
            etf_collector = ETFDataCollector()
            etf_data = etf_collector.get_etf_data(
                data.index[0].to_pydatetime(),
                data.index[-1].to_pydatetime()
            )
            if not etf_data.empty:
                features['etf_flows'] = etf_data['flows']
                features['etf_holdings'] = etf_data['holdings']
            else:
                features['etf_flows'] = 0.0
                features['etf_holdings'] = 0.0
        except Exception as e:
            logger.error(f"Ошибка при получении ETF данных: {e}")
            features['etf_flows'] = 0.0
            features['etf_holdings'] = 0.0
            
        # 15. Доминирование Bitcoin (1 признак)
        try:
            dominance_features = prepare_dominance_features(data)
            if not dominance_features.empty:
                features['btc_dominance'] = dominance_features['btc_dominance']
            else:
                features['btc_dominance'] = 0.0
        except Exception as e:
            logger.error(f"Ошибка при получении данных о доминировании: {e}")
            features['btc_dominance'] = 0.0
            
        # Заполняем пропущенные значения
        features = features.ffill().bfill()
        
        return features
        
    except Exception as e:
        logger.error(f"Ошибка при подготовке среднесрочных признаков: {str(e)}")
        return None

def prepare_trend_features(data: pd.DataFrame, sentiment_analyzer: SentimentAnalyzer = None) -> pd.DataFrame:
    """
    Подготовка признаков для модели тренда (30-90 дней)
    """
    try:
        # Создаем базовые признаки
        features = pd.DataFrame(index=data.index)
        
        # Базовые ценовые признаки
        features['close'] = data['close']
        features['volume'] = data['volume']
        
        # Долгосрочные технические индикаторы
        close_series = pd.Series(data['close'].values.squeeze(), index=data.index)
        
        # 1. Долгосрочный RSI (90 дней)
        features['long_term_rsi'] = ta.momentum.rsi(close_series, window=90)
        
        # 2. Долгосрочная волатильность (90 дней)
        close_pct_change = close_series.pct_change()
        features['long_term_volatility'] = close_pct_change.rolling(window=90).std()
        
        # 3. Долгосрочная SMA (90 дней)
        features['long_term_sma'] = ta.trend.sma_indicator(close_series, window=90)
        
        # 4. Долгосрочный MACD (26, 12, 9)
        macd = ta.trend.MACD(close_series)
        features['macd'] = macd.macd()
        features['macd_signal'] = macd.macd_signal()
        features['macd_diff'] = macd.macd_diff()
        
        # 5. Долгосрочные уровни Bollinger (90 дней)
        bollinger = ta.volatility.BollingerBands(close_series, window=90)
        features['bollinger_high'] = bollinger.bollinger_hband()
        features['bollinger_low'] = bollinger.bollinger_lband()
        features['bollinger_middle'] = bollinger.bollinger_mavg()
        
        # 6. Объемные индикаторы
        volume_series = pd.Series(data['volume'].values.squeeze(), index=data.index)
        features['volume_sma'] = ta.trend.sma_indicator(volume_series, window=90)
        features['volume_ema'] = ta.trend.ema_indicator(volume_series, window=90)
        
        # Заполняем пропущенные значения
        features = features.ffill().bfill()
        
        # Нормализация
        for column in features.columns:
            if column != 'close':  # Не нормализуем целевую переменную
                features[column] = (features[column] - features[column].mean()) / features[column].std()
        
        return features
        
    except Exception as e:
        logger.error(f"Ошибка при подготовке признаков тренда: {str(e)}")
        return None

def prepare_sp500_features(data: pd.DataFrame) -> pd.DataFrame:
    """
    Подготовка признаков на основе S&P 500
    """
    try:
        # Получаем данные S&P 500
        sp500_data = get_sp500_data(data.index[0], data.index[-1])
        
        if sp500_data is None:
            logger.error("Не удалось получить данные S&P 500")
            return pd.DataFrame(index=data.index)
            
        logger.info(f"Получено {len(sp500_data)} записей через ^GSPC")
        
        # Если у нас MultiIndex, берем первый уровень
        if isinstance(sp500_data.columns, pd.MultiIndex):
            sp500_data = sp500_data['Close']
        else:
            sp500_data = sp500_data['Close' if 'Close' in sp500_data.columns else 'close']
        
        # Убеждаемся, что индекс в UTC
        if sp500_data.index.tz is None:
            sp500_data.index = sp500_data.index.tz_localize('UTC')
        elif str(sp500_data.index.tz) != 'UTC':
            sp500_data.index = sp500_data.index.tz_convert('UTC')
            
        # Заполняем пропущенные значения
        sp500_data = sp500_data.ffill().bfill()
        
        logger.info(f"Возвращаем данные с индексом {sp500_data.index[0]} - {sp500_data.index[-1]}")
        
        return sp500_data
        
    except Exception as e:
        logger.error(f"Ошибка при получении данных S&P 500: {str(e)}")
        return pd.Series(dtype=float)

def get_sp500_data(start_date: datetime, end_date: datetime) -> pd.Series:
    """
    Получение данных S&P 500
    """
    try:
        logger.info(f"Получение данных S&P 500 с {start_date} по {end_date}")
        
        # Корректируем даты
        start = start_date
        end = min(end_date, datetime.now(pytz.UTC))
        logger.info(f"Скорректированные даты: с {start} по {end}")
        
        # Получаем данные S&P 500
        sp500_data = yf.download('^GSPC', start=start, end=end)
        
        if sp500_data.empty:
            logger.error("Не удалось получить данные S&P 500")
            return pd.Series(dtype=float)
            
        logger.info(f"Получено {len(sp500_data)} записей через ^GSPC")
        
        # Приводим названия колонок к нижнему регистру
        sp500_data.columns = sp500_data.columns.str.lower()
        
        # Если у нас MultiIndex, берем первый уровень
        if isinstance(sp500_data.columns, pd.MultiIndex):
            sp500_data.columns = sp500_data.columns.get_level_values(-1).str.lower()
            
        # Проверяем наличие колонки close
        if 'close' not in sp500_data.columns:
            logger.error(f"Колонка 'close' не найдена. Доступные колонки: {sp500_data.columns.tolist()}")
            return pd.Series(dtype=float)
            
        sp500_data = sp500_data['close']
        
        # Убеждаемся, что индекс в UTC
        if sp500_data.index.tz is None:
            sp500_data.index = sp500_data.index.tz_localize('UTC')
        elif str(sp500_data.index.tz) != 'UTC':
            sp500_data.index = sp500_data.index.tz_convert('UTC')
            
        # Заполняем пропущенные значения
        sp500_data = sp500_data.ffill().bfill()
        
        logger.info(f"Возвращаем данные с индексом {sp500_data.index[0]} - {sp500_data.index[-1]}")
        
        return sp500_data
        
    except Exception as e:
        logger.error(f"Ошибка при получении данных S&P 500: {str(e)}")
        return pd.Series(dtype=float)

def get_bitcoin_dominance(start_date: datetime, end_date: datetime) -> pd.Series:
    """
    Получение данных о доминировании Bitcoin на рынке
    """
    try:
        # Получаем данные о доминировании Bitcoin через API CoinGecko
        # Используем тикер BTC.D
        btc_dominance = yf.download('BTC.D', start=start_date, end=end_date)
        
        if btc_dominance.shape[0] > 0:
            # Если у нас MultiIndex, берем первый уровень
            if isinstance(btc_dominance.columns, pd.MultiIndex):
                btc_dominance.columns = btc_dominance.columns.get_level_values(1)
            
            # Приводим названия колонок к нижнему регистру
            btc_dominance.columns = [col.lower() if isinstance(col, str) else col for col in btc_dominance.columns]
            
            # Убеждаемся, что индекс в UTC
            if btc_dominance.index.tz is None:
                btc_dominance.index = btc_dominance.index.tz_localize('UTC')
            elif str(btc_dominance.index.tz) != 'UTC':
                btc_dominance.index = btc_dominance.index.tz_convert('UTC')
            
            if 'close' in btc_dominance.columns:
                result = btc_dominance['close'].copy()
                if result.size > 0:
                    return result.astype(float)
                else:
                    logger.error("Колонка close пуста")
                    return pd.Series(dtype=float)
            elif 'adj close' in btc_dominance.columns:
                result = btc_dominance['adj close'].copy()
                if result.size > 0:
                    return result.astype(float)
                else:
                    logger.error("Колонка adj close пуста")
                    return pd.Series(dtype=float)
            else:
                logger.error(f"Не найдены колонки с ценами закрытия. Доступные колонки: {btc_dominance.columns.tolist()}")
                return pd.Series(dtype=float)
        else:
            logger.warning("Не удалось получить данные о доминировании Bitcoin")
            return pd.Series(dtype=float)
            
    except Exception as e:
        logger.error(f"Ошибка при получении данных о доминировании Bitcoin: {e}")
        return pd.Series(dtype=float)

def get_network_hashrate(start_date: datetime, end_date: datetime) -> pd.Series:
    """
    Получение данных о хэшрейте сети Bitcoin
    Временно отключено до получения стабильного API
    """
    logger.warning("Получение данных о хэшрейте временно отключено")
    return pd.Series(dtype=float)

def get_network_difficulty(start_date: datetime, end_date: datetime) -> pd.Series:
    """
    Получение данных о сложности сети Bitcoin
    Временно отключено до получения стабильного API
    """
    logger.warning("Получение данных о сложности сети временно отключено")
    return pd.Series(dtype=float)

def prepare_dominance_features(data: pd.DataFrame) -> pd.DataFrame:
    """
    Подготовка признаков доминирования Bitcoin
    """
    try:
        features = pd.DataFrame(index=data.index)
        
        # Пока что просто заполняем нулями, так как у нас нет данных
        features['btc_dominance'] = 0.0
        features['btc_dominance_change'] = 0.0
        features['btc_market_share'] = 0.0
        
        return features
        
    except Exception as e:
        logger.error(f"Ошибка при подготовке признаков доминирования: {str(e)}")
        return pd.DataFrame()

def prepare_mining_features(data: pd.DataFrame) -> pd.DataFrame:
    """
    Подготовка признаков майнинга
    """
    try:
        features = pd.DataFrame(index=data.index)
        
        # Пока что просто заполняем нулями, так как у нас нет данных
        features['hash_rate'] = 0.0
        features['mining_difficulty'] = 0.0
        features['transaction_fees'] = 0.0
        
        return features
        
    except Exception as e:
        logger.error(f"Ошибка при подготовке признаков майнинга: {str(e)}")
        return pd.DataFrame()

def prepare_institutional_features(data: pd.DataFrame) -> pd.DataFrame:
    """
    Подготовка признаков на основе институциональных данных
    Временно отключено
    """
    logger.warning("Подготовка институциональных признаков временно отключена")
    return pd.DataFrame(index=data.index)

def prepare_data(price_data: pd.DataFrame) -> pd.DataFrame:
    """
    Подготовка данных для моделей
    """
    try:
        # Проверяем наличие необходимых колонок
        required_columns = ['close', 'open', 'high', 'low', 'volume']
        missing_columns = [col for col in required_columns if col not in price_data.columns]
        if missing_columns:
            logger.error(f"Отсутствуют необходимые колонки: {missing_columns}")
            return None
            
        # Проверяем, что у нас достаточно данных (минимум 37 дней)
        if len(price_data) < 37:
            logger.error(f"Недостаточно данных для обучения: {len(price_data)} записей")
            return None
            
        # Убеждаемся, что индекс в UTC
        if not isinstance(price_data.index, pd.DatetimeIndex):
            price_data.index = pd.to_datetime(price_data.index)
        if price_data.index.tz is None:
            price_data.index = price_data.index.tz_localize('UTC')
        elif str(price_data.index.tz) != 'UTC':
            price_data.index = price_data.index.tz_convert('UTC')
            
        # Создаем признаки
        data = pd.DataFrame(index=price_data.index)
        
        # Копируем основные ценовые данные
        for col in required_columns:
            data[col] = price_data[col]
            
        # Технические индикаторы
        for window in [7, 14, 30, 60]:
            # SMA
            data[f'sma_{window}'] = ta.trend.sma_indicator(data['close'], window=window)
            
            # EMA
            data[f'ema_{window}'] = ta.trend.ema_indicator(data['close'], window=window)
            
            # RSI
            close_series = pd.Series(data['close'].values, index=data.index)
            data[f'rsi_{window}'] = ta.momentum.rsi(close_series, window=window)
            
            # Bollinger Bands
            bb = ta.volatility.BollingerBands(close_series, window=window)
            data[f'bb_upper_{window}'] = bb.bollinger_hband()
            data[f'bb_lower_{window}'] = bb.bollinger_lband()
            data[f'bb_width_{window}'] = (data[f'bb_upper_{window}'] - data[f'bb_lower_{window}']) / data['close']
            
            # MACD
            macd = ta.trend.MACD(close_series)
            data[f'macd_{window}'] = macd.macd()
            data[f'macd_signal_{window}'] = macd.macd_signal()
            data[f'macd_diff_{window}'] = macd.macd_diff()
            
        # Дополнительные признаки
        # Волатильность
        close_pct_change = pd.Series(data['close'].values, index=data.index).pct_change()
        data['volatility'] = close_pct_change.rolling(window=30).std()
        
        # Объем относительно среднего
        data['volume_ma'] = data['volume'].rolling(window=30).mean()
        data['volume_ratio'] = data['volume'] / data['volume_ma']
        
        # Направление тренда
        data['trend'] = np.where(data['close'] > data['sma_30'], 1, -1)
        
        # Моментум
        close_pct_change = pd.Series(data['close'].values, index=data.index).pct_change()
        data['momentum'] = close_pct_change.rolling(window=14).mean()
        
        # Заполняем пропущенные значения
        data = data.ffill().bfill()
        
        # Добавляем признаки настроений
        sentiment_features = prepare_sentiment_features(data)
        if sentiment_features is not None:
            data = pd.concat([data, sentiment_features], axis=1)
            
        # Добавляем признаки S&P 500
        sp500_features = prepare_sp500_features(data)
        if not sp500_features.empty:
            data = pd.concat([data, sp500_features], axis=1)
            
        # Добавляем институциональные признаки
        inst_features = prepare_institutional_features(data)
        if inst_features is not None:
            data = pd.concat([data, inst_features], axis=1)
            
        # Добавляем Google Trends
        trends_features = get_google_trends(data.index)
        if trends_features is not None:
            data = pd.concat([data, trends_features], axis=1)
            
        # Добавляем дни с халвинга
        data['days_since_halving'] = calculate_days_since_halving(data.index)
        
        # Проверяем на пропущенные значения
        if data.isnull().any().any():
            logger.warning("В данных есть пропущенные значения после обработки")
            data = data.ffill().bfill()
            
        return data
        
    except Exception as e:
        logger.error(f"Ошибка при подготовке данных: {str(e)}")
        return None

def calculate_days_since_halving(dates: pd.DatetimeIndex) -> pd.Series:
    """
    Рассчитывает количество дней с последнего халвинга для каждой даты
    """
    # Даты халвингов в UTC
    halving_dates = [
        datetime(2012, 11, 28, tzinfo=tz.tzutc()),
        datetime(2016, 7, 9, tzinfo=tz.tzutc()),
        datetime(2020, 5, 11, tzinfo=tz.tzutc()),
        datetime(2024, 4, 20, tzinfo=tz.tzutc())  # Ожидаемая дата следующего халвинга
    ]
    
    result = []
    for date in dates:
        # Убеждаемся, что дата в UTC
        if date.tzinfo is None:
            date = date.replace(tzinfo=tz.tzutc())
        elif str(date.tzinfo) != 'UTC':
            date = date.astimezone(tz.tzutc())
            
        # Находим последний халвинг перед текущей датой
        last_halving = None
        for halving_date in halving_dates:
            if date >= halving_date:
                last_halving = halving_date
            else:
                break
                
        if last_halving is None:
            days_since = 0
        else:
            days_since = (date - last_halving).days
            
        result.append(days_since)
        
    return pd.Series(result, index=dates)

def get_blockchain_info_data(endpoint: str, start_date: datetime, end_date: datetime) -> pd.Series:
    """
    Получение данных с blockchain.info API
    """
    try:
        # Конвертируем даты в timestamp
        start_timestamp = int(start_date.timestamp())
        end_timestamp = int(end_date.timestamp())
        
        # Формируем URL
        url = f"https://blockchain.info/charts/{endpoint}/download"
        params = {
            'timespan': 'custom',
            'start': start_timestamp,
            'end': end_timestamp,
            'format': 'csv'
        }
        
        # Получаем данные
        response = requests.get(url, params=params)
        response.raise_for_status()
        
        # Преобразуем CSV в DataFrame
        df = pd.read_csv(io.StringIO(response.text))
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s', utc=True)
        df.set_index('timestamp', inplace=True)
        
        # Ресемплируем данные на часовые интервалы
        series = df['value'].resample('H').ffill()
        
        # Обрезаем данные по заданному периоду
        series = series[start_date:end_date]
        
        return series
        
    except Exception as e:
        logger.error(f"Ошибка при получении данных с blockchain.info ({endpoint}): {str(e)}")
        return pd.Series(dtype=float)

def get_network_difficulty(start_date: datetime, end_date: datetime) -> pd.Series:
    """
    Получение данных о сложности сети
    """
    try:
        logger.info("Получение данных о сложности сети")
        return get_blockchain_info_data('difficulty', start_date, end_date)
    except Exception as e:
        logger.error(f"Ошибка при получении данных о сложности сети: {str(e)}")
        return pd.Series(dtype=float)

def get_hash_rate(start_date: datetime, end_date: datetime) -> pd.Series:
    """
    Получение данных о хэшрейте
    """
    try:
        logger.info("Получение данных о хэшрейте")
        return get_blockchain_info_data('hash-rate', start_date, end_date)
    except Exception as e:
        logger.error(f"Ошибка при получении данных о хэшрейте: {str(e)}")
        return pd.Series(dtype=float)

def get_btc_dominance(start_date: datetime, end_date: datetime) -> pd.Series:
    """
    Получение данных о доминировании Bitcoin через CoinMarketCap API
    """
    try:
        api_key = '97682646-1e77-483a-892c-74048766908f'
        headers = {
            'X-CMC_PRO_API_KEY': api_key,
            'Accept': 'application/json'
        }
        
        # Получаем текущие данные
        url = 'https://pro-api.coinmarketcap.com/v1/global-metrics/quotes/latest'
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            btc_dominance = data['data']['btc_dominance']
            current_time = pd.Timestamp.now(tz='UTC')
            
            # Создаем Series с текущим значением
            dominance_series = pd.Series([btc_dominance], index=[current_time])
            
            # Получаем исторические данные через альтернативный источник
            if start_date < current_time:
                historical_dominance = yf.download('BTC-USD', start=start_date, end=end_date)
                if not historical_dominance.empty:
                    total_market_cap = historical_dominance['Close'] * historical_dominance['Volume']
                    btc_market_cap = historical_dominance['Close']
                    historical_btc_dominance = (btc_market_cap / total_market_cap) * 100
                    
                    # Объединяем исторические данные с текущими
                    dominance_series = pd.concat([historical_btc_dominance, dominance_series])
            
            # Заполняем пропущенные значения
            dominance_series = dominance_series.ffill().bfill()
            
            return dominance_series
            
        else:
            logger.error(f"Ошибка при получении данных о доминировании Bitcoin: {response.status_code}")
            return pd.Series(dtype=float)
            
    except Exception as e:
        logger.error(f"Ошибка при получении данных о доминировании Bitcoin: {e}")
        return pd.Series(dtype=float)

def prepare_network_features(data: pd.DataFrame) -> pd.DataFrame:
    """
    Подготовка признаков на основе данных сети
    """
    try:
        # Получаем данные о сложности и хэшрейте
        difficulty = get_network_difficulty(data.index[0], data.index[-1])
        hashrate = get_hash_rate(data.index[0], data.index[-1])
        dominance = get_btc_dominance(data.index[0], data.index[-1])
        
        # Создаем DataFrame с признаками
        features = pd.DataFrame(index=data.index)
        
        # Добавляем признаки, если данные получены успешно
        if not difficulty.empty:
            features['difficulty'] = difficulty.reindex(data.index).ffill().bfill()
            features['difficulty_change'] = features['difficulty'].pct_change()
            
        if not hashrate.empty:
            features['hashrate'] = hashrate.reindex(data.index).ffill().bfill()
            features['hashrate_change'] = features['hashrate'].pct_change()
            
        if not dominance.empty:
            features['btc_dominance'] = dominance.reindex(data.index).ffill().bfill()
            features['dominance_change'] = features['btc_dominance'].pct_change()
            
        # Заполняем оставшиеся пропуски
        features = features.ffill().bfill()
        
        return features
        
    except Exception as e:
        logger.error(f"Ошибка при подготовке сетевых признаков: {str(e)}")
        return pd.DataFrame(index=data.index)
