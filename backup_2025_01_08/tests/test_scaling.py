import numpy as np
from sklearn.preprocessing import MinMaxScaler
import matplotlib.pyplot as plt

# Создаем тестовые данные
np.random.seed(42)
n_samples = 100
n_features = 12

# Генерируем случайные данные
data = np.random.randn(n_samples, n_features)
data[:, 0] = np.linspace(1000, 5000, n_samples)  # Первый столбец - цена закрытия

# Масштабирование
scaler = MinMaxScaler()
data_scaled = scaler.fit_transform(data)

# Имитируем предсказания (берем часть реальных данных)
train_size = 80
train_predict = data_scaled[10:train_size, 0].reshape(-1, 1)
test_predict = data_scaled[train_size:90, 0].reshape(-1, 1)

print("Размерности:")
print("train_predict:", train_predict.shape)
print("test_predict:", test_predict.shape)

# Создаем полные массивы для обратного преобразования
train_predict_full = np.zeros((len(train_predict), n_features))
test_predict_full = np.zeros((len(test_predict), n_features))

# Заполняем только первый столбец (цена закрытия)
train_predict_full[:, 0] = train_predict.flatten()
test_predict_full[:, 0] = test_predict.flatten()

# Обратное преобразование
train_predict_orig = scaler.inverse_transform(train_predict_full)[:, 0]
test_predict_orig = scaler.inverse_transform(test_predict_full)[:, 0]

# Создаем массивы для графика
train_plot = np.zeros(n_samples)
test_plot = np.zeros(n_samples)

# Заполняем массивы предсказаниями
look_back = 10
train_plot[look_back:len(train_predict)+look_back] = train_predict_orig
test_plot[len(train_predict)+look_back:90] = test_predict_orig

# Получаем оригинальные значения цены
price_orig = scaler.inverse_transform(data_scaled)[:, 0]

# Строим график
plt.figure(figsize=(15,6))
plt.plot(price_orig, label='Реальные значения')
plt.plot(train_plot, label='Предсказания на обучающей выборке')
plt.plot(test_plot, label='Предсказания на тестовой выборке')
plt.title('Тестовый график')
plt.legend()
plt.grid(True)
plt.show()

print("\nПроверка значений:")
print("Минимальная цена:", min(price_orig))
print("Максимальная цена:", max(price_orig))
print("Мин. предсказание (train):", min(train_predict_orig[train_predict_orig != 0]))
print("Макс. предсказание (train):", max(train_predict_orig))
print("Мин. предсказание (test):", min(test_predict_orig[test_predict_orig != 0]))
print("Макс. предсказание (test):", max(test_predict_orig))
