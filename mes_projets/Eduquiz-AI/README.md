# EduQuiz AI

EduQuiz AI est une application Django qui transforme des documents PDF de cours en quiz interactifs.
Le projet supporte l'extraction de texte, la génération de résumés et la création de QCM dynamiques.

## Fonctionnalités
- Upload sécurisé de PDFs et extraction de texte
- Génération automatique de quiz depuis le contenu de cours
- Résumé et mots-clés générés automatiquement
- Historique des quiz et correction détaillée
- Compatibilité avec IA Anthropic pour une meilleure génération de questions

## Installation
1. Copier le modèle d'environnement :

```powershell
copy .env.example .env
```

2. Installer les dépendances :

```powershell
python -m pip install -r requirements.txt
```

3. Définir les variables d'environnement dans `.env` :
- `SECRET_KEY` : clé secrète Django en production
- `DEBUG=False` en production
- `ALLOWED_HOSTS=localhost,127.0.0.1,votre-domaine.com`
- `DATABASE_URL` : URL PostgreSQL (fortement recommandé sur Render)
- `ANTHROPIC_API_KEY` et `ANTHROPIC_MODEL` : pour activer la génération IA (optionnel)

4. Appliquer les migrations :

```powershell
python manage.py migrate
```

5. Lancer le serveur de développement :

```powershell
python manage.py runserver
```

## Tests
Exécuter les tests Django :

```powershell
python manage.py test
```

## Déploiement
- Le projet utilise `gunicorn` dans `Procfile`
- Les fichiers statiques sont servis avec `whitenoise`
- Render peut utiliser `render.yaml` pour créer le service et la base PostgreSQL.
- Dans Render, ajoutez ou vérifiez les variables d'environnement suivantes :
  - `SECRET_KEY` : clé secrète Django
  - `DEBUG=False`
  - `DATABASE_URL` : PostgreSQL fourni par Render
  - `ANTHROPIC_API_KEY` et `ANTHROPIC_MODEL` si vous voulez activer la génération IA

> Render expose automatiquement `RENDER_EXTERNAL_HOSTNAME`, donc le projet ajoutera ce domaine à `ALLOWED_HOSTS` et `CSRF_TRUSTED_ORIGINS`.

### Commandes Render
- Le build `render.yaml` exécute `pip install -r requirements.txt` puis `python manage.py collectstatic --noinput`.
- Le démarrage exécute `python manage.py migrate --noinput && gunicorn --workers 3 eduquiz.wsgi:application`.

### Conseils de stabilité
- Ne pas utiliser SQLite en production : c'est le principal risque de plantage avec plusieurs utilisateurs.
- Choisis PostgreSQL sur Render et garde `DEBUG=False`.
- `gunicorn` avec plusieurs workers permet de gérer plusieurs connexions simultanées.
- L'application est conçue pour être stateless côté utilisateur : chaque requête est traitée individuellement, donc elle peut supporter plusieurs personnes en même temps si le service Render a assez de ressources.

## Bonnes pratiques
- Ne stockez jamais `SECRET_KEY` dans le dépôt
- Ignorez `db.sqlite3`, `media/`, `env/`, `.venv/` et `.env`
- Activez `DEBUG=False` en production
