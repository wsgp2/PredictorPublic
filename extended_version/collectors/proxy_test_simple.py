import requests
import random
import time
import logging

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

def test_proxy_with_google(proxy):
    """Тестирование прокси с Google Trends"""
    proxy_auth = {
        'http': f'http://s1XEBbG35k:pelmen271296@{proxy}',
        'https': f'http://s1XEBbG35k:pelmen271296@{proxy}'
    }
    
    headers = {
        'User-Agent': get_random_user_agent(),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    }
    
    try:
        # Создаем новую сессию
        session = requests.Session()
        session.headers.update(headers)
        session.proxies.update(proxy_auth)
        
        # Сначала проверяем IP через специальный сервис
        ip_response = session.get('https://api.ipify.org?format=json', timeout=10)
        ip_info = ip_response.json()
        logger.info(f"Текущий IP через прокси: {ip_info['ip']}")
        
        # Делаем паузу
        time.sleep(random.uniform(2, 5))
        
        # Пробуем получить доступ к Google Trends
        response = session.get('https://trends.google.com', timeout=10)
        logger.info(f"Статус ответа Google Trends: {response.status_code}")
        logger.info(f"Заголовки ответа: {dict(response.headers)}")
        
        return True
        
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
    
    # Тестируем первые 3 прокси
    for proxy in proxies[:3]:
        logger.info(f"\nТестирование прокси: {proxy}")
        success = test_proxy_with_google(proxy)
        
        if success:
            logger.info(f"Прокси {proxy} успешно работает с Google")
        else:
            logger.error(f"Прокси {proxy} не работает с Google")
        
        # Пауза между тестами
        time.sleep(random.uniform(10, 15))

if __name__ == "__main__":
    main()
