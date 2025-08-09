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

## Test de l'API
Une fois le serveur lancé, l'endpoint `/health` répond sans authentification.

```bash
# Exemples de commandes curl
# curl http://localhost:5001/health
# curl -X POST -H "Content-Type: application/json" -H "X-API-KEY: VOTRE_CLE" \
#      -d '{"url": "https://exemple.com", "selector": "img"}' \
#      http://localhost:5001/scrape
# curl -H "X-API-KEY: VOTRE_CLE" http://localhost:5001/jobs/<job_id>
```

Les réponses pour les autres endpoints (`/scrape`, `/jobs`, `/profiles`,
`/history`) nécessitent le header `X-API-KEY`.
