@echo off
REM ------------------------------------------------------------
REM  Expert Cleanup & Git Setup for FuelMe Repository
REM  Uso: Coloca este archivo en la raíz del proyecto y ejecuta:
REM       C:\Users\felix\profuel\profuel_v7_1> clean_and_setup.bat
REM ------------------------------------------------------------

REM 1. Sobrescribe .gitignore con reglas estándar Python/Flask
echo Generando .gitignore...
(
  echo # Entornos virtuales
  echo venv/
  echo .venv/
  echo
  echo # Cachés y compilados
  echo __pycache__/
  echo *.py[cod]
  echo .pytest_cache/
  echo
  echo # Base de datos de ejemplo
  echo instance/*.db
  echo
  echo # Variables de entorno
  echo .env
  echo
  echo # Dependencias JS (si las hubiera)
  echo node_modules/
) > .gitignore

REM 2. Asegura carpeta tests y mueve conftest.py
echo Moviendo conftest.py a tests\...
if not exist tests (
  md tests
)
if exist conftest.py (
  git mv conftest.py tests\conftest.py
)

REM 3. Elimina (del árbol de git) archivos/carpetas que NO deben versionarse
echo Eliminando del repositorio entornos y bases de datos versionadas...
git rm -r --cached venv .venv __pycache__ .pytest_cache instance\profuel.db .en >NUL 2>&1

REM 4. Asegura que solo quede un run.py
echo Comprobando duplicados de entrypoint...
if exist run.py (
  echo \- Manteniendo run.py en la raíz.
) 
if exist app\run.py (
  echo \- Eliminando app\run.py duplicado...
  del app\run.py
  git rm --cached app\run.py >NUL 2>&1
)

REM 5. Stage de todos los cambios y commit inicial
echo Haciendo commit de limpieza y estructura base...
git add --all
git commit -m "chore: limpiar estructura de proyecto y ajustar .gitignore"

echo.
echo ===== Repositorio limpio y organizado =====
echo Ramas: main (deployable) y develop (prepárate para crear feature/*).
echo .gitignore actualizado, conftest.py movido, entornos versionados eliminados.
echo =============================================
pause
