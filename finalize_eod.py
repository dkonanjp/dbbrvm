import pandas as pd
from pathlib import Path
from datetime import datetime, timezone

# dbhistorical/ est alimenté EXCLUSIVEMENT par ce script à partir de dbintraday/.
# Ne jamais introduire de source externe (init_brvm_db.py est obsolète).
HISTORICAL_DIR = Path("dbhistorical")
INTRADAY_DIR = Path("dbintraday")

FIRST_SNAPSHOT_HOUR = 9
FIRST_SNAPSHOT_MIN = 50
MIN_SNAPSHOTS = 3


def _after_market_open(ts: str) -> bool:
    try:
        t = datetime.fromisoformat(ts)
        if t.tzinfo is None:
            t = t.replace(tzinfo=timezone.utc)
        return t.hour > FIRST_SNAPSHOT_HOUR or (
            t.hour == FIRST_SNAPSHOT_HOUR and t.minute >= FIRST_SNAPSHOT_MIN
        )
    except Exception:
        return True


def compute_eod(intraday_csv: Path):
    df = pd.read_csv(intraday_csv)

    if df.empty:
        return None

    tickers = df["Ticker"].unique()
    if len(tickers) != 1:
        print(f"  {intraday_csv.name}: tickers multiples, ignoré")
        return None

    today = df["Date"].max()
    df = df[df["Date"] == today]

    df = df[df["Timestamp"].apply(_after_market_open)]

    if len(df) < MIN_SNAPSHOTS:
        print(f"  {intraday_csv.name}: {len(df)} snapshot(s) pour {today} insuffisant(s) (min {MIN_SNAPSHOTS}), ignoré")
        return None

    ticker = tickers[0]
    df = df.sort_values("Timestamp")

    eod = {
        "Date": pd.to_datetime(today).date(),
        "Open": df["Cours_Ouverture"].iloc[0],
        "High": df["Cours"].max(),
        "Low": df["Cours"].min(),
        "Close": df["Cours"].iloc[-1],
        "Volume": df["Volume_Cumule"].iloc[-1],
        "Ticker": ticker,
        "source": "live",
        "updated_at": datetime.now(),
    }
    return eod


def main():
    print("=== Finalisation EOD BRVM ===")
    print(f"Date: {datetime.now().date()}\n")

    intraday_files = sorted(INTRADAY_DIR.glob("[A-Z]*.csv"))

    if not intraday_files:
        print("  Aucun snapshot intraday trouvé.")
        return

    success = 0
    for f in intraday_files:
        ticker = f.stem
        print(f"  {ticker:<5} → ", end="", flush=True)

        eod = compute_eod(f)
        if eod is None:
            print("pas de données")
            continue

        daily_file = HISTORICAL_DIR / f"{ticker}.csv"

        if daily_file.exists():
            existing = pd.read_csv(daily_file)
            existing["Date"] = pd.to_datetime(existing["Date"]).dt.date
            existing = existing[existing["Date"] != eod["Date"]]
            eod_df = pd.DataFrame([eod])
            combined = pd.concat([existing, eod_df], ignore_index=True)
            combined = combined.sort_values("Date", ascending=False)
        else:
            combined = pd.DataFrame([eod])

        combined.to_csv(daily_file, index=False, float_format="%.0f")

        print(
            f"O:{eod['Open']:.0f} H:{eod['High']:.0f} L:{eod['Low']:.0f} C:{eod['Close']:.0f} V:{eod['Volume']:,.0f}"
        )
        success += 1

    print(f"\n  {success} tickers finalisés dans {HISTORICAL_DIR}/")


if __name__ == "__main__":
    main()
