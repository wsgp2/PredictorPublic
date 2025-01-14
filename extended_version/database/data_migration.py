import pandas as pd
import os
from database_manager import DatabaseManager
from datetime import datetime
import logging
import sys

# Добавляем родительскую директорию в путь для импортов
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from config.config import DB_CONFIG

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DataMigration:
    def __init__(self):
        """Инициализация класса миграции данных"""
        self.project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.data_dir = os.path.join(self.project_dir, 'data')
        self.db = DatabaseManager()
        
    def read_and_process_csv(self, file_path: str) -> pd.DataFrame:
        """Читает и обрабатывает CSV файл, определяя его формат"""
        try:
            df = pd.read_csv(file_path)
            
            # Стандартизируем названия колонок
            df.columns = [col.lower().replace('-', '_') for col in df.columns]
            
            # Обработка временной метки
            if 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp'])
            elif 'date' in df.columns:
                df['timestamp'] = pd.to_datetime(df['date'])
                df = df.drop('date', axis=1)
            
            # Обработка значений
            if 'market_price' in df.columns:
                df['value'] = df['market_price']
            elif 'close' in df.columns:
                df['value'] = df['close']
            elif 'price' in df.columns:
                df['value'] = df['price']
            elif 'avg_block_size' in df.columns:
                df['value'] = df['avg_block_size']
            elif len(df.columns) == 2 and 'timestamp' in df.columns:
                # Если у нас только две колонки и одна из них timestamp,
                # предполагаем, что вторая колонка содержит значение
                value_col = [col for col in df.columns if col != 'timestamp'][0]
                df['value'] = df[value_col]
            
            return df
            
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {str(e)}")
            return None
        
    def migrate_price_data(self):
        """Миграция данных о ценах"""
        try:
            # CoinArk данные
            coinark_dir = os.path.join(self.data_dir, 'coinark')
            if os.path.exists(coinark_dir):
                for file in os.listdir(coinark_dir):
                    if file.endswith('.csv') and 'klines' in file:
                        df = self.read_and_process_csv(os.path.join(coinark_dir, file))
                        if df is not None:
                            self.db.insert_price_data(df)
                            logger.info(f"Migrated price data from {file}")
            
            # Данные о ценах из корневой директории
            price_files = ['market_price.csv']
            for filename in price_files:
                file_path = os.path.join(self.project_dir, filename)
                if os.path.exists(file_path):
                    df = self.read_and_process_csv(file_path)
                    if df is not None:
                        self.db.insert_price_data(df)
                        logger.info(f"Migrated price data from {filename}")
                
        except Exception as e:
            logger.error(f"Error migrating price data: {str(e)}")

    def migrate_blockchain_data(self):
        """Миграция данных блокчейна"""
        try:
            blockchain_files = {
                'blockchain_avg_block_size.csv': 'avg_block_size',
                'blockchain_confirmed_transactions.csv': 'transaction_count',
                'blockchain_cost_per_transaction.csv': 'transaction_fees',
                'blockchain_difficulty.csv': 'mining_difficulty',
                'blockchain_median_confirmation_time.csv': 'block_interval',
                'blockchain_mempool_size.csv': 'mempool_size',
                'blockchain_transaction_fees.csv': 'transaction_fees',
                'blockchain_transactions_per_block.csv': 'transaction_count',
                'blockchain_utxo_count.csv': 'utxo_count',
                'network_unique_addresses.csv': 'active_addresses',
                'network_total_transactions.csv': 'transaction_count'
            }
            
            metrics_data = {}
            timestamps = None
            
            for filename, column in blockchain_files.items():
                file_path = os.path.join(self.project_dir, filename)
                if os.path.exists(file_path):
                    df = self.read_and_process_csv(file_path)
                    if df is not None:
                        # Фильтруем строки с NaT значениями
                        df = df.dropna(subset=['timestamp'])
                        
                        # Если это первый файл, сохраняем временные метки
                        if timestamps is None:
                            timestamps = df['timestamp']
                            metrics_data['timestamp'] = timestamps
                        
                        # Добавляем значения в соответствующую колонку
                        metrics_data[column] = df['value']
                        logger.info(f"Loaded blockchain data from {filename}")
            
            if metrics_data:
                metrics_df = pd.DataFrame(metrics_data)
                # Удаляем строки с NaN значениями
                metrics_df = metrics_df.dropna(subset=['timestamp'])
                self.db.insert_on_chain_metrics(metrics_df)
                logger.info("Successfully migrated blockchain metrics")
                    
        except Exception as e:
            logger.error(f"Error migrating blockchain data: {str(e)}")

    def migrate_market_data(self):
        """Миграция рыночных данных"""
        try:
            market_files = {
                'market_market_cap.csv': 'market_cap',
                'market_volume.csv': 'volume',
                'mining_miners_revenue.csv': 'miners_revenue',
                'network_estimated_volume.csv': 'network_volume',
                'network_estimated_volume_usd.csv': 'network_volume_usd'
            }
            
            market_data = {}
            
            for filename, column in market_files.items():
                file_path = os.path.join(self.project_dir, filename)
                if os.path.exists(file_path):
                    df = self.read_and_process_csv(file_path)
                    if df is not None and 'timestamp' in df.columns and 'value' in df.columns:
                        if 'timestamp' not in market_data:
                            market_data['timestamp'] = df['timestamp']
                        market_data[column] = df['value']
                        logger.info(f"Loaded market data from {filename}")
            
            if market_data:
                market_df = pd.DataFrame(market_data)
                self.db.insert_market_data(market_df)
                logger.info("Successfully migrated market data")
                
        except Exception as e:
            logger.error(f"Error migrating market data: {str(e)}")

    def migrate_sentiment_data(self):
        """Миграция данных о настроениях"""
        try:
            # Данные Fear & Greed Index
            fear_greed_file = os.path.join(self.data_dir, 'sentiment', 'fear_and_greed_index.csv')
            if os.path.exists(fear_greed_file):
                df_fear_greed = pd.read_csv(fear_greed_file)
                # Преобразуем индекс в колонку timestamp
                df_fear_greed['timestamp'] = pd.to_datetime(df_fear_greed.index)
                df_fear_greed = df_fear_greed.rename(columns={'value': 'fear_greed_index'})
                logger.info("Loaded Fear & Greed Index data")
            else:
                df_fear_greed = None

            # Данные LunarCrush
            social_file = os.path.join(self.data_dir, 'lunarcrush', 'social_metrics.csv')
            if os.path.exists(social_file):
                df_social = pd.read_csv(social_file)
                df_social['timestamp'] = pd.to_datetime(df_social['timestamp'])
                
                # Переименовываем и выбираем нужные колонки
                df_social = df_social.rename(columns={
                    'contributors_active': 'social_volume',
                    'sentiment': 'social_sentiment',
                    'posts_active': 'reddit_posts',
                    'interactions': 'twitter_volume'
                })
                
                # Выбираем только нужные колонки
                columns_to_keep = ['timestamp', 'social_volume', 'social_sentiment', 
                                 'reddit_posts', 'twitter_volume']
                df_social = df_social[columns_to_keep]
                
                logger.info("Loaded LunarCrush social metrics data")
            else:
                df_social = None

            # Объединяем все данные о настроениях
            if df_fear_greed is not None and df_social is not None:
                # Объединяем по временной метке
                sentiment_df = pd.merge(df_fear_greed[['timestamp', 'fear_greed_index']], 
                                      df_social, 
                                      on='timestamp', 
                                      how='outer')
            elif df_fear_greed is not None:
                sentiment_df = df_fear_greed
            elif df_social is not None:
                sentiment_df = df_social
            else:
                logger.warning("No sentiment data found")
                return

            # Удаляем дубликаты и строки с NaN значениями в timestamp
            sentiment_df = sentiment_df.drop_duplicates(subset=['timestamp'])
            sentiment_df = sentiment_df.dropna(subset=['timestamp'])

            # Заполняем пропущенные значения нулями
            sentiment_df = sentiment_df.fillna(0)

            # Вставляем данные в базу
            self.db.insert_sentiment_metrics(sentiment_df)
            logger.info("Successfully migrated sentiment data")
                        
        except Exception as e:
            logger.error(f"Error migrating sentiment data: {str(e)}")

    def migrate_longshort_data(self):
        """Миграция данных о Long/Short позициях"""
        try:
            # Директория с данными Long/Short
            longshort_dir = os.path.join(self.data_dir, 'coinark', 'longshort')
            if not os.path.exists(longshort_dir):
                logger.warning("Long/Short data directory not found")
                return

            # Обрабатываем файлы с данными Long/Short
            for file in os.listdir(longshort_dir):
                if file.endswith('.csv'):
                    file_path = os.path.join(longshort_dir, file)
                    df = pd.read_csv(file_path)
                    
                    # Определяем символ и таймфрейм из имени файла
                    symbol = 'BTC' if 'BTC' in file else 'ETH'
                    timeframe = '1h'
                    if '4h' in file:
                        timeframe = '4h'
                    elif '1d' in file:
                        timeframe = '1d'
                    
                    # Преобразуем timestamp в зависимости от формата данных
                    if 'begin' in df.columns:
                        df['timestamp'] = pd.to_datetime(df['begin'], unit='ms')
                    
                    df['symbol'] = symbol
                    df['timeframe'] = timeframe
                    
                    # Определяем тип данных из имени файла и структуру данных
                    if 'Account' in file:
                        if 'open' in df.columns:
                            df = df.rename(columns={
                                'open': 'long_account_ratio',
                                'close': 'short_account_ratio'
                            })
                        else:
                            df = df.rename(columns={
                                'ratio_open': 'long_account_ratio',
                                'ratio_close': 'short_account_ratio'
                            })
                    elif 'Position' in file:
                        if 'open' in df.columns:
                            df = df.rename(columns={
                                'open': 'long_position_ratio',
                                'close': 'short_position_ratio'
                            })
                        else:
                            df = df.rename(columns={
                                'ratio_open': 'long_position_ratio',
                                'ratio_close': 'short_position_ratio'
                            })
                    elif 'Person' in file:
                        if 'open' in df.columns:
                            df = df.rename(columns={
                                'open': 'long_person_ratio',
                                'close': 'short_person_ratio'
                            })
                        else:
                            df = df.rename(columns={
                                'ratio_open': 'long_person_ratio',
                                'ratio_close': 'short_person_ratio'
                            })
                    
                    # Выбираем только нужные колонки
                    columns = ['timestamp', 'symbol', 'timeframe']
                    if 'Account' in file:
                        columns.extend(['long_account_ratio', 'short_account_ratio'])
                    elif 'Position' in file:
                        columns.extend(['long_position_ratio', 'short_position_ratio'])
                    elif 'Person' in file:
                        columns.extend(['long_person_ratio', 'short_person_ratio'])
                    
                    # Проверяем, что все нужные колонки есть в DataFrame
                    available_columns = [col for col in columns if col in df.columns]
                    if len(available_columns) < len(columns):
                        missing_columns = set(columns) - set(available_columns)
                        logger.warning(f"Missing columns in {file}: {missing_columns}")
                        continue
                        
                    df = df[columns]
                    
                    # Вставляем данные в базу
                    self.db.insert_longshort_data(df)
                    logger.info(f"Migrated Long/Short data from {file}")
                    
        except Exception as e:
            logger.error(f"Error migrating Long/Short data: {str(e)}")
            raise

    def migrate_related_assets(self):
        """Миграция данных связанных активов"""
        try:
            # Директория с рыночными данными
            market_dir = os.path.join(self.data_dir, 'market_data')
            if not os.path.exists(market_dir):
                logger.warning("Market data directory not found")
                return

            # Словарь соответствия файлов и символов
            asset_files = {
                'mara_historical.csv': 'MARA',
                'riot_historical.csv': 'RIOT',
                'mstr_historical.csv': 'MSTR',
                'coin_historical.csv': 'COIN',
                'spy_historical.csv': 'SPY',
                'qqq_historical.csv': 'QQQ',
                'gld_historical.csv': 'GLD',
                'uup_historical.csv': 'UUP'
            }

            # Обрабатываем каждый файл
            for file, symbol in asset_files.items():
                file_path = os.path.join(market_dir, file)
                if os.path.exists(file_path):
                    df = pd.read_csv(file_path)
                    df['timestamp'] = pd.to_datetime(df['Date'])
                    df['symbol'] = symbol
                    
                    # Переименовываем колонки
                    df = df.rename(columns={
                        'Open': 'open',
                        'High': 'high',
                        'Low': 'low',
                        'Close': 'close',
                        'Volume': 'volume'
                    })
                    
                    # Выбираем нужные колонки
                    columns = ['timestamp', 'symbol', 'open', 'high', 'low', 'close', 'volume']
                    df = df[columns]
                    
                    # Вставляем данные в базу
                    self.db.insert_related_assets(df)
                    logger.info(f"Migrated {symbol} data from {file}")
                    
        except Exception as e:
            logger.error(f"Error migrating related assets data: {str(e)}")

    def migrate_news_data(self):
        """Миграция новостных данных"""
        try:
            # Файл с новостями
            news_file = os.path.join(self.data_dir, 'lunarcrush_new', 'news.csv')
            if not os.path.exists(news_file):
                logger.warning("News data file not found")
                return

            # Читаем и обрабатываем данные
            df = pd.read_csv(news_file)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            # Переименовываем колонки если нужно
            if 'sentiment_score' in df.columns:
                df = df.rename(columns={'sentiment_score': 'sentiment'})
            
            # Вставляем данные в базу
            self.db.insert_news_data(df)
            logger.info("Successfully migrated news data")
                    
        except Exception as e:
            logger.error(f"Error migrating news data: {str(e)}")

    def migrate_all_data(self):
        """Миграция всех данных"""
        with self.db:  # Используем контекстный менеджер для автоматического подключения/отключения
            self.migrate_price_data()
            self.migrate_blockchain_data()
            self.migrate_market_data()
            self.migrate_sentiment_data()
            self.migrate_longshort_data()
            self.migrate_related_assets()
            self.migrate_news_data()
            logger.info("Data migration completed successfully")

if __name__ == "__main__":
    migration = DataMigration()
    migration.migrate_all_data()
