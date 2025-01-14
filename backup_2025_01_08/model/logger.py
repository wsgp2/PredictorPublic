"""
Настройка логирования для проекта
"""

import logging
import sys
from typing import Optional
from pathlib import Path

def setup_logger(name: str, 
                level: int = logging.INFO,
                log_file: Optional[str] = None) -> logging.Logger:
    """
    Настройка логгера
    
    Args:
        name: Имя логгера
        level: Уровень логирования
        log_file: Путь к файлу логов
        
    Returns:
        logging.Logger: Настроенный логгер
    """
    # Создаем логгер
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Форматирование
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Обработчик для консоли
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Обработчик для файла
    if log_file:
        # Создаем директорию для логов если её нет
        log_dir = Path(log_file).parent
        log_dir.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger
