import os
import re
import time
import random
import requests
from bs4 import BeautifulSoup
import pandas as pd
import psycopg2
from datetime import datetime, timezone
import schedule
import urllib3

urllib3.disable_warnings(urllib3.exceptions.SecurityWarning)

# Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://brvm_bot:BrvmSecure2026!@localhost:5433/brvm")
BRVM_URL = "https://www.brvm.org/fr/cours-actions/liste"
SCRAPE_INTERVAL = 15  # minutes

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Safari/605.1.15",
]

TICKER_RE = re.compile(r'^[A-Z]{2,5}$')


def get_db_connection():
    return psycopg2.connect(DATABASE_URL)


def request_with_retry(url, max_attempts=5):
    for attempt in range(1, max_attempts + 1):
        ua = random.choice(USER_AGENTS)
        try:
            resp = requests.get(
                url,
                headers={
                    "User-Agent": ua,
                    "Accept-Language": "fr,fr-FR;q=0.9,en;q=0.8",
                    "Accept": "text/html,application/xhtml+xml",
                    "Referer": "https://www.brvm.org/fr/",
                },
                verify=False,
                timeout=60,
            )
            if resp.status_code == 200:
                return resp
            if resp.status_code == 429:
                wait = (2**attempt) * 10
                print(f"  429 - attente {wait}s")
                time.sleep(wait)
        except requests.RequestException as e:
            print(f"  Tentative {attempt}/{max_attempts} - {e}")
            if attempt < max_attempts:
                time.sleep(5)
    return None


def scrape_brvm():
    resp = request_with_retry(BRVM_URL)
    if resp is None:
        raise RuntimeError("Échec après plusieurs tentatives")

    soup = BeautifulSoup(resp.text, "html.parser")
    tables = soup.find_all("table")

    stock_table = None
    best_count = 0
    for table in tables:
        rows = table.find_all("tr")
        count = sum(1 for row in rows if len(row.find_all("td")) >= 7 and TICKER_RE.match(row.find_all("td")[0].get_text(strip=True)))
        if count > best_count:
            best_count = count
            stock_table = table

    if stock_table is None or best_count < 5:
        raise RuntimeError("Tableau introuvable ou données insuffisantes")

    scrape_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    scrape_date = datetime.now().date()

    records = []
    for row in stock_table.find_all("tr")[1:]:
        cells = row.find_all("td")
        if len(cells) < 7:
            continue

        ticker = cells[0].get_text(strip=True)
        if not TICKER_RE.match(ticker):
            continue

        try:
            cours_cloture = float(cells[5].get_text(strip=True).replace(" ", "").replace(",", "."))
        except ValueError:
            continue

        if cours_cloture == 0:
            continue

        records.append({
            "ticker": ticker,
            "nom": cells[1].get_text(strip=True),
            "volume": float(cells[2].get_text(strip=True).replace(" ", "") or 0),
            "previous_close": float(cells[3].get_text(strip=True).replace(" ", "") or 0),
            "open": float(cells[4].get_text(strip=True).replace(" ", "") or 0),
            "close": cours_cloture,
            "variation": float(cells[6].get_text(strip=True).replace(" ", "").replace(",", ".") or 0),
            "date": str(scrape_date),
            "timestamp": scrape_time,
        })

    return records


def get_existing_snapshots(conn, ticker, date):
    with conn.cursor() as cur:
        cur.execute(
            "SELECT close FROM market_data WHERE ticker = %s AND date = %s ORDER BY timestamp",
            (ticker, date)
        )
        return [row[0] for row in cur.fetchall()]


def insert_market_data(conn, records):
    with conn.cursor() as cur:
        for rec in records:
            existing = get_existing_snapshots(conn, rec["ticker"], rec["date"])
            all_closes = existing + [rec["close"]]
            high = max(all_closes)
            low = min(all_closes)

            cur.execute("""
                INSERT INTO market_data 
                (ticker, nom, date, timestamp, open, high, low, close, previous_close, volume, variation, nb_snapshots)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (ticker, timestamp) DO UPDATE SET
                    high = GREATEST(market_data.high, EXCLUDED.high),
                    low = LEAST(market_data.low, EXCLUDED.low),
                    close = EXCLUDED.close,
                    volume = EXCLUDED.volume,
                    variation = EXCLUDED.variation
            """, (
                rec["ticker"], rec["nom"], rec["date"], rec["timestamp"],
                rec["open"], high, low, rec["close"],
                rec["previous_close"], rec["volume"], rec["variation"],
                len(existing) + 1
            ))
    conn.commit()


def update_daily(conn):
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO daily (ticker, date, open, high, low, close, volume, variation)
            SELECT DISTINCT ON (ticker)
                ticker, date, open, high, low, close, volume, variation
            FROM market_data
            WHERE date = CURRENT_DATE
            ORDER BY ticker, timestamp DESC
            ON CONFLICT (ticker, date) DO UPDATE SET
                open = EXCLUDED.open, high = EXCLUDED.high, low = EXCLUDED.low,
                close = EXCLUDED.close, volume = EXCLUDED.volume, variation = EXCLUDED.variation
        """)
        count = cur.rowcount
    conn.commit()
    return count


def log_scrape(conn, status, tickers_count, errors_count, duration_ms):
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO scrape_logs (timestamp, status, tickers_count, errors_count, duration_ms)
            VALUES (%s, %s, %s, %s, %s)
        """, (datetime.now(), status, tickers_count, errors_count, duration_ms))
    conn.commit()


def job():
    print(f"\n{'='*50}")
    print(f"Scrape BRVM - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*50}")

    start = time.time()
    conn = get_db_connection()

    try:
        records = scrape_brvm()
        insert_market_data(conn, records)
        daily_count = update_daily(conn)
        duration = int((time.time() - start) * 1000)
        log_scrape(conn, "success", len(records), 0, duration)
        print(f"  ✓ {len(records)} actions collectées ({duration}ms) | daily: {daily_count} mis à jour")
    except Exception as e:
        duration = int((time.time() - start) * 1000)
        log_scrape(conn, "error", 0, 1, duration)
        print(f"  ✗ Erreur: {e}")
    finally:
        conn.close()


def main():
    print("🚀 BRVM Scraper démarré")
    print(f"   Intervalle: toutes les {SCRAPE_INTERVAL} minutes")
    print(f"   Base: {DATABASE_URL.split('@')[1]}")

    job()

    schedule.every(SCRAPE_INTERVAL).minutes.do(job)

    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__ == "__main__":
    main()
