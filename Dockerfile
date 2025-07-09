# Dockerfile

# 1. Base image con Python 3.11
FROM python:3.11-slim

# 2. Evitar archivos .pyc y habilitar logs inmediatos
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# 3. Directorio de trabajo
WORKDIR /app

# 4. Copiar e instalar dependencias (incluido Gunicorn)
COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install -r requirements.txt

# 5. Copiar el código de la app
COPY . .

# 6. Exponer el puerto 5000
EXPOSE 5000

# 7. Comando por defecto: lanzar Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "run:app"]
