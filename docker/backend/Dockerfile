FROM python:3.11-slim

WORKDIR /app/app

# Argumento para entorno
ARG ENV=prod

# Variables recomendadas para Python
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Dependencias del sistema
RUN apt-get update && apt-get install -y netcat-openbsd \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Copiar dependencias primero (cache eficiente)
COPY requirements.txt requirements-dev.txt ./

# Instalar dependencias
RUN pip install --upgrade pip && \
    if [ "$ENV" = "dev" ]; then \
        pip install --no-cache-dir -r requirements-dev.txt; \
    else \
        pip install --no-cache-dir -r requirements.txt; \
    fi

# Copiar proyecto
COPY app /app
COPY docker/backend /app/docker/backend

# Permisos
RUN chmod +x /app/docker/backend/entrypoint.sh

# Comando
CMD ["sh", "/app/docker/backend/entrypoint.sh"]