import psycopg2
import logging
from datetime import datetime, timedelta
from collections import defaultdict

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_data_status():
    """Проверка статуса собранных данных"""
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

        # 1. Проверяем данные Google Trends
        logger.info("\n=== Google Trends Data Status ===")
        cur.execute("""
            SELECT 
                category,
                keyword,
                MIN(timestamp) as first_record,
                MAX(timestamp) as last_record,
                COUNT(*) as total_records
            FROM google_trends
            GROUP BY category, keyword
            ORDER BY category, keyword;
        """)
        trends_data = cur.fetchall()
        
        categories_stats = defaultdict(lambda: {'keywords': 0, 'records': 0})
        
        for category, keyword, first, last, total in trends_data:
            categories_stats[category]['keywords'] += 1
            categories_stats[category]['records'] += total
            logger.info(f"{category:12} | {keyword:25} | {first.date()} - {last.date()} | {total:6} records")
        
        logger.info("\nCategory Summary:")
        for category, stats in categories_stats.items():
            logger.info(f"{category:12} | {stats['keywords']:3} keywords | {stats['records']:6} total records")
            
        # 2. Проверяем данные Blockchain
        logger.info("\n=== Blockchain Data Status ===")
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_name LIKE 'blockchain_%'
            AND table_schema = 'public';
        """)
        blockchain_tables = cur.fetchall()
        
        for table in blockchain_tables:
            table_name = table[0]
            cur.execute(f"""
                SELECT 
                    MIN(timestamp) as first_record,
                    MAX(timestamp) as last_record,
                    COUNT(*) as total_records
                FROM {table_name};
            """)
            first, last, total = cur.fetchone()
            if first and last:
                metric = table_name.replace('blockchain_', '')
                logger.info(f"{metric:30} | {first.date()} - {last.date()} | {total:6} records")

        # 3. Проверяем данные CoinArk
        logger.info("\n=== CoinArk Data Status ===")
        for table in ['longshort_data', 'market_data']:
            cur.execute(f"""
                SELECT 
                    MIN(timestamp) as first_record,
                    MAX(timestamp) as last_record,
                    COUNT(*) as total_records
                FROM {table};
            """)
            first, last, total = cur.fetchone()
            if first and last:
                logger.info(f"{table:30} | {first.date()} - {last.date()} | {total:6} records")

        # 4. Проверяем данные Yahoo Finance
        logger.info("\n=== Yahoo Finance Data Status ===")
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_name LIKE 'yahoo_%'
            AND table_schema = 'public';
        """)
        yahoo_tables = cur.fetchall()
        
        for table in yahoo_tables:
            table_name = table[0]
            cur.execute(f"""
                SELECT 
                    MIN(timestamp) as first_record,
                    MAX(timestamp) as last_record,
                    COUNT(*) as total_records
                FROM {table_name};
            """)
            first, last, total = cur.fetchone()
            if first and last:
                symbol = table_name.replace('yahoo_', '')
                logger.info(f"{symbol:30} | {first.date()} - {last.date()} | {total:6} records")

        # 5. Проверяем данные FRED
        logger.info("\n=== FRED Data Status ===")
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_name LIKE 'fred_%'
            AND table_schema = 'public';
        """)
        fred_tables = cur.fetchall()
        
        for table in fred_tables:
            table_name = table[0]
            cur.execute(f"""
                SELECT 
                    MIN(timestamp) as first_record,
                    MAX(timestamp) as last_record,
                    COUNT(*) as total_records
                FROM {table_name};
            """)
            first, last, total = cur.fetchone()
            if first and last:
                indicator = table_name.replace('fred_', '')
                logger.info(f"{indicator:30} | {first.date()} - {last.date()} | {total:6} records")

        # 6. Проверяем данные LunarCrush
        logger.info("\n=== LunarCrush Data Status ===")
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_name LIKE 'lunarcrush_%'
            AND table_schema = 'public';
        """)
        lunar_tables = cur.fetchall()
        
        for table in lunar_tables:
            table_name = table[0]
            cur.execute(f"""
                SELECT 
                    MIN(timestamp) as first_record,
                    MAX(timestamp) as last_record,
                    COUNT(*) as total_records
                FROM {table_name};
            """)
            first, last, total = cur.fetchone()
            if first and last:
                metric = table_name.replace('lunarcrush_', '')
                logger.info(f"{metric:30} | {first.date()} - {last.date()} | {total:6} records")

    except Exception as e:
        logger.error(f"Error checking data status: {str(e)}")
    finally:
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    check_data_status()
