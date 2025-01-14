import praw
import pandas as pd
from datetime import datetime
import time
import logging
import os
import requests
import urllib3
import ssl

# Отключаем проверку SSL
ssl._create_default_https_context = ssl._create_unverified_context

# Отключаем предупреждения о небезопасных SSL соединениях
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class RedditDataCollector:
    def __init__(self, client_id, client_secret, user_agent):
        """Инициализация коллектора данных Reddit"""
        try:
            # Создаем сессию с отключенной проверкой SSL
            session = requests.Session()
            session.verify = False
            
            self.reddit = praw.Reddit(
                client_id=client_id,
                client_secret=client_secret,
                user_agent=user_agent,
                requestor_kwargs={'session': session},
                check_for_updates=False,
                read_only=True  # Устанавливаем режим только для чтения
            )
            logger.info("Reddit клиент успешно инициализирован")
        except Exception as e:
            logger.error(f"Ошибка при инициализации Reddit клиента: {str(e)}")
            raise Exception("Не удалось инициализировать Reddit клиент")

    def collect_posts(self, subreddit_name, limit=100):
        """Сбор постов из указанного сабреддита"""
        try:
            posts_data = []
            subreddit = self.reddit.subreddit(subreddit_name)
            
            # Получаем новые посты
            for post in subreddit.new(limit=limit):
                try:
                    posts_data.append({
                        'id': post.id,
                        'title': post.title,
                        'score': post.score,
                        'num_comments': post.num_comments,
                        'created_utc': datetime.fromtimestamp(post.created_utc),
                        'upvote_ratio': post.upvote_ratio,
                        'url': post.url,
                        'selftext': post.selftext,
                        'subreddit': subreddit_name
                    })
                except Exception as e:
                    logger.warning(f"Ошибка при обработке поста {post.id}: {str(e)}")
                    continue

            df = pd.DataFrame(posts_data)
            logger.info(f"Собрано {len(posts_data)} постов из r/{subreddit_name}")
            return df

        except Exception as e:
            logger.error(f"Ошибка при сборе постов из r/{subreddit_name}: {str(e)}")
            return pd.DataFrame()

    def collect_comments(self, subreddit_name, limit=100):
        """Сбор комментариев из указанного сабреддита"""
        try:
            # Сначала получаем посты
            posts_df = self.collect_posts(subreddit_name, limit)
            if posts_df.empty:
                return pd.DataFrame()

            comments_data = []
            for post_id in posts_df['id']:
                try:
                    submission = self.reddit.submission(id=post_id)
                    submission.comments.replace_more(limit=0)  # Убираем "load more comments"
                    
                    for comment in submission.comments.list():
                        try:
                            comments_data.append({
                                'id': comment.id,
                                'post_id': post_id,
                                'body': comment.body,
                                'score': comment.score,
                                'created_utc': datetime.fromtimestamp(comment.created_utc),
                                'subreddit': subreddit_name
                            })
                        except Exception as e:
                            logger.warning(f"Ошибка при обработке комментария в посте {post_id}: {str(e)}")
                            continue
                except Exception as e:
                    logger.warning(f"Ошибка при обработке комментариев поста {post_id}: {str(e)}")
                    continue

            df = pd.DataFrame(comments_data)
            logger.info(f"Собрано {len(comments_data)} комментариев из r/{subreddit_name}")
            return df

        except Exception as e:
            logger.error(f"Ошибка при сборе комментариев из r/{subreddit_name}: {str(e)}")
            return pd.DataFrame()

def main():
    # Конфигурация Reddit API
    client_id = "V1RELyHRCtfeZr1WVHhm2g"
    client_secret = "pJEzl1t3axsTuBucAGE2ZTfgIke-LQ"
    user_agent = "script:BitcoinPricePredictor:1.0 (by /u/DyshkantSer)"

    # Список сабреддитов для сбора данных
    subreddits = ['bitcoin', 'cryptocurrency', 'CryptoMarkets', 'BitcoinMarkets']
    
    # Создаем директорию для сохранения данных
    data_dir = 'reddit_data'
    os.makedirs(data_dir, exist_ok=True)

    # Инициализация коллектора
    collector = RedditDataCollector(client_id, client_secret, user_agent)

    # Текущая дата для именования файлов
    current_date = datetime.now().strftime('%Y%m%d')

    # Сбор данных из каждого сабреддита
    for subreddit in subreddits:
        # Сбор постов
        posts_df = collector.collect_posts(subreddit)
        if not posts_df.empty:
            posts_df.to_csv(f'{data_dir}/{subreddit}_posts_{current_date}.csv', index=False)
            logger.info(f"Посты из r/{subreddit} сохранены")

        # Сбор комментариев
        comments_df = collector.collect_comments(subreddit)
        if not comments_df.empty:
            comments_df.to_csv(f'{data_dir}/{subreddit}_comments_{current_date}.csv', index=False)
            logger.info(f"Комментарии из r/{subreddit} сохранены")

        # Небольшая задержка между запросами
        time.sleep(2)

if __name__ == "__main__":
    main()
