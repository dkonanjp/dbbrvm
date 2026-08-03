#!/usr/bin/env python3
"""
Fast incremental indicator calculation.
Only recalculates for the latest 30 days per ticker (not all history).
Designed for daily cron execution.
"""

import psycopg2
import numpy as np
from datetime import datetime, timedelta

DB_CONFIG = {
    "host": "brvm-postgres",
    "dbname": "brvm",
    "user": "brvm_bot",
    "password": "BrvmSecure2026!"
}


def get_db():
    return psycopg2.connect(**DB_CONFIG)


def create_tables(cur):
    cur.execute("""
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
        )
    """)
    cur.execute("""
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
        )
    """)


def get_data(cur, ticker, lookback_days=250):
    """Get data with enough lookback for SMA-200 + buffer."""
    cutoff = datetime.now().date() - timedelta(days=lookback_days)
    cur.execute("""
        SELECT date, open, high, low, close, volume
        FROM daily WHERE ticker = %s AND date >= %s ORDER BY date
    """, (ticker, cutoff))
    rows = cur.fetchall()
    if not rows:
        return []
    return [{"date": r[0], "open": float(r[1]), "high": float(r[2]),
             "low": float(r[3]), "close": float(r[4]), "volume": int(r[5] or 0)}
            for r in rows]


def sma(data, period):
    if len(data) < period:
        return [None] * len(data)
    result = [None] * (period - 1)
    for i in range(period - 1, len(data)):
        result.append(round(sum(data[i - period + 1:i + 1]) / period, 4))
    return result


def ema(data, period):
    if not data:
        return []
    k = 2 / (period + 1)
    result = [data[0]]
    for i in range(1, len(data)):
        result.append(round(data[i] * k + result[-1] * (1 - k), 4))
    return result


