from pytrends.request import TrendReq
import pandas as pd
from datetime import datetime, timedelta
import logging
import time
import random
import requests
from fake_useragent import UserAgent

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_random_user_agent():
    """Генерация случайного User-Agent"""
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.1 Safari/605.1.15',
    ]
    return random.choice(user_agents)

def get_random_headers():
    """Генерация случайных заголовков"""
    return {
        'User-Agent': get_random_user_agent(),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': random.choice(['en-US,en;q=0.5', 'en-GB,en;q=0.5', 'en;q=0.5']),
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Cache-Control': 'max-age=0',
    }

def test_connection():
    """Тест прямого подключения к Google"""
    try:
        headers = get_random_headers()
        response = requests.get('https://trends.google.com', headers=headers, timeout=10)
        logger.info(f"Статус подключения к Google Trends: {response.status_code}")
        return response.status_code == 200
    except Exception as e:
        logger.error(f"Ошибка при проверке подключения: {str(e)}")
        return False

def test_single_keyword(keyword: str):
    """Тест сбора данных для одного ключевого слова"""
    try:
        logger.info(f"Тестируем сбор данных для '{keyword}'")
        
        # Сначала проверяем подключение
        if not test_connection():
            logger.error("Нет подключения к Google Trends")
            return False
        
        # Создаем клиент без прокси для теста
        pytrends = TrendReq(
            hl='en-US',
            tz=360,
            requests_args={
                'headers': get_random_headers(),
            }
        )
        
        logger.info("Подключение установлено, пробуем получить данные...")
        
        # Формируем временной интервал
        end_date = datetime.now()
        start_date = end_date - timedelta(days=90)
        timeframe = f"{start_date.strftime('%Y-%m-%d')} {end_date.strftime('%Y-%m-%d')}"
        logger.info(f"Запрашиваем данные за период: {timeframe}")
        
        # Строим запрос
        pytrends.build_payload(
            [keyword],
            cat=0,
            timeframe=timeframe,
            geo='',
            gprop=''
        )
        
        # Получаем данные
        logger.info("Отправляем запрос...")
        df = pytrends.interest_over_time()
        
        if df is not None and not df.empty:
            if 'isPartial' in df.columns:
                df = df.drop('isPartial', axis=1)
            logger.info(f"Успешно получены данные: {len(df)} записей")
            logger.info(f"Диапазон дат: с {df.index.min()} по {df.index.max()}")
            logger.info(f"Пример данных:\n{df.head()}")
            
            # Сохраняем данные для анализа
            output_file = f'test_data_{keyword}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
            df.to_csv(output_file)
            logger.info(f"Данные сохранены в {output_file}")
            
            return True
        else:
            logger.warning(f"Нет данных для {keyword}")
            return False
            
    except Exception as e:
        import traceback
        logger.error(f"Ошибка при сборе данных для {keyword}")
        logger.error(f"Тип ошибки: {type(e).__name__}")
        logger.error(f"Описание: {str(e)}")
        logger.error(f"Traceback:\n{traceback.format_exc()}")
        return False

def create_browser_profile():
    """Создание профиля браузера"""
    ua = UserAgent()
    return {
        'user_agent': ua.random,
        'accept_language': random.choice(['en-US,en;q=0.9', 'en-GB,en;q=0.8', 'en;q=0.7']),
        'timezone': random.choice([0, 360, -480]),
        'platform': random.choice(['Win32', 'MacIntel', 'Linux x86_64'])
    }

