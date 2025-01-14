"""
Тестирование анализа настроений
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
from sentiment_analysis import SentimentAnalyzer
from config import *
import pandas as pd
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def initialize_analyzer():
    """Инициализация анализатора с API ключами"""
    analyzer = SentimentAnalyzer()
    
    # Инициализация Reddit
    analyzer.initialize_reddit(
        client_id=REDDIT_CLIENT_ID,
        client_secret=REDDIT_CLIENT_SECRET
    )
    
    # Инициализация Twitter
    analyzer.initialize_twitter(
        api_key=TWITTER_API_KEY,
        api_secret=TWITTER_API_SECRET,
        access_token=TWITTER_ACCESS_TOKEN,
        access_token_secret=TWITTER_ACCESS_TOKEN_SECRET,
        bearer_token=TWITTER_BEARER_TOKEN
    )
    
    return analyzer

def test_text_sentiment():
    analyzer = initialize_analyzer()
    
    # Тестовые тексты
    texts = [
        "Bitcoin is showing strong bullish momentum",
        "The market is crashing, everything is red",
        "Neutral market conditions, waiting for clear signals",
        "Great news! Bitcoin ETF approved!",
        "Warning: potential market manipulation detected"
    ]
    
    logger.info("\nТестирование анализа текста:")
    for text in texts:
        sentiment = analyzer._analyze_text_sentiment(text)
        logger.info(f"Текст: {text}")
        logger.info(f"Настроение: {sentiment:.3f}\n")

def test_twitter_sentiment():
    analyzer = initialize_analyzer()
    
    # Тестовый период (последние 2 дня)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=2)
    
    logger.info(f"\nТестирование получения данных из Twitter за период: {start_date.date()} - {end_date.date()}")
    
    twitter_sentiment = analyzer.get_twitter_sentiment(start_date, end_date)
    if not twitter_sentiment.empty:
        logger.info("\nПолученные данные из Twitter:")
        logger.info(twitter_sentiment)
        
        logger.info("\nСтатистика:")
        logger.info(twitter_sentiment.describe())
    else:
        logger.warning("Не удалось получить данные из Twitter")

def test_reddit_sentiment():
    analyzer = initialize_analyzer()
    
    # Тестовый период (последние 2 дня)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=2)
    
    logger.info(f"\nТестирование получения данных из Reddit за период: {start_date.date()} - {end_date.date()}")
    
    reddit_sentiment = analyzer.get_reddit_sentiment(start_date, end_date)
    if not reddit_sentiment.empty:
        logger.info("\nПолученные данные из Reddit:")
        logger.info(reddit_sentiment)
        
        logger.info("\nСтатистика:")
        logger.info(reddit_sentiment.describe())
    else:
        logger.warning("Не удалось получить данные из Reddit")

def test_sentiment_aggregation():
    analyzer = initialize_analyzer()
    
    # Тестовые данные
    data = {
        'date': pd.date_range(start='2025-01-01', periods=5),
        'sentiment': [0.5, -0.3, 0.2, 0.8, -0.1],
        'engagement': [100, 50, 200, 150, 75]
    }
    df = pd.DataFrame(data)
    
    logger.info("\nТестирование агрегации настроений:")
    aggregated = analyzer._aggregate_sentiment(df)
    logger.info("\nАгрегированные данные:")
    logger.info(aggregated)
    
    logger.info("\nСтатистика:")
    logger.info(aggregated.describe())

def test_full_pipeline():
    analyzer = initialize_analyzer()
    
    # Тестовый период (последние 2 дня)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=2)
    
    logger.info(f"\nТестирование полного пайплайна за период: {start_date.date()} - {end_date.date()}")
    
    # Получение признаков
    features = analyzer.prepare_sentiment_features(start_date, end_date)
    
    if not features.empty:
        logger.info("\nПолученные признаки:")
        for column in features.columns:
            logger.info(f"- {column}")
            
        logger.info("\nПример данных:")
        logger.info(features.head())
        
        logger.info("\nСтатистика:")
        logger.info(features.describe())
        
        # Проверка на пропущенные значения
        nulls = features.isnull().sum()
        if nulls.any():
            logger.info("\nПропущенные значения:")
            logger.info(nulls[nulls > 0])
        else:
            logger.info("\nПропущенные значения отсутствуют")
    else:
        logger.warning("Не удалось получить признаки настроений")

if __name__ == "__main__":
    test_text_sentiment()
    test_twitter_sentiment()
    test_reddit_sentiment()
    test_sentiment_aggregation()
    test_full_pipeline()
