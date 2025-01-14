"""
Тестирование работы с Reddit API
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sentiment_analysis import SentimentAnalyzer
from config import REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET
import logging
from datetime import datetime, timedelta, timezone
import certifi

# Устанавливаем переменную окружения для SSL сертификатов
os.environ['SSL_CERT_FILE'] = certifi.where()
os.environ['REQUESTS_CA_BUNDLE'] = certifi.where()

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_reddit_connection():
    """Тестирование подключения к Reddit API"""
    try:
        analyzer = SentimentAnalyzer()
        analyzer.initialize_reddit(REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET)
        
        # Проверяем подключение, пытаясь получить данные из сабреддита
        subreddit = analyzer.reddit_client.subreddit('bitcoin')
        posts = list(subreddit.hot(limit=1))
        
        if posts:
            logger.info("Успешное подключение к Reddit API")
            logger.info(f"Пример поста: {posts[0].title}")
            return True
        else:
            logger.error("Не удалось получить посты")
            return False
            
    except Exception as e:
        logger.error(f"Ошибка при подключении к Reddit API: {e}")
        return False

def test_sentiment_analysis():
    """Тестирование анализа настроений"""
    try:
        analyzer = SentimentAnalyzer()
        analyzer.initialize_reddit(REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET)
        
        # Получаем и анализируем настроения за последний день
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=1)
        
        sentiments = analyzer.get_reddit_sentiment(start_date, end_date)
        
        if not sentiments.empty:
            logger.info("Анализ настроений успешно выполнен")
            logger.info(f"Результаты анализа:\n{sentiments.head()}")
            return True
        else:
            logger.error("Не удалось выполнить анализ настроений")
            return False
            
    except Exception as e:
        logger.error(f"Ошибка при анализе настроений: {e}")
        return False

if __name__ == "__main__":
    logger.info("Начало тестирования Reddit API...")
    
    # Тест 1: Подключение к API
    if test_reddit_connection():
        logger.info("Тест подключения пройден успешно")
    else:
        logger.error("Тест подключения не пройден")
        
    # Тест 2: Анализ настроений
    if test_sentiment_analysis():
        logger.info("Тест анализа настроений пройден успешно")
    else:
        logger.error("Тест анализа настроений не пройден")
