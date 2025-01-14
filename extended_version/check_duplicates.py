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

def check_duplicates():
    """Проверка дубликатов в таблице google_trends"""
    try:
        # Подключаемся к базе данных
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        try:
            # Проверяем наличие дубликатов по timestamp, category и keyword
            cur.execute("""
                WITH duplicates AS (
                    SELECT 
                        timestamp,
                        category,
                        keyword,
                        COUNT(*) as count,
                        array_agg(value) as values,
                        array_agg(id) as ids
                    FROM google_trends
                    GROUP BY timestamp, category, keyword
                    HAVING COUNT(*) > 1
                )
                SELECT 
                    timestamp,
                    category,
                    keyword,
                    count,
                    values,
                    ids
                FROM duplicates
                ORDER BY timestamp, category, keyword;
            """)
            
            duplicates = cur.fetchall()
            
            if duplicates:
                logger.info(f"Найдено {len(duplicates)} групп дубликатов:")
                for dup in duplicates:
                    logger.info(f"  Timestamp: {dup[0]}, Category: {dup[1]}, Keyword: {dup[2]}")
                    logger.info(f"  Количество: {dup[3]}, Значения: {dup[4]}, IDs: {dup[5]}")
                    
                # Удаляем дубликаты, оставляя только одну запись
                logger.info("Удаляем дубликаты...")
                cur.execute("""
                    WITH duplicates AS (
                        SELECT id,
                            ROW_NUMBER() OVER (
                                PARTITION BY timestamp, category, keyword
                                ORDER BY id
                            ) as row_num
                        FROM google_trends
                    )
                    DELETE FROM google_trends
                    WHERE id IN (
                        SELECT id 
                        FROM duplicates 
                        WHERE row_num > 1
                    );
                """)
                conn.commit()
                logger.info("Дубликаты удалены")
                
            else:
                logger.info("Дубликатов не найдено")
            
            # Проверяем все таблицы с похожими данными
            cur.execute("""
                SELECT tablename 
                FROM pg_tables 
                WHERE schemaname = 'public' 
                AND tablename LIKE '%trend%' OR tablename LIKE '%google%';
            """)
            
            tables = cur.fetchall()
            if len(tables) > 1:
                logger.warning(f"Найдено несколько таблиц с трендами: {[t[0] for t in tables]}")
            else:
                logger.info("Найдена только одна таблица с трендами")
            
        finally:
            cur.close()
            conn.close()
            
    except Exception as e:
        logger.error(f"Ошибка при проверке дубликатов: {str(e)}")
        raise

if __name__ == "__main__":
    try:
        check_duplicates()
        logger.info("Проверка завершена")
    except Exception as e:
        logger.error(f"Ошибка: {str(e)}")
        sys.exit(1)
