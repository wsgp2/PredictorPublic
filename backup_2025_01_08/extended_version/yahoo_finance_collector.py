import yfinance as yf
import pandas as pd
import logging
from datetime import datetime
import os
import time

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

    def save_data(self, df, filename):
        """Сохранение DataFrame в CSV файл"""
        try:
            full_path = os.path.join(self.data_dir, filename)
            df.to_csv(full_path)
            logger.info(f"Data saved to {full_path}")
        except Exception as e:
            logger.error(f"Error saving data to {filename}: {str(e)}")

    def load_historical_data(self, filename):
        """Загрузка исторических данных из CSV файла"""
        try:
            full_path = os.path.join(self.data_dir, filename)
            if os.path.exists(full_path):
                df = pd.read_csv(full_path, index_col=0, parse_dates=True)
                return df
            return None
        except Exception as e:
            logger.error(f"Error loading historical data from {filename}: {str(e)}")
            return None

    def get_latest_timestamp(self, df):
        """Получение последней временной метки из DataFrame"""
        if df is not None and not df.empty:
            return df.index.max()
        return None

    def collect_data(self, symbol, name):
        """Сбор данных для конкретного тикера"""
        try:
            # Получаем данные
            ticker = yf.Ticker(symbol)
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
                
            logger.info(f"{symbol} ({name}): ✅ {len(hist)} records from {hist.index[0].strftime('%Y-%m-%d')} to {hist.index[-1].strftime('%Y-%m-%d')}")
            
            return hist
            
        except Exception as e:
            logger.error(f"{symbol} ({name}): Error - {str(e)}")
            return None

    def update_all_data(self):
        """Обновление данных для всех тикеров"""
        for category, symbols in self.tickers.items():
            logger.info(f"\nCollecting {category} data:")
            
            for symbol, name in symbols.items():
                # Загружаем существующие данные
                filename = f"{symbol.lower()}_historical.csv"
                existing_data = self.load_historical_data(filename)
                
                # Получаем новые данные
                new_data = self.collect_data(symbol, name)
                
                if new_data is not None:
                    # Если есть существующие данные, обновляем только новые записи
                    if existing_data is not None:
                        latest_timestamp = self.get_latest_timestamp(existing_data)
                        if latest_timestamp:
                            new_data = new_data[new_data.index > latest_timestamp]
                            if not new_data.empty:
                                updated_data = pd.concat([existing_data, new_data])
                            else:
                                updated_data = existing_data
                        else:
                            updated_data = new_data
                    else:
                        updated_data = new_data
                    
                    # Сохраняем обновленные данные
                    self.save_data(updated_data, filename)
                
                # Пауза между запросами
                time.sleep(1)

def main():
    collector = YahooFinanceCollector()
    collector.update_all_data()

if __name__ == "__main__":
    main()
