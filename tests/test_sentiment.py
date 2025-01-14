"""
Тестирование анализа настроений
"""
from datetime import datetime, timedelta
from sentiment_analysis import SentimentAnalyzer
from config import REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET

def main():
    # Создаем анализатор
    analyzer = SentimentAnalyzer()
    
    # Инициализируем Reddit
    analyzer.initialize_reddit(REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET)
    
    # Устанавливаем период анализа
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)
    
    # Получаем признаки
    features = analyzer.prepare_sentiment_features(start_date, end_date)
    
    print("\nГотово! Проверьте файлы логов в директории logs/")

if __name__ == "__main__":
    main()
