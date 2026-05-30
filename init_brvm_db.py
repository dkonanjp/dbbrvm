import sys
import pandas as pd
from pathlib import Path
from datetime import datetime

print("⚠️  ATTENTION: Ce script a été utilisé une seule fois pour initialiser la base historique.")
print("    Il ne doit PLUS être exécuté. Les données historiques sont désormais alimentées")
print("    exclusivement par finalize_eod.py à partir des snapshots dbintraday/.")
print()
rep = input("Toujours exécuter ? (oui/non) : ").strip().lower()
if rep != "oui":
    print("Abandon.")
    sys.exit(0)

HISTORICAL_DIR = Path("dbhistorical")
HISTORICAL_DIR.mkdir(exist_ok=True)

TICKERS = [
    "NTLC", "PALC", "SPHC", "SICC", "STBC", "SOGC", "SLBC", "SCRC", "UNLC",
    "BNBC", "CFAC", "LNBB", "NEIC", "ABJC", "PRSC", "UNXC",
    "SMBC", "TTLC", "TTLS", "SHEC",
    "SDSC", "SEMC", "SIVC", "FTSC", "STAC", "CABC",
    "BOAB", "BOABF", "BOAC", "BOAM", "BOAN", "BOAS",
    "BICB", "BICC", "CBIBF", "ECOC", "ETIT", "NSBC", "ORGT", "SAFC", "SGBC", "SIBC",
    "CIEC", "SDCC",
    "ONTBF", "ORAC", "SNTS",
]

BASE_URL = "https://raw.githubusercontent.com/Fredysessie/brvm-data-public/main/data"

print("=== Initialisation de la base BRVM CSV ===\n")

total_rows = 0
for ticker in TICKERS:
    url = f"{BASE_URL}/{ticker}/{ticker}.daily.csv"
    dest = HISTORICAL_DIR / f"{ticker}.csv"

    print(f"[{ticker}] Téléchargement... ", end="", flush=True)

    try:
        df = pd.read_csv(url)
        if df.empty:
            print("⚠️  fichier vide")
            continue
        df["Date"] = pd.to_datetime(df["Date"]).dt.date
        df["Ticker"] = ticker
        df["source"] = "github"
        df["updated_at"] = datetime.now()
        df = df[["Date", "Open", "High", "Low", "Close", "Volume", "Ticker", "source", "updated_at"]]
        df = df.sort_values("Date")
        df.to_csv(dest, index=False)
        rows = len(df)
        total_rows += rows
        print(f"✅ {rows} lignes (dernière: {df['Date'].max()})")
    except Exception as e:
        print(f"ERREUR: {e}")

print(f"\n=== Terminé: {len(TICKERS)} tickers, {total_rows} lignes total ===")
