import pandas as pd
from db import DB
from collectors.google_trends_collector import GoogleTrendsCollector
import logging
from datetime import datetime, timedelta
import time

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_missing_periods():
    """Получение периодов с пропущенными данными"""
    db = DB()
    
    query = """
    WITH dates AS (
        SELECT generate_series(
            (SELECT MIN(timestamp) FROM google_trends),
            (SELECT MAX(timestamp) FROM google_trends),
            interval '1 month'
        ) as start_date,
        generate_series(
            (SELECT MIN(timestamp) FROM google_trends) + interval '1 month',
            (SELECT MAX(timestamp) FROM google_trends),
            interval '1 month'
        ) as end_date
    ),
    categories AS (
        SELECT DISTINCT category FROM google_trends
    ),
    period_coverage AS (
        SELECT 
            d.start_date,
            d.end_date,
            c.category,
            COUNT(DISTINCT g.timestamp::date) as days_with_data
        FROM dates d
        CROSS JOIN categories c
        LEFT JOIN google_trends g 
            ON g.timestamp::date >= d.start_date 
            AND g.timestamp::date < d.end_date
            AND g.category = c.category
        GROUP BY d.start_date, d.end_date, c.category
    )
    SELECT 
        start_date,
        end_date,
        category,
        days_with_data,
        EXTRACT(DAY FROM (end_date - start_date)) as total_days
    FROM period_coverage
    WHERE days_with_data < EXTRACT(DAY FROM (end_date - start_date)) * 0.8
    ORDER BY start_date, category;
    """
    
    df = pd.read_sql_query(query, db.db.conn)
    return df

def collect_missing_data():
    """Сбор пропущенных данных"""
    # Получаем периоды с пропущенными данными
    missing_periods = get_missing_periods()
    
    if missing_periods.empty:
        logger.info("No missing periods found!")
        return
        
    logger.info(f"Found {len(missing_periods)} periods with missing data")
    
    # Создаем коллектор
    collector = GoogleTrendsCollector()
    
    # Собираем данные для каждого периода
    for _, row in missing_periods.iterrows():
        start_date = row['start_date']
        end_date = row['end_date']
        category = row['category']
        
        logger.info(f"Collecting {category} data from {start_date} to {end_date}")
        
        try:
            # Получаем ключевые слова для категории
            keywords = collector.keywords[category]
            
            # Собираем данные
            df = collector.get_trends_data(
                keywords=keywords,
                start_date=start_date,
                end_date=end_date,
                max_retries=5,
                retry_delay=60  # Увеличиваем задержку для надежности
            )
            
            if not df.empty:
                # Сохраняем в CSV
                filename = f"trends_{category}_{start_date.strftime('%Y%m')}.csv"
                df.to_csv(f"data/trends/{filename}", index=False)
                
                # Сохраняем в базу данных
                collector.save_to_db(df, category)
                
                logger.info(f"Successfully collected and saved data for {category} ({start_date} - {end_date})")
            
            # Делаем паузу между периодами
            time.sleep(30)
            
        except Exception as e:
            logger.error(f"Error collecting data for {category} ({start_date} - {end_date}): {str(e)}")
            continue

if __name__ == "__main__":
    collect_missing_data()
