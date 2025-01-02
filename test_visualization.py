import numpy as np
import pandas as pd
import yfinance as yf
from sklearn.preprocessing import MinMaxScaler
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

# Загрузка данных
def get_test_data():
    # Получаем те же данные, что и в основном скрипте
    btc = yf.download('BTC-USD', start='2020-01-01', end='2023-12-31')
    data = btc[['Close', 'Volume']].copy()
    
    # Нормализация данных
    scaler = MinMaxScaler(feature_range=(0, 1))
    dataset = scaler.fit_transform(data)
    
    # Разделение на тренировочную и тестовую выборки (80/20)
    train_size = int(len(dataset) * 0.8)
    train = dataset[0:train_size, :]
    test = dataset[train_size:len(dataset), :]
    
    # Создаем простые синтетические предсказания
    # для тренировочной выборки (просто немного смещаем реальные данные)
    train_predict = train[:-1, 0].reshape(-1, 1)
    
    # для тестовой выборки
    test_predict = test[:-1, 0].reshape(-1, 1)
    
    return dataset, train_predict, test_predict, scaler

def plot_test_results(dataset, train_predict, test_predict, scaler):
    # Создаем пустые массивы для предсказаний
    train_predict_plot = np.zeros_like(dataset)
    test_predict_plot = np.zeros_like(dataset)
    
    # Подготавливаем данные для обратного преобразования
    train_predict_full = np.zeros((len(train_predict), dataset.shape[1]))
    test_predict_full = np.zeros((len(test_predict), dataset.shape[1]))
    
    # Заполняем первый столбец (Close price) предсказаниями
    train_predict_full[:, 0] = train_predict.flatten()
    test_predict_full[:, 0] = test_predict.flatten()
    
    # Обратное преобразование
    train_predict = scaler.inverse_transform(train_predict_full)[:, 0]
    test_predict = scaler.inverse_transform(test_predict_full)[:, 0]
    
    # Определяем индексы для размещения предсказаний
    train_size = int(len(dataset) * 0.8)
    
    # Заполняем массивы предсказаниями
    train_predict_plot[1:train_size, 0] = train_predict
    test_predict_plot[train_size:-1, 0] = test_predict
    
    # Обратное преобразование реальных значений
    dataset_orig = scaler.inverse_transform(dataset)[:, 0]
    
    # Создаем график
    plt.figure(figsize=(15,6))
    plt.plot(dataset_orig, 'b-', label='Реальные значения', linewidth=2)
    plt.plot(train_predict_plot[:, 0], 'r--', label='Предсказания на обучающей выборке', linewidth=2)
    plt.plot(test_predict_plot[:, 0], 'g--', label='Предсказания на тестовой выборке', linewidth=2)
    plt.title('Тестовая визуализация предсказания цены биткойна', fontsize=14, pad=20)
    plt.xlabel('Дни', fontsize=12)
    plt.ylabel('Цена (USD)', fontsize=12)
    plt.legend(fontsize=10)
    plt.grid(True, linestyle='--', alpha=0.7)
    
    # Настраиваем внешний вид графика
    plt.gca().spines['top'].set_visible(False)
    plt.gca().spines['right'].set_visible(False)
    
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    # Получаем тестовые данные
    dataset, train_predict, test_predict, scaler = get_test_data()
    
    # Визуализируем результаты
    plot_test_results(dataset, train_predict, test_predict, scaler)
