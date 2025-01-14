import psycopg2
import logging
import os

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_tables():
    """Создание всех необходимых таблиц в базе данных"""
    try:
        # Подключаемся к базе данных
        conn = psycopg2.connect(
            dbname='bitcoin_predictor',
            user='postgres',
            password='postgres',
            host='localhost',
            port='5432'
        )
        cur = conn.cursor()
        
        # Читаем SQL-файл
        sql_file_path = os.path.join(
            os.path.dirname(__file__),
            'sql',
            'create_tables.sql'
        )
        
        with open(sql_file_path, 'r') as file:
            sql_commands = file.read()
            
        # Выполняем SQL-команды
        cur.execute(sql_commands)
        
        # Подтверждаем изменения
        conn.commit()
        logger.info("Все таблицы успешно созданы!")
        
        # Проверяем созданные таблицы
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            AND table_type = 'BASE TABLE';
        """)
        tables = cur.fetchall()
        
        logger.info("\nСозданные таблицы:")
        for table in tables:
            logger.info(f"- {table[0]}")
            
    except Exception as e:
        logger.error(f"Ошибка при создании таблиц: {str(e)}")
        conn.rollback()
    finally:
        if conn:
            cur.close()
            conn.close()

if __name__ == "__main__":
    create_tables()
