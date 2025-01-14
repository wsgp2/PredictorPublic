import logging
from database.database_manager import DatabaseManager
import pandas as pd
from datetime import datetime, timedelta

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DB:
    def __init__(self):
        """Инициализация класса для работы с базой данных"""
        from database_manager import DatabaseManager
        self.db = DatabaseManager()
        logger.info("Successfully connected to the database")
        self.db.connect()
        logger.info("Database connection established")

    def __del__(self):
        """Закрытие соединения при удалении объекта"""
        if hasattr(self, 'db'):
            self.db.disconnect()
            logger.info("Database connection closed")

    def insert_price_data(self, df):
        """Вставка данных о ценах"""
        try:
            self.db.insert_price_data(df)
        except Exception as e:
            logger.error(f"Error inserting price data: {str(e)}")
            raise

    def insert_market_data(self, df):
        """Вставка рыночных данных"""
        try:
            self.db.insert_market_data(df)
        except Exception as e:
            logger.error(f"Error inserting market data: {str(e)}")
            raise

    def insert_longshort_data(self, df):
        """Вставка данных о Long/Short позициях"""
        try:
            self.db.insert_longshort_data(df)
        except Exception as e:
            logger.error(f"Error inserting long/short data: {str(e)}")
            raise

    def insert_technical_indicators(self, df):
        """Вставка технических индикаторов"""
        try:
            self.db.insert_technical_indicators(df)
        except Exception as e:
            logger.error(f"Error inserting technical indicators: {str(e)}")
            raise

    def insert_on_chain_metrics(self, df):
        """Вставка метрик блокчейна"""
        try:
            self.db.insert_on_chain_metrics(df)
        except Exception as e:
            logger.error(f"Error inserting on-chain metrics: {str(e)}")
            raise

    def insert_sentiment_metrics(self, df):
        """Вставка метрик настроений"""
        try:
            self.db.insert_sentiment_metrics(df)
        except Exception as e:
            logger.error(f"Error inserting sentiment metrics: {str(e)}")
            raise

    def insert_related_assets(self, df):
        """Вставка данных связанных активов"""
        try:
            self.db.insert_related_assets(df)
        except Exception as e:
            logger.error(f"Error inserting related assets: {str(e)}")
            raise

    def insert_news_data(self, df):
        """Вставка новостных данных"""
        try:
            self.db.insert_news_data(df)
        except Exception as e:
            logger.error(f"Error inserting news data: {str(e)}")
            raise

    def insert_trends_data(self, df: pd.DataFrame) -> None:
        """
        Вставка данных Google Trends в базу данных
        
        Args:
            df: DataFrame с данными трендов
        """
        try:
            # Создаем таблицу если её нет
            self.db.cursor.execute("""
                CREATE TABLE IF NOT EXISTS google_trends (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME NOT NULL,
                    source TEXT NOT NULL,
                    category TEXT NOT NULL,
                    keyword TEXT NOT NULL,
                    value FLOAT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(timestamp, category, keyword)
                )
            """)
            
            # Вставляем данные
            df.to_sql('google_trends', self.db.conn, if_exists='append', index=False)
            self.db.conn.commit()
            
        except Exception as e:
            self.db.conn.rollback()
            raise Exception(f"Error inserting trends data: {str(e)}")

    def get_latest_trends_dates(self) -> dict:
        """
        Получение последних дат для каждой категории Google Trends
        
        Returns:
            Словарь с последними датами по категориям
        """
        try:
            query = """
                SELECT category, MAX(timestamp) as last_date
                FROM google_trends
                GROUP BY category
            """
            
            df = pd.read_sql_query(query, self.db.conn)
            return dict(zip(df['category'], pd.to_datetime(df['last_date'])))
            
        except Exception as e:
            raise Exception(f"Error getting latest trends dates: {str(e)}")

    def get_trends_data(self, category: str = None, start_date: datetime = None, 
                       end_date: datetime = None) -> pd.DataFrame:
        """
        Получение данных Google Trends из базы данных
        
        Args:
            category: Категория данных (опционально)
            start_date: Начальная дата (опционально)
            end_date: Конечная дата (опционально)
            
        Returns:
            DataFrame с данными трендов
        """
        try:
            query = "SELECT * FROM google_trends WHERE 1=1"
            params = []
            
            if category:
                query += " AND category = ?"
                params.append(category)
                
            if start_date:
                query += " AND timestamp >= ?"
                params.append(start_date)
                
            if end_date:
                query += " AND timestamp <= ?"
                params.append(end_date)
                
            df = pd.read_sql_query(query, self.db.conn, params=params)
            return df
            
        except Exception as e:
            raise Exception(f"Error getting trends data: {str(e)}")

    def get_correlations(self, start_date, end_date):
        """Получение корреляций за указанный период"""
        try:
            return self.db.get_correlations(start_date, end_date)
        except Exception as e:
            logger.error(f"Error getting correlations: {str(e)}")
            raise

    def get_latest_timestamp(self, table_name):
        """Получение последней временной метки из указанной таблицы"""
        try:
            return self.db.get_latest_timestamp(table_name)
        except Exception as e:
            logger.error(f"Error getting latest timestamp: {str(e)}")
            return None

    def execute_query(self, query, params=None):
        """
        Выполняет SQL запрос с параметрами.
        
        Args:
            query (str): SQL запрос
            params (tuple): Параметры запроса
            
        Returns:
            list: Результат запроса
        """
        try:
            self.db.cursor.execute(query, params)
            self.db.conn.commit()  # Добавляем commit после каждого запроса
            
            if query.strip().upper().startswith('SELECT'):
                return self.db.cursor.fetchall()
            return []
            
        except Exception as e:
            self.db.conn.rollback()  # Откатываем транзакцию в случае ошибки
            logger.error(f"Error executing query: {str(e)}")
            raise Exception(f"Error executing query: {str(e)}")

    def get_metric_data(self, metric: str, source: str) -> pd.DataFrame:
        """
        Получение данных метрики из базы данных
        
        Args:
            metric: Название метрики
            source: Источник данных (blockchain, sentiment, lunarcrush и т.д.)
            
        Returns:
            DataFrame с данными метрики
        """
        try:
            # Определяем таблицу на основе источника
            table_mapping = {
                'blockchain': 'blockchain_network_data',
                'sentiment': 'fear_and_greed_index',
                'lunarcrush': 'lunarcrush_social_data',
                'coinark': 'coinark_historical',
                'yahoo': 'yahoo_stock_data',
                'google_trends': 'google_trends'
            }
            
            table_name = table_mapping.get(source)
            if not table_name:
                logger.error(f"Unknown source: {source}")
                return None
                
            # Формируем SQL запрос в зависимости от таблицы
            if source == 'blockchain':
                query = f"""
                    SELECT timestamp, value 
                    FROM {table_name}
                    WHERE metric_name = %s
                    ORDER BY timestamp
                """
            elif source == 'yahoo':
                query = f"""
                    SELECT timestamp, close_price as value
                    FROM {table_name}
                    WHERE symbol = %s
                    ORDER BY timestamp
                """
            elif source == 'sentiment':
                query = f"""
                    SELECT timestamp, value
                    FROM {table_name}
                    WHERE type = %s
                    ORDER BY timestamp
                """
            elif source == 'lunarcrush':
                query = f"""
                    SELECT timestamp, value
                    FROM {table_name}
                    WHERE metric = %s
                    ORDER BY timestamp
                """
            elif source == 'coinark':
                query = f"""
                    SELECT timestamp, value
                    FROM {table_name}
                    WHERE metric = %s
                    ORDER BY timestamp
                """
            else:
                query = f"""
                    SELECT timestamp, value
                    FROM {table_name}
                    WHERE keyword = %s
                    ORDER BY timestamp
                """
            
            df = pd.read_sql_query(query, self.db.conn, params=(metric,))
            if not df.empty:
                df.columns = ['timestamp', metric]
            return df
            
        except Exception as e:
            logger.error(f"Error getting metric data: {str(e)}")
            return None

    def save_correlations(self, correlations: pd.DataFrame) -> None:
        """
        Сохранение корреляций в базу данных
        
        Args:
            correlations: DataFrame с корреляциями
        """
        try:
            # Создаем таблицу если её нет
            self.db.cursor.execute("""
                CREATE TABLE IF NOT EXISTS correlations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    metric1 TEXT NOT NULL,
                    metric2 TEXT NOT NULL,
                    correlation FLOAT NOT NULL,
                    UNIQUE(timestamp, metric1, metric2)
                )
            """)
            
            # Преобразуем матрицу корреляций в длинный формат
            correlations_long = correlations.unstack().reset_index()
            correlations_long.columns = ['metric1', 'metric2', 'correlation']
            correlations_long = correlations_long[correlations_long['metric1'] != correlations_long['metric2']]
            
            # Добавляем текущую дату
            correlations_long['timestamp'] = datetime.now()
            
            # Сохраняем в базу
            correlations_long.to_sql('correlations', self.db.conn, if_exists='append', index=False)
            self.db.conn.commit()
            
        except Exception as e:
            self.db.conn.rollback()
            logger.error(f"Error saving correlations: {str(e)}")
            raise

    def get_last_timestamp(self, table_name: str, symbol: str = None, exchange: str = None) -> datetime:
        """
        Получает последнюю временную метку из таблицы для указанного символа и биржи
        
        Args:
            table_name: Название таблицы
            symbol: Торговый символ (опционально)
            exchange: Биржа (опционально)
            
        Returns:
            datetime: Последняя временная метка или None
        """
        try:
            query = f"SELECT MAX(timestamp) FROM {table_name}"
            params = []
            
            if symbol or exchange:
                conditions = []
                if symbol:
                    conditions.append("symbol = %s")
                    params.append(symbol)
                if exchange:
                    conditions.append("exchange = %s")
                    params.append(exchange)
                if conditions:
                    query += " WHERE " + " AND ".join(conditions)
            
            result = self.execute_query(query, params)
            return result[0][0] if result and result[0][0] else None
            
        except Exception as e:
            logger.error(f"Error getting last timestamp: {str(e)}")
            return None

    def get_missing_intervals(self, table_name: str, start_time: datetime, end_time: datetime, 
                            interval: timedelta, symbol: str = None, exchange: str = None) -> list:
        """
        Находит пропущенные интервалы данных в таблице
        
        Args:
            table_name: Название таблицы
            start_time: Начальное время
            end_time: Конечное время
            interval: Интервал между записями
            symbol: Торговый символ (опционально)
            exchange: Биржа (опционально)
            
        Returns:
            list: Список кортежей (start, end) с пропущенными интервалами
        """
        try:
            query = f"SELECT timestamp FROM {table_name}"
            params = []
            
            if symbol or exchange:
                conditions = []
                if symbol:
                    conditions.append("symbol = %s")
                    params.append(symbol)
                if exchange:
                    conditions.append("exchange = %s")
                    params.append(exchange)
                if conditions:
                    query += " WHERE " + " AND ".join(conditions)
            
            query += " ORDER BY timestamp"
            
            result = self.execute_query(query, params)
            if not result:
                return [(start_time, end_time)]
                
            timestamps = [row[0] for row in result]
            missing_intervals = []
            
            # Проверяем первый интервал
            if timestamps[0] - start_time > interval:
                missing_intervals.append((start_time, timestamps[0]))
            
            # Проверяем промежуточные интервалы
            for i in range(len(timestamps) - 1):
                if timestamps[i + 1] - timestamps[i] > interval:
                    missing_intervals.append((timestamps[i], timestamps[i + 1]))
            
            # Проверяем последний интервал
            if end_time - timestamps[-1] > interval:
                missing_intervals.append((timestamps[-1], end_time))
            
            return missing_intervals
            
        except Exception as e:
            logger.error(f"Error getting missing intervals: {str(e)}")
            return [(start_time, end_time)]
