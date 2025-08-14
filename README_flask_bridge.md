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

### Exemples API (tests rapides)

```bash
# Lister les fichiers d'un alias (images_root)
curl -H "X-API-KEY: dev-key" "https://YOUR_PUBLIC_DOMAIN/files/list?folder=images_root"

# Lister les produits (dossiers)
curl -H "X-API-KEY: dev-key" "https://YOUR_PUBLIC_DOMAIN/products"

# Images d'un produit (ex: 'bob avec lacet' → slug 'bob-avec-lacet')
curl -H "X-API-KEY: dev-key" "https://YOUR_PUBLIC_DOMAIN/products/bob-avec-lacet/images"

# Sauvegarder une fiche produit
curl -X POST -H "Content-Type: application/json" -H "X-API-KEY: dev-key" \
  -d '{ "name":"Bob avec lacet jaune", "short_description":"...", "description":"...", "categories":["Bobs"], "tags":["lacet","été"], "regular_price":"", "sale_price":"", "slug":"bob-avec-lacet", "focus_keyword":"bob avec lacet jaune", "meta_title":"Bob avec lacet jaune", "meta_description":"", "internal_link":"" }' \
  "https://YOUR_PUBLIC_DOMAIN/products/bob-avec-lacet/descriptions"
```
