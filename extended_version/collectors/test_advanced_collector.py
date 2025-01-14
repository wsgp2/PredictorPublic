import pandas as pd
from pytrends.request import TrendReq
import logging
from datetime import datetime, timedelta
import time
import random
import requests
from fake_useragent import UserAgent
import json
from typing import List, Dict, Any, Optional
import os
import re

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class AdvancedTrendsCollector:
    def __init__(self):
        self.keywords = {
            'general': [
                'bitcoin', 'btc', 'crypto', 'cryptocurrency', 
                'digital currency', 'blockchain'
            ][:2]  # Для теста берем только первые 2 ключевых слова
        }
        
        # Загружаем прокси
        self.proxies = []
        self.proxy_errors = {}
        self.current_proxy_index = -1
        self.load_proxies()
        
        # Проверяем наличие необходимых библиотек
        try:
            import pytrends
            import fake_useragent
            logger.info("Все необходимые библиотеки установлены")
        except ImportError as e:
            logger.error(f"Ошибка импорта библиотек: {str(e)}")
            logger.error("Установите необходимые библиотеки: pip install pytrends fake-useragent")
            raise
        
        try:
            self.ua = UserAgent()
        except Exception as e:
            logger.error(f"Ошибка при создании UserAgent: {str(e)}")
            # Используем фиксированный список User-Agent как запасной вариант
            self.ua = type('DummyUA', (), {
                'random': lambda: random.choice([
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'
                ])
            })()
        
        # Настройки для имитации браузера
        self.browser_configs = [
            {
                'platform': 'Windows',
                'timezone': 0,
                'screen': (1920, 1080),
                'language': 'en-US'
            },
            {
                'platform': 'MacOS',
                'timezone': -480,
                'screen': (1440, 900),
                'language': 'en-GB'
            },
            {
                'platform': 'Linux',
                'timezone': 360,
                'screen': (1366, 768),
                'language': 'en'
            }
        ]

    def validate_proxy(self, proxy: str) -> bool:
        """Проверка формата прокси"""
        # Формат должен быть IP:PORT
        proxy_pattern = r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d{1,5}$'
        return bool(re.match(proxy_pattern, proxy))

    def load_proxies(self):
        """Загрузка списка прокси"""
        proxy_file = 'working_proxies.txt'
        
        if not os.path.exists(proxy_file):
            logger.error(f"Файл {proxy_file} не найден")
            return
            
        try:
            with open(proxy_file, 'r') as f:
                for line in f:
                    proxy = line.strip()
                    if proxy and self.validate_proxy(proxy):
                        self.proxies.append(proxy)
                    else:
                        logger.warning(f"Пропущен неверный прокси: {proxy}")
            
            if not self.proxies:
                logger.error("Не найдено валидных прокси")
                return
                
            logger.info(f"Загружено {len(self.proxies)} валидных прокси")
            self.proxy_errors = {proxy: 0 for proxy in self.proxies}
            
        except Exception as e:
            logger.error(f"Ошибка при загрузке прокси: {str(e)}")
            self.proxies = []

    def test_proxy(self, proxy_auth: Dict[str, str]) -> bool:
        """Тестирование прокси"""
        try:
            test_url = 'https://www.google.com'
            response = requests.get(
                test_url,
                proxies=proxy_auth,
                timeout=10,
                headers={'User-Agent': self.ua.random}
            )
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"Ошибка при тестировании прокси: {str(e)}")
            return False

    def get_next_proxy(self) -> Optional[Dict[str, str]]:
        """Получение следующего рабочего прокси"""
        if not self.proxies:
            logger.error("Список прокси пуст")
            return None
            
        # Перебираем прокси, пока не найдем рабочий
        attempts = 0
        max_attempts = len(self.proxies)
        
        while attempts < max_attempts:
            self.current_proxy_index = (self.current_proxy_index + 1) % len(self.proxies)
            current_proxy = self.proxies[self.current_proxy_index]
            
            if self.proxy_errors[current_proxy] < 3:
                proxy_auth = {
                    'http': f'http://s1XEBbG35k:pelmen271296@{current_proxy}',
                    'https': f'http://s1XEBbG35k:pelmen271296@{current_proxy}'
                }
                
                # Тестируем прокси перед использованием
                if self.test_proxy(proxy_auth):
                    logger.info(f"Выбран рабочий прокси {current_proxy} (ошибок: {self.proxy_errors[current_proxy]})")
                    return proxy_auth
                else:
                    logger.warning(f"Прокси {current_proxy} не прошел тест")
                    self.proxy_errors[current_proxy] += 1
                
            attempts += 1
        
        logger.error("Не найдено работающих прокси")
        return None

    def create_browser_profile(self) -> Dict[str, Any]:
        """Создание профиля браузера"""
        config = random.choice(self.browser_configs)
        return {
            'user_agent': self.ua.random,
            'accept_language': f"{config['language']},en;q=0.9",
            'platform': config['platform'],
            'timezone': config['timezone'],
            'screen': config['screen']
        }

    def collect_data(self, keyword: str, start_date: datetime, end_date: datetime) -> Optional[pd.DataFrame]:
        """Сбор данных для одного ключевого слова"""
        proxy_auth = self.get_next_proxy()
        if not proxy_auth:
            logger.error("Нет доступных прокси")
            return None
            
        # Получаем адрес прокси для логов
        proxy = proxy_auth['http'].split('@')[1]
        profile = self.create_browser_profile()
        logger.info(f"Используем прокси: {proxy}")
        logger.info(f"Используем профиль: {json.dumps(profile, indent=2)}")
        
        try:
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
            
            # Имитируем посещение Google
            logger.info("Посещаем Google...")
            response = session.get('https://www.google.com', timeout=30)
            if response.status_code != 200:
                raise Exception(f"Ошибка доступа к Google: {response.status_code}")
            
            # Имитируем чтение страницы
            time.sleep(random.uniform(3, 7))
            
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
            timeframe = f"{start_date.strftime('%Y-%m-%d')} {end_date.strftime('%Y-%m-%d')}"
            logger.info(f"Запрашиваем данные для {keyword} за период {timeframe}")
            
            # Добавляем случайную паузу перед запросом
            time.sleep(random.uniform(5, 10))
            
            pytrends.build_payload(
                kw_list=[keyword],
                timeframe=timeframe,
                geo=random.choice(['', 'US', 'GB']),
                gprop=random.choice(['', 'news'])
            )
            
            # Добавляем паузу после build_payload
            time.sleep(random.uniform(3, 7))
            
            # Получаем данные
            data = pytrends.interest_over_time()
            
            if not data.empty:
                logger.info(f"Успешно получены данные для {keyword}")
                # Сохраняем в CSV для проверки
                filename = f"test_data_{keyword}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                data.to_csv(filename)
                logger.info(f"Данные сохранены в {filename}")
                return data
            else:
                logger.error(f"Пустые данные для {keyword}")
                return None
                
        except Exception as e:
            logger.error(f"Ошибка при сборе данных для {keyword}")
            logger.error(f"Тип ошибки: {type(e).__name__}")
            logger.error(f"Описание: {str(e)}")
            
            if "429" in str(e):
                # Увеличиваем счетчик ошибок для прокси
                proxy = proxy_auth['http'].split('@')[1]
                self.proxy_errors[proxy] = self.proxy_errors.get(proxy, 0) + 1
                logger.warning(f"Прокси {proxy} получил ошибку 429. Всего ошибок: {self.proxy_errors[proxy]}")
                
            return None

    def run_test(self):
        """Запуск тестового сбора данных"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=90)  # Тестируем за последние 90 дней
        
        for category, keywords in self.keywords.items():
            logger.info(f"\nТестируем категорию: {category}")
            
            for keyword in keywords:
                logger.info(f"\nСбор данных для ключевого слова: {keyword}")
                
                # Пробуем несколько раз с разными прокси
                max_attempts = 3
                for attempt in range(max_attempts):
                    logger.info(f"Попытка {attempt + 1}/{max_attempts}")
                    
                    # Добавляем случайную задержку между попытками
                    if attempt > 0:
                        wait_time = random.uniform(30, 60)
                        logger.info(f"Ждем {wait_time:.2f} секунд перед следующей попыткой...")
                        time.sleep(wait_time)
                    
                    data = self.collect_data(keyword, start_date, end_date)
                    if data is not None:
                        break
                else:
                    logger.error(f"Не удалось собрать данные для {keyword} после {max_attempts} попыток")
                
                # Большая пауза между ключевыми словами
                time.sleep(random.uniform(60, 120))

if __name__ == "__main__":
    collector = AdvancedTrendsCollector()
    collector.run_test()
