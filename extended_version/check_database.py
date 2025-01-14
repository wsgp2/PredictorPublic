import os
import sys
import psycopg2
import logging
from datetime import datetime, timedelta

# Добавляем родительскую директорию в путь для импортов
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from config.config import DB_CONFIG

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_table_data(conn, table_name):
    """Проверяет данные в указанной таблице"""
    cur = conn.cursor()
    
    # Получаем количество записей
    cur.execute(f"SELECT COUNT(*) FROM {table_name}")
    count = cur.fetchone()[0]
    
    # Получаем временной диапазон
    cur.execute(f"SELECT MIN(timestamp), MAX(timestamp) FROM {table_name}")
    time_range = cur.fetchone()
    
    # Получаем количество записей за последние 7 дней
    seven_days_ago = datetime.now() - timedelta(days=7)
    cur.execute(f"SELECT COUNT(*) FROM {table_name} WHERE timestamp >= %s", (seven_days_ago,))
    recent_count = cur.fetchone()[0]
    
    logger.info(f"\nТаблица {table_name}:")
    logger.info(f"  Всего записей: {count}")
    if time_range[0] and time_range[1]:
        logger.info(f"  Период данных: с {time_range[0]} по {time_range[1]}")
    logger.info(f"  Записей за последние 7 дней: {recent_count}")
    
    cur.close()
    return count, time_range, recent_count

def main():
    """Основная функция проверки базы данных"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        logger.info("Успешное подключение к базе данных")
        
        # Список таблиц для проверки
        tables = [
            'price_data',
            'market_data',
            'longshort_data',
            'technical_indicators',
            'on_chain_metrics',
            'sentiment_metrics',
            'related_assets',
            'news_data',
            'google_trends'
        ]
        
        # Проверяем каждую таблицу
        for table in tables:
            check_table_data(conn, table)
        
        conn.close()
        logger.info("\nПроверка базы данных завершена")
        
    except Exception as e:
        logger.error(f"Ошибка при проверке базы данных: {str(e)}")
        
if __name__ == "__main__":
    main()
