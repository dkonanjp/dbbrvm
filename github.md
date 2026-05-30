# Plan d'implémentation — Collecte BRVM fiable

## Problème

Le cron GitHub Actions (`schedule`) ne déclenche pas les runs de façon fiable.
Aujourd'hui 29 mai 2026 : 0 run schedule sur la période 9h-10h UTC.
Hier 28 mai : runs schedule arrivés avec 13 min à 2h de retard.

Les 2 runs manuels (`workflow_dispatch`) à 09:32 et 09:34 ont fonctionné
(le premier a échoué au push, le second a réussi).

## Solution

Remplacer le cron GH par un service externe gratuit (cron-job.org)
qui appelle l'API GitHub pour déclencher `workflow_dispatch`.

### Étapes

#### 1. Créer un token GitHub

- Aller sur https://github.com/settings/tokens
- "Generate new token (classic)"
- Cocher : `repo` (toutes) + `workflow`
- Générer et copier le token (commence par `ghp_`)

#### 2. Créer un compte cron-job.org

- Aller sur https://cron-job.org
- S'inscrire (gratuit, sans carte)

#### 3. Créer le cron job

Paramètres :

| Champ | Valeur |
|-------|--------|
| **URL** | `https://api.github.com/repos/dkonanjp/dbbrvm/actions/workflows/scrape-intraday.yml/dispatches` |
| **Method** | `POST` |
| **Custom Headers** | `Authorization: Bearer <TON_TOKEN_GITHUB>` |
| | `Content-Type: application/json` |
| | `Accept: application/vnd.github.v3+json` |
| **Request Body** | `{"ref":"main"}` |
| **Schedule** | `5,20,35,50 9-15 * * 1-5` (le code ignore avant 09:50 et après 15:05) |
| **Timezone** | `UTC` |

#### 4. Activer le cron

- Une fois créé, activer le job depuis le dashboard cron-job.org

### Optionnel : corriger l'échec de push

✅ Déjà fait — push sécurisé avec retry loop (3 tentatives, `--autostash`).

Modifications appliquées dans :
- `.github/workflows/scrape-intraday.yml`
- `.github/workflows/finalize-eod.yml`

### Vérification

- Les runs apparaîtront sur https://github.com/dkonanjp/dbbrvm/actions
- Les données dans `logs/_scrape_log.csv` et `dbintraday/`
- Temps réel entre chaque run : ~15 min (au lieu des retards GH)

### Remarque

Le cron GH actuel peut être gardé comme backup (ne coûte rien).
C'est cron-job.org qui sera le déclencheur principal.
