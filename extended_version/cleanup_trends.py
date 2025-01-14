import psycopg2
import logging
import sys
import os
from datetime import datetime

# Импортируем конфигурацию базы данных
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from config.config import DB_CONFIG

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def cleanup_old_trends():
    """Удаление старых данных Google Trends (до 2020 года)"""
    try:
        # Подключаемся к базе данных
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        try:
            # Проверяем количество старых данных
            cur.execute("""
                SELECT COUNT(*) 
                FROM google_trends 
                WHERE timestamp < '2020-01-01'
            """)
            count = cur.fetchone()[0]
            
            if count > 0:
                # Получаем временной диапазон старых данных
                cur.execute("""
                    SELECT MIN(timestamp), MAX(timestamp) 
                    FROM google_trends 
                    WHERE timestamp < '2020-01-01'
                """)
                min_date, max_date = cur.fetchone()
                logger.info(f"Найдено {count} записей с {min_date} по {max_date}")
                
                # Удаляем старые данные
                cur.execute("""
                    DELETE FROM google_trends 
                    WHERE timestamp < '2020-01-01'
                """)
                conn.commit()
                
                logger.info(f"Удалено {count} записей")
            else:
                logger.info("Старых данных (до 2020 года) не найдено")
            
        finally:
            cur.close()
            conn.close()
            
    except Exception as e:
        logger.error(f"Ошибка при удалении данных: {str(e)}")
        raise

if __name__ == "__main__":
    try:
        cleanup_old_trends()
        logger.info("Очистка данных успешно завершена")
    except Exception as e:
        logger.error(f"Ошибка: {str(e)}")
        sys.exit(1)
