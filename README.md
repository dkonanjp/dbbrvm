# BRVM Data Scraper

Scraping automatisé des données boursières de la BRVM avec deux bases distinctes.

Converti de R vers Python.

## Architecture

```
                     ┌─────────────────────────┐
                     │   brvm.org (site officiel)│
                     └────────┬────────────────┘
                              │ GET /cours-actions/liste
                              ▼
┌──────────────────────────────────────────────┐
│       GitHub Actions (toutes les 15 min)     │
│         update_brvm_db.py                    │
├──────────────────────────────────────────────┤
│              dbintraday/{TICKER}.csv          │ ◄── Snapshots 15-min
│              (timestamp, cours, volume)       │
└──────────────────────────────────────────────┘
                              │ 17:05 (clôture)
                              ▼
┌──────────────────────────────────────────────┐
│            finalize_eod.py                   │
│   Calcule Open/High/Low/Close/Volume         │
├──────────────────────────────────────────────┤
│           dbhistorical/{TICKER}.csv           │ ◄── Base historique daily
│   (Date, Open, High, Low, Close, Volume,     │
│    Ticker, source, updated_at)               │
└──────────────────────────────────────────────┘
```

## Scripts

| Script | Usage | Rôle |
|---|---|---|
| `update_brvm_db.py` | `python update_brvm_db.py` | Snapshot 15-min (GH Actions) |
| `finalize_eod.py` | `python finalize_eod.py` | Calcul OHLCV de clôture |
| `init_brvm_db.py` | `python init_brvm_db.py` | Import historique depuis GitHub (one-time) |

## Installation

```bash
pip install -r requirements.txt
```

## Exécution locale

```bash
# Initialiser la base historique (47 tickers depuis 1998)
python init_brvm_db.py

# Lancer un snapshot manuel
python update_brvm_db.py

# Finaliser la journée (calcul OHLCV)
python finalize_eod.py
```
