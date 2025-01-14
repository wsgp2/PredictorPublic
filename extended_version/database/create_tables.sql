-- Создание таблицы для данных о ценах
CREATE TABLE IF NOT EXISTS price_data (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    value DOUBLE PRECISION NOT NULL,
    UNIQUE(timestamp)
);

-- Создание таблицы для рыночных данных
CREATE TABLE IF NOT EXISTS market_data (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    volume DOUBLE PRECISION,
    market_cap DOUBLE PRECISION,
    liquidations DOUBLE PRECISION,
    orderbook_imbalance_0_01 DOUBLE PRECISION,
    orderbook_imbalance_0_03 DOUBLE PRECISION,
    orderbook_imbalance_0_05 DOUBLE PRECISION,
    bitcoin_rainbow_v2 DOUBLE PRECISION,
    hodl_waves_1_year DOUBLE PRECISION,
    hodl_waves DOUBLE PRECISION,
    mvrv_zscore DOUBLE PRECISION,
    relative_unrealized_prof DOUBLE PRECISION,
    bitcoin_price_prediction DOUBLE PRECISION,
    reserve_risk DOUBLE PRECISION,
    rhodl_ratio DOUBLE PRECISION,
    whale_shadows DOUBLE PRECISION,
    UNIQUE(timestamp)
);

-- Создание таблицы для данных о Long/Short позициях
CREATE TABLE IF NOT EXISTS longshort_data (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    timeframe VARCHAR(20) NOT NULL,
    long_account_ratio DOUBLE PRECISION,
    short_account_ratio DOUBLE PRECISION,
    long_position_ratio DOUBLE PRECISION,
    short_position_ratio DOUBLE PRECISION,
    long_person_ratio DOUBLE PRECISION,
    short_person_ratio DOUBLE PRECISION,
    UNIQUE(timestamp, symbol, timeframe)
);

-- Создание таблицы для технических индикаторов
CREATE TABLE IF NOT EXISTS technical_indicators (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    rsi DOUBLE PRECISION,
    macd DOUBLE PRECISION,
    macd_signal DOUBLE PRECISION,
    macd_hist DOUBLE PRECISION,
    bb_upper DOUBLE PRECISION,
    bb_middle DOUBLE PRECISION,
    bb_lower DOUBLE PRECISION,
    ma_20 DOUBLE PRECISION,
    ma_50 DOUBLE PRECISION,
    ma_200 DOUBLE PRECISION,
    volume_sma DOUBLE PRECISION,
    obv DOUBLE PRECISION,
    UNIQUE(timestamp)
);

-- Создание таблицы для метрик блокчейна
CREATE TABLE IF NOT EXISTS on_chain_metrics (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    avg_block_size DOUBLE PRECISION,
    confirmed_transactions DOUBLE PRECISION,
    cost_per_transaction DOUBLE PRECISION,
    difficulty DOUBLE PRECISION,
    median_confirmation_time DOUBLE PRECISION,
    mempool_size DOUBLE PRECISION,
    transaction_fees DOUBLE PRECISION,
    transactions_per_block DOUBLE PRECISION,
    utxo_count DOUBLE PRECISION,
    UNIQUE(timestamp)
);

-- Создание таблицы для метрик настроений
CREATE TABLE IF NOT EXISTS sentiment_metrics (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    fear_and_greed_index DOUBLE PRECISION,
    social_volume DOUBLE PRECISION,
    social_dominance DOUBLE PRECISION,
    social_sentiment DOUBLE PRECISION,
    UNIQUE(timestamp)
);

-- Создание таблицы для связанных активов
CREATE TABLE IF NOT EXISTS related_assets (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    open DOUBLE PRECISION NOT NULL,
    high DOUBLE PRECISION NOT NULL,
    low DOUBLE PRECISION NOT NULL,
    close DOUBLE PRECISION NOT NULL,
    volume DOUBLE PRECISION NOT NULL,
    UNIQUE(timestamp, symbol)
);

-- Создание таблицы для новостных данных
CREATE TABLE IF NOT EXISTS news_data (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    source VARCHAR(100) NOT NULL,
    title TEXT NOT NULL,
    url TEXT NOT NULL,
    sentiment DOUBLE PRECISION,
    UNIQUE(timestamp, url)
);

-- Создание индексов для оптимизации запросов
CREATE INDEX IF NOT EXISTS idx_price_data_timestamp ON price_data(timestamp);
CREATE INDEX IF NOT EXISTS idx_market_data_timestamp ON market_data(timestamp);
CREATE INDEX IF NOT EXISTS idx_longshort_data_timestamp ON longshort_data(timestamp);
CREATE INDEX IF NOT EXISTS idx_technical_indicators_timestamp ON technical_indicators(timestamp);
CREATE INDEX IF NOT EXISTS idx_on_chain_metrics_timestamp ON on_chain_metrics(timestamp);
CREATE INDEX IF NOT EXISTS idx_sentiment_metrics_timestamp ON sentiment_metrics(timestamp);
CREATE INDEX IF NOT EXISTS idx_related_assets_timestamp ON related_assets(timestamp);
CREATE INDEX IF NOT EXISTS idx_news_data_timestamp ON news_data(timestamp);
