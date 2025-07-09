@echo off
REM — 1. Asegurarse de estar en la carpeta del proyecto —
cd /d %~dp0

REM — 2. Crear .gitignore si no existe —
if not exist .gitignore (
  echo venv/> .gitignore
  echo __pycache__/>> .gitignore
  echo *.py[cod]>> .gitignore
  echo .env>> .gitignore
  echo node_modules/>> .gitignore
)

REM — 3. Crear README.md si no existe —
if not exist README.md (
  (
    echo # FuelMe
    echo Proyecto Flask para seguimiento de nutrición y sincronización con Strava.
    echo.
    echo ## Instalación
    echo ```
    echo python -m venv venv
    echo call venv\Scripts\activate.bat
    echo pip install -r requirements.txt
    echo set FLASK_APP=app/run.py
    echo set FLASK_ENV=development
    echo flask run
    echo ```
  ) > README.md
)

REM — 4. Inicializar Git (si no está inicializado) y configurar ramas —
git init
git add .gitignore README.md
git commit -m "chore: add .gitignore and README for project setup"

REM — 5. Crear y cambiar a develop —
git branch -M master main
git checkout -b develop

REM — 6. Primer commit en develop —
git push -u origin develop

REM — 7. Instalar pre-commit y crear configuración básica —
pip install pre-commit
if not exist .pre-commit-config.yaml (
  (
    echo repos:
    echo "-   repo: https://github.com/psf/black"
    echo "    rev: 23.3.0"
    echo "    hooks:"
    echo "    -   id: black"
    echo "-   repo: https://gitlab.com/pycqa/flake8"
    echo "    rev: 6.0.0"
    echo "    hooks:"
    echo "    -   id: flake8"
  ) > .pre-commit-config.yaml
)
pre-commit install

echo.
echo ===== Configuración Git completada =====
echo - Ramas: main (deployable) y develop (desarrollo).
echo - .gitignore y README.md añadidos.
echo - pre-commit instalado para Black y flake8.
echo.
pause
