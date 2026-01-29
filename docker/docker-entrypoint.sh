#!/bin/bash
set -e

echo "==========================================================================="
echo "GEE Area Explorer - Container"
echo "==========================================================================="

# Comprobar credenciales Earth Engine
if [ ! -f "/root/.config/earthengine/credentials" ]; then
  echo ""
  echo "[WARN] No se encontraron credenciales de Earth Engine en /root/.config/earthengine"
  echo ""
  echo "Para autenticar, ejecuta (una sola vez):"
  echo "  docker run -it --rm -v gee-credentials:/root/.config/earthengine ghcr.io/chachr81/gee-area-explorer earthengine authenticate"
  echo ""
  echo "Alternativamente, usa una service account y monta la clave JSON:"
  echo "  docker run -it --rm -v \$(pwd)/service-account-key.json:/app/key.json -e GOOGLE_APPLICATION_CREDENTIALS=/app/key.json -e GEE_PROJECT=tu-proyecto-id ghcr.io/chachr81/gee-area-explorer python scripts/gee_search.py"
  echo ""
fi

# Comprobar .env
if [ ! -f "/app/.env" ]; then
  echo "[INFO] No se encontró /app/.env. Si tienes un .env local, móntalo con:"
  echo "  -v \$(pwd)/.env:/app/.env:ro"
fi

# Ejecutar el comando pasado al contenedor
exec "$@"