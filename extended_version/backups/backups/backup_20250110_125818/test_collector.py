from coinark_collector import CoinArkCollector
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_trading_pairs():
    collector = CoinArkCollector()
    pairs = collector.get_trading_pairs()
    
    if pairs:
        logger.info(f"Successfully retrieved {len(pairs)} trading pairs")
        logger.info(f"First 5 pairs: {pairs[:5]}")
    else:
        logger.error("Failed to retrieve trading pairs")

if __name__ == "__main__":
    test_trading_pairs()
