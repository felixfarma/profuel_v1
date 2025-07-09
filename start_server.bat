@echo off
REM — Comprueba si existe el entorno virtual, si no lo crea —
if not exist venv\Scripts\activate.bat (
    echo Entorno virtual no encontrado. Creando venv...
    python -m venv venv
)

REM — Activa el entorno virtual —
call venv\Scripts\activate.bat

REM — Instala dependencias (solo la primera vez o tras cambios en requirements) —
pip install -r requirements.txt

REM — Define variables de entorno para Flask —
set FLASK_APP=app/run.py
set FLASK_ENV=development

REM — Arranca el servidor Flask —
flask run

pause
