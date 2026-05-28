# BRVM Data Scraper

Scraping automatisé des données boursières de la BRVM via GitHub Actions.

## Architecture

```
                     ┌─────────────────────────┐
                     │   brvm.org (site officiel)│
                     └────────┬────────────────┘
                              │ GET /cours-actions/liste
                              ▼
┌──────────────────────────────────────────────┐
│     GitHub Actions (toutes les 15 min)      │
│         09:05 → 15:50 UTC (lun-ven)         │
│         update_brvm_db.py                    │
├──────────────────────────────────────────────┤
│              dbintraday/{TICKER}.csv          │ ◄── Snapshots 15-min
│              (timestamp, cours, volume)       │
└──────────────────────────────────────────────┘
                              │ 16:05 (EOD)
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

## Horaires de cotation BRVM (UTC)

| Phase | Horaire |
|---|---|
| Pré-ouverture | 09:00 → 09:45 |
| Fixing d'ouverture | 09:45 |
| Négociation continue | 09:45 → 14:00 |
| Pré-clôture | 14:00 → 14:30 |
| Fixing de clôture | 14:30 |
| Dernier cours | 14:30 → 15:00 |
| Clôture officielle | **15:00** |

Les snapshots couvrent 09:05 → 15:50. L'EOD est calculé à 16:05.

## Scripts

| Script | Usage | Rôle |
|---|---|---|
| `update_brvm_db.py` | `python update_brvm_db.py` | Snapshot 15-min (GH Actions) |
| `finalize_eod.py` | `python finalize_eod.py` | Calcul OHLCV de clôture |
| `init_brvm_db.py` | `python init_brvm_db.py` | Import historique depuis GitHub (one-time) |

## Workflows GitHub Actions

| Workflow | Déclencheur | Fichier |
|---|---|---|
| Scrape BRVM Intraday | `5,20,35,50 9-15 * * 1-5` | `.github/workflows/scrape-intraday.yml` |
| Finalize EOD BRVM | `5 16 * * 1-5` | `.github/workflows/finalize-eod.yml` |

## Base de données

- **47 tickers** couvrant la période **16 sept 1998 → aujourd'hui**
- **154 000+ lignes** de données OHLCV quotidiennes
- Source historique : `github` (import initial), source temps réel : `live` (snapshots)
- Données stockées en CSV dans `dbhistorical/` et `dbintraday/`

## Robustesse

- **Parsing HTML** : détection du tableau par comptage de lignes valides (7 colonnes + ticker), résistant aux changements de structure `<th>`/`<td>`
- **SSL** : `verify=False` (le certificat du site BRVM n'est pas reconnu par les CA standards)
- **Validation** : regex `^[A-Z]{2,5}$` sur chaque ticker, cours non numériques loggés
- **Seuil minimum** : 3 snapshots requis avant calcul EOD (évite les OHLCV à plat)
- **Retry** : backoff exponentiel sur erreur 429, 3 tentatives max
- **Alerte** : création automatique d'une Issue GitHub en cas d'échec d'un workflow

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
