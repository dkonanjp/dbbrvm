import re
import requests
from bs4 import BeautifulSoup
import pandas as pd
from pathlib import Path
from datetime import datetime
import time
import random
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

HISTORICAL_DIR = Path("dbhistorical")
INTRADAY_DIR = Path("dbintraday")
LOG_DIR = Path("logs")
INTRADAY_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "_scrape_log.csv"

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:137.0) Gecko/20100101 Firefox/137.0",
]

TICKER_RE = re.compile(r'^[A-Z]{2,5}$')


def request_with_retry(url, max_attempts=3):
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
                timeout=30,
            )
            if resp.status_code == 200:
                return resp
            if resp.status_code == 429:
                wait = (2**attempt) * 5
                print(
                    f"  429 Too Many Requests — attente {wait}s (tentative {attempt}/{max_attempts})"
                )
                time.sleep(wait)
                continue
        except requests.RequestException as e:
            print(f"  Tentative {attempt}/{max_attempts} — {e}")
        if attempt < max_attempts:
            print(f"  Tentative {attempt}/{max_attempts} échouée, nouvelle tentative...")
            time.sleep(5)
    return None


def scrape_brvm():
    url = "https://www.brvm.org/fr/cours-actions/liste"
    resp = request_with_retry(url)

    if resp is None:
        raise RuntimeError("Échec après plusieurs tentatives")

    soup = BeautifulSoup(resp.text, "html.parser")
    tables = soup.find_all("table")

    stock_table = None
    best_count = 0
    for table in tables:
        rows = table.find_all("tr")
        count = 0
        for row in rows:
            cells = row.find_all("td")
            if len(cells) >= 7 and TICKER_RE.match(cells[0].get_text(strip=True)):
                count += 1
        if count > best_count:
            best_count = count
            stock_table = table
    if stock_table is None:
        raise RuntimeError("Tableau des actions introuvable — la structure HTML a peut-être changé")

    rows = stock_table.find_all("tr")

    scrape_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    scrape_date = datetime.now().date()

    records = []
    skipped = []
    for row in rows[1:]:
        cells = row.find_all("td")
        if len(cells) < 7:
            skipped.append((row, "moins de 7 colonnes"))
            continue

        ticker = cells[0].get_text(strip=True)
        if not TICKER_RE.match(ticker):
            skipped.append((row, f"ticker invalide: '{ticker}'"))
            continue

        cours_cloture_str = cells[5].get_text(strip=True).replace(" ", "")
        try:
            cours_cloture = float(cours_cloture_str)
        except ValueError:
            skipped.append((row, f"cours clôture non numérique: '{cours_cloture_str}'"))
            continue
        if cours_cloture == 0:
            skipped.append((row, "cours clôture = 0"))
            continue

        volume_str = cells[2].get_text(strip=True).replace(" ", "")
        cours_veille_str = cells[3].get_text(strip=True).replace(" ", "")
        ouverture_str = cells[4].get_text(strip=True).replace(" ", "")
        variation_str = cells[6].get_text(strip=True).replace(" ", "").replace(",", ".")

        records.append(
            {
                "Ticker": ticker,
                "Nom": cells[1].get_text(strip=True),
                "Volume": float(volume_str) if volume_str else 0,
                "Cours_Veille": float(cours_veille_str) if cours_veille_str else 0,
                "Cours_Ouverture": float(ouverture_str) if ouverture_str else 0,
                "Cours_Cloture": cours_cloture,
                "Variation": float(variation_str) if variation_str else 0,
                "Date": str(scrape_date),
                "Timestamp": scrape_time,
            }
        )

    if skipped:
        for row, reason in skipped:
            print(f"  Ligne ignorée: {reason}")

    if not records:
        raise RuntimeError("Aucune donnée valide extraite")

    df = pd.DataFrame(records)
    df.scrape_time = scrape_time
    return df


def append_intraday(df):
    for ticker in df["Ticker"].unique():
        df_ticker = df[df["Ticker"] == ticker].copy()
        filepath = INTRADAY_DIR / f"{ticker}.csv"

        snapshot = df_ticker[
            ["Ticker", "Date", "Timestamp", "Cours_Ouverture", "Cours_Cloture", "Volume"]
        ].rename(columns={"Cours_Cloture": "Cours", "Volume": "Volume_Cumule"})

        snapshot.to_csv(filepath, mode="a", header=not filepath.exists(), index=False)


def log_scrape(success_count, error_count, scrape_time):
    log_entry = pd.DataFrame(
        [
            {
                "timestamp": scrape_time,
                "date": datetime.now().date(),
                "success": success_count,
                "errors": error_count,
                "total": success_count + error_count,
            }
        ]
    )
    log_entry.to_csv(LOG_FILE, mode="a", header=not LOG_FILE.exists(), index=False)


def main():
    print("=== Snapshot BRVM ===")
    print(f"Date: {datetime.now().date()}\n")

    try:
        df = scrape_brvm()
        scrape_time = df.scrape_time

        print(f"  {len(df)} actions récupérées à {scrape_time}\n")

        success = 0
        for _, row in df.iterrows():
            print(
                f"  {row['Ticker']:<5} → Cours: {row['Cours_Cloture']:>8.0f} FCFA | Vol: {row['Volume']:,.0f}"
            )
            success += 1

        append_intraday(df)
        log_scrape(success, len(df) - success, scrape_time)
        print(f"\n  Snapshot sauvegardé dans {INTRADAY_DIR}/")

    except Exception as e:
        print(f"\nERREUR: {e}")
        log_scrape(0, 1, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        raise


if __name__ == "__main__":
    main()
