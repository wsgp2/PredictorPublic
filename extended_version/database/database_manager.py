import psycopg2
import pandas as pd
from datetime import datetime
import logging
from typing import Optional, Dict, Any
import os
import sys

# Добавляем родительскую директорию в путь для импортов
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from config.config import DB_CONFIG as db_config

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self):
        """Инициализация менеджера базы данных"""
        self.db_params = db_config
        self.conn = None
        self.cur = None

    def connect(self):
        """Установка соединения с базой данных"""
        try:
            self.conn = psycopg2.connect(**self.db_params)
            self.cur = self.conn.cursor()
            logger.info("Successfully connected to the database")
        except Exception as e:
            logger.error(f"Error connecting to the database: {str(e)}")
            raise

    def disconnect(self):
        """Закрытие соединения с базой данных"""
        if self.cur:
            self.cur.close()
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed")

    def insert_price_data(self, df: pd.DataFrame):
        """Вставка данных о ценах"""
        try:
            required_columns = ['timestamp']
            value_columns = ['value', 'close', 'price', 'market_price']
            
            # Проверяем наличие timestamp
            if 'timestamp' not in df.columns:
                raise ValueError("DataFrame must contain 'timestamp' column")
                
            # Находим колонку со значением цены
            price_column = None
            for col in value_columns:
                if col in df.columns:
                    price_column = col
                    break
                    
            if not price_column:
                raise ValueError(f"DataFrame must contain one of these columns: {value_columns}")
            
            # Подготавливаем данные для вставки
            data = []
            for _, row in df.iterrows():
                data.append((
                    row['timestamp'],
                    float(row[price_column])
                ))
            
            # SQL запрос для вставки
            insert_query = """
                INSERT INTO price_data (timestamp, value)
                VALUES (%s, %s)
                ON CONFLICT (timestamp) DO UPDATE
                SET value = EXCLUDED.value;
            """
            
            self.cur.executemany(insert_query, data)
            self.conn.commit()
            logger.info(f"Successfully inserted {len(data)} price records")
            
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Error inserting price data: {str(e)}")
            raise

    def insert_technical_indicators(self, df: pd.DataFrame):
        """Вставка технических индикаторов"""
        try:
            for _, row in df.iterrows():
                self.cur.execute("""
                    INSERT INTO technical_indicators (
                        timestamp, rsi, macd, macd_signal, macd_hist,
                        bb_upper, bb_middle, bb_lower, ma_20, ma_50, ma_200,
                        volume_sma, obv
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (timestamp) DO UPDATE
                    SET rsi = EXCLUDED.rsi,
                        macd = EXCLUDED.macd,
                        macd_signal = EXCLUDED.macd_signal,
                        macd_hist = EXCLUDED.macd_hist,
                        bb_upper = EXCLUDED.bb_upper,
                        bb_middle = EXCLUDED.bb_middle,
                        bb_lower = EXCLUDED.bb_lower,
                        ma_20 = EXCLUDED.ma_20,
                        ma_50 = EXCLUDED.ma_50,
                        ma_200 = EXCLUDED.ma_200,
                        volume_sma = EXCLUDED.volume_sma,
                        obv = EXCLUDED.obv
                """, (
                    row['timestamp'],
                    row.get('rsi'),
                    row.get('macd'),
                    row.get('macd_signal'),
                    row.get('macd_hist'),
                    row.get('bb_upper'),
                    row.get('bb_middle'),
                    row.get('bb_lower'),
                    row.get('ma_20'),
                    row.get('ma_50'),
                    row.get('ma_200'),
                    row.get('volume_sma'),
                    row.get('obv')
                ))
            self.conn.commit()
            logger.info(f"Successfully inserted {len(df)} technical indicator records")
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Error inserting technical indicators: {str(e)}")
            raise

    def insert_on_chain_metrics(self, df: pd.DataFrame):
        """Вставка метрик блокчейна"""
        try:
            # Проверяем наличие обязательных колонок
            required_columns = ['timestamp']
            if not all(col in df.columns for col in required_columns):
                raise ValueError(f"DataFrame must contain all required columns: {required_columns}")
            
            # Подготавливаем данные для вставки
            columns = [col for col in df.columns if col != 'timestamp']
            
            for _, row in df.iterrows():
                values = [row[col] if pd.notna(row[col]) else None for col in columns]
                placeholders = ', '.join(['%s'] * (len(columns) + 1))
                columns_str = ', '.join(['timestamp'] + columns)
                update_str = ', '.join([f"{col} = EXCLUDED.{col}" for col in columns])
                
                insert_query = f"""
                    INSERT INTO on_chain_metrics (timestamp, {', '.join(columns)})
                    VALUES ({placeholders})
                    ON CONFLICT (timestamp) DO UPDATE
                    SET {update_str};
                """
                
                self.cur.execute(insert_query, [row['timestamp']] + values)
            
            self.conn.commit()
            logger.info(f"Successfully inserted {len(df)} on-chain metric records")
            
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Error inserting on-chain metrics: {str(e)}")
            raise

    def insert_sentiment_metrics(self, df: pd.DataFrame):
        """Вставка метрик настроений"""
        try:
            # Проверяем наличие обязательных колонок
            required_columns = ['timestamp']
            if not all(col in df.columns for col in required_columns):
                raise ValueError(f"DataFrame must contain all required columns: {required_columns}")
            
            # Подготавливаем данные для вставки
            columns = [col for col in df.columns if col != 'timestamp']
            
            for _, row in df.iterrows():
                values = [row[col] if pd.notna(row[col]) else None for col in columns]
                placeholders = ', '.join(['%s'] * (len(columns) + 1))
                columns_str = ', '.join(['timestamp'] + columns)
                update_str = ', '.join([f"{col} = EXCLUDED.{col}" for col in columns])
                
                insert_query = f"""
                    INSERT INTO sentiment_metrics (timestamp, {', '.join(columns)})
                    VALUES ({placeholders})
                    ON CONFLICT (timestamp) DO UPDATE
                    SET {update_str};
                """
                
                self.cur.execute(insert_query, [row['timestamp']] + values)
            
            self.conn.commit()
            logger.info(f"Successfully inserted {len(df)} sentiment metric records")
            
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Error inserting sentiment metrics: {str(e)}")
            raise

    def insert_market_data(self, df: pd.DataFrame):
        """Вставка рыночных данных"""
        try:
            # Проверяем наличие обязательных колонок
            required_columns = ['timestamp']
            if not all(col in df.columns for col in required_columns):
                raise ValueError(f"DataFrame must contain all required columns: {required_columns}")
            
            # Подготавливаем данные для вставки
            columns = [col for col in df.columns if col != 'timestamp']
            
            for _, row in df.iterrows():
                values = [row[col] if pd.notna(row[col]) else None for col in columns]
                placeholders = ', '.join(['%s'] * (len(columns) + 1))
                columns_str = ', '.join(['timestamp'] + columns)
                update_str = ', '.join([f"{col} = EXCLUDED.{col}" for col in columns])
                
                insert_query = f"""
                    INSERT INTO market_data (timestamp, {', '.join(columns)})
                    VALUES ({placeholders})
                    ON CONFLICT (timestamp) DO UPDATE
                    SET {update_str};
                """
                
                self.cur.execute(insert_query, [row['timestamp']] + values)
            
            self.conn.commit()
            logger.info(f"Successfully inserted {len(df)} market data records")
            
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Error inserting market data: {str(e)}")
            raise

    def insert_longshort_data(self, df: pd.DataFrame):
        """Вставка данных о Long/Short позициях"""
        try:
            # SQL запрос для вставки
            insert_query = """
                INSERT INTO longshort_data (
                    timestamp, symbol, timeframe,
                    long_account_ratio, short_account_ratio,
                    long_position_ratio, short_position_ratio,
                    long_person_ratio, short_person_ratio
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (timestamp, symbol, timeframe) DO UPDATE
                SET 
                    long_account_ratio = EXCLUDED.long_account_ratio,
                    short_account_ratio = EXCLUDED.short_account_ratio,
                    long_position_ratio = EXCLUDED.long_position_ratio,
                    short_position_ratio = EXCLUDED.short_position_ratio,
                    long_person_ratio = EXCLUDED.long_person_ratio,
                    short_person_ratio = EXCLUDED.short_person_ratio;
            """
            
            # Подготавливаем данные для вставки
            data = []
            for _, row in df.iterrows():
                data.append((
                    row['timestamp'],
                    row['symbol'],
                    row['timeframe'],
                    float(row['long_account_ratio']) if 'long_account_ratio' in row else None,
                    float(row['short_account_ratio']) if 'short_account_ratio' in row else None,
                    float(row['long_position_ratio']) if 'long_position_ratio' in row else None,
                    float(row['short_position_ratio']) if 'short_position_ratio' in row else None,
                    float(row['long_person_ratio']) if 'long_person_ratio' in row else None,
                    float(row['short_person_ratio']) if 'short_person_ratio' in row else None
                ))
            
            self.cur.executemany(insert_query, data)
            self.conn.commit()
            logger.info(f"Successfully inserted {len(data)} longshort records")
            
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Error inserting longshort data: {str(e)}")
            raise

    def insert_related_assets(self, df: pd.DataFrame):
        """Вставка данных связанных активов"""
        try:
            # SQL запрос для вставки
            insert_query = """
                INSERT INTO related_assets (
                    timestamp, symbol, open, high, low, close, volume
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (timestamp, symbol) DO UPDATE
                SET 
                    open = EXCLUDED.open,
                    high = EXCLUDED.high,
                    low = EXCLUDED.low,
                    close = EXCLUDED.close,
                    volume = EXCLUDED.volume;
            """
            
            # Подготавливаем данные для вставки
            data = []
            for _, row in df.iterrows():
                data.append((
                    row['timestamp'],
                    row['symbol'],
                    float(row['open']),
                    float(row['high']),
                    float(row['low']),
                    float(row['close']),
                    float(row['volume'])
                ))
            
            self.cur.executemany(insert_query, data)
            self.conn.commit()
            logger.info(f"Successfully inserted {len(data)} related asset records")
            
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Error inserting related asset data: {str(e)}")
            raise

    def insert_news_data(self, df: pd.DataFrame):
        """Вставка новостных данных"""
        try:
            # SQL запрос для вставки
            insert_query = """
                INSERT INTO news_data (
                    timestamp, source, title, url, sentiment
                )
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (timestamp, url) DO UPDATE
                SET 
                    source = EXCLUDED.source,
                    title = EXCLUDED.title,
                    sentiment = EXCLUDED.sentiment;
            """
            
            # Подготавливаем данные для вставки
            data = []
            for _, row in df.iterrows():
                data.append((
                    row['timestamp'],
                    row['source'],
                    row['title'],
                    row['url'],
                    float(row['sentiment']) if 'sentiment' in row else None
                ))
            
            self.cur.executemany(insert_query, data)
            self.conn.commit()
            logger.info(f"Successfully inserted {len(data)} news records")
            
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Error inserting news data: {str(e)}")
            raise

    def get_correlations(self, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """Получение корреляций за указанный период"""
        try:
            self.cur.execute("""
                SELECT * FROM get_correlations(%s, %s)
            """, (start_date, end_date))
            results = self.cur.fetchall()
            return pd.DataFrame(results, columns=['metric', 'correlation'])
        except Exception as e:
            logger.error(f"Error getting correlations: {str(e)}")
            raise

    def get_latest_timestamp(self, table_name: str) -> Optional[datetime]:
        """Получение последней временной метки из указанной таблицы"""
        try:
            self.cur.execute(f"""
                SELECT MAX(timestamp)
                FROM {table_name}
            """)
            return self.cur.fetchone()[0]
        except Exception as e:
            logger.error(f"Error getting latest timestamp from {table_name}: {str(e)}")
            return None

    def execute_query(self, query: str, params: Optional[tuple] = None) -> pd.DataFrame:
        """Выполнение произвольного SQL запроса"""
        try:
            if params:
                self.cur.execute(query, params)
            else:
                self.cur.execute(query)
            
            columns = [desc[0] for desc in self.cur.description]
            results = self.cur.fetchall()
            return pd.DataFrame(results, columns=columns)
        except Exception as e:
            logger.error(f"Error executing query: {str(e)}")
            raise

    def __enter__(self):
        """Контекстный менеджер для автоматического подключения"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Контекстный менеджер для автоматического отключения"""
        self.disconnect()
