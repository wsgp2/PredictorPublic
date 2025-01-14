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

def migrate_trends_data():
    """Миграция данных Google Trends с 2020 года"""
    try:
        # Подключаемся к основной базе данных
        main_conn = psycopg2.connect(**DB_CONFIG)
        main_cur = main_conn.cursor()
        
        # Подключаемся к базе с данными коллектора
        collector_conn = psycopg2.connect(
            dbname='bitcoin_predictor',
            user='postgres',
            password='postgres',
            host='localhost',
            port='5432'
        )
        collector_cur = collector_conn.cursor()
        
        try:
            # Проверяем данные в базе коллектора с 2020 года
            collector_cur.execute("""
                SELECT COUNT(*) 
                FROM google_trends 
                WHERE timestamp >= '2020-01-01'
            """)
            count = collector_cur.fetchone()[0]
            
            if count > 0:
                # Получаем временной диапазон данных
                collector_cur.execute("""
                    SELECT MIN(timestamp), MAX(timestamp) 
                    FROM google_trends 
                    WHERE timestamp >= '2020-01-01'
                """)
                min_date, max_date = collector_cur.fetchone()
                logger.info(f"Найдено {count} записей с {min_date} по {max_date}")
                
                # Удаляем старые данные из основной базы
                main_cur.execute("""
                    DELETE FROM google_trends 
                    WHERE timestamp >= '2020-01-01'
                """)
                logger.info("Удалены данные с 2020 года из основной базы")
                
                # Копируем данные пакетами
                batch_size = 1000
                offset = 0
                
                while True:
                    collector_cur.execute("""
                        SELECT timestamp, source, category, keyword, value 
                        FROM google_trends 
                        WHERE timestamp >= '2020-01-01'
                        ORDER BY timestamp
                        LIMIT %s OFFSET %s
                    """, (batch_size, offset))
                    
                    rows = collector_cur.fetchall()
                    if not rows:
                        break
                        
                    # Вставляем данные в основную базу
                    main_cur.executemany(
                        """
                        INSERT INTO google_trends 
                        (timestamp, source, category, keyword, value)
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT (timestamp, category, keyword) 
                        DO UPDATE SET value = EXCLUDED.value;
                        """,
                        rows
                    )
                    main_conn.commit()
                    
                    offset += len(rows)
                    logger.info(f"Обработано {offset} из {count} записей")
                
                logger.info("Миграция данных завершена успешно")
            else:
                logger.warning("Нет данных с 2020 года для миграции")
            
        finally:
            main_cur.close()
            main_conn.close()
            collector_cur.close()
            collector_conn.close()
            
    except Exception as e:
        logger.error(f"Ошибка при миграции данных: {str(e)}")
        raise

if __name__ == "__main__":
    try:
        migrate_trends_data()
        logger.info("Миграция данных успешно завершена")
    except Exception as e:
        logger.error(f"Ошибка: {str(e)}")
        sys.exit(1)
