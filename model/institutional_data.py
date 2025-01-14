"""
Модуль для получения и обработки институциональных данных
"""

import pandas as pd
import yfinance as yf
import requests
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Optional, Tuple
import numpy as np
from concurrent.futures import ThreadPoolExecutor
import pytz

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Список тикеров Bitcoin ETF
BTC_ETF_TICKERS = [
    'IBIT',  # BlackRock
    'FBTC',  # Fidelity
    'ARKB',  # ARK 21Shares
    'BITB',  # Bitwise
]

# Список фьючерсных контрактов CME
CME_FUTURES = [
    'BTC=F',     # Ближайший месяц
]

class InstitutionalMetricsCollector:
    """Класс для сбора институциональных метрик"""
    
    def __init__(self):
        self.cache = {}
        
    def get_cme_data(self, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """
        Получение данных о фьючерсах CME
        """
        try:
            all_futures_data = []
            
            for ticker in CME_FUTURES:
                logger.info(f"Получение данных фьючерсов: {ticker}")
                future = yf.Ticker(ticker)
                
                # Получение исторических данных
                hist = future.history(start=start_date, end=end_date)
                
                if hist.empty:
                    logger.warning(f"Нет данных для {ticker}")
                    continue
                
                # Приводим индекс к UTC
                hist.index = hist.index.tz_localize(None)
                
                # Расчет метрик
                hist['Contract'] = ticker
                hist['Volume_USD'] = hist['Close'] * hist['Volume']
                hist['Daily_Return'] = hist['Close'].pct_change()
                
                # Получение Open Interest если доступно
                if 'Open Interest' in hist.columns:
                    hist['Open_Interest_USD'] = hist['Open Interest'] * hist['Close']
                
                all_futures_data.append(hist)
            
            if not all_futures_data:
                raise ValueError("Не удалось получить данные фьючерсов")
            
            # Объединение данных всех фьючерсов
            combined_data = pd.concat(all_futures_data)
            
            # Получение спот цены
            spot = yf.Ticker("BTC-USD").history(start=start_date, end=end_date)
            spot.index = spot.index.tz_localize(None)
            
            # Агрегация по дням
            daily_data = self._aggregate_futures_data(combined_data, spot)
            
            return daily_data
            
        except Exception as e:
            logger.error(f"Ошибка при получении данных фьючерсов: {e}")
            return pd.DataFrame()
    
    def _aggregate_futures_data(self, data: pd.DataFrame, spot_data: pd.DataFrame) -> pd.DataFrame:
        """
        Агрегация данных фьючерсов по дням
        """
        daily = pd.DataFrame()
        
        # Общий объем торгов
        daily['CME_Volume_USD'] = data.groupby(data.index)['Volume_USD'].sum()
        
        # Средневзвешенная цена
        daily['CME_Weighted_Price'] = (data['Close'] * data['Volume_USD']).groupby(data.index).sum() / \
                                     data['Volume_USD'].groupby(data.index).sum()
        
        # Open Interest
        if 'Open_Interest_USD' in data.columns:
            daily['CME_Open_Interest_USD'] = data.groupby(data.index)['Open_Interest_USD'].sum()
        
        # Расчет премии/дисконта к спот цене
        common_dates = daily.index.intersection(spot_data.index)
        daily = daily.reindex(common_dates)
        spot_data = spot_data.reindex(common_dates)
        
        daily['CME_Basis'] = ((daily['CME_Weighted_Price'] - spot_data['Close']) / spot_data['Close']) * 100
        
        # Градиент премии
        daily['CME_Basis_Gradient'] = daily['CME_Basis'].diff()
        
        return daily
    
    def get_institutional_metrics(self, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """
        Получение всех институциональных метрик
        """
        try:
            # Получение данных фьючерсов
            futures_data = self.get_cme_data(start_date, end_date)
            
            if futures_data.empty:
                return pd.DataFrame()
            
            # Создание DataFrame для всех метрик
            metrics = futures_data.copy()
            
            # Добавление дополнительных метрик
            metrics['Institutional_Activity'] = self._calculate_institutional_activity(metrics)
            metrics['Market_Structure'] = self._calculate_market_structure(metrics)
            
            # Заполнение пропущенных значений
            metrics = metrics.fillna(method='ffill').fillna(method='bfill')
            
            return metrics
            
        except Exception as e:
            logger.error(f"Ошибка при получении институциональных метрик: {e}")
            return pd.DataFrame()
    
    def _calculate_institutional_activity(self, data: pd.DataFrame) -> pd.Series:
        """
        Расчет индекса институциональной активности
        """
        if data.empty or 'CME_Volume_USD' not in data.columns or 'CME_Basis' not in data.columns:
            return pd.Series(index=data.index)
        
        # Нормализация объемов
        volume_z = (data['CME_Volume_USD'] - data['CME_Volume_USD'].mean()) / data['CME_Volume_USD'].std()
        
        # Нормализация базиса
        basis_z = (data['CME_Basis'] - data['CME_Basis'].mean()) / data['CME_Basis'].std()
        
        # Комбинированный индикатор
        activity = (volume_z + basis_z) / 2
        
        return activity
    
    def _calculate_market_structure(self, data: pd.DataFrame) -> pd.Series:
        """
        Расчет индикатора структуры рынка
        """
        if data.empty or 'CME_Basis_Gradient' not in data.columns:
            return pd.Series(index=data.index)
        
        # Используем градиент базиса как индикатор структуры рынка
        structure = data['CME_Basis_Gradient'].rolling(window=5).mean()
        
        return structure

class ETFDataCollector:
    def __init__(self):
        self.cache = {}
        
    def get_etf_data(self, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """
        Получение данных о Bitcoin ETF
        """
        try:
            all_etf_data = []
            
            for ticker in BTC_ETF_TICKERS:
                logger.info(f"Получение данных для ETF: {ticker}")
                etf = yf.Ticker(ticker)
                
                # Получение исторических данных
                hist = etf.history(start=start_date, end=end_date)
                
                if hist.empty:
                    logger.warning(f"Нет данных для {ticker}")
                    continue
                
                # Расчет дополнительных метрик
                hist['ETF_Name'] = ticker
                hist['Volume_USD'] = hist['Close'] * hist['Volume']
                hist['Daily_Return'] = hist['Close'].pct_change()
                
                # Получение информации о фонде
                info = etf.info
                hist['AUM'] = info.get('totalAssets', None)
                
                all_etf_data.append(hist)
            
            if not all_etf_data:
                raise ValueError("Не удалось получить данные ни для одного ETF")
            
            # Объединение данных всех ETF
            combined_data = pd.concat(all_etf_data)
            
            # Агрегация по дням
            daily_data = self._aggregate_daily_data(combined_data)
            
            return daily_data
            
        except Exception as e:
            logger.error(f"Ошибка при получении данных ETF: {e}")
            return pd.DataFrame()
    
    def _aggregate_daily_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Агрегация данных по дням
        """
        try:
            # Создаем DataFrame для агрегированных данных
            daily = pd.DataFrame()
            
            # Агрегируем объем торгов
            daily['Total_Volume_USD'] = data.groupby(data.index)['Volume_USD'].sum()
            
            # Средневзвешенная цена
            daily['Weighted_Price'] = (data['Close'] * data['Volume_USD']).groupby(data.index).sum() / \
                                    data['Volume_USD'].groupby(data.index).sum()
            
            # Количество активных ETF
            daily['Active_ETFs'] = data.groupby(data.index)['ETF_Name'].count()
            
            # Добавляем потоки ETF если они есть
            if 'Estimated_Flow' in data.columns:
                daily['Total_Flow'] = data.groupby(data.index)['Estimated_Flow'].sum()
            
            return daily
        except Exception as e:
            logger.error(f"Ошибка при агрегации данных ETF: {e}")
            return pd.DataFrame()
    
    def get_etf_flows(self, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """
        Получение данных о потоках в/из Bitcoin ETF
        
        Args:
            start_date: Начальная дата
            end_date: Конечная дата
            
        Returns:
            DataFrame с данными о потоках ETF
        """
        try:
            all_flows = []
            
            for ticker in BTC_ETF_TICKERS:
                etf = yf.Ticker(ticker)
                
                # Получение исторических данных
                hist = etf.history(start=start_date, end=end_date)
                
                if hist.empty:
                    continue
                
                # Расчет дневного изменения объема
                hist['Daily_Volume_Change'] = hist['Volume'].diff()
                
                # Оценка потоков на основе изменения объема и цены
                hist['Estimated_Flow'] = hist['Daily_Volume_Change'] * hist['Close']
                
                hist['ETF_Name'] = ticker
                all_flows.append(hist[['ETF_Name', 'Estimated_Flow']])
            
            if not all_flows:
                return pd.DataFrame()
            
            # Объединение данных всех ETF
            combined_flows = pd.concat(all_flows)
            
            # Агрегация по дням
            daily_flows = combined_flows.groupby(['ETF_Name', combined_flows.index])['Estimated_Flow'].sum()
            daily_flows = daily_flows.unstack(level=0)
            
            # Добавление общего потока
            daily_flows['Total_Flow'] = daily_flows.sum(axis=1)
            
            return daily_flows
            
        except Exception as e:
            logger.error(f"Ошибка при получении данных о потоках ETF: {e}")
            return pd.DataFrame()

class WhaleAnalyzer:
    """Класс для анализа активности крупных холдеров Bitcoin"""
    
    def __init__(self):
        self.cache = {}
        self.whale_threshold = 1000  # Минимальное количество BTC для определения кита
        self.api_base_url = "https://api.glassnode.com/v1"
        
    def get_whale_metrics(self, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """
        Получение метрик активности крупных холдеров
        """
        try:
            # Создаем базовый DataFrame
            metrics = pd.DataFrame(index=pd.date_range(start=start_date, end=end_date, freq='D'))
            
            # Получаем различные метрики
            whale_count = self._get_whale_count(start_date, end_date)
            whale_balance = self._get_whale_balance(start_date, end_date)
            whale_transactions = self._get_whale_transactions(start_date, end_date)
            
            # Объединяем все метрики
            if not whale_count.empty:
                metrics['Whale_Count'] = whale_count
            if not whale_balance.empty:
                metrics['Whale_Balance'] = whale_balance
            if not whale_transactions.empty:
                metrics = metrics.join(whale_transactions)
            
            # Добавляем производные метрики
            if not metrics.empty:
                metrics['Whale_Dominance'] = self._calculate_whale_dominance(metrics)
                metrics['Whale_Activity'] = self._calculate_whale_activity(metrics)
            
            return metrics
            
        except Exception as e:
            logger.error(f"Ошибка при получении метрик китов: {e}")
            return pd.DataFrame()
    
    def _get_whale_count(self, start_date: datetime, end_date: datetime) -> pd.Series:
        """
        Получение количества адресов с балансом > whale_threshold BTC
        """
        try:
            # В реальном приложении здесь будет API-запрос
            # Сейчас возвращаем синтетические данные для демонстрации
            dates = pd.date_range(start=start_date, end=end_date, freq='D')
            base_count = 2000  # Базовое количество китов
            
            # Генерируем реалистичные колебания
            noise = np.random.normal(0, 50, size=len(dates))
            trend = np.linspace(0, 100, len(dates))  # Небольшой восходящий тренд
            
            counts = base_count + noise + trend
            return pd.Series(counts, index=dates, name='Whale_Count')
            
        except Exception as e:
            logger.error(f"Ошибка при получении количества китов: {e}")
            return pd.Series()
    
    def _get_whale_balance(self, start_date: datetime, end_date: datetime) -> pd.Series:
        """
        Получение общего баланса крупных холдеров
        """
        try:
            # В реальном приложении здесь будет API-запрос
            # Сейчас возвращаем синтетические данные
            dates = pd.date_range(start=start_date, end=end_date, freq='D')
            base_balance = 5_000_000  # ~25% от общего предложения BTC
            
            # Генерируем реалистичные колебания
            noise = np.random.normal(0, 10000, size=len(dates))
            trend = np.linspace(0, 20000, len(dates))  # Небольшой восходящий тренд
            
            balances = base_balance + noise + trend
            return pd.Series(balances, index=dates, name='Whale_Balance')
            
        except Exception as e:
            logger.error(f"Ошибка при получении баланса китов: {e}")
            return pd.Series()
    
    def _get_whale_transactions(self, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """
        Получение данных о крупных транзакциях
        """
        try:
            # В реальном приложении здесь будет API-запрос
            # Сейчас возвращаем синтетические данные
            dates = pd.date_range(start=start_date, end=end_date, freq='D')
            transactions = pd.DataFrame(index=dates)
            
            # Генерируем данные о транзакциях
            base_volume = 50000  # Базовый дневной объем транзакций китов
            base_count = 100    # Базовое количество транзакций
            
            # Объем транзакций
            noise_vol = np.random.normal(0, 5000, size=len(dates))
            transactions['Whale_Tx_Volume'] = base_volume + noise_vol
            
            # Количество транзакций
            noise_count = np.random.normal(0, 10, size=len(dates))
            transactions['Whale_Tx_Count'] = base_count + noise_count
            
            # Средний размер транзакции
            transactions['Whale_Avg_Tx_Size'] = transactions['Whale_Tx_Volume'] / transactions['Whale_Tx_Count']
            
            return transactions
            
        except Exception as e:
            logger.error(f"Ошибка при получении данных о транзакциях: {e}")
            return pd.DataFrame()
    
    def _calculate_whale_dominance(self, data: pd.DataFrame) -> pd.Series:
        """
        Расчет доминирования китов (% от общего предложения)
        """
        if 'Whale_Balance' not in data.columns:
            return pd.Series(index=data.index)
        
        total_supply = 21_000_000  # Максимальное предложение BTC
        current_supply = 19_600_000  # Примерное текущее предложение
        
        dominance = (data['Whale_Balance'] / current_supply) * 100
        return dominance
    
    def _calculate_whale_activity(self, data: pd.DataFrame) -> pd.Series:
        """
        Расчет индекса активности китов
        """
        if 'Whale_Tx_Volume' not in data.columns or 'Whale_Count' not in data.columns:
            return pd.Series(index=data.index)
        
        # Нормализуем объем транзакций
        volume_z = (data['Whale_Tx_Volume'] - data['Whale_Tx_Volume'].mean()) / data['Whale_Tx_Volume'].std()
        
        # Нормализуем количество китов
        count_z = (data['Whale_Count'] - data['Whale_Count'].mean()) / data['Whale_Count'].std()
        
        # Комбинированный индикатор
        activity = (volume_z + count_z) / 2
        return activity

def prepare_institutional_features(start_date: datetime, end_date: datetime) -> pd.DataFrame:
    """
    Подготовка всех институциональных признаков
    """
    try:
        # Убедимся, что даты в UTC
        if not start_date.tzinfo:
            start_date = start_date.replace(tzinfo=pytz.UTC)
        if not end_date.tzinfo:
            end_date = end_date.replace(tzinfo=pytz.UTC)

        # Инициализация коллекторов данных
        etf_collector = ETFDataCollector()
        inst_collector = InstitutionalMetricsCollector()
        whale_analyzer = WhaleAnalyzer()

        # Получение данных из разных источников
        etf_data = etf_collector.get_etf_data(start_date, end_date)
        cme_data = inst_collector.get_cme_data(start_date, end_date)
        whale_data = whale_analyzer.get_whale_metrics(start_date, end_date)

        # Убедимся, что индексы всех DataFrame в UTC
        for df in [etf_data, cme_data, whale_data]:
            if df is not None and not df.empty:
                if df.index.tzinfo is None:
                    df.index = df.index.tz_localize('UTC')
                elif df.index.tzinfo != pytz.UTC:
                    df.index = df.index.tz_convert('UTC')

        # Объединение всех метрик
        metrics = pd.concat([
            df for df in [etf_data, cme_data, whale_data]
            if df is not None and not df.empty
        ], axis=1)

        # Заполнение пропущенных значений
        metrics = metrics.ffill().bfill()

        return metrics

    except Exception as e:
        logger.error(f"Ошибка при подготовке институциональных признаков: {str(e)}")
        return pd.DataFrame()
