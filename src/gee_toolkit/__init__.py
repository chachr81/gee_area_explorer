"""
Google Earth Engine Toolkit

Un toolkit profesional para exploración, análisis y verificación
de colecciones de Google Earth Engine.
"""

from .catalog import CatalogoGEE
from .config import get_project_id

__version__ = '1.0.0'
__author__ = 'Data Scientist'
__all__ = [
    'CatalogoGEE',
    'get_project_id'
]


