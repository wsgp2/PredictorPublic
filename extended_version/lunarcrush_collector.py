import requests
import pandas as pd
import logging
from datetime import datetime, timedelta
import os
import time
from typing import Optional, Dict, Any
import psycopg2
from psycopg2.extras import execute_values

# Настройка API ключа
LUNARCRUSH_API_KEY = 'czj05lqp91si9h16b975gtgbe2m5nblt367frwltf'

# Настройка подключения к базе данных
DB_NAME = "bitcoin_predictor"
DB_USER = "postgres"
DB_PASSWORD = "postgres"
DB_HOST = "localhost"
DB_PORT = "5432"

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class LunarCrushCollector:
    def __init__(self):
        """
        Инициализация коллектора данных LunarCrush
        """
        self.api_key = LUNARCRUSH_API_KEY
        self.base_url = "https://lunarcrush.com/api4/public"
        self.request_delay = 1.1  # задержка между запросами в секундах
        
        # Подключение к базе данных
        self.conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        
        # Начальная дата для исторических данных (1 января 2019)
        self.historical_start = datetime(2019, 1, 1)

    def __del__(self):
        """
        Закрытие соединения с базой данных
        """
        if hasattr(self, 'conn'):
            self.conn.close()

    def api_request(self, endpoint: str, params: Dict[str, Any] = None) -> Optional[Dict]:
        """
        Выполнение запроса к API с обработкой ошибок и задержкой
        
        Args:
            endpoint (str): Конечная точка API
            params (Dict[str, Any], optional): Параметры запроса
            
        Returns:
            Optional[Dict]: Ответ API или None в случае ошибки
        """
        try:
            url = f"{self.base_url}/{endpoint}"
            headers = {'Authorization': f'Bearer {self.api_key}'}
            
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            
            # Задержка перед следующим запросом
            time.sleep(self.request_delay)
            
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"API request error for {endpoint}: {str(e)}")
            if hasattr(e.response, 'text'):
                logger.error(f"Response text: {e.response.text}")
            return None

    def save_to_db(self, df: pd.DataFrame, table: str, columns: list) -> None:
        """
        Сохранение DataFrame в базу данных
        
        Args:
            df (pd.DataFrame): DataFrame для сохранения
            table (str): Имя таблицы
            columns (list): Список колонок
        """
        try:
            # Подготовка данных
            tuples = [tuple(x) for x in df[columns].to_numpy()]
            
            # Создание SQL запроса
            cols = ','.join(columns)
            vals = ','.join(['%s'] * len(columns))
            
            # Вставка данных
            with self.conn.cursor() as cur:
                execute_values(cur, 
                    f"INSERT INTO {table} ({cols}) VALUES %s ON CONFLICT DO NOTHING",
                    tuples
                )
            self.conn.commit()
            logger.info(f"Saved {len(df)} records to {table}")
        except Exception as e:
            logger.error(f"Error saving to database: {str(e)}")
            self.conn.rollback()

    def get_latest_timestamp(self, table: str) -> Optional[datetime]:
        """
        Получение последней временной метки из таблицы
        
        Args:
            table (str): Имя таблицы
            
        Returns:
            Optional[datetime]: Последняя временная метка или None
        """
        try:
            with self.conn.cursor() as cur:
                cur.execute(f"SELECT MAX(timestamp) FROM {table}")
                result = cur.fetchone()
                return result[0] if result and result[0] else None
        except Exception as e:
            logger.error(f"Error getting latest timestamp: {str(e)}")
            return None

    def get_social_metrics(self, symbol: str = 'BTC', 
                          start_time: Optional[datetime] = None) -> Optional[pd.DataFrame]:
        """
        Получение социальных метрик
        
        Args:
            symbol (str): Символ криптовалюты
            start_time (Optional[datetime]): Начальная временная метка
            
        Returns:
            Optional[pd.DataFrame]: DataFrame с социальными метриками
        """
        try:
            params = {
                'interval': '1d',  # дневные данные
                'bucket': 'day'
            }
            
            if start_time:
                # Если указано начальное время, указываем и конечное (текущее)
                params['start'] = int(start_time.timestamp())
                params['end'] = int(datetime.now().timestamp())
            
            response = self.api_request(f'coins/{symbol}/time-series/v2', params)
            if response and 'data' in response:
                df = pd.DataFrame(response['data'])
                df['timestamp'] = pd.to_datetime(df['time'], unit='s')
                
                # Выбираем нужные колонки
                columns = [
                    'timestamp', 'social_dominance', 'contributors_active',
                    'posts_active', 'interactions', 'galaxy_score', 'sentiment'
                ]
                available_columns = ['timestamp']
                for col in columns[1:]:
                    if col in df.columns:
                        available_columns.append(col)
                return df[available_columns]
            
            return None
        except Exception as e:
            logger.error(f"Error getting social metrics: {str(e)}")
            return None

    def get_market_metrics(self, symbol: str = 'BTC',
                          start_time: Optional[datetime] = None) -> Optional[pd.DataFrame]:
        """
        Получение рыночных метрик
        
        Args:
            symbol (str): Символ криптовалюты
            start_time (Optional[datetime]): Начальная временная метка
            
        Returns:
            Optional[pd.DataFrame]: DataFrame с рыночными метриками
        """
        try:
            params = {
                'interval': '1d',
                'bucket': 'day'
            }
            
            if start_time:
                # Если указано начальное время, указываем и конечное (текущее)
                params['start'] = int(start_time.timestamp())
                params['end'] = int(datetime.now().timestamp())
            
            response = self.api_request(f'coins/{symbol}/time-series/v2', params)
            if response and 'data' in response:
                df = pd.DataFrame(response['data'])
                df['timestamp'] = pd.to_datetime(df['time'], unit='s')
                
                # Выбираем только доступные колонки
                available_columns = ['timestamp']
                for col in ['close', 'volume_24h', 'market_cap', 'market_dominance', 'volatility']:
                    if col in df.columns:
                        available_columns.append(col)
                
                return df[available_columns]
            
            return None
        except Exception as e:
            logger.error(f"Error getting market metrics: {str(e)}")
            return None

    def get_news_metrics(self, symbol: str = 'BTC') -> Optional[pd.DataFrame]:
        """
        Получение новостных метрик
        
        Args:
            symbol (str): Символ криптовалюты
            
        Returns:
            Optional[pd.DataFrame]: DataFrame с новостями
        """
        try:
            # Используем /posts/v1 для категории cryptocurrencies
            response = self.api_request('category/cryptocurrencies/posts/v1')
            
            if response and 'data' in response:
                df = pd.DataFrame(response['data'])
                # Фильтруем только посты, связанные с Bitcoin
                df = df[df['post_title'].str.contains('Bitcoin|BTC', case=False, na=False)]
                
                if 'post_created' in df.columns:
                    df['timestamp'] = pd.to_datetime(df['post_created'], unit='s')
                elif 'time' in df.columns:
                    df['timestamp'] = pd.to_datetime(df['time'], unit='s')
                
                # Выбираем доступные колонки и переименовываем их
                available_columns = ['timestamp']
                column_mapping = {
                    'post_title': 'title',
                    'post_link': 'url',
                    'creator_name': 'source',
                    'post_sentiment': 'sentiment'
                }
                
                for old_col, new_col in column_mapping.items():
                    if old_col in df.columns:
                        df[new_col] = df[old_col]
                        available_columns.append(new_col)
                
                return df[available_columns]
            
            return None
        except Exception as e:
            logger.error(f"Error getting news metrics: {str(e)}")
            return None

    def get_influencers(self, symbol: str = 'BTC') -> Optional[pd.DataFrame]:
        """
        Получение данных о влиятельных лицах
        
        Args:
            symbol (str): Символ криптовалюты
            
        Returns:
            Optional[pd.DataFrame]: DataFrame с данными о влиятельных лицах
        """
        try:
            # Используем новый endpoint для influencers
            response = self.api_request('influencers/v2', {
                'symbol': symbol,
                'limit': 100  # Получаем топ-100 инфлюенсеров
            })
            
            if response and 'data' in response:
                df = pd.DataFrame(response['data'])
                
                # Выбираем и переименовываем нужные колонки
                df['timestamp'] = pd.to_datetime('now')
                columns = {
                    'twitter_screen_name': 'username',
                    'twitter_followers': 'followers',
                    'twitter_following': 'following',
                    'average_sentiment': 'sentiment',
                    'influence_score': 'influence',
                    'engagement_rate': 'engagement'
                }
                
                available_columns = ['timestamp']
                for old_col, new_col in columns.items():
                    if old_col in df.columns:
                        df[new_col] = df[old_col]
                        available_columns.append(new_col)
                
                return df[available_columns]
            
            return None
        except Exception as e:
            logger.error(f"Error getting influencers: {str(e)}")
            return None

    def update_all_metrics(self, symbol: str = 'BTC') -> None:
        """
        Обновление всех метрик
        
        Args:
            symbol (str): Символ криптовалюты
        """
        # Получаем исторические данные
        self.get_historical_data(symbol)
        
        # Получаем новости
        news_df = self.get_news_metrics(symbol)
        if news_df is not None:
            self.save_to_db(
                news_df,
                'lunarcrush_news',
                ['timestamp', 'title', 'url', 'source', 'sentiment']
            )
        
        # Получаем данные о влиятельных лицах
        influencers_df = self.get_influencers(symbol)
        if influencers_df is not None:
            self.save_to_db(
                influencers_df,
                'lunarcrush_influencers',
                ['timestamp', 'username', 'followers', 'following', 'sentiment', 'influence', 'engagement']
            )

    def get_historical_data(self, symbol: str = 'BTC') -> None:
        """
        Получение полных исторических данных
        
        Args:
            symbol (str): Символ криптовалюты
        """
        try:
            end_time = datetime.now()
            
            # Получаем последние временные метки
            social_start = self.get_latest_timestamp('lunarcrush_social') or self.historical_start
            market_start = self.get_latest_timestamp('lunarcrush_market') or self.historical_start
            
            start_time = min(social_start, market_start)
            logger.info(f"Collecting historical data from {start_time} to {end_time}")
            
            # Собираем данные по годам для избежания ограничений API
            current_start = start_time
            while current_start < end_time:
                try:
                    current_end = min(current_start + timedelta(days=365), end_time)
                    logger.info(f"Processing period: {current_start} to {current_end}")
                    
                    params = {
                        'interval': '1d',
                        'bucket': 'day',
                        'start': int(current_start.timestamp()),
                        'end': int(current_end.timestamp())
                    }
                    
                    response = self.api_request(f'coins/{symbol}/time-series/v2', params)
                    
                    if response and 'data' in response:
                        df = pd.DataFrame(response['data'])
                        df['timestamp'] = pd.to_datetime(df['time'], unit='s')
                        
                        # Обработка социальных метрик
                        social_columns = [
                            'timestamp', 'social_dominance', 'contributors_active',
                            'posts_active', 'interactions', 'galaxy_score', 'sentiment',
                            'social_score', 'average_sentiment', 'social_impact_score',
                            'correlation_rank', 'social_volume', 'alt_rank'
                        ]
                        
                        available_columns = ['timestamp']
                        for col in social_columns[1:]:
                            if col in df.columns:
                                available_columns.append(col)
                        
                        if len(available_columns) > 1:
                            social_df = df[available_columns]
                            self.save_to_db(social_df, 'lunarcrush_social', available_columns)
                            logger.info(f"Social metrics collected for {current_start} - {current_end}")
                        
                        # Обработка рыночных метрик
                        market_columns = [
                            'timestamp', 'close', 'volume_24h', 'market_cap',
                            'market_dominance', 'volatility', 'high', 'low', 'open'
                        ]
                        
                        available_columns = ['timestamp']
                        for col in market_columns[1:]:
                            if col in df.columns:
                                available_columns.append(col)
                        
                        if len(available_columns) > 1:
                            market_df = df[available_columns]
                            self.save_to_db(market_df, 'lunarcrush_market', available_columns)
                            logger.info(f"Market metrics collected for {current_start} - {current_end}")
                    
                    current_start = current_end + timedelta(days=1)
                    time.sleep(self.request_delay)
                
                except Exception as e:
                    logger.error(f"Error processing period {current_start} - {current_end}: {str(e)}")
                    current_start = current_end + timedelta(days=1)
                    time.sleep(self.request_delay * 2)
        
        except Exception as e:
            logger.error(f"Error in get_historical_data: {str(e)}")

def main():
    """
    Основная функция для запуска коллектора
    """
    try:
        collector = LunarCrushCollector()
        collector.update_all_metrics()
    except Exception as e:
        logger.error(f"Error in main: {str(e)}")

if __name__ == "__main__":
    main()