def rsi(closes, period=14):
    if len(closes) < period + 1:
        return [None] * len(closes)
    deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    gains = [max(d, 0) for d in deltas]
    losses = [abs(min(d, 0)) for d in deltas]
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    result = [None] * period
    rs = avg_gain / avg_loss if avg_loss != 0 else 100
    result.append(round(100 - (100 / (1 + rs)), 4))
    for i in range(period, len(deltas)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        rs = avg_gain / avg_loss if avg_loss != 0 else 100
        result.append(round(100 - (100 / (1 + rs)), 4))
    return result


def compute_indicators(data):
    closes = [d["close"] for d in data]
    highs = [d["high"] for d in data]
    lows = [d["low"] for d in data]
    volumes = [d["volume"] for d in data]

    sma20 = sma(closes, 20)
    sma50 = sma(closes, 50)
    sma200 = sma(closes, 200)

    ema12 = ema(closes, 12)
    ema26 = ema(closes, 26)

    rsi_vals = rsi(closes, 14)

    macd_line = [round(ema12[i] - ema26[i], 4) if ema12[i] and ema26[i] else None for i in range(len(closes))]
    macd_signal = ema([x for x in macd_line if x is not None], 9)
    sig_idx = 0
    macd_signal_full = []
    for v in macd_line:
        if v is not None:
            macd_signal_full.append(macd_signal[sig_idx])
            sig_idx += 1
        else:
            macd_signal_full.append(None)
    macd_hist = [round(macd_line[i] - macd_signal_full[i], 4) if macd_line[i] and macd_signal_full[i] else None for i in range(len(closes))]

    bb_mid = sma(closes, 20)
    bb_upper, bb_lower = [], []
    for i in range(len(closes)):
        if bb_mid[i] is None:
            bb_upper.append(None)
            bb_lower.append(None)
        else:
            window = closes[i - 19:i + 1]
            std = float(np.std(window)) if len(window) >= 2 else 0
            bb_upper.append(round(bb_mid[i] + 2 * std, 2))
            bb_lower.append(round(bb_mid[i] - 2 * std, 2))

    stoch_k, stoch_d = [], []
    for i in range(len(closes)):
        if i < 13:
            stoch_k.append(None)
            stoch_d.append(None)
        else:
            h14 = max(highs[i - 13:i + 1])
            l14 = min(lows[i - 13:i + 1])
            k = ((closes[i] - l14) / (h14 - l14) * 100) if h14 != l14 else 50
            stoch_k.append(round(k, 4))
            if len(stoch_k) >= 3 and stoch_k[-3] is not None:
                stoch_d.append(round(sum(stoch_k[-3:]) / 3, 4))
            else:
                stoch_d.append(None)

    atr = []
    for i in range(len(closes)):
        if i == 0:
            atr.append(round(highs[i] - lows[i], 4))
        else:
            tr = max(highs[i] - lows[i], abs(highs[i] - closes[i - 1]), abs(lows[i] - closes[i - 1]))
            atr.append(round((atr[-1] * 13 + tr) / 14, 4))

    obv = [0]
    for i in range(1, len(closes)):
        if closes[i] > closes[i - 1]:
            obv.append(obv[-1] + volumes[i])
        elif closes[i] < closes[i - 1]:
            obv.append(obv[-1] - volumes[i])
        else:
            obv.append(obv[-1])

    vwap = []
    cum_vol = 0
    cum_vp = 0
    for i in range(len(closes)):
        tp = (highs[i] + lows[i] + closes[i]) / 3
        cum_vol += volumes[i]
        cum_vp += tp * volumes[i]
        vwap.append(round(cum_vp / cum_vol, 2) if cum_vol > 0 else closes[i])

    results = []
    for i in range(len(data)):
        results.append((
            data[i]["date"],
            sma20[i], sma50[i], sma200[i],
            ema12[i], ema26[i],
            rsi_vals[i] if i < len(rsi_vals) else None,
            macd_line[i], macd_signal_full[i], macd_hist[i],
            bb_upper[i], bb_mid[i], bb_lower[i],
            stoch_k[i], stoch_d[i],
            atr[i], obv[i], vwap[i]
        ))
    return results


def generate_signals(indicator_row, price):
    ind_date = indicator_row[0]
    sma20_val, sma50_val = indicator_row[1], indicator_row[2]
    rsi_val = indicator_row[6]
    macd_l, macd_s, macd_h = indicator_row[7], indicator_row[8], indicator_row[9]
    stoch_k_val = indicator_row[13]

    signals = []

    if rsi_val is not None:
        if rsi_val < 30:
            signals.append((ind_date, "BUY", float(rsi_val) / 100, "RSI", f"RSI survente ({rsi_val:.1f})", price))
        elif rsi_val > 70:
            signals.append((ind_date, "SELL", (100 - float(rsi_val)) / 100, "RSI", f"RSI surachat ({rsi_val:.1f})", price))

    if macd_h is not None and macd_s is not None:
        if macd_h > 0 and macd_s < 0:
            signals.append((ind_date, "BUY", 0.6, "MACD", "MACD croisement haussier", price))
        elif macd_h < 0 and macd_s > 0:
            signals.append((ind_date, "SELL", 0.6, "MACD", "MACD croisement baissier", price))

    if stoch_k_val is not None:
        if stoch_k_val < 20:
            signals.append((ind_date, "BUY", 0.55, "STOCH", f"Stochastique survente ({stoch_k_val:.1f})", price))
        elif stoch_k_val > 80:
            signals.append((ind_date, "SELL", 0.55, "STOCH", f"Stochastique surachat ({stoch_k_val:.1f})", price))

    if sma20_val and sma50_val:
        if price > sma20_val > sma50_val:
            signals.append((ind_date, "BUY", 0.5, "SMA", "Prix > SMA20 > SMA50 (tendance haussière)", price))
        elif price < sma20_val < sma50_val:
            signals.append((ind_date, "SELL", 0.5, "SMA", "Prix < SMA20 < SMA50 (tendance baissière)", price))

    if not signals:
        signals.append((ind_date, "HOLD", 0.5, "MULTI", "Aucun signal fort détecté", price))

    return signals


def main():
    print(f"[{datetime.now()}] Starting incremental indicators...")
    conn = get_db()
    cur = conn.cursor()
    create_tables(cur)

    cur.execute("SELECT DISTINCT ticker FROM daily ORDER BY ticker")
    tickers = [r[0] for r in cur.fetchall()]
    print(f"Processing {len(tickers)} tickers (incremental, 250-day lookback)...")

    total_ind = 0
    total_sig = 0

    for ticker in tickers:
        data = get_data(cur, ticker, lookback_days=250)
        if len(data) < 2:
            continue

        indicators = compute_indicators(data)

        # Only upsert the last 30 days (incremental)
        cutoff = datetime.now().date() - timedelta(days=30)
        recent = [ind for ind in indicators if ind[0] >= cutoff]

        for ind in recent:
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
            total_ind += 1

        for ind in recent:
            sigs = generate_signals(ind, data[-1]["close"])
            for sig in sigs:
                try:
                    cur.execute("""
                        INSERT INTO signals (ticker, date, signal_type, confidence, indicator, reason, price_at_signal)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """, (ticker,) + sig)
                    total_sig += 1
                except Exception as e:
                    print(f"  SIGNAL ERROR: {e}")
                    conn.rollback()

        conn.commit()
        print(f"  {ticker}: {len(recent)} indicators updated")

    print(f"\nDone! {total_ind} indicators, {total_sig} signals updated (last 30 days)")
    conn.close()


if __name__ == "__main__":
    main()
