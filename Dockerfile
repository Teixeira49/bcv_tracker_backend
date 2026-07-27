# syntax=docker/dockerfile:1
#
# Imagen de la API de DolarTracker (FastAPI + Uvicorn).
# Base slim de Python; psycopg2-binary trae wheels, así que no se necesitan
# toolchains de compilación en la imagen.

FROM python:3.12-slim

# - PYTHONUNBUFFERED: logs sin buffer (se ven en tiempo real en `docker logs`).
# - PYTHONDONTWRITEBYTECODE: no generar .pyc dentro del contenedor.
# - PIP_*: instalación limpia y silenciosa.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Se copian primero solo las dependencias para aprovechar la caché de capas:
# el `pip install` solo se re-ejecuta si cambia requirements.txt.
COPY requirements.txt ./
RUN pip install -r requirements.txt

# Código de la aplicación (el .dockerignore excluye venv, .git, .env, etc.).
COPY . .

# Ejecuta como usuario sin privilegios (no-root) por seguridad.
RUN useradd --create-home --uid 1000 appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# La app lee la configuración de variables de entorno (ver Config); en
# contenedor se inyectan con `--env-file`/`environment`, no con un .env montado.
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
