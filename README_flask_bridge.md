# Flask Bridge

Ce module ajoute un petit serveur Flask permettant de piloter le scraping à
l'aide d'appels HTTP.  Il peut être lancé depuis l'onglet **Serveur Flask** de
l'application.

## Démarrage
1. Lancez l'application graphique `app.py`.
2. Rendez-vous dans l'onglet *Serveur Flask*.
3. Choisissez un port et une clé API puis cliquez sur **Démarrer**.
4. Optionnel : cochez *Expose via ngrok* pour obtenir une URL publique.

L'API key est également lue depuis la variable d'environnement
``SCRAPER_API_KEY``.  Pour ngrok, la variable ``NGROK_AUTHTOKEN`` est prise en
compte si aucun jeton n'est saisi.

## Configuration en ligne de commande
1. Installez les dépendances : `pip install -r requirements.txt`.
2. Définissez les variables d'environnement :
   ```bash
   export SCRAPER_API_KEY=VOTRE_CLE
   export NGROK_AUTHTOKEN=VOTRE_JETON  # optionnel
   ```
3. Lancez le serveur :
   ```bash
   python localapp/app.py
   ```
   Dans l'onglet **Serveur Flask**, cliquez sur **Démarrer**.

Les fichiers générés sont attendus aux emplacements suivants :
- `export/products_export.csv`
- `generated.json`

## Test de l'API
Une fois le serveur lancé, l'endpoint `/health` répond sans authentification.

```bash
# Vérification basique
curl http://localhost:5001/health

# Liste des fichiers d'un dossier
curl -H "X-API-KEY: $SCRAPER_API_KEY" \
     "http://localhost:5001/files/list?folder=sample_folder"

# Récupération d'une image
curl -H "X-API-KEY: $SCRAPER_API_KEY" \
     "http://localhost:5001/files/raw?folder=sample_folder&name=exemple.jpg" \
     --output exemple.jpg

# Lecture d'une fiche produit sauvegardée
curl -H "X-API-KEY: $SCRAPER_API_KEY" \
     "http://localhost:5001/products?path=generated.json"
# ou pour un export CSV
# curl -H "X-API-KEY: $SCRAPER_API_KEY" \
#      "http://localhost:5001/products?path=export/products_export.csv"

# Lancement d'un scraping
curl -X POST -H "Content-Type: application/json" -H "X-API-KEY: $SCRAPER_API_KEY" \
     -d '{"url": "https://exemple.com", "selector": "img"}' \
     http://localhost:5001/scrape

# Vérification d'un job
curl -H "X-API-KEY: $SCRAPER_API_KEY" http://localhost:5001/jobs/<job_id>

# Traitement d'images
curl -X POST http://localhost:5001/actions/image-edit \
     -H "X-API-KEY: $SCRAPER_API_KEY" -H "Content-Type: application/json" \
     -d '{"source":{"folder":"/path/images"},"operations":[{"op":"resize","width":1024,"height":1024,"keep_ratio":true}]}'
```

Les réponses pour les autres endpoints (`/scrape`, `/jobs`, `/profiles`,
`/history`) nécessitent le header `X-API-KEY`.
