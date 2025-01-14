import psycopg2
import logging
import sys
import os
from datetime import datetime, timedelta

# Импортируем конфигурацию базы данных
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from config.config import DB_CONFIG

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_latest_data():
    """Проверка последних данных по каждой категории"""
    try:
        # Подключаемся к базе данных
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        try:
            # Текущая дата
            now = datetime.now()
            yesterday = now - timedelta(days=1)
            
            # Проверяем последние данные по каждой категории
            cur.execute("""
                WITH latest_by_category AS (
                    SELECT 
                        category,
                        keyword,
                        MAX(timestamp) as last_update,
                        COUNT(*) as total_records
                    FROM google_trends
                    GROUP BY category, keyword
                )
                SELECT 
                    category,
                    keyword,
                    last_update,
                    total_records,
                    EXTRACT(EPOCH FROM (%s - last_update))/3600 as hours_behind
                FROM latest_by_category
                ORDER BY last_update ASC;
            """, (now,))
            
            results = cur.fetchall()
            
            logger.info(f"Проверка актуальности данных на {now}")
            logger.info("-" * 80)
            
            outdated_keywords = []
            for category, keyword, last_update, total_records, hours_behind in results:
                status = "✓" if last_update >= yesterday else "✗"
                logger.info(f"{status} {category:12} | {keyword:25} | Последнее обновление: {last_update} | {total_records:5} записей | {hours_behind:5.1f} часов назад")
                
                if last_update < yesterday:
                    outdated_keywords.append((category, keyword))
            
            logger.info("-" * 80)
            if outdated_keywords:
                logger.warning(f"Найдено {len(outdated_keywords)} устаревших ключевых слов:")
                for category, keyword in outdated_keywords:
                    logger.warning(f"  - {category}/{keyword}")
            else:
                logger.info("Все данные актуальны (не старше 24 часов)")
            
        finally:
            cur.close()
            conn.close()
            
    except Exception as e:
        logger.error(f"Ошибка при проверке данных: {str(e)}")
        raise

if __name__ == "__main__":
    try:
        check_latest_data()
    except Exception as e:
        logger.error(f"Ошибка: {str(e)}")
        sys.exit(1)
