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

def analyze_coverage():
    """Анализ покрытия данных по категориям"""
    db = DB()
    
    # Анализ по категориям
    query = """
    SELECT 
        category,
        MIN(timestamp) as first_date,
        MAX(timestamp) as last_date,
        COUNT(*) as records,
        COUNT(DISTINCT keyword) as unique_keywords
    FROM google_trends
    GROUP BY category
    ORDER BY category;
    """
    
    df = pd.read_sql_query(query, db.db.conn)
    logger.info("\nПокрытие данных по категориям:")
    logger.info(df.to_string())
    
    # Анализ пропусков
    query = """
    WITH dates AS (
        SELECT generate_series(
            (SELECT MIN(timestamp) FROM google_trends),
            (SELECT MAX(timestamp) FROM google_trends),
            interval '1 day'
        ) as date
    ),
    categories AS (
        SELECT DISTINCT category FROM google_trends
    )
    SELECT 
        c.category,
        COUNT(d.date) as total_days,
        COUNT(g.timestamp) as days_with_data,
        COUNT(d.date) - COUNT(g.timestamp) as missing_days
    FROM dates d
    CROSS JOIN categories c
    LEFT JOIN google_trends g ON d.date = g.timestamp::date AND c.category = g.category
    GROUP BY c.category
    ORDER BY missing_days DESC;
    """
    
    df_gaps = pd.read_sql_query(query, db.db.conn)
    logger.info("\nАнализ пропусков данных:")
    logger.info(df_gaps.to_string())
    
    return df, df_gaps

if __name__ == "__main__":
    analyze_coverage()
