"""
Тестирование доступа к API
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tweepy
import praw
from config import *
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_twitter_access():
    """Проверка доступа к Twitter API v2"""
    logger.info("\nПроверка доступа к Twitter API v2:")
    
    try:
        # Аутентификация с использованием Bearer token
        client = tweepy.Client(
            bearer_token=TWITTER_BEARER_TOKEN,
            consumer_key=TWITTER_API_KEY,
            consumer_secret=TWITTER_API_SECRET,
            access_token=TWITTER_ACCESS_TOKEN,
            access_token_secret=TWITTER_ACCESS_TOKEN_SECRET
        )
        
        # Поиск твитов
        logger.info("Поиск твитов по запросу 'bitcoin'...")
        tweets = client.search_recent_tweets(
            query="bitcoin",
            max_results=10,
            tweet_fields=['created_at', 'public_metrics']
        )
        
        if tweets.data:
            logger.info("✅ Поиск работает. Примеры твитов:")
            for tweet in tweets.data[:3]:
                logger.info(f"- {tweet.text[:100]}...")
                logger.info(f"  Метрики: {tweet.public_metrics}")
        else:
            logger.info("✅ API работает, но твиты не найдены")
            
        # Получение информации о пользователе
        logger.info("\nПолучение информации о пользователе...")
        user = client.get_me()
        if user.data:
            logger.info(f"✅ Успешная аутентификация как: @{user.data.username}")
        
    except Exception as e:
        logger.error(f"❌ Ошибка Twitter API: {str(e)}")

def test_reddit_access():
    """Проверка доступа к Reddit API"""
    logger.info("\nПроверка доступа к Reddit API:")
    
    try:
        # Инициализация клиента
        reddit = praw.Reddit(
            client_id=REDDIT_CLIENT_ID,
            client_secret=REDDIT_CLIENT_SECRET,
            user_agent=REDDIT_USER_AGENT
        )
        
        # Проверка доступа к сабреддиту
        logger.info("Проверка доступа к r/bitcoin...")
        subreddit = reddit.subreddit("bitcoin")
        
        # Получение последних постов
        logger.info("Получение последних постов...")
        posts = list(subreddit.new(limit=3))
        if posts:
            logger.info("✅ Доступ работает. Примеры постов:")
            for post in posts:
                logger.info(f"- {post.title}")
                logger.info(f"  Рейтинг: {post.score}, Комментарии: {post.num_comments}")
        
        # Проверка rate limits
        logger.info("\nПроверка rate limits:")
        logger.info(f"Оставшиеся запросы: {reddit.auth.limits}")
        
    except Exception as e:
        logger.error(f"❌ Ошибка Reddit API: {str(e)}")

if __name__ == "__main__":
    test_twitter_access()
    test_reddit_access()
