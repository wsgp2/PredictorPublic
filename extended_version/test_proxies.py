import requests
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_proxy(proxy_line):
    try:
        proxy_data = proxy_line.strip().split(':')
        if len(proxy_data) >= 4:
            ip, port, username, password = proxy_data[:4]
            proxy = {
                'http': f'http://{username}:{password}@{ip}:{port}',
                'https': f'http://{username}:{password}@{ip}:{port}'
            }
            
            start_time = time.time()
            response = requests.get('https://trends.google.com', 
                                 proxies=proxy, 
                                 timeout=10)
            end_time = time.time()
            
            if response.status_code == 200:
                logger.info(f"Proxy {ip}:{port} is working! Response time: {end_time - start_time:.2f} seconds")
                return True, ip, port, end_time - start_time
            else:
                logger.warning(f"Proxy {ip}:{port} returned status code {response.status_code}")
                return False, ip, port, None
    except Exception as e:
        logger.error(f"Error testing proxy {proxy_line.strip()}: {str(e)}")
        return False, ip, port, None

def main():
    working_proxies = []
    with open('config/proxies.txt', 'r') as f:
        proxy_lines = f.readlines()
    
    logger.info(f"Testing {len(proxy_lines)} proxies...")
    
    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_proxy = {executor.submit(test_proxy, line): line for line in proxy_lines}
        for future in as_completed(future_to_proxy):
            result = future.result()
            if result[0]:  # если прокси работает
                working_proxies.append((result[1], result[2], result[3]))  # ip, port, response_time
    
    # Сортируем прокси по времени отклика
    working_proxies.sort(key=lambda x: x[2])
    
    logger.info(f"\nResults:")
    logger.info(f"Total proxies tested: {len(proxy_lines)}")
    logger.info(f"Working proxies: {len(working_proxies)}")
    
    if working_proxies:
        logger.info("\nTop 5 fastest proxies:")
        for i, (ip, port, response_time) in enumerate(working_proxies[:5], 1):
            logger.info(f"{i}. {ip}:{port} - Response time: {response_time:.2f} seconds")
    
    # Создаем новый файл только с рабочими прокси
    if working_proxies:
        with open('config/working_proxies.txt', 'w') as f:
            for proxy_line in proxy_lines:
                ip = proxy_line.split(':')[0]
                if any(wp[0] == ip for wp in working_proxies):
                    f.write(proxy_line)
        logger.info(f"\nWorking proxies have been saved to config/working_proxies.txt")

if __name__ == "__main__":
    main()
