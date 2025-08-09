# Manual Profiles Test

1. Lancer l'application Qt et démarrer le serveur Flask depuis l'onglet dédié.
2. Depuis un terminal ou Postman, envoyer :
   ```bash
   curl -X POST https://<ngrok>.ngrok-free.app/profiles \
        -H "X-API-KEY: <CLE>" -H "Content-Type: application/json" \
        -d '{"name":"Test","selector":".img-class"}'
   ```
3. Vérifier que la réponse HTTP est `201` et que le profil "Test" apparaît immédiatement dans l'onglet Profil Scraping.
4. Répéter la requête POST identique : la réponse doit être `409` et aucun doublon ne doit apparaître dans l'UI.
5. Tester la route de liste :
   ```bash
   curl -X GET https://<ngrok>.ngrok-free.app/profiles -H "X-API-KEY: <CLE>"
   ```
   Le profil "Test" doit être présent dans le JSON retourné.
