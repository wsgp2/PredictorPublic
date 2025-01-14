import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import logging

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_sp500_data_fetch():
    """
    Тестирование различных способов получения данных S&P 500
    """
    # Получаем даты для тестирования
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)
    
    logger.info(f"Тестирование получения данных S&P 500 с {start_date.date()} по {end_date.date()}")
    
    # Тест 1: Получение данных через тикер ^GSPC
    try:
        logger.info("\nТест 1: Получение данных через ^GSPC")
        sp500 = yf.download('^GSPC', start=start_date, end=end_date)
        logger.info(f"Форма данных: {sp500.shape}")
        logger.info(f"Столбцы: {sp500.columns.tolist()}")
        logger.info(f"Пример данных:\n{sp500.head()}")
    except Exception as e:
        logger.error(f"Ошибка в тесте 1: {str(e)}")

    # Тест 2: Получение только цены закрытия
    try:
        logger.info("\nТест 2: Получение только цены закрытия")
        sp500_close = yf.download('^GSPC', start=start_date, end=end_date)['Close']
        logger.info(f"Форма данных: {sp500_close.shape}")
        logger.info(f"Тип данных: {type(sp500_close)}")
        logger.info(f"Пример данных:\n{sp500_close.head()}")
    except Exception as e:
        logger.error(f"Ошибка в тесте 2: {str(e)}")

    # Тест 3: Получение данных через SPY ETF
    try:
        logger.info("\nТест 3: Получение данных через SPY ETF")
        spy = yf.download('SPY', start=start_date, end=end_date)
        logger.info(f"Форма данных: {spy.shape}")
        logger.info(f"Столбцы: {spy.columns.tolist()}")
        logger.info(f"Пример данных:\n{spy.head()}")
    except Exception as e:
        logger.error(f"Ошибка в тесте 3: {str(e)}")

    # Тест 4: Получение данных с ресемплингом
    try:
        logger.info("\nТест 4: Получение данных с ресемплингом")
        sp500_daily = yf.download('^GSPC', start=start_date, end=end_date, interval='1d')
        logger.info(f"Форма дневных данных: {sp500_daily.shape}")
        logger.info(f"Пример дневных данных:\n{sp500_daily.head()}")
    except Exception as e:
        logger.error(f"Ошибка в тесте 4: {str(e)}")

    # Тест 5: Проверка размерности и преобразование в нужный формат
    try:
        logger.info("\nТест 5: Проверка размерности и преобразование")
        sp500_close = yf.download('^GSPC', start=start_date, end=end_date)['Close']
        sp500_array = sp500_close.values.reshape(-1, 1)
        logger.info(f"Исходная форма: {sp500_close.shape}")
        logger.info(f"Форма после reshape: {sp500_array.shape}")
        logger.info(f"Тип данных после reshape: {type(sp500_array)}")
    except Exception as e:
        logger.error(f"Ошибка в тесте 5: {str(e)}")

def test_sp500_data_quality(days=30):
    """
    Тестирование качества данных S&P 500
    """
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    logger.info(f"\nПроверка качества данных S&P 500 за последние {days} дней")
    
    try:
        # Получаем данные
        data = yf.download('^GSPC', start=start_date, end=end_date)
        
        # Проверка 1: Отсутствие пропущенных значений
        missing_values = data.isnull().sum()
        logger.info("\nПроверка пропущенных значений:")
        logger.info(f"Количество пропущенных значений:\n{missing_values}")
        assert missing_values.sum() == 0, "Обнаружены пропущенные значения"
        
        # Проверка 2: Корректность временного ряда
        time_diff = data.index.to_series().diff().dropna()
        business_days = time_diff.dt.days.value_counts()
        logger.info("\nПроверка временного ряда:")
        logger.info(f"Распределение промежутков между датами (в днях):\n{business_days}")
        assert (time_diff.dt.days > 3).sum() == 0, "Обнаружены слишком большие промежутки между датами"
        
        # Проверка 3: Диапазон значений
        price_changes = data['Close'].pct_change().dropna()
        logger.info("\nПроверка изменений цены:")
        max_change = float(price_changes.max().values[0])
        min_change = float(price_changes.min().values[0])
        logger.info(f"Максимальное дневное изменение: {max_change*100:.2f}%")
        logger.info(f"Минимальное дневное изменение: {min_change*100:.2f}%")
        assert max_change < 0.2 and min_change > -0.2, "Обнаружены подозрительно большие изменения цены"
        
        logger.info("\nВсе проверки качества данных пройдены успешно!")
        
    except Exception as e:
        logger.error(f"Ошибка при проверке качества данных: {str(e)}")
        raise

if __name__ == "__main__":
    test_sp500_data_fetch()
    test_sp500_data_quality()
