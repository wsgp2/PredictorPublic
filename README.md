# Прогнозирование цены Bitcoin с использованием LSTM

Проект по предсказанию цены Bitcoin с использованием нейронной сети LSTM, технических индикаторов и индекса страха и жадности.

## Особенности

- Использование LSTM (Long Short-Term Memory) для прогнозирования
- Расширенный набор технических индикаторов:
  - RSI (Relative Strength Index)
  - MACD (Moving Average Convergence Divergence)
  - OBV (On-Balance Volume)
- Учет индекса страха и жадности (Fear and Greed Index)
- Улучшенная нормализация данных для точных предсказаний
- Визуализация результатов прогнозирования с сохранением графиков
- Автоматическое сохранение обученной модели
- Проверка размерности входных данных для надежности предсказаний

## Требования

```
numpy==1.24.3
pandas==2.1.0
yfinance
scikit-learn==1.3.0
tensorflow==2.13.0
matplotlib==3.7.2
requests
keras==2.13.1
```

## Установка

1. Клонируйте репозиторий
2. Установите зависимости:
```bash
pip install -r requirements.txt
```

## Использование

Запустите скрипт:
```bash
python bitcoin_prediction.py
```

Скрипт выполнит следующие действия:
1. Загрузит исторические данные о цене Bitcoin
2. Получит данные индекса страха и жадности
3. Рассчитает технические индикаторы
4. Обучит LSTM модель
5. Создаст и сохранит графики:
   - `prediction_results.png` - график реальных данных и предсказаний
   - `training_history.png` - график процесса обучения
6. Сохранит обученную модель в директории `model`
7. Сделает прогноз цены на следующие 7 дней

## Структура проекта

- `bitcoin_prediction.py` - основной скрипт с реализацией модели
- `requirements.txt` - файл зависимостей
- `model/` - директория для сохранения обученной модели
- `prediction_results.png` - график результатов предсказания
- `training_history.png` - график процесса обучения
- `README.md` - документация проекта
- `CHANGELOG.md` - история изменений

## Результаты

Модель учитывает следующие параметры:
- Цена закрытия Bitcoin
- Объем торгов
- Индекс страха и жадности
- Технические индикаторы (RSI, MACD, OBV)

Результаты визуализируются в двух графиках:
1. График предсказаний (`prediction_results.png`):
   - Реальные данные
   - Предсказания на обучающей выборке
   - Предсказания на тестовой выборке
   - Прогноз на следующие 7 дней

2. График обучения (`training_history.png`):
   - Ошибка на обучающей выборке
   - Ошибка на проверочной выборке

## Точность модели

- Модель использует расширенный набор технических индикаторов для улучшения точности предсказаний
- Проверка размерности входных данных обеспечивает надежность предсказаний
- Улучшенная нормализация данных помогает модели лучше обрабатывать различные масштабы признаков

## Лицензия

MIT License

Copyright (c) 2020 Siddhant Golangade

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
