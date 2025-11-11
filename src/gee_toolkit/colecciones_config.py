"""
Configuración de propiedades de colecciones GEE.

Basado en análisis de propiedades de nubes realizado el 2025-11-11.
"""

# Colecciones que tienen la propiedad CLOUDY_PIXEL_PERCENTAGE
COLECCIONES_CON_FILTRO_NUBES = {
    'COPERNICUS/S2_SR_HARMONIZED',
    'COPERNICUS/S2_HARMONIZED',
}

# Colecciones que tienen CLOUD_COVER pero NO CLOUDY_PIXEL_PERCENTAGE
# Estas usan una propiedad diferente para filtrar nubes
COLECCIONES_CON_CLOUD_COVER = {
    'LANDSAT/LC09/C02/T1_L2',
    'LANDSAT/LC09/C02/T1_TOA',
    'LANDSAT/LC08/C02/T1_L2',
    'LANDSAT/LC08/C02/T1_TOA',
    'LANDSAT/LE07/C02/T1_L2',
    'LANDSAT/LT05/C02/T1_L2',
    'LANDSAT/LT04/C02/T1_L2',
}

# Colecciones SAR, climáticas, MODIS y otras que NO tienen filtro de nubes
COLECCIONES_SIN_FILTRO_NUBES = {
    # MODIS (solo versión 061 actualizada)
    'MODIS/061/MCD43A4',
    'MODIS/061/MCD43A3',
    'MODIS/061/MOD09A1',
    'MODIS/061/MOD09GA',
    'MODIS/061/MYD11A2',
    'MODIS/061/MOD13A1',
    'MODIS/061/MYD13A1',
    'MODIS/061/MOD13Q1',
    'MODIS/061/MYD13Q1',
    'MODIS/061/MOD17A2H',
    'MODIS/061/MYD17A2H',
    'MODIS/061/MOD17A3HGF',
    'MODIS/061/MOD16A2',
    'MODIS/061/MOD44B',
    'MODIS/061/MYD13A2',
    'MODIS/061/MCD15A3H',
    'MODIS/061/MOD11A2',
    'MODIS/061/MOD11A1',
    'MODIS/061/MOD14A2',
    'MODIS/061/MOD14A1',
    'MODIS/061/MCD64A1',
    'MODIS/061/MCD19A2_GRANULES',
    'MODIS/061/MOD10A1',
    'MODIS/061/MYD10A1',
    # SAR
    'COPERNICUS/S1_GRD',
    'COPERNICUS/S1_GRD_FLOAT',
    # Climáticas
    'ECMWF/ERA5_LAND/DAILY_AGGR',
    'ECMWF/ERA5_LAND/MONTHLY_AGGR',
    'ECMWF/ERA5/DAILY',
    'ECMWF/ERA5/MONTHLY',
    'UCSB-CHG/CHIRPS/DAILY',
    'UCSB-CHG/CHIRPS/PENTAD',
    'NASA/GPM_L3/IMERG_V07',  # Actualizada desde V06
    'NASA/GLDAS/V021/NOAH/G025/T3H',
    'NASA/GLDAS/V022/CLSM/G025/DA1D',
    'NASA/GDDP-CMIP6',
    'NASA/FLDAS/NOAH01/C/GL/M/V001',
    # VIIRS (versión NASA actualizada)
    'NASA/VIIRS/002/VNP13A1',
    'NASA/VIIRS/002/VNP21A1D',
    # Uso de suelo
    'ESA/WorldCover/v100',
    'ESA/WorldCover/v200',
    'COPERNICUS/CORINE/V20/100m',
    'USGS/NLCD_RELEASES/2021_REL/NLCD',
    'GOOGLE/DYNAMICWORLD/V1',
    # Recursos hídricos
    'JRC/GSW1_4/MonthlyHistory',
    'NASA/OCEANDATA/MODIS-Terra/L3SMI',
    'NASA/OCEANDATA/MODIS-Aqua/L3SMI',
    'COPERNICUS/S3/OLCI',
    'HYCOM/sea_temp_salinity',
    'NOAA/CDR/OISST/V2_1',
    # Incendios
    'FIRMS',
    'ESA/CCI/FireCCI/5_1',
    # Atmósfera (Sentinel-5P)
    'COPERNICUS/S5P/NRTI/L3_NO2',
    'COPERNICUS/S5P/NRTI/L3_CO',
    'COPERNICUS/S5P/NRTI/L3_O3',
    'COPERNICUS/S5P/OFFL/L3_NO2',
    'COPERNICUS/S5P/OFFL/L3_CO',
    'COPERNICUS/S5P/OFFL/L3_O3',
    'COPERNICUS/S5P/OFFL/L3_CH4',
    'COPERNICUS/S5P/OFFL/L3_SO2',
    'COPERNICUS/S5P/OFFL/L3_HCHO',
    'COPERNICUS/S5P/OFFL/L3_AER_AI',
    # LiDAR y Biomasa (GEDI)
    'LARSE/GEDI/GEDI02_A_002_MONTHLY',
    'LARSE/GEDI/GEDI02_B_002_MONTHLY',
    'LARSE/GEDI/GEDI04_A_002_MONTHLY',
    'LARSE/GEDI/GEDI04_B_002',
}


def soporta_filtro_nubes(collection_id: str) -> tuple[bool, str]:
    """
    Determina si una colección soporta filtrado de nubes y qué propiedad usar.
    
    Args:
        collection_id: ID de la colección de GEE
    
    Returns:
        tuple: (soporta_filtro, propiedad_a_usar)
            - soporta_filtro: True si soporta filtrado
            - propiedad_a_usar: 'CLOUDY_PIXEL_PERCENTAGE', 'CLOUD_COVER' o None
    """
    if collection_id in COLECCIONES_CON_FILTRO_NUBES:
        return (True, 'CLOUDY_PIXEL_PERCENTAGE')
    
    if collection_id in COLECCIONES_CON_CLOUD_COVER:
        return (True, 'CLOUD_COVER')
    
    if collection_id in COLECCIONES_SIN_FILTRO_NUBES:
        return (False, None)
    
    # Para colecciones no catalogadas, intentar detectar automáticamente
    # (esto requeriría hacer una consulta a GEE)
    return (None, None)  # Desconocido


def get_descripcion_filtro(collection_id: str) -> str:
    """
    Obtiene una descripción del tipo de filtro de nubes para una colección.
    
    Returns:
        str: Descripción del tipo de filtro
    """
    soporta, propiedad = soporta_filtro_nubes(collection_id)
    
    if soporta is True:
        if propiedad == 'CLOUDY_PIXEL_PERCENTAGE':
            return "Filtro de nubes disponible (CLOUDY_PIXEL_PERCENTAGE)"
        elif propiedad == 'CLOUD_COVER':
            return "Filtro de nubes disponible (CLOUD_COVER)"
    elif soporta is False:
        return "Sin filtro de nubes (colección no óptica o sin metadata de nubes)"
    else:
        return "Filtro de nubes no catalogado (se detectará automáticamente)"
