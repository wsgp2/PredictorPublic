import requests
import logging
from datetime import datetime, timedelta

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_endpoint(endpoint, timespan='1days'):
    """Тестирование одного эндпоинта"""
    url = f'https://api.blockchain.info/charts/{endpoint}'
    params = {
        'timespan': timespan,
        'format': 'json',
        'sampled': 'true'
    }
    
    logger.info(f"\nТестирование эндпоинта: {endpoint}")
    logger.info(f"URL: {url}")
    logger.info(f"Параметры: {params}")
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()  # Проверяем статус ответа
        
        data = response.json()
        logger.info("Ответ получен успешно")
        logger.info(f"Название: {data.get('name', 'Н/Д')}")
        logger.info(f"Описание: {data.get('description', 'Н/Д')}")
        logger.info(f"Единица измерения: {data.get('unit', 'Н/Д')}")
        
        values = data.get('values', [])
        if values:
            logger.info(f"Количество точек данных: {len(values)}")
            first_point = datetime.fromtimestamp(values[0]['x'])
            last_point = datetime.fromtimestamp(values[-1]['x'])
            logger.info(f"Период данных: с {first_point} по {last_point}")
            logger.info(f"Пример значения: {values[-1]['y']}")
        
        return True
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Ошибка при запросе: {str(e)}")
        if hasattr(e.response, 'status_code'):
            logger.error(f"Статус код: {e.response.status_code}")
        return False

def main():
    # Список эндпоинтов для тестирования
    endpoints = [
        'trade-volume',
        'miners-revenue',
        'estimated-transaction-volume-usd',
        'market-price',
        'total-bitcoins',
        'market-cap',
        'hash-rate',
        'difficulty',
        'transaction-fees',
        'n-unique-addresses',
        'n-transactions'
    ]
    
    results = {}
    for endpoint in endpoints:
        success = test_endpoint(endpoint)
        results[endpoint] = success
    
    logger.info("\nИтоговые результаты:")
    for endpoint, success in results.items():
        status = "✅ Работает" if success else "❌ Ошибка"
        logger.info(f"{endpoint}: {status}")

if __name__ == "__main__":
    main()
