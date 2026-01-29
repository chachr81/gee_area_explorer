# Dockerfile: GEE Area Explorer (Modo "Appliance" / Ejecutable)
FROM python:3.12-slim

LABEL maintainer="chachr81"
LABEL description="GEE Area Explorer - Toolkit autoejecutable para Google Earth Engine"

# Variables para optimizar Python en contenedor
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# 1. Instalar dependencias del sistema mínimas necesarias
RUN apt-get update && apt-get install -y --no-install-recommends \
    gdal-bin \
    libgdal-dev \
    libspatialindex-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 2. Instalar dependencias Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 3. Copiar la aplicación
COPY scripts/ ./scripts/
COPY src/ ./src/
COPY config/ ./config/
COPY .env.example .

# 4. Crear puntos de montaje
# Usamos /root para configuración simplificada
RUN mkdir -p /app/data /app/output /app/logs /root/.config/earthengine

# 5. Configurar Entrypoint
COPY docker/docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Volúmenes expuestos
VOLUME ["/app/data", "/app/output", "/app/logs", "/root/.config/earthengine"]

# El contenedor actúa como el ejecutable 'gee_search' por defecto
ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["python", "scripts/gee_search.py"]