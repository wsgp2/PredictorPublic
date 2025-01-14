import pandas as pd
from pytrends.request import TrendReq
import logging
from datetime import datetime, timedelta
import time
import random
import os

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def load_proxies():
    """Загрузка списка прокси"""
    proxies = []
    try:
        proxy_file = os.path.join(os.path.dirname(__file__), 'proxy_list.txt')
        if not os.path.exists(proxy_file):
            logger.error(f"Файл с прокси не найден: {proxy_file}")
            return proxies

        with open(proxy_file, 'r') as f:
            for line in f:
                if ':' in line:
                    ip, port = line.strip().split(':')
                    proxy_url = f'http://s1XEBbG35k:pelmen271296@{ip}:{port}'
                    proxies.append({
                        'http': proxy_url,
                        'https': proxy_url
                    })
        
        logger.info(f"Загружено {len(proxies)} прокси")
    except Exception as e:
        logger.error(f"Ошибка при загрузке прокси: {str(e)}")
    
    return proxies

def test_proxy(proxy, keyword='bitcoin'):
    """Тестирование одного прокси"""
    try:
        logger.info(f"Настройка соединения с прокси...")
        
        # User agents для ротации
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0'
        ]
        
        # Создаем клиент с текущим прокси
        pytrends = TrendReq(
            hl='en-US',
            tz=360,
            timeout=(30,45),  # Увеличиваем таймаут
            proxies=proxy,
            retries=3,
            backoff_factor=1.5,
            requests_args={
                'headers': {
                    'User-Agent': random.choice(user_agents)
                },
                'verify': True,
                'timeout': 30
            }
        )
        
        logger.info(f"Пробуем подключиться к Google Trends...")
        
        # Пробуем получить данные за последнюю неделю
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        timeframe = f"{start_date.strftime('%Y-%m-%d')} {end_date.strftime('%Y-%m-%d')}"
        
        logger.info(f"Отправляем запрос за период {timeframe}")
        
        pytrends.build_payload(
            [keyword],
            cat=0,
            timeframe=timeframe,
            geo='',
            gprop=''
        )
        
        df = pytrends.interest_over_time()
        
        if df is not None and not df.empty:
            logger.info(f"Прокси работает: {list(proxy.values())[0]}")
            logger.info(f"Получены данные:\n{df.head()}")
            return True
        else:
            logger.warning(f"Прокси не вернул данные: {list(proxy.values())[0]}")
            return False
            
    except Exception as e:
        import traceback
        logger.error(f"Ошибка при тестировании прокси {list(proxy.values())[0]}")
        logger.error(f"Тип ошибки: {type(e).__name__}")
        logger.error(f"Описание: {str(e)}")
        logger.error(f"Traceback:\n{traceback.format_exc()}")
        return False

def test_all_proxies():
    """Тестирование всех прокси"""
    proxies = load_proxies()
    working_proxies = []
    
    for proxy in proxies:
        logger.info(f"Тестируем прокси: {proxy}")
        if test_proxy(proxy):
            working_proxies.append(proxy)
        time.sleep(random.uniform(2, 5))  # Пауза между тестами
    
    logger.info(f"Всего рабочих прокси: {len(working_proxies)} из {len(proxies)}")
    return working_proxies

def test_data_collection(proxy, keywords=['bitcoin', 'crypto'], days=7):
    """Тестирование сбора данных"""
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        timeframe = f"{start_date.strftime('%Y-%m-%d')} {end_date.strftime('%Y-%m-%d')}"
        
        pytrends = TrendReq(
            hl='en-US',
            tz=360,
            timeout=(10,25),
            proxies=proxy,
            retries=2,
            backoff_factor=0.5
        )
        
        pytrends.build_payload(
            keywords,
            cat=0,
            timeframe=timeframe,
            geo='',
            gprop=''
        )
        
        df = pytrends.interest_over_time()
        
        if df is not None and not df.empty:
            # Удаляем колонку isPartial если она есть
            if 'isPartial' in df.columns:
                df = df.drop('isPartial', axis=1)
            
            logger.info(f"Успешно собраны данные за период {timeframe}")
            logger.info(f"Форма данных: {df.shape}")
            logger.info(f"Колонки: {df.columns.tolist()}")
            logger.info(f"Пример данных:\n{df.head()}")
            return df
        else:
            logger.warning("Не удалось получить данные")
            return None
            
    except Exception as e:
        logger.error(f"Ошибка при сборе данных: {str(e)}")
        return None

if __name__ == "__main__":
    # Сначала тестируем прокси
    working_proxies = test_all_proxies()
    
    if working_proxies:
        # Тестируем сбор данных с первым рабочим прокси
        logger.info("Тестируем сбор данных...")
        test_data_collection(working_proxies[0])
    else:
        logger.error("Не найдено рабочих прокси")
