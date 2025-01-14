import requests
import random
import time
import logging
import json
from fake_useragent import UserAgent
from datetime import datetime, timedelta

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_random_viewport():
    """Генерация случайного размера viewport"""
    common_resolutions = [
        (1920, 1080),
        (1366, 768),
        (1536, 864),
        (1440, 900),
        (1280, 720)
    ]
    return random.choice(common_resolutions)

def get_random_platform():
    """Генерация случайной платформы"""
    platforms = [
        {"os": "Windows", "platform": "Win32", "vendor": "Google Inc."},
        {"os": "MacOS", "platform": "MacIntel", "vendor": "Apple Computer, Inc."},
        {"os": "Linux", "platform": "Linux x86_64", "vendor": "Google Inc."}
    ]
    return random.choice(platforms)

def create_browser_fingerprint():
    """Создание реалистичного отпечатка браузера"""
    ua = UserAgent()
    platform = get_random_platform()
    viewport = get_random_viewport()
    
    return {
        "user_agent": ua.random,
        "accept_language": random.choice([
            "en-US,en;q=0.9",
            "en-GB,en;q=0.9",
            "en;q=0.9,ru;q=0.8",
        ]),
        "platform": platform,
        "viewport": viewport,
        "color_depth": random.choice([24, 32]),
        "timezone_offset": random.choice([-480, -420, -360, 0, 60, 120, 180]),
    }

def get_request_headers(fingerprint):
    """Генерация заголовков запроса на основе отпечатка"""
    return {
        "User-Agent": fingerprint["user_agent"],
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": fingerprint["accept_language"],
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Cache-Control": "max-age=0",
    }

def test_proxy_advanced(proxy):
    """Продвинутое тестирование прокси с имитацией реального браузера"""
    # Создаем уникальный отпечаток браузера
    fingerprint = create_browser_fingerprint()
    headers = get_request_headers(fingerprint)
    
    proxy_auth = {
        'http': f'http://s1XEBbG35k:pelmen271296@{proxy}',
        'https': f'http://s1XEBbG35k:pelmen271296@{proxy}'
    }
    
    try:
        # Создаем новую сессию
        session = requests.Session()
        session.headers.update(headers)
        session.proxies.update(proxy_auth)
        
        # 1. Проверяем IP
        logger.info(f"Тестирование прокси {proxy} с User-Agent: {fingerprint['user_agent']}")
        ip_response = session.get('https://api.ipify.org?format=json', timeout=10)
        ip_info = ip_response.json()
        logger.info(f"IP через прокси: {ip_info['ip']}")
        
        # Случайная пауза как у реального пользователя
        time.sleep(random.uniform(2, 5))
        
        # 2. Сначала посещаем главную страницу Google
        google_response = session.get('https://www.google.com', timeout=10)
        logger.info(f"Статус Google: {google_response.status_code}")
        
        # Имитируем время чтения страницы
        time.sleep(random.uniform(3, 7))
        
        # 3. Переходим на Google Trends
        trends_response = session.get('https://trends.google.com', timeout=10)
        logger.info(f"Статус Google Trends: {trends_response.status_code}")
        
        # Проверяем заголовки ответа на наличие признаков блокировки
        if 'x-robots-tag' in trends_response.headers:
            logger.warning(f"Обнаружен x-robots-tag: {trends_response.headers['x-robots-tag']}")
        
        if trends_response.status_code == 200:
            logger.info("Успешное подключение к Google Trends")
            return True
        else:
            logger.error(f"Ошибка доступа к Google Trends: {trends_response.status_code}")
            return False
            
    except Exception as e:
        logger.error(f"Ошибка при тестировании прокси {proxy}")
        logger.error(f"Тип ошибки: {type(e).__name__}")
        logger.error(f"Описание: {str(e)}")
        return False

def main():
    # Читаем список прокси
    try:
        with open('working_proxies.txt', 'r') as f:
            proxies = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        logger.error("Файл working_proxies.txt не найден")
        return
    
    if not proxies:
        logger.error("Список прокси пуст")
        return
    
    # Тестируем каждый прокси с разными отпечатками
    successful_proxies = []
    
    for proxy in proxies[:3]:  # Тестируем первые 3 прокси
        logger.info(f"\nТестирование прокси: {proxy}")
        
        # Пробуем каждый прокси 2 раза с разными отпечатками
        success_count = 0
        for attempt in range(2):
            logger.info(f"Попытка {attempt + 1}")
            if test_proxy_advanced(proxy):
                success_count += 1
            
            # Длительная пауза между попытками
            if attempt < 1:  # Не ждем после последней попытки
                wait_time = random.uniform(30, 45)
                logger.info(f"Ждем {wait_time:.2f} секунд перед следующей попыткой...")
                time.sleep(wait_time)
        
        if success_count > 0:
            successful_proxies.append({
                'proxy': proxy,
                'success_rate': success_count / 2 * 100
            })
        
        # Большая пауза между прокси
        time.sleep(random.uniform(60, 90))
    
    # Выводим результаты
    logger.info("\nРезультаты тестирования:")
    for result in successful_proxies:
        logger.info(f"Прокси {result['proxy']}: успешность {result['success_rate']}%")

if __name__ == "__main__":
    main()
