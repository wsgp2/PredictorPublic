import requests
import json
import logging
import pandas as pd
from datetime import datetime, timedelta
import os

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class BlockchainDataCollector:
    def __init__(self):
        """Инициализация коллектора данных"""
        self.data_dir = 'data'
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)

    def save_data(self, df, filename):
        """Сохранение DataFrame в CSV файл"""
        try:
            df.to_csv(filename, index=False)
            logger.info(f"Data saved to {filename}")
        except Exception as e:
            logger.error(f"Error saving data to {filename}: {str(e)}")

    def load_historical_data(self, filename):
        """Загрузка исторических данных из CSV файла"""
        try:
            if os.path.exists(filename):
                df = pd.read_csv(filename)
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
        if historical_df is None:
            merged_df = new_df
        else:
            merged_df = pd.concat([historical_df, new_df]).drop_duplicates(subset=['timestamp']).sort_values('timestamp')
        
        self.save_data(merged_df, filename)
        return merged_df

    def get_active_addresses(self, timespan='all', rolling_average='24hours'):
        """Получение количества уникальных активных адресов"""
        try:
            response = requests.get(
                "https://api.blockchain.info/charts/n-unique-addresses",
                params={
                    'timespan': timespan,
                    'rollingAverage': rolling_average,
                    'format': 'json'
                },
                verify=False
            )
            response.raise_for_status()
            data = response.json()
            
            # Создаем DataFrame
            values = data['values']
            df = pd.DataFrame(values)
            df.columns = ['timestamp', 'active_addresses']
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
            
            return df
            
        except Exception as e:
            logger.error(f"Error getting active addresses: {str(e)}")
            return None

    def get_transactions_count(self, timespan='all', rolling_average='24hours'):
        """Получение количества транзакций"""
        try:
            response = requests.get(
                "https://api.blockchain.info/charts/n-transactions",
                params={
                    'timespan': timespan,
                    'rollingAverage': rolling_average,
                    'format': 'json'
                },
                verify=False
            )
            response.raise_for_status()
            data = response.json()
            
            # Создаем DataFrame
            values = data['values']
            df = pd.DataFrame(values)
            df.columns = ['timestamp', 'transactions_count']
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
            
            return df
            
        except Exception as e:
            logger.error(f"Error getting transactions count: {str(e)}")
            return None

    def get_hash_rate(self, timespan='all', rolling_average='24hours'):
        """Получение хэшрейта сети"""
        try:
            response = requests.get(
                "https://api.blockchain.info/charts/hash-rate",
                params={
                    'timespan': timespan,
                    'rollingAverage': rolling_average,
                    'format': 'json'
                },
                verify=False
            )
            response.raise_for_status()
            data = response.json()
            
            # Создаем DataFrame
            values = data['values']
            df = pd.DataFrame(values)
            df.columns = ['timestamp', 'hash_rate']
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
            
            return df
            
        except Exception as e:
            logger.error(f"Error getting hash rate: {str(e)}")
            return None

    def get_total_bitcoins(self, timespan='all', rolling_average='24hours'):
        """Получение общего количества биткоинов в обращении"""
        try:
            response = requests.get(
                "https://api.blockchain.info/charts/total-bitcoins",
                params={
                    'timespan': timespan,
                    'rollingAverage': rolling_average,
                    'format': 'json'
                },
                verify=False
            )
            response.raise_for_status()
            data = response.json()
            
            # Создаем DataFrame
            values = data['values']
            df = pd.DataFrame(values)
            df.columns = ['timestamp', 'total_bitcoins']
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
            
            return df
            
        except Exception as e:
            logger.error(f"Error getting total bitcoins: {str(e)}")
            return None

    def update_historical_data(self, get_data_func, historical_file, metric_name, **kwargs):
        """Обновление исторических данных для заданной метрики"""
        # Загружаем исторические данные
        historical_df = self.load_historical_data(historical_file)
        
        if historical_df is None:
            # Если исторических данных нет, получаем полную историю
            logger.info(f"No historical data found for {metric_name}. Fetching all historical data...")
            new_df = get_data_func(**kwargs)
            if new_df is not None:
                self.save_data(new_df, historical_file)
                return new_df
        else:
            # Если исторические данные есть, получаем только новые данные
            latest_timestamp = self.get_latest_timestamp(historical_df)
            if latest_timestamp:
                days_diff = (datetime.now() - latest_timestamp).days + 1
                if days_diff > 0:
                    logger.info(f"Fetching {days_diff} days of new data for {metric_name}...")
                    new_df = get_data_func(timespan=f"{days_diff}days", **kwargs)
                    if new_df is not None:
                        return self.merge_and_save_data(historical_df, new_df, historical_file)
            
            return historical_df
        
        return None

    def get_current_price(self, symbol="BTC-USD"):
        """Получение текущей цены"""
        try:
            response = requests.get(
                f"https://api.blockchain.info/v3/exchange/tickers/{symbol}",
                verify=False
            )
            response.raise_for_status()
            data = response.json()
            
            # Создаем DataFrame с текущими данными
            df = pd.DataFrame([{
                'timestamp': datetime.now(),
                'symbol': data['symbol'],
                'price': data['last_trade_price'],
                'price_24h': data['price_24h'],
                'volume_24h': data['volume_24h']
            }])
            
            return df
            
        except Exception as e:
            logger.error(f"Error getting current price: {str(e)}")
            return None
            
    def get_order_book(self, symbol="BTC-USD"):
        """Получение книги ордеров"""
        try:
            response = requests.get(
                f"https://api.blockchain.info/v3/exchange/l2/{symbol}",
                verify=False
            )
            response.raise_for_status()
            data = response.json()
            
            # Создаем DataFrame для ордеров на покупку
            bids_df = pd.DataFrame(data['bids'])
            bids_df['type'] = 'bid'
            
            # Создаем DataFrame для ордеров на продажу
            asks_df = pd.DataFrame(data.get('asks', []))
            asks_df['type'] = 'ask'
            
            # Объединяем данные
            df = pd.concat([bids_df, asks_df], ignore_index=True)
            df['timestamp'] = datetime.now()
            df['symbol'] = symbol
            
            return df
            
        except Exception as e:
            logger.error(f"Error getting order book: {str(e)}")
            return None
            
    def get_blockchain_metric(self, endpoint, timespan='all', rolling_average='24hours'):
        """Получение метрики с blockchain.info"""
        try:
            response = requests.get(
                f"https://api.blockchain.info/charts/{endpoint}",
                params={
                    'timespan': timespan,
                    'rollingAverage': rolling_average,
                    'format': 'json'
                },
                verify=False
            )
            response.raise_for_status()
            data = response.json()
            
            # Создаем DataFrame
            values = data['values']
            df = pd.DataFrame(values)
            df.columns = ['timestamp', endpoint]
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
            
            return df
            
        except Exception as e:
            logger.error(f"Error getting blockchain metric: {str(e)}")
            return None

    def update_all_metrics(self):
        """Обновление всех метрик"""
        # Blockchain.com рыночные данные
        market_metrics = {
            'price': 'market-price',  # Цена в USD
            'market_cap': 'market-cap',  # Рыночная капитализация
            'volume': 'trade-volume',  # Объем торгов
            'volume_usd': 'volume-usd',  # Объем в USD
        }
        
        for metric, endpoint in market_metrics.items():
            df = self.update_historical_data(
                lambda timespan='all': self.get_blockchain_metric(endpoint, timespan=timespan),
                f'market_{metric}.csv',
                metric
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
                lambda timespan='all': self.get_blockchain_metric(endpoint, timespan=timespan),
                f'mining_{metric}.csv',
                metric
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
                lambda timespan='all': self.get_blockchain_metric(endpoint, timespan=timespan),
                f'network_{metric}.csv',
                metric
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
                lambda timespan='all': self.get_blockchain_metric(endpoint, timespan=timespan),
                f'blockchain_{metric}.csv',
                metric
            )
            if df is not None:
                logger.info(f"{metric} records: {len(df)}")

