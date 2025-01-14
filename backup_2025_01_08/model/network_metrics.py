"""
Модуль для получения метрик сети Bitcoin
"""

import pandas as pd
import requests
from datetime import datetime, timedelta
from typing import Optional
from .logger import setup_logger

logger = setup_logger(__name__)

def get_bitcoin_dominance() -> Optional[pd.DataFrame]:
    """
    Получение данных о доминировании Bitcoin на рынке криптовалют
    """
    try:
        url = "https://api.coingecko.com/api/v3/global/bitcoin/dominance"
        response = requests.get(url)
        data = response.json()
        
        df = pd.DataFrame({
            'date': [datetime.now()],
            'dominance': [data['bitcoin_dominance']]
        })
        df.set_index('date', inplace=True)
        
        return df
        
    except Exception as e:
        logger.error(f"Ошибка при получении данных о доминировании Bitcoin: {str(e)}")
        return None

def get_network_hashrate() -> Optional[pd.DataFrame]:
    """
    Получение данных о хешрейте сети Bitcoin
    """
    try:
        url = "https://api.blockchain.info/charts/hash-rate?timespan=all&format=json"
        response = requests.get(url)
        data = response.json()
        
        df = pd.DataFrame(data['values'])
        df['date'] = pd.to_datetime(df['x'], unit='s')
        df.rename(columns={'y': 'hashrate'}, inplace=True)
        df.set_index('date', inplace=True)
        df.drop('x', axis=1, inplace=True)
        
        return df
        
    except Exception as e:
        logger.error(f"Ошибка при получении данных о хешрейте: {str(e)}")
        return None

def get_network_difficulty() -> Optional[pd.DataFrame]:
    """
    Получение данных о сложности майнинга Bitcoin
    """
    try:
        url = "https://api.blockchain.info/charts/difficulty?timespan=all&format=json"
        response = requests.get(url)
        data = response.json()
        
        df = pd.DataFrame(data['values'])
        df['date'] = pd.to_datetime(df['x'], unit='s')
        df.rename(columns={'y': 'difficulty'}, inplace=True)
        df.set_index('date', inplace=True)
        df.drop('x', axis=1, inplace=True)
        
        return df
        
    except Exception as e:
        logger.error(f"Ошибка при получении данных о сложности: {str(e)}")
        return None
