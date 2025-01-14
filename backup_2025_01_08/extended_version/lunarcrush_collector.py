import requests
import pandas as pd
import logging
from datetime import datetime, timedelta
import os
import time
from typing import Optional, Dict, Any

# Настройка API ключа
LUNARCRUSH_API_KEY = 'czj05lqp91si9h16b975gtgbe2m5nblt367frwltf'

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
        self.data_dir = 'data/lunarcrush_new'  # Обновленный путь сохранения данных
        self.request_delay = 1.1  # задержка между запросами в секундах
        
        # Создаем директории для данных
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
            
        # Определяем файлы для каждого типа метрик
        self.metric_files = {
            'social': os.path.join(self.data_dir, 'social_metrics.csv'),
            'market': os.path.join(self.data_dir, 'market_metrics.csv'),
            'news': os.path.join(self.data_dir, 'news.csv'),
            'influencers': os.path.join(self.data_dir, 'influencers.csv')
        }
        
        # Начальная дата для исторических данных (1 января 2019)
        self.historical_start = datetime(2019, 1, 1)

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

    def load_historical_data(self, filename: str) -> Optional[pd.DataFrame]:
        """
        Загрузка исторических данных из CSV файла
        
        Args:
            filename (str): Путь к файлу
            
        Returns:
            Optional[pd.DataFrame]: DataFrame с данными или None
        """
        try:
            if os.path.exists(filename):
                df = pd.read_csv(filename)
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                return df
            return None
        except Exception as e:
            logger.error(f"Error loading data from {filename}: {str(e)}")
            return None

    def save_data(self, df: pd.DataFrame, filename: str) -> None:
        """
        Сохранение DataFrame в CSV файл
        
        Args:
            df (pd.DataFrame): DataFrame для сохранения
            filename (str): Путь к файлу
        """
        try:
            df.to_csv(filename, index=False)
            logger.info(f"Data saved to {filename}")
        except Exception as e:
            logger.error(f"Error saving data to {filename}: {str(e)}")

    def get_latest_timestamp(self, df: Optional[pd.DataFrame]) -> Optional[datetime]:
        """
        Получение последней временной метки из DataFrame
        
        Args:
            df (Optional[pd.DataFrame]): DataFrame с данными
            
        Returns:
            Optional[datetime]: Последняя временная метка или None
        """
        if df is not None and not df.empty:
            return df['timestamp'].max()
        return None

    def merge_and_save_data(self, historical_df: Optional[pd.DataFrame], 
                           new_df: pd.DataFrame, filename: str) -> Optional[pd.DataFrame]:
        """
        Объединение исторических и новых данных
        
        Args:
            historical_df (Optional[pd.DataFrame]): Исторические данные
            new_df (pd.DataFrame): Новые данные
            filename (str): Путь к файлу для сохранения
            
        Returns:
            Optional[pd.DataFrame]: Объединенный DataFrame
        """
        try:
            if historical_df is None:
                merged_df = new_df
            else:
                merged_df = pd.concat([historical_df, new_df])
                merged_df = merged_df.drop_duplicates(subset=['timestamp'])
                merged_df = merged_df.sort_values('timestamp')
            
            self.save_data(merged_df, filename)
            return merged_df
        except Exception as e:
            logger.error(f"Error merging data: {str(e)}")
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

    def get_historical_data(self, symbol: str = 'BTC') -> None:
        """
        Получение полных исторических данных
        
        Args:
            symbol (str): Символ криптовалюты
        """
        try:
            end_time = datetime.now()
            
            # Если нет исторических данных, начинаем с 2019 года
            social_df = self.load_historical_data(self.metric_files['social'])
            market_df = self.load_historical_data(self.metric_files['market'])
            
            start_time = self.historical_start
            if social_df is not None:
                social_start = social_df['timestamp'].min()
                if social_start > self.historical_start:
                    start_time = self.historical_start
                else:
                    start_time = social_df['timestamp'].max()
            
            logger.info(f"Collecting historical data from {start_time} to {end_time}")
            
            # Собираем данные по годам для избежания ограничений API
            current_start = start_time
            while current_start < end_time:
                try:
                    current_end = min(current_start + timedelta(days=365), end_time)
                    logger.info(f"Processing period: {current_start} to {current_end}")
                    
                    # Социальные метрики
                    params = {
                        'interval': '1d',
                        'bucket': 'day',
                        'start': int(current_start.timestamp()),
                        'end': int(current_end.timestamp())
                    }
                    
                    logger.info(f"Requesting data with params: {params}")
                    
                    # Получаем данные
                    response = self.api_request(f'coins/{symbol}/time-series/v2', params)
                    if response:
                        logger.info(f"Got response keys: {response.keys()}")
                        
                    if response and 'data' in response:
                        logger.info("Processing social metrics...")
                        df = pd.DataFrame(response['data'])
                        df['timestamp'] = pd.to_datetime(df['time'], unit='s')
                        
                        # Расширенный список социальных метрик
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
                        
                        if len(available_columns) > 1:  # Если есть хотя бы одна метрика кроме timestamp
                            social_df = df[available_columns]
                            self.merge_and_save_data(
                                self.load_historical_data(self.metric_files['social']),
                                social_df,
                                self.metric_files['social']
                            )
                            logger.info(f"Social metrics collected for {current_start} - {current_end}")
                        else:
                            logger.warning("No social metrics found in response")
                    
                        # Получаем рыночные метрики из того же ответа
                        logger.info("Processing market metrics...")
                        market_columns = [
                            'timestamp', 'close', 'volume_24h', 'market_cap',
                            'market_dominance', 'volatility', 'high', 'low', 'open'
                        ]
                        
                        available_columns = ['timestamp']
                        for col in market_columns[1:]:
                            if col in df.columns:
                                available_columns.append(col)
                        
                        if len(available_columns) > 1:  # Если есть хотя бы одна метрика кроме timestamp
                            market_df = df[available_columns]
                            self.merge_and_save_data(
                                self.load_historical_data(self.metric_files['market']),
                                market_df,
                                self.metric_files['market']
                            )
                            logger.info(f"Market metrics collected for {current_start} - {current_end}")
                        else:
                            logger.warning("No market metrics found in response")
                    else:
                        logger.error("No data in response")
                    
                    current_start = current_end + timedelta(days=1)
                    time.sleep(self.request_delay)  # Задержка между запросами
                
                except Exception as e:
                    logger.error(f"Error processing period {current_start} - {current_end}: {str(e)}")
                    # Продолжаем со следующего периода
                    current_start = current_end + timedelta(days=1)
                    time.sleep(self.request_delay * 2)  # Увеличенная задержка после ошибки
        
        except Exception as e:
            logger.error(f"Error in get_historical_data: {str(e)}")
            raise

    def update_all_metrics(self, symbol: str = 'BTC') -> None:
        """
        Обновление всех метрик
        
        Args:
            symbol (str): Символ криптовалюты
        """
        # Сначала проверяем и собираем исторические данные
        self.get_historical_data(symbol)
        
        # Затем собираем текущие новости
        new_df = self.get_news_metrics(symbol)
        if new_df is not None:
            historical_df = self.load_historical_data(self.metric_files['news'])
            self.merge_and_save_data(historical_df, new_df, self.metric_files['news'])
            logger.info(f"News metrics updated, {len(new_df)} new records")

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
