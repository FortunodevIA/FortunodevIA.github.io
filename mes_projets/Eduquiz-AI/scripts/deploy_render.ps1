Param(
    [string]$SecretKey = "",
    [string]$ServiceId = "",
    [switch]$Deploy
)

Write-Host "--- Début du script de déploiement EduQuiz (PowerShell) ---"

if (Test-Path ".\env\Scripts\Activate.ps1") {
    Write-Host "Activation du virtualenv..."
    . .\env\Scripts\Activate.ps1
} else {
    Write-Host "Virtualenv non trouvé dans .\env. Assure-toi d'exécuter depuis la racine du projet." -ForegroundColor Red
    exit 1
}

Write-Host "(optionnel) Installation des dépendances si nécessaire..."
python -m pip install -r requirements.txt

if ($SecretKey -ne "") {
    Write-Host "SECRET_KEY fourni en paramètre. Garde cette valeur secrète."
    Write-Host "Pour l'ajouter sur Render (UI) : Web Service → Environment → Add Environment Variable → Name=SECRET_KEY, Value=<la clé>"
}

Write-Host "Exécution des migrations..."
python manage.py migrate --noinput

Write-Host "Collectstatic..."
python manage.py collectstatic --noinput

Write-Host "Lancer la suite de tests rapides..."
python manage.py test

if ($Deploy) {
    $renderCmd = Get-Command render -ErrorAction SilentlyContinue
    if ($null -eq $renderCmd) {
        Write-Host "Le Render CLI n'est pas installé ou non trouvé dans le PATH. Installe via 'npm i -g @render/cli' puis 'render login'" -ForegroundColor Yellow
        exit 1
    }

    if ($ServiceId -eq "") {
        Write-Host "Aucun ServiceId fourni. Utilise 'render services' pour lister, puis relance avec -ServiceId <ID>" -ForegroundColor Yellow
        exit 1
    }

    Write-Host "Déclenchement du déploiement via Render CLI pour le service : $ServiceId"
    render services deploy $ServiceId
}

Write-Host "--- Fin du script ---"
