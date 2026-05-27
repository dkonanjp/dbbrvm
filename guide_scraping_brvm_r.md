# Guide : Pipeline R — Scraping BRVM Direct

Deux pipelines R coexistent pour collecter les données de la Bourse Régionale des Valeurs Mobilières (BRVM).

---

## 📦 Packages R requis

```r
install.packages(c("rvest", "httr", "dplyr", "readr", "lubridate", "glue", "DBI", "RPostgres"))
```

---

## 🔵 Pipeline 1 : Scraping direct BRVM (temps réel)

Scrape `www.brvm.org/fr/cours-actions/liste` et stocke dans des CSV.

### Architecture

```
www.brvm.org/fr/cours-actions/liste
        │
        ▼  GET (User-Agent navigateur)
   rvest parse <table>
        │
        ▼  47 tickers, 7 colonnes
   Symbole | Nom | Volume | Cours Veille | Ouverture | Clôture | Variation
        │
        ▼  Upsert par ticker
   R_scraping_lab/data/{TICKER}.csv
```

### Scripts

**`init_brvm_db.R`** — Import historique one-time depuis GitHub (154 619 lignes)
```bash
Rscript R_scraping_lab/init_brvm_db.R
```
- Source : `raw.githubusercontent.com/Fredysessie/brvm-data-public/`
- 47 tickers, données daily depuis 1998
- Colonnes : `Date, Open, High, Low, Close, Volume, Ticker, source, updated_at`

**`update_brvm_db.R`** — Scraping temps réel (toutes les 15 min)
```bash
Rscript R_scraping_lab/update_brvm_db.R
```
- Scrape les 47 actions en une requête
- Remplace la ligne du jour dans chaque CSV
- Trace chaque scraping dans `_scrape_log.csv`

### Format CSV
```csv
Date,Open,High,Low,Close,Volume,Ticker,source,updated_at
2026-05-26,28800,28800,28800,28500,2514,SNTS,brvm_live,2026-05-26T10:45:22Z
```

- `source=github` : données historiques
- `source=brvm_live` : scraping temps réel

---

## 🟡 Pipeline 2 : Package R `BRVM` (production → PostgreSQL)

Alimente la base PostgreSQL via le package CRAN `BRVM` (qui utilise l'API Sika Finance en backend).

```bash
cd backend
Rscript update_brvm_daily.R       # BRVM_get() → données OHLCV
python sync_daily_r.py            # Upsert PostgreSQL + recalcule indicateurs
```

### Automation (macOS launchd)
```xml
~/.plist → Lun-Ven 16:50 → Rscript + sync_daily_r.py
```

---

## 📊 Comparaison des pipelines

| Critère | Pipeline 1 (BRVM direct) | Pipeline 2 (Package R) |
|---------|-------------------------|----------------------|
| Source | `www.brvm.org` (officiel) | Sika Finance (agrégateur) |
| Fréquence | Toutes les 15 min | 1×/jour (16:50) |
| Stockage | CSV (`R_scraping_lab/data/`) | PostgreSQL |
| Dépendances | `rvest` + `httr` | Package R `BRVM` + RPostgres |
| Risque | Site BRVM change → casser | Sika change → casser |
| Snapshot | Instantané (cours du moment) | OHLCV journée complète |

---

## 🔄 Évolution des sources

| Source | Usage | Statut |
|--------|-------|--------|
| `sikafinance.com/api/general/GetHistos` | Scraping runtime (`scraper.py`) | ❌ Supprimé |
| `www.richbourse.com` | Script one-time (`scrape_richbourse.py`) | ❌ Supprimé |
| `raw.githubusercontent.com/Fredysessie/brvm-data-public` | Import historique CSV | ✅ GitHub → CSV |
| `www.brvm.org/fr/cours-actions/liste` | Scraping temps réel R | ✅ Actif |
| Package R `BRVM` | Pipeline PostgreSQL | ✅ Existant |

---

## 🧪 Test manuel

```bash
# 1. Tester l'URL BRVM
curl -s https://www.brvm.org/fr/cours-actions/liste | grep -c "table"

# 2. Lancer l'init historique
cd R_scraping_lab && Rscript init_brvm_db.R

# 3. Lancer un scraping live
cd R_scraping_lab && Rscript update_brvm_db.R

# 4. Vérifier les données
head -3 data/SNTS.csv
cat data/_scrape_log.csv
```
