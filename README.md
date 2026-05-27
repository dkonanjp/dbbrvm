# BRVM Data Scraper

Scraping automatisé des données boursières de la BRVM (Bourse Régionale des Valeurs Mobilières) avec stockage intraday 15-min et calcul OHLCV journalier.

## Architecture

```
                     ┌─────────────────────────┐
                     │   brvm.org (site officiel)│
                     └────────┬────────────────┘
                              │ GET /cours-actions/liste
                              ▼
┌──────────────────────────────────────────────┐
│        GitHub Actions (toutes les 15 min)     │
│         update_brvm_db.R                      │
├──────────────────────────────────────────────┤
│              data/intraday/{TICKER}.csv        │ ◄── Snapshots 15-min
│              (timestamp, ouverture, cloture,   │
│               volume)                          │
└──────────────────────────────────────────────┘
                              │ 17:05 (clôture)
                              ▼
┌──────────────────────────────────────────────┐
│            finalize_eod.R                     │
│   Calcule Open/High/Low/Close/Volume          │
├──────────────────────────────────────────────┤
│           data/{TICKER}.csv                    │ ◄── Base historique daily
│   (Date, Open, High, Low, Close, Volume,      │
│    Ticker, source, updated_at)                 │
└──────────────────────────────────────────────┘
```

## Base de données

### data/{TICKER}.csv — Historique daily (OHLCV)
| Colonne | Description |
|---|---|
| Date | Date de la séance |
| Open | Premier cours |
| High | Plus haut du jour |
| Low | Plus bas du jour |
| Close | Dernier cours |
| Volume | Volume échangé |
| Ticker | Symbole (ex: SNTS) |
| source | `github` (historique) ou `live` (calculé) |
| updated_at | Dernière mise à jour |

### data/intraday/{TICKER}.csv — Snapshots 15-min
| Colonne | Description |
|---|---|
| Ticker | Symbole |
| Date | Date du snapshot |
| Timestamp | Heure exacte (YYYY-MM-DD HH:MM:SS) |
| Cours_Ouverture | Prix d'ouverture au moment du snapshot |
| Cours_Cloture | Dernier cours au moment du snapshot |
| Volume | Volume cumulé |

## Workflows GitHub Actions

| Workflow | Déclencheur | Action |
|---|---|---|
| `scrape-intraday.yml` | Lun-Ven 09:20→16:50 UTC */15 min | Scrape brvm.org → append dans `data/intraday/` |
| `finalize-eod.yml` | Lun-Ven 17:05 UTC | Calcule OHLCV → complète `data/{TICKER}.csv` |

## Scripts

| Script | Usage | Rôle |
|---|---|---|
| `update_brvm_db.R` | `Rscript update_brvm_db.R` | Snapshot 15-min (GH Actions) |
| `finalize_eod.R` | `Rscript finalize_eod.R` | Calcul OHLCV de clôture |
| `init_brvm_db.R` | `Rscript init_brvm_db.R` | Import historique depuis GitHub (one-time) |

## Exécution locale

```bash
# Initialiser la base historique (47 tickers depuis 1998)
Rscript init_brvm_db.R

# Lancer un snapshot manuel
Rscript update_brvm_db.R

# Finaliser la journée (calcul OHLCV)
Rscript finalize_eod.R
```
