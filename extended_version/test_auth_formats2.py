import requests
import logging
import json

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

API_KEY = '84068f54707949bc8f86e2dd9dcee6ac'
BASE_URL = 'https://api.coinank.com/api/v1'

def test_auth_format(header_format):
    """Тестирует различные форматы заголовков авторизации"""
    
    # Тестируем простой эндпоинт market/pairs
    url = f"{BASE_URL}/market/pairs"
    
    logger.info(f"\n{'='*50}")
    logger.info(f"Тестирование формата заголовка: {header_format}")
    
    try:
        response = requests.get(url, headers=header_format)
            
        logger.info(f"Статус код: {response.status_code}")
        logger.info(f"Заголовки ответа: {json.dumps(dict(response.headers), indent=2)}")
        logger.info(f"Ответ: {json.dumps(response.json(), indent=2)}")
        
    except Exception as e:
        logger.error(f"Ошибка: {str(e)}")
    
    logger.info(f"{'='*50}\n")

def main():
    # Тестируем новые форматы заголовков
    formats = [
        # Формат 1: appkey
        {
            'appkey': API_KEY,
            'Content-Type': 'application/json'
        },
        
        # Формат 2: x-appkey
        {
            'x-appkey': API_KEY,
            'Content-Type': 'application/json'
        },
        
        # Формат 3: coinank-apikey в нижнем регистре
        {
            'coinank-apikey': API_KEY.lower(),
            'Content-Type': 'application/json'
        },
        
        # Формат 4: appkey в нижнем регистре
        {
            'appkey': API_KEY.lower(),
            'Content-Type': 'application/json'
        },
        
        # Формат 5: комбинация coinank-apikey и appkey
        {
            'coinank-apikey': API_KEY,
            'appkey': API_KEY,
            'Content-Type': 'application/json'
        },
        
        # Формат 6: с дополнительными заголовками
        {
            'coinank-apikey': API_KEY,
            'appkey': API_KEY,
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'User-Agent': 'CoinArk/1.0',
            'Origin': 'https://api.coinank.com'
        },

        # Формат 7: с web-version
        {
            'coinank-apikey': API_KEY,
            'Content-Type': 'application/json',
            'web-version': '1.0'
        },

        # Формат 8: с app-version
        {
            'coinank-apikey': API_KEY,
            'Content-Type': 'application/json',
            'app-version': '1.0'
        },

        # Формат 9: с extCode
        {
            'coinank-apikey': API_KEY,
            'Content-Type': 'application/json',
            'extCode': 'default'
        },

        # Формат 10: все возможные заголовки
        {
            'coinank-apikey': API_KEY,
            'appkey': API_KEY,
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'User-Agent': 'CoinArk/1.0',
            'Origin': 'https://api.coinank.com',
            'web-version': '1.0',
            'app-version': '1.0',
            'extCode': 'default'
        }
    ]

    # Тестируем каждый формат
    for format in formats:
        test_auth_format(format)

if __name__ == "__main__":
    main()
