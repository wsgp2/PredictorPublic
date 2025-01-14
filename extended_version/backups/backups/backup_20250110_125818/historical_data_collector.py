import requests
import pandas as pd
import logging
from datetime import datetime, timedelta
import os
from pycoingecko import CoinGeckoAPI
from yahoo_finance_collector import YahooFinanceCollector
from blockchain_data_collector import BlockchainDataCollector
from sentiment_data_collector import SentimentDataCollector
from lunarcrush_collector import LunarCrushCollector
from fred_data_collector import FREDDataCollector
from coinark_collector import CoinArkCollector

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class HistoricalDataCollector:
    def __init__(self):
        """Инициализация коллектора исторических данных"""
        self.data_dir = 'data/historical'
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
        
        # API ключи
        self.fred_api_key = 'bb08bba3969b795cb832f4c1eb721494'
        
        # Инициализация коллекторов
        self.cg = CoinGeckoAPI()
        self.blockchain_collector = BlockchainDataCollector()
        self.yahoo_collector = YahooFinanceCollector()
        self.sentiment_collector = SentimentDataCollector()
        self.lunarcrush_collector = LunarCrushCollector()
        self.fred_collector = FREDDataCollector(api_key=self.fred_api_key)
        self.coinark_collector = CoinArkCollector()

    def save_data(self, df, filename):
        """Сохранение DataFrame в CSV файл"""
        try:
            full_path = os.path.join(self.data_dir, filename)
            df.to_csv(full_path, index=False)
            logger.info(f"Data saved to {full_path}")
        except Exception as e:
            logger.error(f"Error saving data to {filename}: {str(e)}")

    def load_historical_data(self, filename):
        """Загрузка исторических данных из CSV файла"""
        try:
            full_path = os.path.join(self.data_dir, filename)
            if os.path.exists(full_path):
                df = pd.read_csv(full_path)
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                return df
            return None
        except Exception as e:
            logger.error(f"Error loading historical data from {filename}: {str(e)}")
            return None

    def get_latest_timestamp(self, df):
        """Получение последней временной метки из DataFrame"""
        if df is not None and not df.empty:
            return df['timestamp'].max()
        return None

    def merge_and_save_data(self, historical_df, new_df, filename):
        """Объединение исторических и новых данных и сохранение результата"""
        try:
            if historical_df is None:
                merged_df = new_df
            else:
                # Объединяем старые и новые данные
                merged_df = pd.concat([historical_df, new_df])
                # Удаляем дубликаты
                merged_df = merged_df.drop_duplicates(subset=['timestamp'])
                # Сортируем по времени
                merged_df = merged_df.sort_values('timestamp')
            
            self.save_data(merged_df, filename)
            return merged_df
        except Exception as e:
            logger.error(f"Error merging data: {str(e)}")
            return None

    def update_historical_data(self, data_getter, filename, metric_name, **kwargs):
        """Обновление исторических данных"""
        try:
            # Загружаем существующие данные
            historical_df = self.load_historical_data(filename)
            
            # Получаем последнюю временную метку
            latest_timestamp = self.get_latest_timestamp(historical_df)
            
            # Получаем новые данные
            new_df = data_getter(**kwargs)
            
            if new_df is not None and not new_df.empty:
                # Если есть исторические данные, фильтруем только новые записи
                if latest_timestamp:
                    new_df = new_df[new_df['timestamp'] > latest_timestamp]
                
                if not new_df.empty:
                    # Объединяем и сохраняем данные
                    merged_df = self.merge_and_save_data(historical_df, new_df, filename)
                    return merged_df
                else:
                    logger.info(f"No new data for {metric_name}")
                    return historical_df
            else:
                logger.error(f"Failed to get new data for {metric_name}")
                return historical_df
                
        except Exception as e:
            logger.error(f"Error updating {metric_name}: {str(e)}")
            return None

    def update_all_data(self):
        """Обновление всех исторических данных"""
        # Blockchain.com рыночные данные
        market_metrics = {
            'price': 'market-price',  # Цена в USD
            'market_cap': 'market-cap',  # Рыночная капитализация
            'volume': 'trade-volume',  # Объем торгов
            'volume_usd': 'volume-usd',  # Объем в USD
        }
        
        for metric, endpoint in market_metrics.items():
            df = self.update_historical_data(
                lambda **kwargs: self.get_blockchain_metric(endpoint, **kwargs),
                f'market_{metric}.csv',
                metric,
                timespan='all',
                rolling_average='24hours'
            )
            if df is not None:
                logger.info(f"{metric} records: {len(df)}")
        
        # Blockchain.com майнинг метрики
        mining_metrics = {
            'miners_revenue': 'miners-revenue',  # Доход майнеров
            'mining_revenue_percentage': 'mining-revenue-percentage',  # % дохода от комиссий
        }
        
        for metric, endpoint in mining_metrics.items():
            df = self.update_historical_data(
                lambda **kwargs: self.get_blockchain_metric(endpoint, **kwargs),
                f'mining_{metric}.csv',
                metric,
                timespan='all',
                rolling_average='24hours'
            )
            if df is not None:
                logger.info(f"{metric} records: {len(df)}")
        
        # Blockchain.com сетевые метрики
        network_metrics = {
            'unique_addresses': 'n-unique-addresses',  # Уникальные адреса
            'total_transactions': 'n-transactions-total',  # Общее число транзакций
            'estimated_volume': 'estimated-transaction-volume',  # Оценочный объем
            'estimated_volume_usd': 'estimated-transaction-volume-usd',  # Оценочный объем в USD
        }
        
        for metric, endpoint in network_metrics.items():
            df = self.update_historical_data(
                lambda **kwargs: self.get_blockchain_metric(endpoint, **kwargs),
                f'network_{metric}.csv',
                metric,
                timespan='all',
                rolling_average='24hours'
            )
            if df is not None:
                logger.info(f"{metric} records: {len(df)}")
        
        # Blockchain.com дополнительные метрики
        blockchain_metrics = {
            'difficulty': 'difficulty',
            'avg_block_size': 'avg-block-size',
            'transaction_fees': 'transaction-fees',
            'median_confirmation_time': 'median-confirmation-time',
            'confirmed_transactions': 'n-transactions-excluding-popular',
            'mempool_size': 'mempool-size',
            'transactions_per_block': 'n-transactions-per-block',
            'cost_per_transaction': 'cost-per-transaction',
            'utxo_count': 'utxo-count',
        }
        
        for metric, endpoint in blockchain_metrics.items():
            df = self.update_historical_data(
                lambda **kwargs: self.get_blockchain_metric(endpoint, **kwargs),
                f'blockchain_{metric}.csv',
                metric,
                timespan='all',
                rolling_average='24hours'
            )
            if df is not None:
                logger.info(f"{metric} records: {len(df)}")
        
        # Обновляем данные о деривативах и фьючерсах
        logger.info("Updating derivatives and futures data from CoinArk...")
        self.coinark_collector.update_all_data()

    def get_blockchain_metric(self, endpoint, timespan='all', rolling_average='24hours'):
        """Получение метрики с blockchain.info через BlockchainDataCollector"""
        return self.blockchain_collector.get_blockchain_metric(endpoint, timespan, rolling_average)

def main():
    """Основная функция для сбора данных"""
    logger.info("Starting data collection process...")
    
    collector = HistoricalDataCollector()
    
    # Собираем данные Blockchain.com
    logger.info("\nCollecting Blockchain.com data...")
    collector.blockchain_collector.update_all_metrics()
    
    # Собираем исторические данные
    logger.info("\nCollecting historical data...")
    collector.update_all_data()
    
    # Собираем данные о корреляциях рынка
    logger.info("\nCollecting market correlation data...")
    collector.yahoo_collector.update_all_data()
    
    # Собираем данные о настроениях рынка
    logger.info("\nCollecting market sentiment data...")
    collector.sentiment_collector.update_fear_and_greed_index()
    
    # Собираем данные LunarCrush
    logger.info("\nCollecting LunarCrush data...")
    collector.lunarcrush_collector.update_all_metrics()
    
    # Собираем макроэкономические данные FRED
    logger.info("\nCollecting FRED macroeconomic data...")
    collector.fred_collector.update_all_series()
    
    logger.info("\nData collection completed successfully!")

if __name__ == "__main__":
    main()
