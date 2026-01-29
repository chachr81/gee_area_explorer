"""
Utilidades para manejo de datos geoespaciales y GeoJSON.
"""

import sys
import ee
import geopandas as gpd
from pathlib import Path
from typing import Tuple

def cargar_geojson(ruta_geojson: Path) -> Tuple[ee.Geometry, gpd.GeoDataFrame]:
    """
    Carga un archivo GeoJSON y lo convierte a geometría de Earth Engine.
    
    Args:
        ruta_geojson: Ruta al archivo .geojson
        
    Returns:
        Tuple[ee.Geometry, gpd.GeoDataFrame]: Geometría de EE y el GeoDataFrame original.
    
    Raises:
        SystemExit: Si falla la carga (para uso en scripts CLI).
    """
    try:
        gdf = gpd.read_file(ruta_geojson)
        
        if len(gdf) == 0:
            raise ValueError("El GeoJSON no contiene features")
        
        geom_geojson = gdf.geometry.iloc[0].__geo_interface__
        ee_geometry = ee.Geometry(geom_geojson)
        
        return ee_geometry, gdf
        
    except Exception as e:
        print(f"[ERROR] No se pudo cargar el GeoJSON: {e}")
        # En un contexto de librería idealmente haríamos raise, 
        # pero mantenemos el comportamiento del script original por ahora.
        sys.exit(1)