def main():
    collector = BlockchainDataCollector()
    
    # Получаем текущую цену
    price_df = collector.get_current_price()
    if price_df is not None:
        collector.save_data(price_df, 'data/blockchain_price_data.csv')
        logger.info(f"Current price data:\n{price_df}")
    
    # Получаем книгу ордеров
    order_book_df = collector.get_order_book()
    if order_book_df is not None:
        collector.save_data(order_book_df, 'data/blockchain_order_book_data.csv')
        logger.info(f"Order book data:\n{order_book_df.head()}")
    
    # Обновляем исторические данные для каждой метрики
    metrics = [
        (collector.get_active_addresses, 'data/historical_active_addresses.csv', 'active addresses'),
        (collector.get_transactions_count, 'data/historical_transactions.csv', 'transactions'),
        (collector.get_hash_rate, 'data/historical_hash_rate.csv', 'hash rate'),
        (collector.get_total_bitcoins, 'data/historical_total_bitcoins.csv', 'total bitcoins')
    ]
    
    for get_func, filename, metric_name in metrics:
        df = collector.update_historical_data(get_func, filename, metric_name)
        if df is not None:
            logger.info(f"{metric_name.capitalize()} data:\n{df.head()}")
            logger.info(f"Total records for {metric_name}: {len(df)}")

    collector.update_all_metrics()

if __name__ == "__main__":
    main()
