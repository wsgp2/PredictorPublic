#!/bin/bash

# Создаем директорию для бэкапа с текущей датой
BACKUP_DIR="backups/backup_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

# Копируем все Python файлы
cp *.py "$BACKUP_DIR/"

# Копируем документацию
cp *.md "$BACKUP_DIR/"

# Копируем данные
cp -r data "$BACKUP_DIR/"

# Копируем requirements.txt если существует
if [ -f requirements.txt ]; then
    cp requirements.txt "$BACKUP_DIR/"
fi

# Создаем архив
tar -czf "${BACKUP_DIR}.tar.gz" "$BACKUP_DIR"

# Удаляем временную директорию
rm -rf "$BACKUP_DIR"

echo "Backup created: ${BACKUP_DIR}.tar.gz"
