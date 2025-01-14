import requests
import logging
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_daily_data(endpoint='market-price', timespan='30days'):
    """Тестирование получения ежедневных данных"""
    url = f'https://api.blockchain.info/charts/{endpoint}'
    params = {
        'timespan': timespan,
        'format': 'json',
        'sampled': 'false',
        'rolling_average': '24hours'
    }
    
    logger.info(f"\nПолучение ежедневных данных для: {endpoint}")
    logger.info(f"URL: {url}")
    logger.info(f"Параметры: {params}")
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        
        data = response.json()
        values = data.get('values', [])
        
        if values:
            first_point = datetime.fromtimestamp(values[0]['x'])
            last_point = datetime.fromtimestamp(values[-1]['x'])
            
            logger.info(f"\nСтатистика данных:")
            logger.info(f"Количество точек: {len(values)}")
            logger.info(f"Начало периода: {first_point}")
            logger.info(f"Конец периода: {last_point}")
            logger.info(f"Первое значение: {values[0]['y']}")
            logger.info(f"Последнее значение: {values[-1]['y']}")
            
            # Проверяем интервал между точками
            if len(values) > 1:
                interval = values[1]['x'] - values[0]['x']
                logger.info(f"Интервал между точками: {interval} секунд ({interval/3600:.2f} часов)")
        
        return True
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Ошибка при запросе: {str(e)}")
        return False

if __name__ == "__main__":
    # Тестируем получение ежедневных данных
    test_daily_data('market-price', '30days')
