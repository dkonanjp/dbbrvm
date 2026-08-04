# Guide d'Installation - BRVM Trading Platform

## Prérequis

### Matériel
- Synology NAS avec DSM 7.4+
- Docker Station installé
- 4 Go RAM minimum
- 20 Go espace disque

### Logiciel
- Mac/Linux/Windows avec SSH
- Git
- Connexion réseau vers le NAS

## Étape 1 : Préparer le NAS

### 1.1 Activer SSH sur le NAS
1. Ouvrir **Panneau de configuration** → **Terminal & SNMP**
2. Cocher **Activer le service SSH**
3. Noter le port (par défaut 22)

### 1.2 Créer la clé SSH (si pas déjà fait)
```bash
ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519 -N "" -C "brvm-deploy"
```

### 1.3 Ajouter la clé sur le NAS
```bash
# Copier la clé publique
cat ~/.ssh/id_ed25519.pub

# Sur le NAS, dans DSM :
# 1. Ouvrir Terminal → SSH
# 2. Ajouter la clé publique dans authorized_keys
```

## Étape 2 : Cloner le Repository

```bash
git clone https://github.com/dkonanjp/dbbrvm.git
cd dbbrvm/nas_deploy
```

## Étape 3 : Lancer l'Installation

```bash
./install.sh <IP_NAS> <PORT_SSH> <UTILISATEUR>
```

### Exemple
```bash
./install.sh 192.168.1.64 2202 dkonan
```

### Ce que fait le script
1. Teste la connexion SSH au NAS
2. Crée l'arborescence `/volume1/docker/brvm/`
3. Transfère tous les fichiers
4. Construit les images Docker
5. Lance les 6 services
6. Propose d'importer les données historiques
7. Propose de configurer le miroir GitLab

## Étape 4 : Vérifier l'Installation

### 4.1 Vérifier les containers
```bash
./deploy.sh status
```

Résultat attendu :
```
NAMES           STATUS
brvm-postgres   Up (healthy)
brvm-grafana    Up
brvm-api        Up
brvm-scraper    Up
brvm-indicators Up
brvm-redis      Up
gitlab          Up (healthy)
```

### 4.2 Accéder aux services
- **Grafana** : http://192.168.1.64:3000
  - Login : `admin`
  - Mot de passe : `admin123`
- **API** : http://192.168.1.64:8000/docs
- **Dashboard** : http://192.168.1.64:3000/d/brvm-main-dashboard

### 4.3 Vérifier les données
```bash
# Nombre de lignes dans la base
docker exec brvm-postgres psql -U brvm_bot -d brvm -c "SELECT COUNT(*) FROM daily;"
# Résultat attendu : ~156 000
```

## Étape 5 : Configuration Optionnelle

### 5.1 Importer les données historiques
Si le script ne l'a pas fait :
```bash
# Cloner le repo de données
ssh dkonan@192.168.1.64 -p 2202
cd /tmp
git clone https://github.com/dkonanjp/dbbrvm.git

# Importer chaque ticker
for f in dbhistorical/*.csv; do
    ticker=$(basename "$f" .csv)
    docker exec -i brvm-postgres psql -U brvm_bot -d brvm \
        -c "\COPY daily(ticker, date, open, high, low, close, volume, variation) FROM '/dev/stdin' WITH CSV HEADER;" < "$f"
done
```

### 5.2 Configurer le miroir GitLab
```bash
# Activer le miroir sur GitLab
curl -X POST "http://192.168.1.64:8088/api/v4/projects/root%2Fbrvm-data/mirror/pull" \
    -H "PRIVATE-TOKEN: glpat-BEeoxnihJPizTAULoQ02VG86MQp1OjEH.01.0w1b5pe85"
```

### 5.3 Modifier les ports
Éditer le fichier `.env` :
```bash
PG_PORT=5433
REDIS_PORT=6380
API_PORT=8000
GRAFANA_PORT=3000
```

Puis redémarrer :
```bash
./deploy.sh restart
```

## Étape 6 : Utilisation Quotidienne

### Voir les logs
```bash
./deploy.sh logs
```

### Redémarrer un service
```bash
docker exec brvm-scraper restart
```

### Mettre à jour
```bash
git pull
./deploy.sh update
```

### Sauvegarder la base
```bash
docker exec brvm-postgres pg_dump -U brvm_bot brvm > backup_$(date +%Y%m%d).sql
```

## Dépannage

### Le container ne démarre pas
```bash
# Voir les logs
docker logs brvm-scraper

# Vérifier l'espace disque
df -h /volume1/docker
```

### Erreur de connexion à la base
```bash
# Vérifier que PostgreSQL tourne
docker exec brvm-postgres pg_isready -U brvm_bot

# Vérifier le mot de passe
docker exec brvm-postgres psql -U brvm_bot -d brvm -c "SELECT 1;"
```

### Grafana ne charge pas le dashboard
```bash
# Recréer le dashboard
docker cp grafana/add_indicators_panels.py brvm-scraper:/tmp/
docker exec brvm-scraper python /tmp/add_indicators_panels.py
```

### Le scraper ne collecte pas
```bash
# Vérifier la connectivité vers BRVM
docker exec brvm-scraper curl -s https://www.brvm.org | head -20

# Forcer un scrpe
docker exec brvm-scraper python /app/scraper.py
```

## Informations de connexion

### NAS Synology
| Paramètre | Valeur |
|---|---|
| IP | 192.168.1.64 |
| SSH Port | 2202 |
| Utilisateur | dkonan |
| Mot de passe | Yaki@1606 |

### PostgreSQL
| Paramètre | Valeur |
|---|---|
| Host | 192.168.1.64:5433 |
| Base | brvm |
| User | brvm_bot |
| Mot de passe | BrvmSecure2026! |

### Grafana
| Paramètre | Valeur |
|---|---|
| URL | http://192.168.1.64:3000 |
| Login | admin |
| Mot de passe | admin123 |

### GitLab
| Paramètre | Valeur |
|---|---|
| URL | http://192.168.1.64:8088 |
| Root password | cGhHO0tNOJXt9fe8QtI+HCk4pa72jpsNm4kTy7Ch7dw= |
| API Token | glpat-BEeoxnihJPizTAULoQ02VG86MQp1OjEH.01.0w1b5pe85 |

## Support

Pour toute question ou problème :
1. Consulter les logs : `./deploy.sh logs`
2. Vérifier ce README
3. Ouvrir une issue sur GitHub
