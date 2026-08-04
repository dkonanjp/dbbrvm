# BRVM Trading Platform

Plateforme de trading automatisée pour la Bourse Régionale des Valeurs Mobilières (BRVM).

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Scraper   │────▶│  PostgreSQL │◀────│    API      │
│  (15 min)   │     │   (5433)    │     │  (8000)     │
└─────────────┘     └─────────────┘     └─────────────┘
                           ▲
┌─────────────┐            │
│  Indicateurs│────────────┘
│   (6h)      │
└─────────────┘
                           ▲
┌─────────────┐            │
│   Grafana   │────────────┘
│   (3000)    │
└─────────────┘
```

## Services

| Service | Port | Description |
|---------|------|-------------|
| PostgreSQL | 5433 | Base de données |
| Grafana | 3000 | Tableau de bord |
| FastAPI | 8000 | API REST |
| GitLab | 8088 | Miroir GitHub |
| Redis | 6380 | Cache |

## Installation Rapide

```bash
# Cloner le repo
git clone https://github.com/dkonanjp/dbbrvm.git
cd dbbrvm/nas_deploy

# Lancer l'installation
./install.sh 192.168.1.64 2202 dkonan
```

## Gestion

```bash
./deploy.sh start    # Démarrer
./deploy.sh stop     # Arrêter
./deploy.sh restart  # Redémarrer
./deploy.sh status   # État
./deploy.sh logs     # Logs
./deploy.sh update   # Mettre à jour
```

## Accès

| Service | URL | Identifiants |
|---------|-----|--------------|
| Grafana | http://192.168.1.64:3000 | admin / admin123 |
| API | http://192.168.1.64:8000/docs | - |
| Dashboard | http://192.168.1.64:3000/d/brvm-main-dashboard | - |

## API Endpoints

```
GET /              → Status
GET /health        → Santé
GET /tickers       → Liste des tickers
GET /daily         → Données quotidiennes
GET /market_data   → Données intraday
GET /stats         → Statistiques
GET /ticker/{id}   → Détail d'un ticker
```

## Données

- **47 tickers** BRVM
- **156 828 lignes** quotidiennes (1998-2026)
- **48 457 lignes** intraday
- **155 717 indicateurs** techniques
- **191 860 signaux** trading

## Indicateurs Techniques

- SMA (20, 50, 200)
- EMA (12, 26)
- RSI (14)
- MACD (12, 26, 9)
- Bollinger Bands (20, 2)
- Stochastique (14)
- ATR (14)
- OBV
- VWAP

## Signaux

| Signal | Description |
|--------|-------------|
| BUY | Signal d'achat (RSI < 30, MACD haussier, etc.) |
| SELL | Signal de vente (RSI > 70, MACD baissier, etc.) |
| HOLD | Aucun signal fort |

## Structure du Projet

```
nas_deploy/
├── install.sh              # Script d'installation
├── deploy.sh               # Script de gestion
├── docker-compose.yml      # Stack Docker
├── .env.example            # Variables d'environnement
├── db/
│   └── init.sql            # Schéma base de données
├── scraper/
│   ├── Dockerfile
│   ├── scraper.py          # Script de scraping
│   ├── indicators.py       # Calcul complet
│   └── indicators_incr.py  # Calcul incrémental
├── api/
│   ├── Dockerfile
│   ├── main.py             # FastAPI
│   └── requirements.txt
└── grafana/
    └── provisioning/       # Configuration auto
```

## License

Projet privé - Usage interne uniquement.
