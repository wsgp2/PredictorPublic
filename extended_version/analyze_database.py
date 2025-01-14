import pandas as pd
from db import DB
import logging
from datetime import datetime

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def analyze_tables():
    """Анализ всех таблиц в базе данных"""
    db = DB()
    
    # Получаем список всех таблиц
    query = """
    SELECT tablename 
    FROM pg_catalog.pg_tables 
    WHERE schemaname = 'public';
    """
    
    tables = pd.read_sql_query(query, db.db.conn)
    
    for _, row in tables.iterrows():
        table_name = row['tablename']
        logger.info(f"\nАнализ таблицы {table_name}:")
        
        # Количество записей
        count_query = f"SELECT COUNT(*) as count FROM {table_name}"
        count = pd.read_sql_query(count_query, db.db.conn)
        logger.info(f"Количество записей: {count['count'].iloc[0]}")
        
        # Временной диапазон (если есть поле timestamp)
        try:
            time_range_query = f"""
            SELECT 
                MIN(timestamp) as first_date,
                MAX(timestamp) as last_date
            FROM {table_name}
            """
            time_range = pd.read_sql_query(time_range_query, db.db.conn)
            logger.info(f"Период данных: с {time_range['first_date'].iloc[0]} по {time_range['last_date'].iloc[0]}")
        except:
            logger.info("Таблица не содержит временных данных")
        
        # Уникальные значения в важных столбцах
        try:
            if 'symbol' in pd.read_sql(f"SELECT * FROM {table_name} LIMIT 0", db.db.conn).columns:
                symbols_query = f"""
                SELECT DISTINCT symbol, COUNT(*) as count
                FROM {table_name}
                GROUP BY symbol
                """
                symbols = pd.read_sql_query(symbols_query, db.db.conn)
                logger.info("\nРаспределение по символам:")
                logger.info(symbols.to_string())
            
            if 'exchange' in pd.read_sql(f"SELECT * FROM {table_name} LIMIT 0", db.db.conn).columns:
                exchanges_query = f"""
                SELECT DISTINCT exchange, COUNT(*) as count
                FROM {table_name}
                GROUP BY exchange
                """
                exchanges = pd.read_sql_query(exchanges_query, db.db.conn)
                logger.info("\nРаспределение по биржам:")
                logger.info(exchanges.to_string())
        except:
            pass

if __name__ == "__main__":
    analyze_tables()
