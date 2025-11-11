# Directorio de Datos

Este directorio contiene archivos GeoJSON para análisis con Google Earth Engine.

## Estructura

```
data/
└── geojson/          # Archivos GeoJSON de áreas de interés
    ├── nunoa.geojson
    └── santiago_centro.geojson
```

## Uso

Los archivos GeoJSON en este directorio pueden ser usados con el script de prueba:

```bash
python scripts/test.py data/geojson/nunoa.geojson
```

## Formato GeoJSON

Los archivos deben seguir el estándar GeoJSON (RFC 7946):

```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "properties": {
        "name": "Nombre del área",
        "description": "Descripción"
      },
      "geometry": {
        "type": "Polygon",
        "coordinates": [[[lon, lat], [lon, lat], ...]]
      }
    }
  ]
}
```

## Ejemplos Incluidos

- **nunoa.geojson**: Comuna de Ñuñoa, Santiago
- **santiago_centro.geojson**: Centro histórico de Santiago

## Agregar Nuevos GeoJSON

Puedes agregar tus propios archivos GeoJSON en esta carpeta. Formatos soportados:

- Point (punto)
- Polygon (polígono)
- MultiPolygon (múltiples polígonos)
- FeatureCollection (colección de geometrías)

## Herramientas para Crear GeoJSON

- **geojson.io**: https://geojson.io/ (editor visual)
- **QGIS**: Software GIS para exportar a GeoJSON
- **Python**: Usar geopandas para crear/convertir GeoJSON
