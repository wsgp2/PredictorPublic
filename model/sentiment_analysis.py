"""
Модуль для анализа настроений из Reddit и Twitter
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import praw
from textblob import TextBlob
import json
import os
import time
import pickle
from typing import Dict, List, Optional
import hashlib
from pathlib import Path
from .logger import setup_logger

logger = setup_logger(__name__)

class SentimentAnalyzer:
    """Класс для анализа настроений из различных источников"""
    
    def __init__(self, cache_dir: str = None):
        self.cache = {}
        self.reddit_client = None
        self.twitter_client = None
        
        # Настройка кэширования
        if cache_dir is None:
            cache_dir = os.path.join(os.path.dirname(__file__), 'cache')
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Ключевые слова для поиска
        self.keywords = [
            'bitcoin', 'BTC', 'crypto', 'cryptocurrency',
            'bitcoin price', 'bitcoin trading', 'buy bitcoin',
            'sell bitcoin', 'BTC market', 'blockchain',
            'digital gold', 'hodl'
        ]
        
        # Хэштеги для поиска
        self.hashtags = [
            '#Bitcoin', '#BTC', '#CryptoNews', '#BitcoinPrice',
            '#BTCtoTheMoon', '#CryptoTrading', '#BuyBitcoin'
        ]
        
        # Сабреддиты для анализа
        self.subreddits = [
            'bitcoin', 'cryptocurrency', 'CryptoMarkets',
            'BitcoinMarkets'
        ]
    
    def _get_cache_key(self, prefix: str, **kwargs) -> str:
        """Генерация ключа кэша"""
        key_dict = {k: str(v) for k, v in sorted(kwargs.items())}
        key_str = json.dumps(key_dict, sort_keys=True)
        return f"{prefix}_{hashlib.md5(key_str.encode()).hexdigest()}"
    
    def _get_from_cache(self, key: str) -> Optional[pd.DataFrame]:
        """Получение данных из кэша"""
        try:
            cache_file = self.cache_dir / f"{key}.parquet"
            if cache_file.exists():
                df = pd.read_parquet(cache_file)
                # Проверяем и устанавливаем временную зону
                if df.index.tz is None:
                    df.index = df.index.tz_localize('UTC')
                elif str(df.index.tz) != 'UTC':
                    df.index = df.index.tz_convert('UTC')
                logger.info(f"Данные загружены из кэша: {key}")
                return df
        except Exception as e:
            logger.error(f"Ошибка при загрузке из кэша: {e}")
        return None
    
    def _save_to_cache(self, key: str, df: pd.DataFrame):
        """Сохранение данных в кэш"""
        try:
            cache_file = self.cache_dir / f"{key}.parquet"
            df.to_parquet(cache_file)
            logger.info(f"Данные сохранены в кэш: {key}")
        except Exception as e:
            logger.error(f"Ошибка при сохранении в кэш: {e}")
    
    def get_reddit_sentiment(self, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """
        Получение и анализ настроений с Reddit из сохраненных данных
        """
        try:
            # Проверяем кэш
            cache_key = self._get_cache_key('reddit', start_date=start_date, end_date=end_date)
            cached_data = self._get_from_cache(cache_key)
            if cached_data is not None:
                return cached_data
            
            # Путь к директории с данными Reddit
            reddit_data_dir = os.path.join(os.path.dirname(__file__), 'reddit_data')
            current_date = datetime.now().strftime('%Y%m%d')
            
            all_data = []
            total_posts = 0
            total_comments = 0
            
            # Убеждаемся, что даты в UTC
            if start_date.tzinfo is None:
                start_date = start_date.replace(tzinfo=timezone.utc)
            if end_date.tzinfo is None:
                end_date = end_date.replace(tzinfo=timezone.utc)
            
            # Получаем список всех файлов
            files = os.listdir(reddit_data_dir)
            
            # Обрабатываем посты и комментарии для каждого сабреддита
            for subreddit in self.subreddits:
                # Обрабатываем посты
                posts_file = f'{subreddit}_posts_{current_date}.csv'
                if posts_file in files:
                    try:
                        posts_path = os.path.join(reddit_data_dir, posts_file)
                        posts_df = pd.read_csv(posts_path)
                        posts_df['created_utc'] = pd.to_datetime(posts_df['created_utc']).dt.tz_localize('UTC')
                        
                        # Фильтруем по дате
                        mask = (posts_df['created_utc'] >= start_date) & (posts_df['created_utc'] <= end_date)
                        filtered_posts = posts_df[mask]
                        total_posts += len(filtered_posts)
                        
                        # Анализируем каждый пост
                        for _, post in filtered_posts.iterrows():
                            title_sentiment = self._analyze_text_sentiment(str(post['title']))
                            body_sentiment = self._analyze_text_sentiment(str(post.get('selftext', '')))
                            
                            # Вес поста зависит от рейтинга и количества комментариев
                            score = float(post['score'])
                            num_comments = float(post['num_comments'])
                            upvote_ratio = float(post.get('upvote_ratio', 1.0))
                            
                            # Рассчитываем вес на основе метрик взаимодействия
                            engagement = (score * upvote_ratio * 1.5) + (num_comments * 0.5)
                            
                            # Взвешенное настроение (заголовок важнее текста)
                            weighted_sentiment = (title_sentiment * 0.6 + body_sentiment * 0.4)
                            
                            all_data.append({
                                'date': post['created_utc'],
                                'sentiment': weighted_sentiment,
                                'engagement': engagement,
                                'subreddit': subreddit,
                                'type': 'post',
                                'score': score,
                                'num_comments': num_comments,
                                'upvote_ratio': upvote_ratio
                            })
                            
                    except Exception as e:
                        logger.error(f"Ошибка при обработке постов {subreddit}: {e}")
                
                # Обрабатываем комментарии
                comments_file = f'{subreddit}_comments_{current_date}.csv'
                if comments_file in files:
                    try:
                        comments_path = os.path.join(reddit_data_dir, comments_file)
                        comments_df = pd.read_csv(comments_path)
                        comments_df['created_utc'] = pd.to_datetime(comments_df['created_utc']).dt.tz_localize('UTC')
                        
                        # Фильтруем по дате
                        mask = (comments_df['created_utc'] >= start_date) & (comments_df['created_utc'] <= end_date)
                        filtered_comments = comments_df[mask]
                        total_comments += len(filtered_comments)
                        
                        # Анализируем каждый комментарий
                        for _, comment in filtered_comments.iterrows():
                            sentiment = self._analyze_text_sentiment(str(comment['body']))
                            score = float(comment['score'])
                            
                            # Для комментариев вес зависит только от рейтинга
                            engagement = score
                            
                            all_data.append({
                                'date': comment['created_utc'],
                                'sentiment': sentiment,
                                'engagement': engagement,
                                'subreddit': subreddit,
                                'type': 'comment',
                                'score': score,
                                'num_comments': 0,
                                'upvote_ratio': 1.0
                            })
                            
                    except Exception as e:
                        logger.error(f"Ошибка при обработке комментариев {subreddit}: {e}")
            
            # Создаем DataFrame из всех данных
            df = pd.DataFrame(all_data)
            
            if not df.empty:
                # Устанавливаем дату как индекс и сортируем
                df.set_index('date', inplace=True)
                df.sort_index(inplace=True)
                
                # Убеждаемся, что индекс в UTC
                if df.index.tz is None:
                    df.index = df.index.tz_localize('UTC')
                elif str(df.index.tz) != 'UTC':
                    df.index = df.index.tz_convert('UTC')
                
                # Группируем по дате и агрегируем
                daily_df = df.resample('D').agg({
                    'sentiment': 'mean',
                    'engagement': 'sum',
                    'score': 'mean',
                    'num_comments': 'sum'
                }).fillna(method='ffill').fillna(method='bfill')
                
                # Логируем статистику
                self._log_reddit_statistics(total_posts, total_comments, df)
                
                # Сохраняем в кэш
                self._save_to_cache(cache_key, daily_df)
                
                return daily_df
            
            return pd.DataFrame()
            
        except Exception as e:
            logger.error(f"Ошибка при анализе данных Reddit: {e}")
            return pd.DataFrame()
    
    def _analyze_text_sentiment(self, text: str) -> float:
        """Анализ настроений текста"""
        try:
            if not text or text == 'nan':
                return 0.0
            
            # Очистка текста
            text = re.sub(r'http\S+|www\S+|https\S+', '', text, flags=re.MULTILINE)
            text = re.sub(r'\@\w+|\#\w+', '', text)
            text = re.sub(r'[^\w\s]', '', text)
            
            # Анализ настроений
            blob = TextBlob(text)
            sentiment = blob.sentiment.polarity
            
            return sentiment
            
        except Exception as e:
            logger.error(f"Ошибка при анализе текста: {e}")
            return 0.0
    
    def _aggregate_sentiment(self, df: pd.DataFrame) -> pd.DataFrame:
        """Агрегация настроений по дням"""
        try:
            # Убеждаемся, что 'date' в формате datetime
            df['date'] = pd.to_datetime(df['date'])
            
            # Группируем по дням
            daily = df.groupby(df['date'].dt.date).agg({
                'sentiment': lambda x: np.average(x, weights=df.loc[x.index, 'engagement']),
                'engagement': 'sum',
                'score': 'mean',
                'num_comments': 'mean'
            }).reset_index()
            
            # Переименовываем колонки
            daily.columns = ['date', 'sentiment', 'engagement', 'avg_score', 'avg_comments']
            
            # Добавляем скользящее среднее
            daily['sentiment_ma'] = daily['sentiment'].rolling(window=3, min_periods=1).mean()
            
            return daily
            
        except Exception as e:
            logger.error(f"Ошибка при агрегации данных: {e}")
            return pd.DataFrame()
    
    def prepare_sentiment_features(self, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """Подготовка всех признаков настроений"""
        try:
            # Получаем настроения с Reddit
            reddit_sentiment = self.get_reddit_sentiment(start_date, end_date)
            
            if reddit_sentiment.empty:
                logger.warning("Не удалось получить данные о настроениях")
                return pd.DataFrame()
            
            # Добавляем дополнительные признаки
            reddit_sentiment['sentiment_std'] = reddit_sentiment['sentiment'].rolling(window=7, min_periods=1).std()
            reddit_sentiment['engagement_ma'] = reddit_sentiment['engagement'].rolling(window=7, min_periods=1).mean()
            
            # Добавляем индекс страха и жадности (пока заглушка)
            reddit_sentiment['fear_greed_index'] = 50  # Нейтральное значение
            
            return reddit_sentiment
            
        except Exception as e:
            logger.error(f"Ошибка при подготовке признаков настроений: {e}")
            return pd.DataFrame()

    def _log_reddit_statistics(self, total_posts, total_comments, df):
        logger.info("\nСтатистика Reddit:")
        logger.info(f"Всего постов: {total_posts}")
        logger.info(f"Всего комментариев: {total_comments}")
        logger.info(f"Среднее настроение: {df['sentiment'].mean():.3f}")
        logger.info(f"Средний рейтинг постов: {df[df['type'] == 'post']['score'].mean():.1f}")
        logger.info(f"Средний рейтинг комментариев: {df[df['type'] == 'comment']['score'].mean():.1f}")

        # Статистика по сабреддитам
        for subreddit in self.subreddits:
            subreddit_data = df[df['subreddit'] == subreddit]
            if not subreddit_data.empty:
                logger.info(f"\nr/{subreddit}:")
                logger.info(f"Постов: {len(subreddit_data[subreddit_data['type'] == 'post'])}")
                logger.info(f"Комментариев: {len(subreddit_data[subreddit_data['type'] == 'comment'])}")
                logger.info(f"Среднее настроение: {subreddit_data['sentiment'].mean():.3f}")

if __name__ == "__main__":
    # Тестирование анализатора настроений
    analyzer = SentimentAnalyzer()
    end_date = datetime.now(tz=timezone.utc)
    start_date = end_date - timedelta(days=30)
    
    sentiment_data = analyzer.prepare_sentiment_features(start_date, end_date)
    if not sentiment_data.empty:
        print("\nРезультаты анализа настроений:")
        print(sentiment_data.head())
