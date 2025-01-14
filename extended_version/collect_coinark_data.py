from coinark_collector import CoinArkCollector
import logging
from datetime import datetime, timedelta
import time

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def collect_all_data():
    """Собирает все доступные данные с CoinArk"""
    collector = CoinArkCollector()
    
    # Проверяем статус API
    if not collector.check_api_status():
        logger.error("API key is not valid!")
        return
        
    try:
        # 1. Собираем исторические данные за последние 3 года
        logger.info("Collecting historical data...")
        collector.collect_historical_data()
        
        # 2. Собираем данные книги ордеров
        exchanges = {
            'SWAP': 'Binance,Bybit,OKX,Huobi,Bitfinex',
            'SPOT': 'Binance,Bybit,OKX,Bitfinex,Kraken,Coinbase'
        }
        
        intervals = ['5m', '15m', '30m', '1h', '4h', '1d']
        rates = ['0.01', '0.03', '0.05']
        
        for product_type, exchange_list in exchanges.items():
            for interval in intervals:
                for rate in rates:
                    logger.info(f"Collecting orderbook data for {product_type} {interval} {rate}...")
                    
                    # По символу
                    collector.get_orderbook_by_symbol(
                        symbol='BTCUSDT',
                        exchange='Binance',
                        rate=rate,
                        product_type=product_type,
                        interval=interval,
                        size=500
                    )
                    
                    # По бирже
                    collector.get_orderbook_by_exchange(
                        base_coin='BTC',
                        exchanges=exchange_list,
                        type=rate,
                        product_type=product_type,
                        interval=interval,
                        size=500
                    )
                    
                    # Небольшая пауза между запросами
                    time.sleep(1)
        
        logger.info("Data collection completed successfully!")
        
    except Exception as e:
        logger.error(f"Error collecting data: {str(e)}")

if __name__ == "__main__":
    collect_all_data()
