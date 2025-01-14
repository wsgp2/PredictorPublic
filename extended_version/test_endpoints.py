import requests
import logging
import json

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

API_KEY = '84068f54707949bc8f86e2dd9dcee6ac'
BASE_URL = 'https://open-api.coinank.com/api'

headers = {
    'apikey': API_KEY,
    'accept': 'application/json'
}

def test_endpoint(endpoint, params=None, description=""):
    """Тестирует endpoint API"""
    url = f"{BASE_URL}/{endpoint}"
    
    logger.info(f"\n{'='*50}")
    logger.info(f"Тестирование: {description}")
    logger.info(f"Endpoint: {endpoint}")
    logger.info(f"Params: {params}")
    
    try:
        response = requests.get(url, headers=headers, params=params)
        logger.info(f"Статус код: {response.status_code}")
        logger.info(f"Ответ: {json.dumps(response.json(), indent=2)}")
    except Exception as e:
        logger.error(f"Ошибка: {str(e)}")
    
    logger.info(f"{'='*50}\n")

def main():
    # Тестируем различные эндпоинты с BTC вместо BTCUSDT
    
    # 1. Market Data
    test_endpoint(
        'market/depth',
        {'symbol': 'BTC', 'limit': 5},
        'Market Depth'
    )
    
    test_endpoint(
        'market/ticker',
        {'symbol': 'BTC'},
        'Ticker'
    )
    
    # 2. Funding
    test_endpoint(
        'funding/rate',
        {'symbol': 'BTC'},
        'Funding Rate'
    )
    
    test_endpoint(
        'funding/history',
        {'symbol': 'BTC'},
        'Funding Rate History'
    )
    
    # 3. Open Interest
    test_endpoint(
        'openInterest',
        {'symbol': 'BTC'},
        'Open Interest'
    )
    
    test_endpoint(
        'openInterest/history',
        {'symbol': 'BTC'},
        'Open Interest History'
    )
    
    # 4. Liquidations
    test_endpoint(
        'liquidation/orders',
        {'symbol': 'BTC'},
        'Liquidation Orders'
    )
    
    # 5. Additional endpoints to try
    test_endpoint(
        'contract/detail',
        {'symbol': 'BTC'},
        'Contract Details'
    )
    
    test_endpoint(
        'trades',
        {'symbol': 'BTC', 'limit': 5},
        'Recent Trades'
    )

if __name__ == "__main__":
    main()
