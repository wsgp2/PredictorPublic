-- CoinArk таблицы
CREATE TABLE IF NOT EXISTS longshort_data (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    long_short_ratio FLOAT,
    long_account_ratio FLOAT,
    short_account_ratio FLOAT,
    exchange VARCHAR(50),
    UNIQUE(timestamp, symbol, exchange)
);

CREATE TABLE IF NOT EXISTS market_data (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    open_price FLOAT,
    high_price FLOAT,
    low_price FLOAT,
    close_price FLOAT,
    volume FLOAT,
    exchange VARCHAR(50),
    UNIQUE(timestamp, symbol, exchange)
);

CREATE TABLE IF NOT EXISTS funding_rate_data (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    funding_rate FLOAT,
    exchange VARCHAR(50),
    UNIQUE(timestamp, symbol, exchange)
);

-- Yahoo Finance таблицы
CREATE TABLE IF NOT EXISTS yahoo_stock_data (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    open_price FLOAT,
    high_price FLOAT,
    low_price FLOAT,
    close_price FLOAT,
    adj_close FLOAT,
    volume BIGINT,
    UNIQUE(timestamp, symbol)
);

-- FRED таблицы
CREATE TABLE IF NOT EXISTS fred_economic_data (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    indicator_code VARCHAR(50) NOT NULL,
    value FLOAT,
    UNIQUE(timestamp, indicator_code)
);

-- LunarCrush таблицы
CREATE TABLE IF NOT EXISTS lunarcrush_social_data (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    social_volume INT,
    social_score FLOAT,
    social_engagement INT,
    tweet_volume INT,
    tweet_sentiment FLOAT,
    reddit_volume INT,
    reddit_sentiment FLOAT,
    UNIQUE(timestamp, symbol)
);

-- Blockchain таблицы
CREATE TABLE IF NOT EXISTS blockchain_network_data (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    hash_rate FLOAT,
    difficulty FLOAT,
    transaction_volume FLOAT,
    active_addresses INT,
    transaction_count INT,
    average_transaction_fee FLOAT,
    mempool_size INT,
    UNIQUE(timestamp)
);

-- Индексы для оптимизации запросов
CREATE INDEX IF NOT EXISTS idx_longshort_timestamp ON longshort_data(timestamp);
CREATE INDEX IF NOT EXISTS idx_market_timestamp ON market_data(timestamp);
CREATE INDEX IF NOT EXISTS idx_funding_timestamp ON funding_rate_data(timestamp);
CREATE INDEX IF NOT EXISTS idx_yahoo_timestamp ON yahoo_stock_data(timestamp);
CREATE INDEX IF NOT EXISTS idx_fred_timestamp ON fred_economic_data(timestamp);
CREATE INDEX IF NOT EXISTS idx_lunarcrush_timestamp ON lunarcrush_social_data(timestamp);
CREATE INDEX IF NOT EXISTS idx_blockchain_timestamp ON blockchain_network_data(timestamp);
