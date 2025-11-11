# GEE Area Explorer

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Earth Engine API](https://img.shields.io/badge/Earth%20Engine-API-green.svg)](https://earthengine.google.com/)

Toolkit de consola para explorar disponibilidad de imágenes satelitales en Google Earth Engine por área geográfica.

## ¿Qué es?

Herramienta de línea de comandos diseñada para usuarios que se están iniciando en el uso de la API de Google Earth Engine con Python. Permite descubrir qué imágenes satelitales están disponibles en un área específica, filtrarlas por fecha y calidad, y exportar los resultados.

**Ideal para:**
- Desarrolladores aprendiendo la API de Earth Engine
- Análisis exploratorio de disponibilidad de datos
- Validación de cobertura temporal en áreas de interés
- Ambiente de desarrollo y prototipado

## Estructura del Proyecto

```
gee_area_explorer/
├── scripts/
│   ├── gee_search.py              # Búsqueda de imágenes por área
│   └── maintain_catalog.py        # Gestión del catálogo
├── src/gee_toolkit/
│   ├── catalog.py                 # Catálogo de 88 colecciones
│   ├── config.py                  # Configuración GEE
│   └── colecciones_config.py      # Filtros de nubes
├── config/
│   └── colecciones_gee.json       # Metadata de colecciones
├── data/geojson/                  # Áreas de ejemplo
│   └── *.geojson
└── output/                        # Resultados CSV
```

## Instalación

```bash
# Clonar repositorio
git clone https://github.com/chachr81/gee_area_explorer.git
cd gee_area_explorer

# Crear entorno virtual
python3.12 -m venv venv
source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt

# Configurar proyecto GEE
cp .env.example .env
# Editar .env: PROJECT_ID=tu-proyecto-gee

# Autenticar
earthengine authenticate
```

## Uso Principal: Búsqueda por Área

### Modo Interactivo

```bash
python scripts/gee_search.py
```

**Menú de opciones:**

1. **Análisis rápido** - Prueba con área de ejemplo (Sentinel-2)
2. **Búsqueda personalizada** - Configurar todos los parámetros
3. **Listar niveles de procesamiento** - Ver L1C, L2A, TOA, etc.
4. **Buscar por nivel** - Filtrar colecciones por nivel

### Modo Directo

```bash
python scripts/gee_search.py data/geojson/tu_area.geojson
```

Ejecuta búsqueda Sentinel-2 directamente en el área especificada.

## Flujo de Trabajo con GeoJSON

### 1. Preparar Área de Interés

Crear archivo GeoJSON con tu área:

```json
{
  "type": "FeatureCollection",
  "features": [{
    "type": "Feature",
    "geometry": {
      "type": "Polygon",
      "coordinates": [[
        [-70.6, -33.4],
        [-70.6, -33.5],
        [-70.5, -33.5],
        [-70.5, -33.4],
        [-70.6, -33.4]
      ]]
    },
    "properties": {
      "name": "Area Estudio"
    }
  }]
}
```

Guardar en: `data/geojson/mi_area.geojson`

### 2. Ejecutar Búsqueda

**Opción A: Menú interactivo**

```bash
python scripts/gee_search.py

# Seleccionar opción 2: Búsqueda personalizada
# 1. Elegir colección (ej: Sentinel-2 L2A Harmonized)
# 2. Ingresar ruta GeoJSON: data/geojson/mi_area.geojson
# 3. Definir fechas: 2024-01-01 a 2024-12-31
# 4. Filtro nubes: 20% (opcional)
```

**Opción B: Directo**

```bash
python scripts/gee_search.py data/geojson/mi_area.geojson
```

### 3. Revisar Resultados

Los resultados se exportan a `output/busqueda_espacial_<area>_<timestamp>.csv`:

```csv
id,fecha,nubes,properties
COPERNICUS/S2/20240115T143729_20240115T144430_T19HBB,2024-01-15,8.5,{...}
COPERNICUS/S2/20240120T143729_20240120T144430_T19HBB,2024-01-20,12.3,{...}
```

El script también muestra:
- Número total de imágenes encontradas
- Distribución temporal por año
- Estadísticas de calidad (% nubes promedio, min, max)
- Top 5 mejores imágenes (menos nubes)

## Catálogo de Colecciones

El toolkit incluye un catálogo curado de **88 colecciones** organizadas en 12 categorías:

- **Ópticas (15)**: Sentinel-2, Landsat 9/8/7/5/4, MODIS
- **Vegetación (14)**: MODIS NDVI/EVI, GPP/NPP, LAI, FPAR
- **Clima (16)**: ERA5, CHIRPS, GPM, MODIS LST
- **Elevación (7)**: Copernicus DEM, SRTM, ALOS
- **SAR (4)**: Sentinel-1, ALOS PALSAR
- **Cobertura (7)**: ESA WorldCover, Dynamic World
- **Agua (7)**: JRC Water, MODIS Ocean Color
- **Criosfera (2)**: MODIS Snow Cover
- **Incendios (5)**: MODIS Fire, FIRMS
- **Atmósfera (11)**: Sentinel-5P (NO₂, CO, O₃, CH₄, SO₂)
- **Población (2)**: WorldPop, GPW
- **Misceláneos**: Otros productos especializados

## Gestión del Catálogo

```bash
# Ver estado del catálogo
python scripts/maintain_catalog.py --report

# Agregar nueva colección (se clasifica automáticamente)
python scripts/maintain_catalog.py --add COPERNICUS/S2_SR_HARMONIZED

# Verificar disponibilidad
python scripts/maintain_catalog.py --verify COPERNICUS/S2_SR_HARMONIZED

# Actualizar metadata
python scripts/maintain_catalog.py --refresh COPERNICUS/S2_SR_HARMONIZED

# Revalidar colecciones antiguas
python scripts/maintain_catalog.py --revalidate
```

## Uso Programático

### Búsqueda de Imágenes

```python
import ee
from src.gee_toolkit.config import get_project_id

# Inicializar
project_id = get_project_id()
ee.Initialize(project=project_id)

# Definir área (ejemplo: rectángulo)
geometry = ee.Geometry.Rectangle([-70.7, -33.5, -70.5, -33.3])

# Buscar Sentinel-2 con filtros
collection = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED') \
    .filterBounds(geometry) \
    .filterDate('2024-01-01', '2024-12-31') \
    .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20))

# Obtener resultados
count = collection.size().getInfo()
print(f"Imágenes encontradas: {count}")
```

### Consultar Catálogo

```python
from src.gee_toolkit import CatalogoGEE, get_project_id

# Inicializar catálogo
catalog = CatalogoGEE(project_id=get_project_id())

# Obtener colecciones por categoría
opticas = catalog.obtener_colecciones_por_categoria('opticas_media_res')
print(f"Colecciones ópticas: {len(opticas)}")

# Generar reporte completo
df = catalog.generar_catalogo_completo()
df.to_csv('catalogo.csv', index=False)
```

### Verificar Soporte de Filtro de Nubes

```python
from src.gee_toolkit.colecciones_config import soporta_filtro_nubes

# Verificar si colección soporta filtro
soporta, propiedad = soporta_filtro_nubes('COPERNICUS/S2_SR_HARMONIZED')

if soporta:
    print(f"Filtrar usando propiedad: {propiedad}")
    # Aplicar filtro
    collection = collection.filter(ee.Filter.lt(propiedad, 20))
```

## Configuración

### Variables de Entorno

Crear archivo `.env` en la raíz:

```bash
PROJECT_ID=tu-proyecto-gee
```

### Estructura del Catálogo

`config/colecciones_gee.json` contiene metadata de 88 colecciones:

```json
{
  "categorias": {
    "opticas_media_res": {
      "nombre": "Imágenes Ópticas - Resolución Media",
      "colecciones": [
        {
          "id": "COPERNICUS/S2_SR_HARMONIZED",
          "nombre": "Sentinel-2 MSI L2A (Harmonized)",
          "nivel_procesamiento": "L2A",
          "resolucion_m": 10,
          "inicio_datos": "2015-06-23",
          "activo": true
        }
      ]
    }
  }
}
```

## Dependencias

```
earthengine-api>=0.1.400    # API de Google Earth Engine
pandas>=2.2.0               # Manipulación de datos
geopandas>=0.14.0           # Datos espaciales
shapely>=2.0.0              # Operaciones geométricas
python-dotenv>=1.0.0        # Configuración
```

## Solución de Problemas

### Error de Autenticación

```bash
earthengine authenticate
```

### Proyecto No Encontrado

Verificar `.env`:

```bash
cat .env
# Debe mostrar: PROJECT_ID=tu-proyecto-gee
```

### Timeout en Consultas

Reducir parámetros de búsqueda:
- Área geográfica más pequeña
- Rango de fechas más corto
- Límite de imágenes: `collection.limit(100)`

## Casos de Uso

### Caso 1: Planificación de Estudio

Determinar disponibilidad de imágenes Sentinel-2 con <10% nubes en área de estudio durante 2024:

```bash
python scripts/gee_search.py

# Opción 2: Búsqueda personalizada
# Colección: Sentinel-2 L2A Harmonized
# Área: data/geojson/area_estudio.geojson
# Fechas: 2024-01-01 a 2024-12-31
# Nubes: 10
```

**Resultado:** CSV con todas las imágenes disponibles y sus fechas.

### Caso 2: Comparación de Sensores

Evaluar qué sensor tiene mejor cobertura en tu área:

```bash
# Probar Sentinel-2
python scripts/gee_search.py data/geojson/mi_area.geojson

# Probar Landsat 8 (menú interactivo)
python scripts/gee_search.py
# Seleccionar: Landsat 8 L2
```

Comparar número de imágenes y distribución temporal.

### Caso 3: Validación de Datos Climáticos

Verificar disponibilidad de datos ERA5 o CHIRPS en período específico:

```bash
python scripts/gee_search.py

# Buscar en categoría "Datos Climáticos"
# Ejemplo: ECMWF/ERA5/DAILY o UCSB-CHG/CHIRPS/DAILY
```

## Notas para Desarrollo

- **Entorno recomendado**: Python 3.12 en venv
- **API de GEE**: Requiere cuenta Google Cloud con Earth Engine habilitado
- **GeoJSON**: Usar geometrías simples para mejores resultados
- **Límites**: API de GEE tiene límites de procesamiento - usar áreas pequeñas para testing

## Licencia

MIT License

---

**GEE Area Explorer v1.0.0** - Toolkit de consola para exploración de imágenes satelitales en Google Earth Engine
