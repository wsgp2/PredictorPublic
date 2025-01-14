import os
import sys
import psycopg2
import logging

# Добавляем родительскую директорию в путь для импортов
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from config.config import DB_CONFIG as db_config

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def init_database():
    """Инициализация базы данных и создание таблиц"""
    try:
        # Подключаемся к базе данных
        conn = psycopg2.connect(**db_config)
        cur = conn.cursor()
        logger.info("Successfully connected to the database")

        # Читаем SQL скрипт
        current_dir = os.path.dirname(os.path.abspath(__file__))
        sql_file = os.path.join(current_dir, 'create_tables.sql')
        
        with open(sql_file, 'r') as f:
            sql_script = f.read()

        # Выполняем SQL скрипт
        cur.execute(sql_script)
        conn.commit()
        logger.info("Successfully created database tables")

        # Закрываем соединение
        cur.close()
        conn.close()
        logger.info("Database connection closed")

        return True

    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}")
        return False

if __name__ == "__main__":
    init_database()
