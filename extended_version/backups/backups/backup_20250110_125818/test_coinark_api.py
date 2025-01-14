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
        self.base_url = 'https://api.coinank.com/api/v1'
        self.headers = {
            'coinank-apikey': self.api_key,
            'Content-Type': 'application/json'
        }

    def test_request(self, endpoint, params=None):
        """Тестовый запрос к API с выводом полного ответа"""
        url = f"{self.base_url}/{endpoint}"
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
            if hasattr(e.response, 'text'):
                logger.error(f"Ответ сервера: {e.response.text}")
            return None

    def test_all_endpoints(self):
        """Тестирование всех необходимых эндпоинтов"""
        
        # 1. Тест получения открытого интереса
        logger.info("Тестирование Open Interest API")
        self.test_request('futures/openInterest', {  
            'symbol': 'BTCUSDT',
            'interval': '1h'
        })

        # 2. Тест получения ликвидаций
        logger.info("Тестирование Liquidations API")
        start_time = int((datetime.now() - timedelta(days=1)).timestamp() * 1000)
        end_time = int(datetime.now().timestamp() * 1000)
        self.test_request('futures/liquidations', {
            'symbol': 'BTCUSDT',
            'startTime': start_time,
            'endTime': end_time
        })

        # 3. Тест получения ставок финансирования
        logger.info("Тестирование Funding Rates API")
        self.test_request('futures/fundingRates', {  
            'symbol': 'BTCUSDT',
            'startTime': start_time,
            'endTime': end_time
        })

        # 4. Тест получения глубины рынка
        logger.info("Тестирование Order Book API")
        self.test_request('market/depth', {  
            'symbol': 'BTCUSDT',
            'limit': 100
        })

        # 5. Тест получения торговых пар
        logger.info("Тестирование Trading Pairs API")
        self.test_request('market/pairs')  

        # 6. Тест получения тиков
        logger.info("Тестирование Ticker API")
        self.test_request('market/ticker', {
            'symbol': 'BTCUSDT'
        })

def main():
    logger.info("Начинаем тестирование CoinArk API")
    tester = CoinArkAPITester()
    tester.test_all_endpoints()

if __name__ == "__main__":
    main()
