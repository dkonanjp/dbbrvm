#!/usr/bin/env python3
"""
End-of-Day (EOD) job: copies the last intraday snapshot of each ticker
from market_data into the daily table.
"""

import psycopg2
from datetime import datetime, date

DB_CONFIG = {
    "host": "brvm-postgres",
    "dbname": "brvm",
    "user": "brvm_bot",
    "password": "BrvmSecure2026!"
}


def run_eod():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    today = date.today()
    print(f"[{datetime.now()}] EOD job for {today}")

    cur.execute("""
        INSERT INTO daily (ticker, date, open, high, low, close, volume, variation)
        SELECT DISTINCT ON (ticker)
            ticker,
            date,
            open,
            high,
            low,
            close,
            volume,
            variation
        FROM market_data
        WHERE date = %s
        ORDER BY ticker, timestamp DESC
        ON CONFLICT (ticker, date) DO UPDATE SET
            open = EXCLUDED.open,
            high = EXCLUDED.high,
            low = EXCLUDED.low,
            close = EXCLUDED.close,
            volume = EXCLUDED.volume,
            variation = EXCLUDED.variation
    """, (today,))

    affected = cur.rowcount
    conn.commit()
    print(f"  Updated {affected} tickers in daily table")

    cur.close()
    conn.close()


if __name__ == "__main__":
    run_eod()