def test_with_proxy(keyword: str, proxy: str, retry_delay: int = 180):
    """Тест сбора данных через прокси"""
    try:
        logger.info(f"Тестируем сбор данных для '{keyword}' через прокси {proxy}")
        
        # Создаем профиль браузера
        profile = create_browser_profile()
        logger.info(f"Используем User-Agent: {profile['user_agent']}")
        
        # Добавляем случайную задержку перед запросом
        sleep_time = random.uniform(30, 60)
        logger.info(f"Ждем {sleep_time:.2f} секунд перед запросом...")
        time.sleep(sleep_time)
        
        proxy_auth = {
            'http': f'http://s1XEBbG35k:pelmen271296@{proxy}',
            'https': f'http://s1XEBbG35k:pelmen271296@{proxy}'
        }
        
        # Создаем сессию
        session = requests.Session()
        session.headers.update({
            'User-Agent': profile['user_agent'],
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': profile['accept_language'],
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
        session.proxies.update(proxy_auth)
        
        # Сначала посещаем Google
        google_response = session.get('https://www.google.com', timeout=30)
        if google_response.status_code != 200:
            logger.error(f"Ошибка доступа к Google: {google_response.status_code}")
            return False
            
        # Имитируем время чтения страницы
        time.sleep(random.uniform(5, 10))
        
        # Создаем клиент pytrends
        pytrends = TrendReq(
            hl=profile['accept_language'].split(',')[0],
            tz=profile['timezone'],
            timeout=(30, 60),
            requests_args={
                'verify': True,
                'proxies': proxy_auth,
                'headers': session.headers
            }
        )
        
        # Очищаем куки
        pytrends.cookies.clear()
        
        # Строим запрос
        logger.info("Отправляем запрос к Google Trends...")
        timeframes = ['today 3-m', 'today 1-m', 'now 7-d']
        pytrends.build_payload(
            kw_list=[keyword],
            timeframe=random.choice(timeframes),
            geo=random.choice(['', 'US', 'GB']),
            gprop=random.choice(['', 'news'])
        )
        
        # Добавляем паузу после build_payload
        time.sleep(random.uniform(5, 10))
        
        # Получаем данные
        data = pytrends.interest_over_time()
        
        if not data.empty:
            # Сохраняем данные
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"test_data_{keyword}_{timestamp}.csv"
            data.to_csv(filename)
            logger.info(f"Данные сохранены в {filename}")
            return True
        else:
            logger.error(f"Данные пусты для {keyword} через прокси {proxy}")
            return False
            
    except Exception as e:
        logger.error(f"Ошибка при сборе данных для {keyword} через прокси {proxy}")
        logger.error(f"Тип ошибки: {type(e).__name__}")
        logger.error(f"Описание: {str(e)}")
        logger.error("Traceback:", exc_info=True)
        
        if "429" in str(e):
            actual_delay = retry_delay + random.uniform(60, 120)
            logger.info(f"Прокси {proxy} временно заблокирован. Ждем {actual_delay:.2f} секунд...")
            time.sleep(actual_delay)
            
        return False

def main():
    """Основная функция тестирования"""
    # Читаем список рабочих прокси
    try:
        with open('working_proxies.txt', 'r') as f:
            proxies = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        logger.error("Файл working_proxies.txt не найден")
        logger.info("Сначала запустите proxy_tester.py для получения списка рабочих прокси")
        return
    
    if not proxies:
        logger.error("Список прокси пуст")
        return
    
    # Тестируем только один ключевой запрос
    keyword = 'bitcoin'
    max_retries = 3
    retry_delay = 180  # 3 минуты между попытками
    
    # Перемешиваем список прокси
    random.shuffle(proxies)
    
    # Пробуем разные прокси
    for proxy in proxies[:max_retries]:
        logger.info(f"Попытка использовать прокси {proxy}")
        
        # Длительная пауза перед запросом
        wait_time = random.uniform(60, 120)  # 1-2 минуты
        logger.info(f"Ждем {wait_time:.2f} секунд перед запросом...")
        time.sleep(wait_time)
        
        if test_with_proxy(keyword, proxy, retry_delay):
            logger.info("Успешно собраны данные!")
            break
        else:
            wait_time = random.uniform(120, 180)  # 2-3 минуты между прокси
            logger.info(f"Ждем {wait_time:.2f} секунд перед следующим прокси...")
            time.sleep(wait_time)
    else:
        logger.error(f"Не удалось собрать данные после {max_retries} попыток с разными прокси")

if __name__ == "__main__":
    main()
