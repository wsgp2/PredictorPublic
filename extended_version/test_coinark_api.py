import requests
import pandas as pd
from datetime import datetime, timedelta
import logging
import json

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CoinArkAPITester:
    def __init__(self, api_key='84068f54707949bc8f86e2dd9dcee6ac'):
        self.api_key = api_key
        self.base_url = 'https://open-api.coinank.com'
        self.headers = {
            'apikey': self.api_key,
            'accept': 'application/json'
        }

    def test_request(self, endpoint, params=None):
        """Тестовый запрос к API с выводом полного ответа"""
        url = f"{self.base_url}{endpoint}"
        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            
            logger.info(f"\n{'='*50}")
            logger.info(f"Тестирование endpoint: {endpoint}")
            logger.info(f"URL: {url}")
            logger.info(f"Параметры запроса: {params}")
            logger.info(f"Заголовки запроса: {self.headers}")
            logger.info(f"Статус код: {response.status_code}")
            logger.info(f"Headers ответа: {json.dumps(dict(response.headers), indent=2)}")
            logger.info(f"Ответ: {json.dumps(response.json(), indent=2)}")
            logger.info(f"{'='*50}\n")
            
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка при запросе к {endpoint}: {str(e)}")
            logger.error(f"URL запроса: {url}")
            logger.error(f"Заголовки запроса: {self.headers}")
            if hasattr(e, 'response') and hasattr(e.response, 'text'):
                logger.error(f"Ответ сервера: {e.response.text}")
            return None

    def test_all_endpoints(self):
        """Тестирование всех необходимых эндпоинтов"""
        
        # 1. Тест получения открытого интереса
        logger.info("Тестирование Open Interest API")
        self.test_request('/api/openInterest/all', {
            'baseCoin': 'BTC'
        })

        # 2. Тест получения ликвидаций
        logger.info("Тестирование Liquidations API")
        self.test_request('/api/liquidation/history', {
            'baseCoin': 'BTC',
            'interval': '1h',
            'size': 500
        })

        # 3. Тест получения ставок финансирования
        logger.info("Тестирование Funding Rates API")
        self.test_request('/api/fundingRate', {
            'symbol': 'BTCUSDT',
            'exchange': 'Binance',
            'marginType': 'USDT'
        })

        # 4. Тест получения исторических данных
        logger.info("Тестирование Kline API")
        self.test_request('/api/kline', {
            'symbol': 'BTCUSDT',
            'exchange': 'Binance',
            'interval': '1h',
            'size': 500
        })

        # 5. Тест получения глубины рынка
        logger.info("Тестирование Order Book API")
        self.test_request('/api/orderBook/v2/bySymbol', {
            'symbol': 'BTCUSDT',
            'exchange': 'Binance',
            'rate': '0.01',
            'productType': 'SWAP',
            'interval': '1h',
            'size': 500
        })

        # 6. Тест получения исторических данных о ставках финансирования
        logger.info("Тестирование get_historical_funding_rate API")
        self.test_request('/api/fundingRate/hist', {
            'baseCoin': 'BTC',
            'exchangeType': 'USDT',
            'size': '20'
        })

        # 7. Тест получения данных об открытом интересе
        logger.info("Тестирование get_open_interest_kline API")
        self.test_request('/api/openInterest/kline', {
            'symbol': 'BTCUSDT',
            'exchange': 'Binance',
            'interval': '1h'
        })

    def test_get_longshort_ratio(self):
        """Тест получения соотношения длинных и коротких позиций"""
        logger.info("Тестирование get_longshort_ratio API")
        self.test_request('/api/longshort/realtimeAll', {
            'baseCoin': 'BTC',
            'interval': '5m'
        })

    def test_get_historical_funding_rate(self):
        """Тест получения исторических данных о ставках финансирования"""
        logger.info("Тестирование get_historical_funding_rate API")
        self.test_request('/api/fundingRate/hist', {
            'baseCoin': 'BTC',
            'exchangeType': 'USDT',
            'size': '20'
        })

    def test_get_open_interest_kline(self):
        """Тест получения данных об открытом интересе"""
        logger.info("Тестирование get_open_interest_kline API")
        self.test_request('/api/openInterest/kline', {
            'symbol': 'BTCUSDT',
            'exchange': 'Binance',
            'interval': '1h'
        })

def main():
    logger.info("Начинаем тестирование CoinArk API")
    tester = CoinArkAPITester()
    tester.test_all_endpoints()

if __name__ == "__main__":
    main()
