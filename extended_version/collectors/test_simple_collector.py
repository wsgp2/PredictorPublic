import pandas as pd
import psycopg2
from pytrends.request import TrendReq
import logging
from datetime import datetime, timedelta
import time
import random
import sys
from typing import List, Dict, Any

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SlowTrendsCollector:
    def __init__(self):
        # Подключение к базе данных
        self.db = psycopg2.connect(
            dbname='bitcoin_predictor',
            user='postgres',
            password='postgres',
            host='localhost',
            port='5432'
        )
        
        # Создаем таблицы если их нет
        self.init_database()
        
        # Настройки запросов
        self.max_retries = 5  # увеличиваем количество попыток
        self.min_wait = 30  # минимальное время ожидания между запросами (0.5 минуты)
        self.max_wait = 60  # максимальное время ожидания (1 минута)
        
        # Загружаем ключевые слова
        self.keywords = {
            'general': [
                'bitcoin', 'btc', 'crypto', 'cryptocurrency', 
                'digital currency', 'blockchain'
            ],
            'trading': [
                'buy bitcoin', 'sell bitcoin', 'bitcoin price',
                'bitcoin trading', 'bitcoin investment', 'bitcoin profit',
                'bitcoin loss', 'bitcoin market'
            ],
            'technical': [
                'bitcoin mining', 'bitcoin wallet', 'bitcoin halving',
                'bitcoin node', 'bitcoin lightning', 'bitcoin transaction',
                'bitcoin address', 'bitcoin block'
            ],
            'news': [
                'bitcoin news', 'crypto news', 'bitcoin crash',
                'bitcoin regulation', 'bitcoin ban', 'bitcoin adoption',
                'bitcoin etf', 'bitcoin sec'
            ],
            'sentiment': [
                'bitcoin dead', 'bitcoin bubble', 'bitcoin scam',
                'bitcoin future', 'bitcoin gold', 'bitcoin safe',
                'bitcoin risk', 'bitcoin opportunity'
            ],
            'related': [
                'ethereum', 'defi', 'nft', 'web3',
                'metaverse', 'cryptocurrency exchange', 'binance', 'coinbase'
            ]
        }

    def init_database(self):
        """Инициализация базы данных"""
        try:
            with self.db.cursor() as cursor:
                # Создаем таблицу для данных Google Trends
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS google_trends (
                        id SERIAL PRIMARY KEY,
                        timestamp TIMESTAMP NOT NULL,
                        source VARCHAR(50) NOT NULL,
                        category VARCHAR(50) NOT NULL,
                        keyword VARCHAR(100) NOT NULL,
                        value DOUBLE PRECISION NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(timestamp, category, keyword)
                    );
                    CREATE INDEX IF NOT EXISTS idx_google_trends_timestamp ON google_trends(timestamp);
                    CREATE INDEX IF NOT EXISTS idx_google_trends_category ON google_trends(category);
                """)
                self.db.commit()
                logger.info("База данных инициализирована")
        except Exception as e:
            logger.error(f"Ошибка при инициализации БД: {str(e)}")
            raise

    def get_date_range(self, category: str, keyword: str) -> tuple[datetime, datetime]:
        """Определение диапазона дат для сбора данных"""
        try:
            # Начинаем с 2020 года
            start_date = datetime(2020, 1, 1)
            end_date = datetime.now()
            
            # Разбиваем период на части по 6 месяцев
            while start_date < end_date:
                period_end = min(
                    start_date + timedelta(days=180),  # примерно 6 месяцев
                    end_date
                )
                yield start_date, period_end
                start_date = period_end + timedelta(days=1)
                
        except Exception as e:
            logger.error(f"Ошибка при получении дат: {str(e)}")
            yield datetime(2020, 1, 1), datetime.now()

    def save_to_db(self, data: pd.DataFrame, category: str, keyword: str):
        """Сохранение данных в БД"""
        try:
            with self.db.cursor() as cursor:
                # Преобразуем данные в формат для записи
                records = []
                for date, row in data.iterrows():
                    records.append((
                        date,  # timestamp
                        'google_trends',  # source
                        category,  # category
                        keyword,  # keyword
                        float(row[keyword])  # value
                    ))
                
                # Записываем данные
                cursor.executemany('''
                    INSERT INTO google_trends 
                    (timestamp, source, category, keyword, value)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (timestamp, category, keyword) 
                    DO UPDATE SET value = EXCLUDED.value
                ''', records)
                self.db.commit()
                logger.info(f"Сохранено {len(records)} записей для {category}/{keyword}")
        except Exception as e:
            logger.error(f"Ошибка при сохранении в БД: {str(e)}")
            self.db.rollback()
            raise

    def wait_with_backoff(self, attempt: int):
        """Ожидание с экспоненциальным увеличением времени"""
        wait_time = min(
            self.min_wait * (2 ** attempt) + random.uniform(0, 10),
            self.max_wait
        )
        logger.info(f"Ожидание {wait_time:.2f} секунд перед следующим запросом...")
        time.sleep(wait_time)

    def collect_data_with_retry(self, keyword: str, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """Сбор данных с повторными попытками"""
        for attempt in range(self.max_retries):
            try:
                # Создаем новый клиент для каждой попытки
                pytrends = TrendReq(
                    hl='en-US',
                    tz=360,
                    timeout=(30, 30)  # увеличиваем таймаут
                )
                
                # Строим запрос
                timeframe = f"{start_date.strftime('%Y-%m-%d')} {end_date.strftime('%Y-%m-%d')}"
                logger.info(f"Попытка {attempt + 1}/{self.max_retries} для {keyword} за период {timeframe}")
                
                pytrends.build_payload(
                    kw_list=[keyword],
                    timeframe=timeframe
                )
                
                # Получаем данные
                data = pytrends.interest_over_time()
                
                if not data.empty:
                    logger.info(f"Успешно получены данные для {keyword}")
                    return data
                else:
                    logger.warning(f"Пустые данные для {keyword} на попытке {attempt + 1}")
                    
            except Exception as e:
                logger.error(f"Ошибка при сборе данных для {keyword} на попытке {attempt + 1}")
                logger.error(f"Тип ошибки: {type(e).__name__}")
                logger.error(f"Описание: {str(e)}")
                
                if attempt < self.max_retries - 1:
                    self.wait_with_backoff(attempt)
                else:
                    logger.error(f"Все попытки исчерпаны для {keyword}")
        
        return pd.DataFrame()

    def collect_for_period(self, category: str, keyword: str, start_date: datetime, end_date: datetime):
        """Сбор данных за период. Берем максимально возможный период за раз."""
        logger.info(f"Сбор данных для {category}/{keyword} с {start_date.date()} по {end_date.date()}")
        data = self.collect_data_with_retry(keyword, start_date, end_date)
        
        if not data.empty:
            self.save_to_db(data, category, keyword)
        
        # Ждем перед следующим запросом
        wait_time = random.uniform(self.min_wait, self.max_wait)
        logger.info(f"Ждем {wait_time:.2f} секунд перед следующим запросом...")
        time.sleep(wait_time)

    def run_collection(self):
        """Запуск сбора данных"""
        for category, keywords in self.keywords.items():
            logger.info(f"\nОбработка категории: {category}")
            for keyword in keywords:
                try:
                    logger.info(f"\nОбработка {category}/{keyword}")
                    
                    # Получаем периоды для сбора данных
                    for start_date, end_date in self.get_date_range(category, keyword):
                        logger.info(f"Сбор данных за период {start_date.date()} - {end_date.date()}")
                        
                        # Собираем данные
                        self.collect_for_period(category, keyword, start_date, end_date)
                    
                except Exception as e:
                    logger.error(f"Ошибка при обработке {category}/{keyword}: {str(e)}")
                    continue

if __name__ == "__main__":
    try:
        collector = SlowTrendsCollector()
        collector.run_collection()
    except KeyboardInterrupt:
        logger.info("Программа остановлена пользователем")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Неожиданная ошибка: {str(e)}")
        sys.exit(1)
