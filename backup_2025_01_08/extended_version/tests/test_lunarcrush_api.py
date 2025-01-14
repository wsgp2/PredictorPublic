"""
LunarCrush API v4 Тестер
========================

Документация по эндпоинтам:

1. Категории (Categories)
------------------------
- GET /public/categories/list/v1
  Получение списка трендовых социальных категорий
  
- GET /public/category/:category/creators/v1
  Получение топ-создателей контента для категории
  Параметры: category (str) - название категории
  
- GET /public/category/:category/news/v1
  Получение топ-новостей для категории
  Параметры: category (str) - название категории
  
- GET /public/category/:category/posts/v1
  Получение топ-постов для категории
  Параметры: 
  - category (str) - название категории
  - start (timestamp) - начальное время
  - end (timestamp) - конечное время
  
- GET /public/category/:category/time-series/v1
  Получение исторических данных для категории
  Параметры:
  - category (str) - название категории
  - bucket (str) - группировка (hour/day)
  - interval (str) - интервал (1d,1w,1m,3m,6m,1y,5y,all)
  - start (timestamp) - начальное время
  - end (timestamp) - конечное время

- GET /public/category/:category/topics/v1
  Получение топ-тем для категории
  Параметры: category (str) - название категории

- GET /public/category/:category/v1
  Получение сводной информации по категории
  Параметры: category (str) - название категории

2. Криптовалюты (Coins)
----------------------
- GET /public/coins/:coin/meta/v1
  Получение мета-информации о криптовалюте
  Параметры: coin (str) - символ или ID монеты

- GET /public/coins/:coin/time-series/v2
  Получение исторических данных по криптовалюте
  Параметры:
  - coin (str) - символ или ID монеты
  - bucket (str) - группировка (hour/day)
  - interval (str) - интервал (1d,1w,1m,3m,6m,1y,5y,all)
  - start (timestamp) - начальное время
  - end (timestamp) - конечное время

- GET /public/coins/:coin/v1
  Получение текущих данных по криптовалюте
  Параметры: coin (str) - символ или ID монеты
"""

import requests
import json
from datetime import datetime, timedelta
import pandas as pd

class LunarCrushAPITester:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://lunarcrush.com/api4/public"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json"
        }

    def test_endpoint(self, endpoint, params=None, description=""):
        """Тестирование эндпоинта с выводом результатов"""
        url = f"{self.base_url}/{endpoint}"
        try:
            print(f"\nТестирование: {description}")
            print(f"URL: {url}")
            print(f"Параметры: {params}")
            
            response = requests.get(url, headers=self.headers, params=params)
            
            print(f"Status Code: {response.status_code}")
            if response.status_code == 200:
                print("✅ Успешно!")
                data = response.json()
                print(f"Получено полей: {len(data) if data else 0}")
                return data
            else:
                print(f"❌ Ошибка: {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Исключение: {str(e)}")
            return None

    def analyze_data(self, data, prefix=""):
        """Анализ структуры данных"""
        if not data:
            return
            
        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, (dict, list)):
                    print(f"{prefix}- {key} ({type(value).__name__})")
                    self.analyze_data(value, prefix + "  ")
                else:
                    print(f"{prefix}- {key}: {type(value).__name__}")
        elif isinstance(data, list) and len(data) > 0:
            print(f"{prefix}Список из {len(data)} элементов:")
            self.analyze_data(data[0], prefix + "  ")

    def test_all_endpoints(self):
        """Тестирование всех доступных эндпоинтов v4"""
        
        print("\n=== Тестирование LunarCrush API v4 ===")
        
        # 1. Категории
        print("\n=== Тестирование Categories API ===")
        
        # 1.1 Список категорий
        categories = self.test_endpoint(
            'categories/list/v1',
            description="Получение списка категорий"
        )
        
        print("\nСтруктура данных категорий:")
        self.analyze_data(categories.get('data'))
        
        # Если получили категории, используем первую для тестирования
        if categories and categories.get('data'):
            # Используем 'cryptocurrencies' как тестовую категорию
            category = "cryptocurrencies"
            
            # 1.2 Создатели контента категории
            self.test_endpoint(
                f'category/{category}/creators/v1',
                description=f"Топ-создатели для категории {category}"
            )
            
            # 1.3 Новости категории
            self.test_endpoint(
                f'category/{category}/news/v1',
                description=f"Топ-новости для категории {category}"
            )
            
            # 1.4 Посты категории с подробным анализом
            print("\nПодробный анализ постов категории:")
            posts_data = self.test_endpoint(
                f'category/{category}/posts/v1',
                {
                    'start': int((datetime.now() - timedelta(days=1)).timestamp()),
                    'end': int(datetime.now().timestamp())
                },
                description=f"Топ-посты для категории {category}"
            )
            if posts_data:
                print("\nСтруктура данных постов:")
                self.analyze_data(posts_data.get('data'))

            # 1.5 Временные ряды категории с подробным анализом
            print("\nПодробный анализ временных рядов категории:")
            timeseries_data = self.test_endpoint(
                f'category/{category}/time-series/v1',
                {
                    'bucket': 'hour',  # почасовые данные
                    'interval': '1d'   # за последний день
                },
                description=f"Исторические данные для категории {category}"
            )
            if timeseries_data:
                print("\nСтруктура временных рядов категории:")
                self.analyze_data(timeseries_data.get('data'))
            
            # 1.6 Темы категории
            self.test_endpoint(
                f'category/{category}/topics/v1',
                description=f"Топ-темы для категории {category}"
            )
            
            # 1.7 Сводная информация по категории
            self.test_endpoint(
                f'category/{category}/v1',
                description=f"Сводная информация по категории {category}"
            )
        
        # 2. Криптовалюты
        print("\n=== Тестирование Coins API ===")
        
        # 2.1 Мета-информация
        meta_data = self.test_endpoint(
            'coins/BTC/meta/v1',
            description="Мета-информация по Bitcoin"
        )
        
        # 2.2 Исторические данные
        now = datetime.now()
        historical_data = self.test_endpoint(
            'coins/BTC/time-series/v2',
            {
                'interval': '1d',
                'bucket': 'day',
                'start': int((now - timedelta(days=30)).timestamp()),
                'end': int(now.timestamp())
            },
            description="Исторические данные по Bitcoin"
        )
        
        # 2.3 Текущие данные
        current_data = self.test_endpoint(
            'coins/BTC/v1',
            description="Текущие данные по Bitcoin"
        )

        # Анализ структуры данных
        if current_data:
            print("\nСтруктура текущих данных Bitcoin:")
            self.analyze_data(current_data.get('data'))

        if historical_data:
            print("\nСтруктура исторических данных Bitcoin:")
            self.analyze_data(historical_data.get('data'))

        if meta_data:
            print("\nСтруктура мета-данных Bitcoin:")
            self.analyze_data(meta_data.get('data'))

def main():
    api_key = "czj05lqp91si9h16b975gtgbe2m5nblt367frwltf"
    tester = LunarCrushAPITester(api_key)
    tester.test_all_endpoints()

if __name__ == "__main__":
    main()
