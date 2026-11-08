# Cahier de vacances Machine Learnia

Bienvenue dans le cahier de vacances Machine Learnia !

Chaque dimanche de l'été, un mini projet est publié. L'objectif est de pratiquer de façon concrète et progressive, les bases de l'analyse de données, le ML classique en passant par les RAG, et les graphes.

## Structure du repo

Chaque projet a son propre dossier, qui regroupe toutes ses ressources (notebook, données, images) :

```
cahier-de-vacances/
├── Projet_01/
│   └── projet_01.ipynb
├── Projet_02/
│   └── ...
├── pyproject.toml
└── README.md
```

## Faire le cahier de vacances depuis le début

### Étape 1 : cloner le projet

La première chose à faire est de récupérer le projet sur votre ordinateur. Ouvrez un terminal, placez-vous dans le dossier de votre choix et tapez :

```shell
git clone https://github.com/MachineLearnia/Cahier-Vacances-2026.git
```

Un dossier `Cahier-Vacances-2026` apparaît, c'est votre copie locale du projet. C'est aussi grâce à git que vous récupérerez les nouveaux projets chaque semaine (on en reparle plus bas).

### Étape 2 : installer uv

Pour l'environnement python, vous pouvez utiliser celui que vous préférez si vous êtes à l'aise avec, mais sinon, nous utiliserons le gestionnaire [`uv`](https://docs.astral.sh/uv/) qui est un outil récent et très populaire. Pour le télécharger, cela dépend de votre système d'exploitation. Si vous êtes sur Linux, MacOS ou WSL ouvrez votre terminal et tapez :

```shell
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Si vous êtes sur Windows ouvrez le powershell et tapez :

```shell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### Étape 3 : créer l'environnement

Le repo contient déjà tout ce qu'il faut pour construire l'environnement : le fichier `pyproject.toml` (qui décrit le projet et ses dépendances) et le fichier `.python-version` (qui fixe la version de python, ici la 3.13.2). Autrement dit, pas besoin d'initialiser quoi que ce soit, il suffit de demander à `uv` de tout construire.

Ouvrez un terminal à la racine du dossier `Cahier-Vacances-2026` (dans vscode, clique droit sur le dossier puis "open in integrated terminal") et tapez :

```shell
uv sync
```

`uv` va télécharger la bonne version de python si elle n'est pas déjà sur votre machine, puis créer un dossier `.venv`, c'est notre environnement ! Certains projets vous demanderont d'ajouter une librairie avec `uv add`, ce sera toujours indiqué dans le notebook.

### Étape 4 : ouvrir les notebooks et travailler

Ouvrez le dossier dans votre éditeur (par exemple vscode avec les extensions Python et Jupyter), puis ouvrez le notebook du projet en cours. En haut à droite, cliquez sur "Select Kernel" et choisissez l'environnement du projet (celui qui mentionne `.venv`).

Dans les notebooks il y a des blocs balisés `### START CODE HERE ###` / `### END CODE HERE ###`, ce sont les blocs à remplir ! Il faut compléter entre les deux lignes. Une fois fini il suffit de lancer la cellule de code, puis de voir si les tests passent.

## Récupérer les projets des semaines suivantes

Un nouveau projet est publié chaque dimanche de l'été. Pour le récupérer, ouvrez un terminal à la racine du dossier et tapez :

```shell
git pull
```

Le nouveau dossier `Projet_XX` apparaît, et vous pouvez vous lancer. Les projets déjà publiés ne sont jamais modifiés, donc votre travail dans les notebooks précédents ne sera pas écrasé et vous ne devriez pas rencontrer de conflit.

*Bonne pratique, et bon été !*
