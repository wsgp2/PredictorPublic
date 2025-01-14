import requests
import logging
import json

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

API_KEY = '84068f54707949bc8f86e2dd9dcee6ac'
BASE_URL = 'https://api.coinank.com/api/v1'

def test_auth_format(header_format, method='GET'):
    """Тестирует различные форматы заголовков авторизации"""
    
    # Тестируем простой эндпоинт market/pairs
    url = f"{BASE_URL}/market/pairs"
    
    logger.info(f"\n{'='*50}")
    logger.info(f"Тестирование формата заголовка: {header_format}")
    logger.info(f"Метод: {method}")
    
    try:
        if method == 'GET':
            response = requests.get(url, headers=header_format)
        else:
            response = requests.post(url, headers=header_format)
            
        logger.info(f"Статус код: {response.status_code}")
        logger.info(f"Заголовки ответа: {json.dumps(dict(response.headers), indent=2)}")
        logger.info(f"Ответ: {json.dumps(response.json(), indent=2)}")
        
    except Exception as e:
        logger.error(f"Ошибка: {str(e)}")
    
    logger.info(f"{'='*50}\n")

def main():
    # Тестируем разные форматы заголовков
    formats = [
        # Формат 1: coinank-apikey
        {
            'coinank-apikey': API_KEY,
            'Content-Type': 'application/json'
        },
        
        # Формат 2: X-API-Key
        {
            'X-API-Key': API_KEY,
            'Content-Type': 'application/json'
        },
        
        # Формат 3: Authorization Bearer
        {
            'Authorization': f'Bearer {API_KEY}',
            'Content-Type': 'application/json'
        },
        
        # Формат 4: apikey
        {
            'apikey': API_KEY,
            'Content-Type': 'application/json'
        },
        
        # Формат 5: x-coinank-apikey
        {
            'x-coinank-apikey': API_KEY,
            'Content-Type': 'application/json'
        },
        
        # Формат 6: API-Key
        {
            'API-Key': API_KEY,
            'Content-Type': 'application/json'
        },

        # Формат 7: token
        {
            'token': API_KEY,
            'Content-Type': 'application/json'
        },

        # Формат 8: api_key в параметрах
        {
            'Content-Type': 'application/json',
            'api_key': API_KEY
        },

        # Формат 9: все в нижнем регистре
        {
            'coinank-apikey': API_KEY.lower(),
            'content-type': 'application/json'
        },

        # Формат 10: с дополнительными заголовками
        {
            'coinank-apikey': API_KEY,
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'User-Agent': 'CoinArk/1.0'
        }
    ]

    # Тестируем GET запросы
    for format in formats:
        test_auth_format(format, 'GET')
        
    # Тестируем POST запросы
    for format in formats:
        test_auth_format(format, 'POST')

if __name__ == "__main__":
    main()
