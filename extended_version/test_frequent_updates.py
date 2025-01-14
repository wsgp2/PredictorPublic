import psycopg2
import pandas as pd
from datetime import datetime, timedelta
import logging
from config.config import DB_CONFIG
import time
from pycoingecko import CoinGeckoAPI

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_price_update():
    """Тестирование частого обновления цен"""
    try:
        # Инициализация CoinGecko API
        cg = CoinGeckoAPI()
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()

        # Создаем временную тестовую таблицу
        cur.execute("""
            CREATE TABLE IF NOT EXISTS test_price_updates (
                timestamp TIMESTAMP PRIMARY KEY,
                price FLOAT,
                market_cap FLOAT,
                total_volume FLOAT
            )
        """)
        
        # Тестируем обновление каждый час в течение 3 часов
        for _ in range(3):
            try:
                # Получаем текущие данные
                data = cg.get_price(
                    ids='bitcoin',
                    vs_currencies='usd',
                    include_market_cap=True,
                    include_24hr_vol=True
                )
                
                if data and 'bitcoin' in data:
                    btc_data = data['bitcoin']
                    timestamp = datetime.now()
                    
                    # Вставляем данные
                    cur.execute("""
                        INSERT INTO test_price_updates (timestamp, price, market_cap, total_volume)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (timestamp) DO NOTHING
                    """, (
                        timestamp,
                        btc_data.get('usd', 0),
                        btc_data.get('usd_market_cap', 0),
                        btc_data.get('usd_24h_vol', 0)
                    ))
                    
                    conn.commit()
                    logger.info(f"Тестовое обновление выполнено в {timestamp}")
                    
                    # Проверяем количество записей
                    cur.execute("SELECT COUNT(*) FROM test_price_updates")
                    count = cur.fetchone()[0]
                    logger.info(f"Всего записей в тестовой таблице: {count}")
                
                # Ждем 1 час перед следующим обновлением
                logger.info("Ожидание 1 час...")
                time.sleep(3600)  # 1 час
                
            except Exception as e:
                logger.error(f"Ошибка при обновлении: {str(e)}")
                continue
        
        # Анализируем результаты
        cur.execute("""
            SELECT 
                timestamp,
                price,
                market_cap,
                total_volume
            FROM test_price_updates
            ORDER BY timestamp DESC
        """)
        
        results = cur.fetchall()
        logger.info("\nРезультаты теста:")
        for row in results:
            logger.info(f"Время: {row[0]}, Цена: ${row[1]:,.2f}, Объем: ${row[3]:,.2f}")
        
        # Очищаем тестовую таблицу
        cur.execute("DROP TABLE test_price_updates")
        conn.commit()
        
    except Exception as e:
        logger.error(f"Ошибка в тесте: {str(e)}")
    finally:
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    logger.info("Начало тестирования частых обновлений...")
    test_price_update()
    logger.info("Тестирование завершено")
