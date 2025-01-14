import requests
import concurrent.futures
import time

def test_proxy(proxy):
    proxy_auth = {
        'http': f'http://s1XEBbG35k:pelmen271296@{proxy}',
        'https': f'http://s1XEBbG35k:pelmen271296@{proxy}'
    }
    
    try:
        start_time = time.time()
        response = requests.get('http://httpbin.org/ip', proxies=proxy_auth, timeout=10)
        elapsed_time = time.time() - start_time
        
        if response.status_code == 200:
            return proxy, True, elapsed_time, response.json()
        return proxy, False, elapsed_time, "Bad status code"
    except Exception as e:
        return proxy, False, 0, str(e)

def main():
    # Читаем список прокси
    with open('proxy_list.txt', 'r') as f:
        proxies = [line.strip() for line in f if line.strip()]
    
    print(f"Тестируем {len(proxies)} прокси...")
    working_proxies = []
    
    # Тестируем каждый прокси параллельно
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        future_to_proxy = {executor.submit(test_proxy, proxy): proxy for proxy in proxies}
        
        for future in concurrent.futures.as_completed(future_to_proxy):
            proxy, success, elapsed_time, result = future.result()
            if success:
                print(f"✅ {proxy} - Работает! Время ответа: {elapsed_time:.2f}с")
                working_proxies.append(proxy)
            else:
                print(f"❌ {proxy} - Ошибка: {result}")
    
    print(f"\nИтого рабочих прокси: {len(working_proxies)} из {len(proxies)}")
    
    # Сохраняем рабочие прокси
    if working_proxies:
        with open('working_proxies.txt', 'w') as f:
            for proxy in working_proxies:
                f.write(f"{proxy}\n")
        print("Рабочие прокси сохранены в файл working_proxies.txt")

if __name__ == "__main__":
    main()
