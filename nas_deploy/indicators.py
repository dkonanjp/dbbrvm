import psycopg2
import math

DB_CONFIG = {
    "host": "brvm-postgres",
    "port": 5432,
    "database": "brvm",
    "user": "brvm_bot",
    "password": "BrvmSecure2026!"
}


def get_db():
    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = True
    return conn


def create_tables(cur):
    cur.execute("""
        CREATE TABLE IF NOT EXISTS indicators (
            id BIGSERIAL PRIMARY KEY,
            ticker VARCHAR(10) NOT NULL,
            date DATE NOT NULL,
            sma_20 NUMERIC(12,2),
            sma_50 NUMERIC(12,2),
            sma_200 NUMERIC(12,2),
            ema_12 NUMERIC(12,2),
            ema_26 NUMERIC(12,2),
            rsi_14 NUMERIC(8,4),
            macd_line NUMERIC(12,4),
            macd_signal NUMERIC(12,4),
            macd_histogram NUMERIC(12,4),
            bb_upper NUMERIC(12,2),
            bb_middle NUMERIC(12,2),
            bb_lower NUMERIC(12,2),
            stoch_k NUMERIC(8,4),
            stoch_d NUMERIC(8,4),
            atr_14 NUMERIC(12,4),
            obv NUMERIC(16,2),
            vwap NUMERIC(12,2),
            created_at TIMESTAMP DEFAULT NOW(),
            UNIQUE(ticker, date)
        );
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_indicators_ticker_date ON indicators(ticker, date);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_indicators_ticker ON indicators(ticker);")


def get_data(cur, ticker):
    cur.execute("""
        SELECT date, open, high, low, close, volume
        FROM daily
        WHERE ticker = %s
        ORDER BY date ASC
    """, (ticker,))
    return cur.fetchall()


def calc_sma(prices, period):
    if len(prices) < period:
        return None
    return sum(prices[-period:]) / period


def calc_ema(prices, period):
    if len(prices) < period:
        return None
    k = 2 / (period + 1)
    ema = sum(prices[:period]) / period
    for p in prices[period:]:
        ema = p * k + ema * (1 - k)
    return ema


def calc_rsi(closes, period=14):
    if len(closes) < period + 1:
        return None
    gains = []
    losses = []
    for i in range(1, len(closes)):
        diff = closes[i] - closes[i - 1]
        gains.append(max(diff, 0))
        losses.append(max(-diff, 0))
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def calc_macd(closes, fast=12, slow=26, signal=9):
    if len(closes) < slow + signal:
        return None, None, None
    ema_fast = calc_ema(closes, fast)
    ema_slow = calc_ema(closes, slow)
    if ema_fast is None or ema_slow is None:
        return None, None, None

    macd_values = []
    k_fast = 2 / (fast + 1)
    k_slow = 2 / (slow + 1)
    ema_f = sum(closes[:fast]) / fast
    ema_s = sum(closes[:slow]) / slow
    for i in range(slow, len(closes)):
        if i >= fast:
            ema_f = closes[i] * k_fast + ema_f * (1 - k_fast)
        ema_s = closes[i] * k_slow + ema_s * (1 - k_slow)
        macd_values.append(ema_f - ema_s)

    if len(macd_values) < signal:
        return None, None, None

    sig_k = 2 / (signal + 1)
    sig_ema = sum(macd_values[:signal]) / signal
    for v in macd_values[signal:]:
        sig_ema = v * sig_k + sig_ema * (1 - sig_k)

    macd_line = macd_values[-1]
    return macd_line, sig_ema, macd_line - sig_ema


def calc_bollinger(closes, period=20, num_std=2):
    if len(closes) < period:
        return None, None, None
    sma = sum(closes[-period:]) / period
    variance = sum((c - sma) ** 2 for c in closes[-period:]) / period
    std = math.sqrt(variance)
    return sma + num_std * std, sma, sma - num_std * std


def calc_stochastic(highs, lows, closes, k_period=14, d_period=3):
    if len(closes) < k_period:
        return None, None
    highest = max(highs[-k_period:])
    lowest = min(lows[-k_period:])
    if highest == lowest:
        k = 50.0
    else:
        k = ((closes[-1] - lowest) / (highest - lowest)) * 100
    return k, None


def calc_atr(highs, lows, closes, period=14):
    if len(closes) < period + 1:
        return None
    trs = []
    for i in range(1, len(closes)):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1])
        )
        trs.append(tr)
    if len(trs) < period:
        return None
    atr = sum(trs[:period]) / period
    for tr in trs[period:]:
        atr = (atr * (period - 1) + tr) / period
    return atr


def calc_obv(closes, volumes):
    if len(closes) < 2:
        return 0
    obv = 0
    for i in range(1, len(closes)):
        if closes[i] > closes[i - 1]:
            obv += volumes[i]
        elif closes[i] < closes[i - 1]:
            obv -= volumes[i]
    return obv


def calc_vwap(highs, lows, closes, volumes):
    if not volumes or not closes:
        return None
    tp_vol = sum((h + l + c) / 3 * v for h, l, c, v in zip(highs, lows, closes, volumes))
    total_vol = sum(volumes)
    if total_vol == 0:
        return None
    return tp_vol / total_vol


def compute_indicators(data):
    dates = [r[0] for r in data]
    opens = [float(r[1]) if r[1] else 0 for r in data]
    highs = [float(r[2]) if r[2] else 0 for r in data]
    lows = [float(r[3]) if r[3] else 0 for r in data]
    closes = [float(r[4]) if r[4] else 0 for r in data]
    volumes = [int(r[5]) if r[5] else 0 for r in data]

    results = []
    for i in range(len(data)):
        d = dates[i]
        c = closes[:i + 1]
        h = highs[:i + 1]
        l = lows[:i + 1]
        v = volumes[:i + 1]

        sma20 = calc_sma(c, 20)
        sma50 = calc_sma(c, 50)
        sma200 = calc_sma(c, 200)
        ema12 = calc_ema(c, 12)
        ema26 = calc_ema(c, 26)
        rsi = calc_rsi(c, 14)
        macd_l, macd_s, macd_h = calc_macd(c)
        bb_u, bb_m, bb_l = calc_bollinger(c)
        stoch_k, stoch_d = calc_stochastic(h, l, c)
        atr = calc_atr(h, l, c)
        obv = calc_obv(c, v)
        vwap = calc_vwap(h, l, c, v)

        results.append((
            d,
            round(sma20, 2) if sma20 else None,
            round(sma50, 2) if sma50 else None,
            round(sma200, 2) if sma200 else None,
            round(ema12, 2) if ema12 else None,
            round(ema26, 2) if ema26 else None,
            round(rsi, 4) if rsi else None,
            round(macd_l, 4) if macd_l else None,
            round(macd_s, 4) if macd_s else None,
            round(macd_h, 4) if macd_h else None,
            round(bb_u, 2) if bb_u else None,
            round(bb_m, 2) if bb_m else None,
            round(bb_l, 2) if bb_l else None,
            round(stoch_k, 4) if stoch_k else None,
            None,
            round(atr, 4) if atr else None,
            round(obv, 2) if obv else None,
            round(vwap, 2) if vwap else None,
        ))
    return results


def generate_signals(cur, ticker, indicators):
    signals = []
    for i in range(1, len(indicators)):
        curr = indicators[i]
        prev = indicators[i - 1]
        date = curr[0]
        reasons = []
        score = 0

        rsi = curr[6]
        if rsi is not None:
            if rsi < 30:
                score += 1
                reasons.append(f"RSI oversold ({rsi:.1f})")
            elif rsi > 70:
                score -= 1
                reasons.append(f"RSI overbought ({rsi:.1f})")

        macd_h = curr[9]
        prev_macd_h = prev[9]
        if macd_h is not None and prev_macd_h is not None:
            if prev_macd_h < 0 and macd_h > 0:
                score += 2
                reasons.append("MACD bullish crossover")
            elif prev_macd_h > 0 and macd_h < 0:
                score -= 2
                reasons.append("MACD bearish crossover")

        sma20 = curr[1]
        sma50 = curr[2]
        if sma20 and sma50:
            prev_sma20 = prev[1]
            prev_sma50 = prev[2]
            if prev_sma20 and prev_sma50:
                if prev_sma20 < prev_sma50 and sma20 > sma50:
                    score += 2
                    reasons.append("SMA20 crossed above SMA50 (Golden Cross)")
                elif prev_sma20 > prev_sma50 and sma20 < sma50:
                    score -= 2
                    reasons.append("SMA20 crossed below SMA50 (Death Cross)")

        stoch_k = curr[13]
        if stoch_k is not None:
            if stoch_k < 20:
                score += 1
                reasons.append(f"Stochastic oversold ({stoch_k:.1f})")
            elif stoch_k > 80:
                score -= 1
                reasons.append(f"Stochastic overbought ({stoch_k:.1f})")

        if score >= 3:
            signal_type = "BUY"
            confidence = min(score / 6.0, 1.0)
        elif score <= -3:
            signal_type = "SELL"
            confidence = min(abs(score) / 6.0, 1.0)
        elif score >= 1:
            signal_type = "BUY"
            confidence = score / 6.0
        elif score <= -1:
            signal_type = "SELL"
            confidence = abs(score) / 6.0
        else:
            signal_type = "HOLD"
            confidence = 0.5

        if reasons:
            signals.append((
                ticker, date, signal_type, confidence,
                "multi-indicator",
                " | ".join(reasons),
                curr[4] or curr[3] or 0
            ))
    return signals


def main():
    import sys
    print("Connecting to PostgreSQL...")
    conn = get_db()
    cur = conn.cursor()

    create_tables(cur)

    if len(sys.argv) > 1:
        tickers = sys.argv[1].split(",")
        print(f"Processing {len(tickers)} specified tickers...")
    else:
        cur.execute("SELECT DISTINCT ticker FROM daily ORDER BY ticker")
        tickers = [r[0] for r in cur.fetchall()]
        print(f"Processing {len(tickers)} tickers...")

    total_indicators = 0
    total_signals = 0

    for ticker in tickers:
        data = get_data(cur, ticker)
        if len(data) < 2:
            continue

        indicators = compute_indicators(data)

        for ind in indicators:
            cur.execute("""
                INSERT INTO indicators (ticker, date, sma_20, sma_50, sma_200,
                    ema_12, ema_26, rsi_14, macd_line, macd_signal, macd_histogram,
                    bb_upper, bb_middle, bb_lower, stoch_k, stoch_d, atr_14, obv, vwap)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (ticker, date) DO UPDATE SET
                    sma_20 = EXCLUDED.sma_20, sma_50 = EXCLUDED.sma_50, sma_200 = EXCLUDED.sma_200,
                    ema_12 = EXCLUDED.ema_12, ema_26 = EXCLUDED.ema_26, rsi_14 = EXCLUDED.rsi_14,
                    macd_line = EXCLUDED.macd_line, macd_signal = EXCLUDED.macd_signal, macd_histogram = EXCLUDED.macd_histogram,
                    bb_upper = EXCLUDED.bb_upper, bb_middle = EXCLUDED.bb_middle, bb_lower = EXCLUDED.bb_lower,
                    stoch_k = EXCLUDED.stoch_k, stoch_d = EXCLUDED.stoch_d, atr_14 = EXCLUDED.atr_14,
                    obv = EXCLUDED.obv, vwap = EXCLUDED.vwap
            """, (ticker,) + ind)
            total_indicators += 1

        signals = generate_signals(cur, ticker, indicators)
        for sig in signals:
            try:
                cur.execute("""
                    INSERT INTO signals (ticker, date, signal_type, confidence, indicator, reason, price_at_signal)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, sig)
            except Exception:
                pass
            total_signals += 1

        print(f"  {ticker}: {len(indicators)} indicators, {len(signals)} signals")

    conn.commit()
    cur.close()
    conn.close()
    print(f"\nTotal: {total_indicators} indicators, {total_signals} signals")


if __name__ == "__main__":
    main()
