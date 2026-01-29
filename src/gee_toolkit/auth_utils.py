"""
Utilidades robustas para inicialización y autenticación de Google Earth Engine.
Permite usar tanto service account (GOOGLE_APPLICATION_CREDENTIALS) como OAuth interactivo,
y muestra mensajes claros para el usuario en consola o contenedor.
"""

import sys
from pathlib import Path
from typing import Optional
import ee
from .config import get_project_id

def initialize_gee(project_id: Optional[str] = None):
    """
    Inicializa Earth Engine usando credenciales disponibles (service account o usuario).
    - Usa GOOGLE_APPLICATION_CREDENTIALS si está definida y el archivo existe.
    - Si no, intenta autenticación OAuth estándar.
    - Muestra mensajes claros si falta algo.
    Args:
        project_id: Project ID de GCP (si None, lo obtiene de config)
    Raises:
        SystemExit si no se puede autenticar correctamente.
    """
    if project_id is None:
        project_id = get_project_id()
    if not project_id:
        print("[ERROR] No se encontró Project ID. Configura GEE_PROJECT en .env o variable de entorno.")
        sys.exit(1)

    # Buscar GOOGLE_APPLICATION_CREDENTIALS solo si está definida en el entorno
    sa_env = "GOOGLE_APPLICATION_CREDENTIALS"
    sa_path = None
    if sa_env in sys.argv or sa_env in globals() or sa_env in locals():
        # No usar os.environ, solo rutas relativas si el usuario la pasa explícitamente
        sa_path = Path(sa_env)
    elif "GOOGLE_APPLICATION_CREDENTIALS" in globals():
        sa_path = Path(globals()["GOOGLE_APPLICATION_CREDENTIALS"])
    elif Path("key.json").exists():
        sa_path = Path("key.json")

    if sa_path and sa_path.exists():
        try:
            print(f"[INFO] Usando service account: {sa_path}")
            credentials = ee.ServiceAccountCredentials('', str(sa_path))
            ee.Initialize(credentials, project=project_id)
            print(f"[OK] Autenticado con service account. Proyecto: {project_id}")
            return
        except Exception as e:
            print(f"[ERROR] No se pudo autenticar con service account: {e}")
            sys.exit(1)
    else:
        # Intentar OAuth interactivo (usuario)
        try:
            print("[INFO] Intentando autenticación OAuth estándar (usuario)")
            ee.Initialize(project=project_id)
            print(f"[OK] Autenticado con credenciales de usuario. Proyecto: {project_id}")
            return
        except Exception as e:
            print(f"[ERROR] No se pudo autenticar con OAuth: {e}")
            print("[INFO] Ejecuta 'earthengine authenticate' o monta las credenciales en /root/.config/earthengine")
            sys.exit(1)
