import pandas as pd
import sqlite3
from datetime import datetime, timedelta
import logging
from collectors.google_trends_collector import GoogleTrendsCollector

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_missing_data(db_path='google_trends.db'):
    """Проверяет пропущенные данные в базе данных"""
    conn = sqlite3.connect(db_path)
    
    categories = [
        'general', 'news', 'related', 'sentiment', 
        'technical', 'trading'
    ]
    
    missing_data = {}
    
    for category in categories:
        table_name = f'google_trends_{category}'
        
        # Получаем все даты из базы
        query = f"SELECT DISTINCT date FROM {table_name} ORDER BY date"
        dates_df = pd.read_sql_query(query, conn)
        
        if dates_df.empty:
            logger.warning(f"No data found for category: {category}")
            missing_data[category] = {
                'start_date': datetime(2015, 1, 1),
                'end_date': datetime.now()
            }
            continue
            
        dates = pd.to_datetime(dates_df['date'])
        
        # Создаем полный диапазон дат
        full_range = pd.date_range(
            start=datetime(2015, 1, 1),
            end=datetime.now(),
            freq='D'
        )
        
        # Находим пропущенные даты
        missing_dates = full_range.difference(dates)
        
        if len(missing_dates) > 0:
            # Группируем пропущенные даты по периодам
            gaps = []
            gap_start = missing_dates[0]
            
            for i in range(1, len(missing_dates)):
                if missing_dates[i] - missing_dates[i-1] > timedelta(days=1):
                    gaps.append((gap_start, missing_dates[i-1]))
                    gap_start = missing_dates[i]
            
            gaps.append((gap_start, missing_dates[-1]))
            
            missing_data[category] = gaps
            
            logger.info(f"Category {category} has {len(missing_dates)} missing dates")
            for start, end in gaps:
                logger.info(f"Gap from {start.date()} to {end.date()}")
    
    conn.close()
    return missing_data

def collect_missing_data(missing_data):
    """Собирает пропущенные данные"""
    collector = GoogleTrendsCollector()
    
    for category, data in missing_data.items():
        if isinstance(data, dict):
            # Если нет данных вообще
            start_date = data['start_date']
            end_date = data['end_date']
            
            logger.info(f"Collecting all data for {category} from {start_date.date()} to {end_date.date()}")
            
            # Разбиваем на периоды по 6 месяцев
            current_date = start_date
            while current_date < end_date:
                next_date = min(current_date + timedelta(days=180), end_date)
                
                try:
                    collector.collect_category_data(category, current_date, next_date)
                    logger.info(f"Successfully collected {category} data from {current_date.date()} to {next_date.date()}")
                except Exception as e:
                    logger.error(f"Error collecting {category} data: {str(e)}")
                
                current_date = next_date
                
        else:
            # Если есть пропуски в данных
            for start, end in data:
                logger.info(f"Collecting missing {category} data from {start.date()} to {end.date()}")
                
                try:
                    collector.collect_category_data(category, start, end)
                    logger.info(f"Successfully collected {category} data from {start.date()} to {end.date()}")
                except Exception as e:
                    logger.error(f"Error collecting {category} data: {str(e)}")

if __name__ == "__main__":
    # Проверяем пропущенные данные
    missing_data = check_missing_data()
    
    # Выводим итоговую статистику
    print("\nMissing Data Summary:")
    print("=" * 50)
    for category, gaps in missing_data.items():
        if isinstance(gaps, dict):
            print(f"\n{category.upper()}:")
            print("  No data at all. Need to collect everything.")
        else:
            total_days = sum((end - start).days + 1 for start, end in gaps)
            print(f"\n{category.upper()}:")
            print(f"Total missing days: {total_days}")
            print("Missing periods:")
            for start, end in gaps:
                print(f"  - From {start.date()} to {end.date()}")
    
    # Начинаем сбор данных
    print("\nStarting data collection...")
    collect_missing_data(missing_data)
