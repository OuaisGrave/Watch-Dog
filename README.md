# Discord Bot Monitor (Python)

Ce dépôt contient un bot Discord autonome en Python qui surveille un autre bot (UP/DOWN) et poste uniquement dans le salon 📉-down-bot.

## Fichiers importants
- `main.py` : le code principal (utilise .env)
- `status.json` : garde en mémoire le dernier statut
- `.env` : fichier pour stocker ton token et IDs (NE PAS publier)
- `requirements.txt` : dépendances
- `Procfile` : pour deploy sur Render

## Sécurité
Le token **NE DOIT JAMAIS** être poussé sur GitHub. Utilise le fichier `.env` localement et ajoute `.env` à ton `.gitignore`.

## Exemple .env (remplis avec tes valeurs)
```
DISCORD_TOKEN=ton_token_ici
GUILD_ID=123456789012345678
TARGET_BOT_ID=234567890123456789
CHANNEL_ID=1434510458315997325
MEMBRE_ROLE_ID=1402041174298198188
BOT_ROLES_ROLE_ID=1401997139675975792
PORT=3000
```

## Déploiement sur Render
- Pousse le repo sur GitHub
- Crée un Web Service sur Render
- Build Command: `pip install -r requirements.txt`
- Start Command: `python main.py`
- Ajoute les variables d'environnement sur Render (ou utilise .env localement pour tests)
- Crée un Cron Job qui ping `/ping` toutes les 5 minutes
