import yfinance as yf
import pandas as pd
import logging
from datetime import datetime
import os
import time
import psycopg2
from psycopg2.extras import execute_batch

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class YahooFinanceCollector:
    def __init__(self):
        """Инициализация коллектора данных Yahoo Finance"""
        self.data_dir = 'data/market_data'
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
            
        # Подключение к базе данных
        self.conn = psycopg2.connect(
            dbname='bitcoin_predictor',
            user='postgres',
            password='postgres',
            host='localhost',
            port='5432'
        )
        self.cur = self.conn.cursor()
            
        # Определяем тикеры и их описания
        self.tickers = {
            'crypto_companies': {
                'MSTR': 'MicroStrategy',
                'COIN': 'Coinbase',
                'MARA': 'Marathon Digital',
                'RIOT': 'Riot Platforms'
            },
            'indices': {
                'SPY': 'S&P 500 ETF',
                'QQQ': 'NASDAQ ETF',
                'GLD': 'Gold ETF',
                'UUP': 'US Dollar Index ETF'
            }
        }

    def __del__(self):
        """Закрытие соединения с базой данных при уничтожении объекта"""
        if hasattr(self, 'cur') and self.cur:
            self.cur.close()
        if hasattr(self, 'conn') and self.conn:
            self.conn.close()

    def save_to_database(self, df, symbol):
        """Сохранение данных в базу данных"""
        try:
            # Подготовка данных для вставки
            data = []
            for idx, row in df.iterrows():
                data.append((
                    idx,  # timestamp
                    symbol,
                    row['open'],
                    row['high'],
                    row['low'],
                    row['close'],
                    row['close'],  # adj_close (используем close, так как для криптовалют они одинаковы)
                    row['volume']
                ))
            
            # SQL для вставки данных
            sql = """
                INSERT INTO yahoo_stock_data 
                (timestamp, symbol, open_price, high_price, low_price, close_price, adj_close, volume)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (timestamp, symbol) DO UPDATE SET
                    open_price = EXCLUDED.open_price,
                    high_price = EXCLUDED.high_price,
                    low_price = EXCLUDED.low_price,
                    close_price = EXCLUDED.close_price,
                    adj_close = EXCLUDED.adj_close,
                    volume = EXCLUDED.volume;
            """
            
            # Пакетная вставка данных
            execute_batch(self.cur, sql, data, page_size=1000)
            self.conn.commit()
            
            logger.info(f"Saved {len(data)} records to database for {symbol}")
            
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Error saving data to database for {symbol}: {str(e)}")

    def get_latest_from_database(self, symbol):
        """Получение последней временной метки из базы данных"""
        try:
            self.cur.execute("""
                SELECT MAX(timestamp)
                FROM yahoo_stock_data
                WHERE symbol = %s;
            """, (symbol,))
            result = self.cur.fetchone()
            return result[0] if result and result[0] else None
        except Exception as e:
            logger.error(f"Error getting latest timestamp for {symbol}: {str(e)}")
            return None

    def update_stock_data(self, symbol):
        """
        Обновление данных для указанного символа
        
        Args:
            symbol: Тикер акции или ETF
        """
        try:
            logger.info(f"Updating data for {symbol}")
            
            # Получаем последнюю дату из базы
            last_date = self.get_latest_from_database(symbol)
            
            # Загружаем данные с Yahoo Finance
            ticker = yf.Ticker(symbol)
            
            if last_date:
                # Если есть данные, загружаем только новые
                start_date = last_date + pd.Timedelta(days=1)
                if start_date >= pd.Timestamp.now():
                    logger.info(f"Data for {symbol} is up to date")
                    return
            else:
                # Если данных нет, загружаем за последние 5 лет
                start_date = pd.Timestamp.now() - pd.Timedelta(days=365*5)
            
            # Загружаем исторические данные
            df = ticker.history(start=start_date)
            
            if df.empty:
                logger.info(f"No new data available for {symbol}")
                return
                
            # Сохраняем в базу данных
            self.save_to_database(df, symbol)
            
            logger.info(f"Successfully updated data for {symbol}")
            
        except Exception as e:
            logger.error(f"Error updating data for {symbol}: {str(e)}")
            raise

    def update_all_data(self):
        """Обновление данных для всех тикеров"""
        try:
            # Обновляем данные для криптовалютных компаний
            for symbol in self.tickers['crypto_companies']:
                self.update_stock_data(symbol)
                time.sleep(1)  # Задержка между запросами
            
            # Обновляем данные для индексов
            for symbol in self.tickers['indices']:
                self.update_stock_data(symbol)
                time.sleep(1)  # Задержка между запросами
                
            logger.info("Successfully updated all stock data")
            
        except Exception as e:
            logger.error(f"Error updating all stock data: {str(e)}")
            raise

    def collect_data(self, symbol, name):
        """Сбор данных для конкретного тикера"""
        try:
            # Получаем последнюю дату из базы данных
            latest_timestamp = self.get_latest_from_database(symbol)
            
            # Получаем данные
            ticker = yf.Ticker(symbol)
            if latest_timestamp:
                # Если есть данные в базе, получаем только новые
                start_date = latest_timestamp + pd.Timedelta(days=1)
                if start_date >= pd.Timestamp.now():
                    logger.info(f"{symbol} ({name}): Already up to date")
                    return None
                hist = ticker.history(start=start_date)
            else:
                # Если данных нет, получаем всю историю
                hist = ticker.history(period="max")
            
            if hist.empty:
                logger.error(f"{symbol} ({name}): No data available")
                return None
                
            # Переименовываем колонки для единообразия
            hist = hist.rename(columns={
                'Open': 'open',
                'High': 'high',
                'Low': 'low',
                'Close': 'close',
                'Volume': 'volume'
            })
            
            # Добавляем дополнительные метрики
            hist['daily_return'] = hist['close'].pct_change()
            hist['volatility'] = hist['daily_return'].rolling(window=30).std()
            
            # Удаляем ненужные колонки
            if 'Dividends' in hist.columns:
                hist = hist.drop(['Dividends', 'Stock Splits'], axis=1)
            
            # Сохраняем в базу данных
            self.save_to_database(hist, symbol)
                
            logger.info(f"{symbol} ({name}): ✅ {len(hist)} records from {hist.index[0].strftime('%Y-%m-%d')} to {hist.index[-1].strftime('%Y-%m-%d')}")
            
            return hist
            
        except Exception as e:
            logger.error(f"{symbol} ({name}): Error - {str(e)}")
            return None

def main():
    collector = YahooFinanceCollector()
    collector.update_all_data()

if __name__ == "__main__":
    main()
