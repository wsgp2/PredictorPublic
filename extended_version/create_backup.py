import os
import shutil
import datetime
import tarfile

def create_backup():
    # Создаем имя директории для бэкапа с текущей датой и временем
    backup_name = f"backup_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
    backup_dir = os.path.join("backups", backup_name)
    
    # Создаем директорию для бэкапа
    os.makedirs(backup_dir, exist_ok=True)
    
    # Копируем все Python файлы
    for file in os.listdir('.'):
        if file.endswith('.py'):
            shutil.copy2(file, backup_dir)
    
    # Копируем документацию
    for file in os.listdir('.'):
        if file.endswith('.md'):
            shutil.copy2(file, backup_dir)
    
    # Копируем requirements.txt если существует
    if os.path.exists('requirements.txt'):
        shutil.copy2('requirements.txt', backup_dir)
    
    # Копируем данные
    if os.path.exists('data'):
        shutil.copytree('data', os.path.join(backup_dir, 'data'))
    
    # Создаем архив
    with tarfile.open(f"{backup_dir}.tar.gz", "w:gz") as tar:
        tar.add(backup_dir, arcname=os.path.basename(backup_dir))
    
    # Удаляем временную директорию
    shutil.rmtree(backup_dir)
    
    print(f"Backup created: {backup_dir}.tar.gz")

if __name__ == "__main__":
    create_backup()
