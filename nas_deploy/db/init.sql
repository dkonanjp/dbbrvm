-- BRVM Database Schema
-- PostgreSQL 16

CREATE TABLE IF NOT EXISTS daily (
    id BIGSERIAL PRIMARY KEY,
    ticker VARCHAR(10) NOT NULL,
    date DATE NOT NULL,
    open NUMERIC(12,2),
    high NUMERIC(12,2),
    low NUMERIC(12,2),
    close NUMERIC(12,2),
    volume BIGINT,
    variation NUMERIC(8,4),
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(ticker, date)
);

CREATE TABLE IF NOT EXISTS market_data (
    id BIGSERIAL PRIMARY KEY,
    ticker VARCHAR(10) NOT NULL,
    nom VARCHAR(100),
    date DATE NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    open NUMERIC(12,2),
    high NUMERIC(12,2),
    low NUMERIC(12,2),
    close NUMERIC(12,2),
    previous_close NUMERIC(12,2),
    volume NUMERIC(15,2),
    variation NUMERIC(8,4),
    nb_snapshots INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(ticker, timestamp)
);

CREATE TABLE IF NOT EXISTS indicators (
    ticker VARCHAR(10) NOT NULL,
    date DATE NOT NULL,
    sma_20 NUMERIC(12,2),
    sma_50 NUMERIC(12,2),
    sma_200 NUMERIC(12,2),
    ema_12 NUMERIC(12,2),
    ema_26 NUMERIC(12,2),
    rsi_14 NUMERIC(5,4),
    macd_line NUMERIC(12,4),
    macd_signal NUMERIC(12,4),
    macd_histogram NUMERIC(12,4),
    bb_upper NUMERIC(12,2),
    bb_middle NUMERIC(12,2),
    bb_lower NUMERIC(12,2),
    stoch_k NUMERIC(5,4),
    stoch_d NUMERIC(5,4),
    atr_14 NUMERIC(12,4),
    obv NUMERIC(18,2),
    vwap NUMERIC(12,2),
    created_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (ticker, date)
);

CREATE TABLE IF NOT EXISTS signals (
    id BIGSERIAL PRIMARY KEY,
    ticker VARCHAR(10) NOT NULL,
    date DATE NOT NULL,
    signal_type VARCHAR(10) NOT NULL,
    confidence NUMERIC(5,4),
    indicator VARCHAR(50),
    reason TEXT,
    price_at_signal NUMERIC(12,2),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS alerts (
    id BIGSERIAL PRIMARY KEY,
    ticker VARCHAR(10) NOT NULL,
    alert_type VARCHAR(50) NOT NULL,
    message TEXT,
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS predictions (
    id BIGSERIAL PRIMARY KEY,
    ticker VARCHAR(10) NOT NULL,
    model_name VARCHAR(50),
    prediction_date DATE NOT NULL,
    target_date DATE NOT NULL,
    predicted_price NUMERIC(12,2),
    confidence NUMERIC(5,4),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS indices (
    id BIGSERIAL PRIMARY KEY,
    index_name VARCHAR(50) NOT NULL,
    date DATE NOT NULL,
    value NUMERIC(12,2),
    variation NUMERIC(8,4),
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(index_name, date)
);

CREATE TABLE IF NOT EXISTS scrape_logs (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    status VARCHAR(20),
    tickers_count INTEGER DEFAULT 0,
    errors_count INTEGER DEFAULT 0,
    duration_ms INTEGER DEFAULT 0
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_daily_ticker ON daily(ticker);
CREATE INDEX IF NOT EXISTS idx_daily_date ON daily(date);
CREATE INDEX IF NOT EXISTS idx_daily_ticker_date ON daily(ticker, date);
CREATE INDEX IF NOT EXISTS idx_market_data_ticker ON market_data(ticker);
CREATE INDEX IF NOT EXISTS idx_market_data_date ON market_data(date);
CREATE INDEX IF NOT EXISTS idx_indicators_ticker ON indicators(ticker);
CREATE INDEX IF NOT EXISTS idx_signals_ticker ON signals(ticker);
CREATE INDEX IF NOT EXISTS idx_signals_date ON signals(date);
CREATE INDEX IF NOT EXISTS idx_scrape_logs_timestamp ON scrape_logs(timestamp);
