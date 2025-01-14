-- Создаем базу данных
CREATE DATABASE bitcoin_prediction;

\c bitcoin_prediction;

-- Основные ценовые данные
CREATE TABLE price_data (
    timestamp TIMESTAMPTZ NOT NULL,
    open DECIMAL,
    high DECIMAL,
    low DECIMAL,
    close DECIMAL,
    volume DECIMAL
);

-- Создаем индекс по временной метке
CREATE INDEX idx_price_timestamp ON price_data(timestamp);

-- Технические индикаторы
CREATE TABLE technical_indicators (
    timestamp TIMESTAMPTZ NOT NULL,
    rsi DECIMAL,
    macd DECIMAL,
    macd_signal DECIMAL,
    macd_hist DECIMAL,
    bb_upper DECIMAL,
    bb_middle DECIMAL,
    bb_lower DECIMAL,
    ma_20 DECIMAL,
    ma_50 DECIMAL,
    ma_200 DECIMAL,
    volume_sma DECIMAL,
    obv DECIMAL
);

CREATE INDEX idx_tech_timestamp ON technical_indicators(timestamp);

-- Данные блокчейна
CREATE TABLE on_chain_metrics (
    timestamp TIMESTAMPTZ NOT NULL,
    active_addresses INTEGER,
    transaction_count INTEGER,
    mempool_size INTEGER,
    mining_difficulty DECIMAL,
    transaction_fees DECIMAL,
    utxo_count INTEGER,
    avg_block_size DECIMAL,
    avg_transaction_size DECIMAL,
    block_interval DECIMAL
);

CREATE INDEX idx_chain_timestamp ON on_chain_metrics(timestamp);

-- Данные о настроениях
CREATE TABLE sentiment_metrics (
    timestamp TIMESTAMPTZ NOT NULL,
    fear_greed_index INTEGER,
    social_volume INTEGER,
    social_sentiment DECIMAL,
    google_trends INTEGER,
    twitter_volume INTEGER,
    reddit_posts INTEGER,
    reddit_comments INTEGER,
    github_activity INTEGER
);

CREATE INDEX idx_sentiment_timestamp ON sentiment_metrics(timestamp);

-- Макроэкономические показатели
CREATE TABLE macro_indicators (
    timestamp TIMESTAMPTZ NOT NULL,
    sp500 DECIMAL,
    nasdaq DECIMAL,
    gold_price DECIMAL,
    silver_price DECIMAL,
    dxy_index DECIMAL,
    us_interest_rate DECIMAL,
    us_inflation_rate DECIMAL,
    vix DECIMAL,
    us_unemployment DECIMAL,
    us_gdp_growth DECIMAL
);

CREATE INDEX idx_macro_timestamp ON macro_indicators(timestamp);

-- Данные деривативов
CREATE TABLE derivatives_data (
    timestamp TIMESTAMPTZ NOT NULL,
    exchange VARCHAR(50),
    open_interest DECIMAL,
    long_short_ratio DECIMAL,
    funding_rate DECIMAL,
    liquidations_long DECIMAL,
    liquidations_short DECIMAL,
    total_volume_24h DECIMAL,
    futures_volume DECIMAL,
    options_volume DECIMAL
);

CREATE INDEX idx_derivatives_timestamp ON derivatives_data(timestamp);

-- Создаем представление для корреляционного анализа
CREATE VIEW correlations_view AS
WITH combined_data AS (
    SELECT 
        p.timestamp,
        p.close as price,
        t.rsi,
        t.macd,
        o.active_addresses,
        o.transaction_count,
        s.fear_greed_index,
        s.social_sentiment,
        m.sp500,
        m.dxy_index,
        d.open_interest,
        d.long_short_ratio
    FROM price_data p
    LEFT JOIN technical_indicators t ON date_trunc('hour', p.timestamp) = date_trunc('hour', t.timestamp)
    LEFT JOIN on_chain_metrics o ON date_trunc('hour', p.timestamp) = date_trunc('hour', o.timestamp)
    LEFT JOIN sentiment_metrics s ON date_trunc('hour', p.timestamp) = date_trunc('hour', s.timestamp)
    LEFT JOIN macro_indicators m ON date_trunc('hour', p.timestamp) = date_trunc('hour', m.timestamp)
    LEFT JOIN derivatives_data d ON date_trunc('hour', p.timestamp) = date_trunc('hour', d.timestamp)
)
SELECT 
    corr(price, rsi) as price_rsi_corr,
    corr(price, macd) as price_macd_corr,
    corr(price, active_addresses) as price_addresses_corr,
    corr(price, transaction_count) as price_transactions_corr,
    corr(price, fear_greed_index) as price_fgi_corr,
    corr(price, social_sentiment) as price_sentiment_corr,
    corr(price, sp500) as price_sp500_corr,
    corr(price, dxy_index) as price_dxy_corr,
    corr(price, open_interest) as price_oi_corr,
    corr(price, long_short_ratio) as price_ls_ratio_corr
FROM combined_data;

-- Создаем функцию для расчета корреляций за указанный период
CREATE OR REPLACE FUNCTION get_correlations(start_date TIMESTAMPTZ, end_date TIMESTAMPTZ)
RETURNS TABLE (
    metric VARCHAR,
    correlation DECIMAL
)
AS $$
BEGIN
    RETURN QUERY
    WITH combined_data AS (
        SELECT 
            p.timestamp,
            p.close as price,
            t.rsi,
            t.macd,
            o.active_addresses,
            o.transaction_count,
            s.fear_greed_index,
            s.social_sentiment,
            m.sp500,
            m.dxy_index,
            d.open_interest,
            d.long_short_ratio
        FROM price_data p
        LEFT JOIN technical_indicators t ON date_trunc('hour', p.timestamp) = date_trunc('hour', t.timestamp)
        LEFT JOIN on_chain_metrics o ON date_trunc('hour', p.timestamp) = date_trunc('hour', o.timestamp)
        LEFT JOIN sentiment_metrics s ON date_trunc('hour', p.timestamp) = date_trunc('hour', s.timestamp)
        LEFT JOIN macro_indicators m ON date_trunc('hour', p.timestamp) = date_trunc('hour', m.timestamp)
        LEFT JOIN derivatives_data d ON date_trunc('hour', p.timestamp) = date_trunc('hour', d.timestamp)
        WHERE p.timestamp BETWEEN start_date AND end_date
    )
    SELECT 'RSI' as metric, corr(price, rsi) as correlation FROM combined_data
    UNION ALL
    SELECT 'MACD', corr(price, macd) FROM combined_data
    UNION ALL
    SELECT 'Active Addresses', corr(price, active_addresses) FROM combined_data
    UNION ALL
    SELECT 'Transaction Count', corr(price, transaction_count) FROM combined_data
    UNION ALL
    SELECT 'Fear & Greed Index', corr(price, fear_greed_index) FROM combined_data
    UNION ALL
    SELECT 'Social Sentiment', corr(price, social_sentiment) FROM combined_data
    UNION ALL
    SELECT 'S&P 500', corr(price, sp500) FROM combined_data
    UNION ALL
    SELECT 'DXY Index', corr(price, dxy_index) FROM combined_data
    UNION ALL
    SELECT 'Open Interest', corr(price, open_interest) FROM combined_data
    UNION ALL
    SELECT 'Long/Short Ratio', corr(price, long_short_ratio) FROM combined_data;
END;
$$ LANGUAGE plpgsql;
