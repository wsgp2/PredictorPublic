import pandas as pd
import numpy as np
from typing import Tuple, Optional

class TechnicalIndicators:
    """Класс для расчета технических индикаторов"""
    
    @staticmethod
    def calculate_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
        """
        Рассчитывает индикатор RSI (Relative Strength Index)
        
        Args:
            prices: Серия цен закрытия
            period: Период для расчета (по умолчанию 14)
            
        Returns:
            pd.Series: Значения RSI
        """
        delta = prices.diff()
        
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    @staticmethod
    def calculate_macd(prices: pd.Series, 
                      fast_period: int = 12,
                      slow_period: int = 26,
                      signal_period: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        Рассчитывает индикатор MACD (Moving Average Convergence Divergence)
        
        Args:
            prices: Серия цен закрытия
            fast_period: Период быстрой EMA (по умолчанию 12)
            slow_period: Период медленной EMA (по умолчанию 26)
            signal_period: Период сигнальной линии (по умолчанию 9)
            
        Returns:
            Tuple[pd.Series, pd.Series, pd.Series]: MACD, Signal, Histogram
        """
        exp1 = prices.ewm(span=fast_period, adjust=False).mean()
        exp2 = prices.ewm(span=slow_period, adjust=False).mean()
        macd = exp1 - exp2
        signal = macd.ewm(span=signal_period, adjust=False).mean()
        hist = macd - signal
        
        return macd, signal, hist
    
    @staticmethod
    def calculate_bollinger_bands(prices: pd.Series,
                                period: int = 20,
                                num_std: float = 2.0) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        Рассчитывает Bollinger Bands
        
        Args:
            prices: Серия цен закрытия
            period: Период для расчета (по умолчанию 20)
            num_std: Количество стандартных отклонений (по умолчанию 2)
            
        Returns:
            Tuple[pd.Series, pd.Series, pd.Series]: Upper Band, Middle Band, Lower Band
        """
        middle_band = prices.rolling(window=period).mean()
        std = prices.rolling(window=period).std()
        
        upper_band = middle_band + (std * num_std)
        lower_band = middle_band - (std * num_std)
        
        return upper_band, middle_band, lower_band
    
    @staticmethod
    def calculate_atr(high: pd.Series,
                     low: pd.Series,
                     close: pd.Series,
                     period: int = 14) -> pd.Series:
        """
        Рассчитывает ATR (Average True Range)
        
        Args:
            high: Серия максимальных цен
            low: Серия минимальных цен
            close: Серия цен закрытия
            period: Период для расчета (по умолчанию 14)
            
        Returns:
            pd.Series: Значения ATR
        """
        prev_close = close.shift(1)
        tr = pd.DataFrame({
            'hl': high - low,
            'hc': abs(high - prev_close),
            'lc': abs(low - prev_close)
        }).max(axis=1)
        
        atr = tr.rolling(window=period).mean()
        return atr
    
    @staticmethod
    def calculate_stochastic(high: pd.Series,
                           low: pd.Series,
                           close: pd.Series,
                           k_period: int = 14,
                           d_period: int = 3) -> Tuple[pd.Series, pd.Series]:
        """
        Рассчитывает Stochastic Oscillator
        
        Args:
            high: Серия максимальных цен
            low: Серия минимальных цен
            close: Серия цен закрытия
            k_period: Период для %K (по умолчанию 14)
            d_period: Период для %D (по умолчанию 3)
            
        Returns:
            Tuple[pd.Series, pd.Series]: %K, %D
        """
        lowest_low = low.rolling(window=k_period).min()
        highest_high = high.rolling(window=k_period).max()
        
        k = 100 * ((close - lowest_low) / (highest_high - lowest_low))
        d = k.rolling(window=d_period).mean()
        
        return k, d
    
    @staticmethod
    def calculate_obv(close: pd.Series, volume: pd.Series) -> pd.Series:
        """
        Рассчитывает OBV (On Balance Volume)
        
        Args:
            close: Серия цен закрытия
            volume: Серия объемов
            
        Returns:
            pd.Series: Значения OBV
        """
        price_change = close.diff()
        obv = pd.Series(0, index=close.index)
        
        obv[price_change > 0] = volume[price_change > 0]
        obv[price_change < 0] = -volume[price_change < 0]
        
        return obv.cumsum()
    
    def calculate_all_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Рассчитывает все технические индикаторы
        
        Args:
            df: DataFrame с данными OHLCV
            
        Returns:
            pd.DataFrame: DataFrame с добавленными индикаторами
        """
        result = df.copy()
        
        # RSI
        result['RSI'] = self.calculate_rsi(result['close'])
        
        # MACD
        result['MACD'], result['MACD_Signal'], result['MACD_Hist'] = \
            self.calculate_macd(result['close'])
        
        # Bollinger Bands
        result['BB_Upper'], result['BB_Middle'], result['BB_Lower'] = \
            self.calculate_bollinger_bands(result['close'])
        
        # ATR
        result['ATR'] = self.calculate_atr(result['high'], result['low'], result['close'])
        
        # Stochastic
        result['Stoch_K'], result['Stoch_D'] = \
            self.calculate_stochastic(result['high'], result['low'], result['close'])
        
        # OBV
        if 'volume' in result.columns:
            result['OBV'] = self.calculate_obv(result['close'], result['volume'])
        
        # Moving Averages
        for period in [20, 50, 100, 200]:
            result[f'SMA_{period}'] = result['close'].rolling(window=period).mean()
            result[f'EMA_{period}'] = result['close'].ewm(span=period, adjust=False).mean()
        
        return result
