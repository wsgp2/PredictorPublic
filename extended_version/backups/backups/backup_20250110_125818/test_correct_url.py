import requests
import logging
import json

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

API_KEY = '84068f54707949bc8f86e2dd9dcee6ac'
BASE_URL = 'https://open-api.coinank.com/api'  # Обновленный URL

# Заголовки как в примере curl
headers = {
    'apikey': API_KEY,
    'accept': 'application/json'
}

def test_endpoint():
    # Используем тот же endpoint, что в примере
    url = f"{BASE_URL}/baseCoin/list"
    params = {
        'productType': 'SWAP'
    }
    
    logger.info(f"\nТестирование с правильным URL и заголовками")
    logger.info(f"URL: {url}")
    logger.info(f"Headers: {headers}")
    logger.info(f"Params: {params}")
    
    try:
        response = requests.get(url, headers=headers, params=params)
        logger.info(f"Статус код: {response.status_code}")
        logger.info(f"Заголовки ответа: {json.dumps(dict(response.headers), indent=2)}")
        logger.info(f"Ответ: {json.dumps(response.json(), indent=2)}")
        
    except Exception as e:
        logger.error(f"Ошибка: {str(e)}")

if __name__ == "__main__":
    test_endpoint()
