import psycopg2
import logging
from typing import Optional, Any, List, Dict
import os
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Настройка логирования
logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self, db_name=None, db_user=None, db_password=None, db_host=None, db_port=None):
        """Инициализация менеджера базы данных"""
        self.db_name = db_name or os.getenv('DB_NAME', 'bitcoin_predictor')
        self.db_user = db_user or os.getenv('DB_USER', 'postgres')
        self.db_password = db_password or os.getenv('DB_PASSWORD', 'postgres')
        self.db_host = db_host or os.getenv('DB_HOST', 'localhost')
        self.db_port = db_port or os.getenv('DB_PORT', '5432')
        
        self.conn = None
        self.cursor = None
        self.connect()

    def connect(self):
        """Установка соединения с базой данных"""
        try:
            self.conn = psycopg2.connect(
                dbname=self.db_name,
                user=self.db_user,
                password=self.db_password,
                host=self.db_host,
                port=self.db_port
            )
            self.cursor = self.conn.cursor()
            logger.info("Database connection established")
        except Exception as e:
            logger.error(f"Error connecting to database: {str(e)}")
            raise
            
    def disconnect(self):
        """Закрытие соединения с базой данных"""
        if self.conn:
            self.conn.close()
            self.conn = None
            logger.info("Database connection closed")
            
    def __del__(self):
        """Деструктор для закрытия соединения при удалении объекта"""
        self.disconnect()

    def execute_query(self, query: str, params: Optional[tuple] = None) -> None:
        """
        Выполнение SQL запроса
        
        Args:
            query: SQL запрос
            params: Параметры запроса (опционально)
        """
        try:
            if not self.conn or self.conn.closed:
                self.connect()
                
            if params:
                self.cursor.execute(query, params)
            else:
                self.cursor.execute(query)
                
            self.conn.commit()
            
        except Exception as e:
            self.conn.rollback()
            raise Exception(f"Error executing query: {str(e)}")

    def fetch_all(self) -> List[tuple]:
        """
        Получение всех результатов запроса
        
        Returns:
            Список кортежей с результатами
        """
        return self.cursor.fetchall()

    def fetch_one(self) -> Optional[tuple]:
        """
        Получение одной строки результата
        
        Returns:
            Кортеж с результатом или None
        """
        return self.cursor.fetchone()
