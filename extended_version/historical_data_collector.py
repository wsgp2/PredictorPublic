import requests
import pandas as pd
import logging
from datetime import datetime, timedelta
import os
from pycoingecko import CoinGeckoAPI
from yahoo_finance_collector import YahooFinanceCollector
from blockchain_data_collector_v2 import BlockchainDataCollector
from sentiment_data_collector import SentimentDataCollector
from lunarcrush_collector import LunarCrushCollector
from fred_data_collector import FREDDataCollector
from coinark_collector import CoinArkCollector
from collectors.google_trends_collector import GoogleTrendsCollector
from db import DB

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
        self.fred_api_key = os.getenv('FRED_API_KEY', 'bb08bba3969b795cb832f4c1eb721494')
        
        # Инициализация коллекторов
        self.cg = CoinGeckoAPI()
        self.blockchain_collector = BlockchainDataCollector()
        self.yahoo_collector = YahooFinanceCollector()
        self.sentiment_collector = SentimentDataCollector()
        self.lunarcrush_collector = LunarCrushCollector()
        self.fred_collector = FREDDataCollector(api_key=self.fred_api_key)
        self.coinark_collector = CoinArkCollector()
        self.google_trends_collector = GoogleTrendsCollector()
        self.db = DB()

    def get_latest_timestamp(self, table_name):
        """Получение последней временной метки из таблицы"""
        return self.db.get_latest_timestamp(table_name)

    def collect_google_trends_data(self):
        """Сбор данных из Google Trends"""
        try:
            logger.info("Начинаем сбор данных из Google Trends")
            self.google_trends_collector.run_collection()
            logger.info("Сбор данных из Google Trends завершен")
        except Exception as e:
            logger.error(f"Ошибка при сборе данных из Google Trends: {str(e)}")

    def collect_all_data(self, force_update: bool = False):
        """
        Сбор всех исторических данных
        
        Args:
            force_update: Принудительное обновление всех данных
        """
        try:
            # 1. Blockchain.info данные
            logger.info("Collecting blockchain data...")
            self.blockchain_collector.update_blockchain_metrics()

            # 2. Сбор данных из Google Trends
            self.collect_google_trends_data()
            
            # 3. Сбор данных с Yahoo Finance
            logger.info("Collecting Yahoo Finance data...")
            symbols = ['MSTR', 'MARA', 'RIOT', 'COIN', 'SPY', 'QQQ', 'GLD', 'UUP']
            for symbol in symbols:
                self.yahoo_collector.update_stock_data(symbol)
            
            # 4. Сбор данных о настроениях
            logger.info("Collecting sentiment data...")
            self.sentiment_collector.update_fear_and_greed_index()
            
            # 5. Сбор данных LunarCrush
            logger.info("Collecting LunarCrush data...")
            self.lunarcrush_collector.update_all_metrics()
            
            # 6. Сбор данных CoinArk
            logger.info("Collecting CoinArk data...")
            self.coinark_collector.update_all_data()
            
            logger.info("All data collection completed successfully")
            
        except Exception as e:
            logger.error(f"Error collecting all data: {str(e)}")

    def analyze_correlations(self):
        """Анализ корреляций между метриками со всех коллекторов"""
        try:
            logger.info("Analyzing correlations between all metrics...")
            
            # Определяем метрики для каждого коллектора
            metrics = {
                'blockchain': [
                    'trade_volume', 'miners_revenue', 'estimated_transaction_volume_usd',
                    'market_price', 'total_bitcoins', 'market_cap', 'hash_rate',
                    'difficulty', 'transaction_fees', 'n_unique_addresses', 'n_transactions'
                ],
                'sentiment': [
                    'fear_and_greed_index', 'fear_value', 'greed_value'
                ],
                'lunarcrush': [
                    'social_volume', 'social_dominance', 'social_contributors',
                    'social_engagement', 'average_sentiment', 'galaxy_score',
                    'market_dominance', 'market_score'
                ],
                'coinark': [
                    'long_short_ratio', 'funding_rate', 'open_interest',
                    'liquidations_volume', 'total_volume'
                ],
                'yahoo': [
                    'MSTR_close', 'MARA_close', 'RIOT_close', 'COIN_close',
                    'SPY_close', 'QQQ_close', 'GLD_close', 'UUP_close'
                ],
                'google_trends': [
                    'bitcoin_trend', 'crypto_trend', 'blockchain_trend'
                ]
            }
            
            # Создаем DataFrame для анализа корреляций
            all_dfs = []
            
            # Собираем данные из каждого коллектора
            for source, source_metrics in metrics.items():
                logger.info(f"Getting data from {source}...")
                for metric in source_metrics:
                    df = self.db.get_metric_data(metric, source)
                    if df is not None and not df.empty:
                        df = df.set_index('timestamp')
                        df.columns = [f"{source}_{metric}"]
                        all_dfs.append(df)
                    else:
                        logger.warning(f"No data available for {source}_{metric}")
            
            if all_dfs:
                # Объединяем все метрики
                combined_df = pd.concat(all_dfs, axis=1)
                
                # Заполняем пропуски методом forward fill, затем backward fill
                combined_df = combined_df.fillna(method='ffill').fillna(method='bfill')
                
                # Рассчитываем корреляции
                correlations = combined_df.corr()
                
                # Сохраняем корреляции в базу данных
                self.db.save_correlations(correlations)
                
                # Анализируем корреляции с ценой биткоина
                btc_price = 'blockchain_market_price'
                if btc_price in correlations.columns:
                    price_correlations = correlations[btc_price].sort_values(ascending=False)
                    
                    logger.info("\nТоп-10 метрик с самой сильной положительной корреляцией с ценой:")
                    logger.info(price_correlations.head(10))
                    
                    logger.info("\nТоп-10 метрик с самой сильной отрицательной корреляцией с ценой:")
                    logger.info(price_correlations.tail(10))
                    
                    # Группируем корреляции по источникам данных
                    for source in metrics.keys():
                        source_correlations = price_correlations[
                            price_correlations.index.str.startswith(source)
                        ]
                        if not source_correlations.empty:
                            logger.info(f"\nКорреляции с ценой для {source}:")
                            logger.info(source_correlations)
                else:
                    logger.warning("Price data not available for correlation analysis")
            else:
                logger.warning("No data available for correlation analysis")
                
        except Exception as e:
            logger.error(f"Error in correlation analysis: {str(e)}")
            logger.exception("Detailed error information:")

def main():
    """Основная функция для сбора данных"""
    try:
        collector = HistoricalDataCollector()
        
        # Собираем все данные из разных источников
        collector.collect_all_data()
        
        # Анализируем корреляции
        collector.analyze_correlations()
        
    except Exception as e:
        logger.error(f"Ошибка в main(): {str(e)}")
    finally:
        if 'collector' in locals():
            collector.blockchain_collector.close()

if __name__ == "__main__":
    main()