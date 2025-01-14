-- Создание таблицы для данных о ценах
CREATE TABLE IF NOT EXISTS price_data (
    timestamp TIMESTAMP PRIMARY KEY,
    value DECIMAL(30, 8) NOT NULL
);

-- Создание таблицы для on-chain метрик
CREATE TABLE IF NOT EXISTS on_chain_metrics (
    timestamp TIMESTAMP PRIMARY KEY,
    active_addresses BIGINT,
    transaction_count BIGINT,
    mempool_size BIGINT,
    mining_difficulty DECIMAL(30, 8),
    transaction_fees DECIMAL(30, 8),
    utxo_count BIGINT,
    avg_block_size DECIMAL(30, 8),
    block_interval DECIMAL(30, 8)
);

-- Создание таблицы для рыночных данных
CREATE TABLE IF NOT EXISTS market_data (
    timestamp TIMESTAMP PRIMARY KEY,
    market_cap DECIMAL(30, 8),
    volume DECIMAL(30, 8),
    miners_revenue DECIMAL(30, 8),
    network_volume DECIMAL(30, 8),
    network_volume_usd DECIMAL(30, 8)
);

-- Создание таблицы для метрик настроений
CREATE TABLE IF NOT EXISTS sentiment_metrics (
    timestamp TIMESTAMP PRIMARY KEY,
    fear_greed_index INTEGER,
    social_volume BIGINT,
    social_sentiment DECIMAL(5, 2),
    google_trends INTEGER,
    twitter_volume BIGINT,
    reddit_posts INTEGER,
    reddit_comments INTEGER,
    github_activity INTEGER
);

-- Создание таблицы для данных Long/Short позиций
CREATE TABLE IF NOT EXISTS longshort_data (
    timestamp TIMESTAMP,
    symbol VARCHAR(10),
    timeframe VARCHAR(3),
    long_account_ratio DECIMAL(10, 4),
    short_account_ratio DECIMAL(10, 4),
    long_position_ratio DECIMAL(10, 4),
    short_position_ratio DECIMAL(10, 4),
    long_person_ratio DECIMAL(10, 4),
    short_person_ratio DECIMAL(10, 4),
    PRIMARY KEY (timestamp, symbol, timeframe)
);

-- Создание таблицы для данных связанных активов
CREATE TABLE IF NOT EXISTS related_assets (
    timestamp TIMESTAMP,
    symbol VARCHAR(10),
    open DECIMAL(20, 8),
    high DECIMAL(20, 8),
    low DECIMAL(20, 8),
    close DECIMAL(20, 8),
    volume DECIMAL(30, 8),
    PRIMARY KEY (timestamp, symbol)
);

-- Создание таблицы для новостей
CREATE TABLE IF NOT EXISTS news_data (
    timestamp TIMESTAMP,
    source VARCHAR(100),
    title TEXT,
    url TEXT,
    sentiment DECIMAL(5, 2),
    PRIMARY KEY (timestamp, url)
);

-- Создание индексов для оптимизации запросов
CREATE INDEX IF NOT EXISTS idx_price_data_timestamp ON price_data(timestamp);
CREATE INDEX IF NOT EXISTS idx_on_chain_metrics_timestamp ON on_chain_metrics(timestamp);
CREATE INDEX IF NOT EXISTS idx_market_data_timestamp ON market_data(timestamp);
CREATE INDEX IF NOT EXISTS idx_sentiment_metrics_timestamp ON sentiment_metrics(timestamp);
CREATE INDEX IF NOT EXISTS idx_longshort_data_timestamp ON longshort_data(timestamp);
CREATE INDEX IF NOT EXISTS idx_related_assets_timestamp ON related_assets(timestamp);
CREATE INDEX IF NOT EXISTS idx_news_data_timestamp ON news_data(timestamp);
