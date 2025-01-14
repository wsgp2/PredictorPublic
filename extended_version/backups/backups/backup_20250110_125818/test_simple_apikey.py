import requests
import logging
import json

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

API_KEY = '84068f54707949bc8f86e2dd9dcee6ac'
BASE_URL = 'https://api.coinank.com/api/v1'

# Простой заголовок с apikey
headers = {
    'X-ApiKey': API_KEY
}

def test_endpoint():
    url = f"{BASE_URL}/market/pairs"
    
    logger.info(f"\nТестирование с простым заголовком apikey")
    logger.info(f"URL: {url}")
    logger.info(f"Headers: {headers}")
    
    try:
        response = requests.get(url, headers=headers)
        logger.info(f"Статус код: {response.status_code}")
        logger.info(f"Заголовки ответа: {json.dumps(dict(response.headers), indent=2)}")
        logger.info(f"Ответ: {json.dumps(response.json(), indent=2)}")
        
    except Exception as e:
        logger.error(f"Ошибка: {str(e)}")

if __name__ == "__main__":
    test_endpoint()
