import psycopg2
import pandas as pd
from datetime import datetime, timedelta
import logging
from config.config import DB_CONFIG

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def analyze_table_frequency(conn, table_name):
    """Анализирует частоту обновления данных в таблице"""
    cur = conn.cursor()
    
    # Получаем все временные метки
    cur.execute(f"SELECT timestamp FROM {table_name} ORDER BY timestamp")
    timestamps = [row[0] for row in cur.fetchall()]
    
    if not timestamps:
        logger.info(f"Таблица {table_name} пуста")
        return
    
    # Преобразуем в pandas Series для удобного анализа
    ts_series = pd.Series(timestamps)
    
    # Вычисляем разницу между последовательными записями
    time_diffs = ts_series.diff()
    
    logger.info(f"\nАнализ таблицы {table_name}:")
    logger.info(f"Всего записей: {len(timestamps)}")
    logger.info(f"Период данных: с {timestamps[0]} по {timestamps[-1]}")
    logger.info(f"Средний интервал между записями: {time_diffs.mean()}")
    logger.info(f"Медианный интервал: {time_diffs.median()}")
    logger.info(f"Минимальный интервал: {time_diffs.min()}")
    logger.info(f"Максимальный интервал: {time_diffs.max()}")
    
    # Анализ последних обновлений
    last_week = datetime.now() - timedelta(days=7)
    cur.execute(f"SELECT timestamp FROM {table_name} WHERE timestamp >= %s ORDER BY timestamp", (last_week,))
    recent_updates = [row[0] for row in cur.fetchall()]
    
    if recent_updates:
        recent_series = pd.Series(recent_updates)
        recent_diffs = recent_series.diff()
        logger.info("\nПоследние 7 дней:")
        logger.info(f"Количество обновлений: {len(recent_updates)}")
        logger.info(f"Средний интервал: {recent_diffs.mean()}")
    
    cur.close()

def main():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        
        tables = [
            'price_data',
            'market_data',
            'on_chain_metrics'
        ]
        
        for table in tables:
            analyze_table_frequency(conn, table)
        
        conn.close()
        
    except Exception as e:
        logger.error(f"Ошибка при анализе: {str(e)}")

if __name__ == "__main__":
    main()
