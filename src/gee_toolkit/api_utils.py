"""
Utilidades para manejo de la API de Google Earth Engine.
Versión simplificada: Sin reintentos automáticos ni retardos artificiales.
"""

import logging
import ee
from functools import wraps
from typing import Type, Tuple, Optional

logger = logging.getLogger(__name__)

def retry_api_call(
    retries: int = 0,  # Desactivado por defecto
    delay: float = 0,  # Desactivado
    backoff: float = 0, # Desactivado
    exceptions: Tuple[Type[Exception], ...] = (ee.EEException, Exception),
    raise_on_failure: bool = True
):
    """
    Decorador simplificado. Ya NO realiza reintentos ni esperas.
    Solo captura excepciones si raise_on_failure es False.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except exceptions as e:
                error_msg = str(e).lower()
                
                # Loguear el error
                if "not found" in error_msg or "permission denied" in error_msg:
                    logger.warning(f"Asset no encontrado/sin permiso en {func.__name__}: {e}")
                else:
                    logger.error(f"Error en {func.__name__}: {e}")

                if raise_on_failure:
                    raise e
                
                return None
        return wrapper
    return decorator

def safe_ee_execute(func, *args, **kwargs):
    """
    Ejecuta una función de GEE capturando errores pero sin reintentos.
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        logger.error(f"Error ejecutando {func.__name__}: {e}")
        return None