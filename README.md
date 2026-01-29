# GEE Area Explorer Toolkit

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Earth Engine API](https://img.shields.io/badge/Earth%20Engine-API-green.svg)](https://earthengine.google.com/)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://www.docker.com/)
[![Updated with Gemini CLI](https://img.shields.io/badge/Updated%20with-Gemini%20CLI-blueviolet.svg)](#)

GEE Area Explorer es una herramienta de ingeniería de datos geoespaciales diseñada para optimizar la interacción, descubrimiento y validación de activos en Google Earth Engine (GEE). Su propósito principal es servir como eslabón inicial en pipelines de datos, permitiendo identificar con precisión quirúrgica qué imágenes satelitales cumplen con criterios espaciales y temporales específicos antes de iniciar procesos de descarga o cómputo masivo.

---

## INDICE DE CONTENIDOS

1.  [Visión General del Sistema](#vision-general)
2.  [Arquitectura de Software](#arquitectura)
3.  [Descripción Detallada de Módulos](#modulos)
    *   [Catalog (Gestión de Metadatos)](#modulo-catalog)
    *   [Analysis (Motor de Búsqueda)](#modulo-analysis)
    *   [API Utils (Resiliencia)](#modulo-api-utils)
4.  [Base de Datos de Colecciones](#base-datos)
5.  [Instalación y Configuración](#instalacion)
6.  [Guía de Uso (Tutorial Completo)](#tutorial)
    *   [Modo Interactivo](#uso-interactivo)
    *   [Modo Pipeline (CLI)](#uso-pipeline)
7.  [Mantenimiento del Sistema](#mantenimiento)
8.  [Solución de Problemas](#troubleshooting)

---

## 1. <a name="vision-general"></a>VISIÓN GENERAL DEL SISTEMA

El problema fundamental al trabajar con Google Earth Engine en entornos de producción es la incertidumbre sobre la disponibilidad de datos. Intentar acceder a una colección deprecada, privada o vacía en un script de producción puede detener todo un flujo de trabajo (ETL). Además, las operaciones de filtrado espacial sobre colecciones globales masivas (como Landsat o Sentinel) pueden resultar en tiempos de espera excesivos o errores de memoria ("computation timed out", "aggregated over 5000 elements").

GEE Area Explorer resuelve estos problemas mediante:

1.  **Validación API-First**: Utiliza la API REST de GEE (`ee.data`) para validar la existencia y metadatos de las colecciones sin instanciar objetos pesados en el servidor de cálculo.
2.  **Inventario Local**: Mantiene un registro JSON persistente de colecciones validadas, actuando como una caché inteligente para búsquedas rápidas.
3.  **Búsqueda Optimizada**: Implementa estrategias de filtrado ("Fail-Fast", "Limit-First") que previenen el desbordamiento de memoria al consultar catálogos masivos.
4.  **Despliegue Contenerizado**: Se distribuye como un "Appliance" Docker que abstrae la complejidad de las dependencias geoespaciales (GDAL, earthengine-api).

---

## 2. <a name="arquitectura"></a>ARQUITECTURA DE SOFTWARE

El sistema está construido en Python 3.12 y sigue una arquitectura modular. No existe una interfaz gráfica (GUI); toda la interacción es a través de la línea de comandos (CLI), optimizada para su ejecución en servidores headless o contenedores.

### Árbol de Directorios y Archivos

```text
gee_area_explorer/
├── config/
│   └── colecciones_gee.json       # [PERSISTENCIA] Base de datos JSON. Contiene la definición de +600 colecciones.
├── src/
│   └── gee_toolkit/               # [NÚCLEO] Paquete Python principal.
│       ├── __init__.py            # Inicializador del paquete.
│       ├── api_utils.py           # [UTILIDAD] Decoradores y manejo de excepciones GEE.
│       ├── auth_utils.py          # [SEGURIDAD] Gestión de credenciales y sesiones.
│       ├── analysis.py            # [LÓGICA] Algoritmos de intersección espacial y filtrado.
│       ├── catalog.py             # [LÓGICA] CRUD del catálogo y crawler de metadatos.
│       ├── config.py              # [CONFIG] Variables de entorno (.env).
│       └── geo_utils.py           # [UTILIDAD] Lectura y transformación de GeoJSON.
├── scripts/
│   ├── gee_search.py              # [CLI] Punto de entrada para usuarios (Búsqueda).
│   ├── maintain_catalog.py        # [CLI] Herramienta de mantenimiento (Admin).
│   ├── generate_docs.py           # [DOCS] Generador de documentación Markdown.
│   └── test_integral.py           # [TEST] Script de validación E2E.
├── docker/
│   ├── Dockerfile                 # Definición de la imagen del sistema.
│   └── docker-entrypoint.sh       # Script de arranque del contenedor.
├── data/
│   └── geojson/                   # [INPUT] Directorio para archivos de área de interés.
├── output/                        # [OUTPUT] Directorio para CSVs generados.
├── .env                           # [SECRETO] Variables de entorno (Project ID).
└── requirements.txt               # Dependencias de Python.
```

---

## 3. <a name="modulos"></a>DESCRIPCIÓN DETALLADA DE MÓDULOS

A continuación se detalla la responsabilidad y funcionamiento interno de cada módulo crítico en `src/gee_toolkit`.

### <a name="modulo-catalog"></a>3.1. Catalog (`catalog.py`)

Este es el componente central del sistema. Su clase principal `CatalogoGEE` administra el archivo `colecciones_gee.json`.

**Funciones Clave:**

*   **`buscar_coleccion_api(collection_id)`**:
    Esta función es el "guardián" del sistema. Antes de permitir el uso de una colección, verifica su estado en GEE.
    *   *Estrategia Híbrida*: Primero consulta `ee.data.getAsset(id)` (ligero). Si el activo no existe o devuelve error 404/403, retorna `None` inmediatamente.
    *   *Filtro de Deprecación*: Analiza las propiedades del activo. Si `deprecated` es `true` o el título contiene "[DEPRECATED]", el activo se descarta.
    *   *Optimización de Bandas*: Para obtener la lista de bandas, intenta encontrar una sola imagen reciente (filtrando por el último año). Si la colección es masiva (Landsat/Sentinel) y no tiene datos recientes, omite la inspección profunda para evitar timeouts.

*   **`limpiar_invalidas()`**:
    Recorre todo el catálogo local y verifica cada ID contra la API. Si un ID ya no es accesible (fue eliminado por Google o cambiaron los permisos), lo elimina del JSON.

*   **`descubrir_colecciones(providers)`**:
    Un "crawler" que explora carpetas públicas de GEE (ej: `projects/earthengine-public/assets/COPERNICUS`) buscando nuevos `IMAGE_COLLECTION` que no estén en el catálogo local.

### <a name="modulo-analysis"></a>3.2. Analysis (`analysis.py`)

Motor encargado de cruzar la dimensión espacial (GeoJSON) con la dimensión temporal (Colección GEE).

**Funciones Clave:**

*   **`buscar_imagenes_por_espacio(id, geometry, dates, ...)`**:
    Ejecuta la consulta principal.
    *   *Paso 1*: Instancia la colección.
    *   *Paso 2*: Aplica `filterBounds(geometry)`. Esto es mucho más eficiente que `.geometry().intersects()`, ya que GEE utiliza índices espaciales (R-Tree/Quadtree) para filtrar tiles sin procesar píxeles.
    *   *Paso 3*: Aplica `filterDate(start, end)`.
    *   *Paso 4*: Detección de Nubes. Verifica si la colección tiene propiedades conocidas (`CLOUDY_PIXEL_PERCENTAGE`, `CLOUD_COVER`) y aplica el filtro si el usuario lo solicita.
    *   *Paso 5 (Crítico)*: Ejecuta `limit(limit)` **ANTES** de cualquier operación de materialización (`toList`). Esto previene errores de memoria si el filtro retorna millones de imágenes.

*   **`analizar_cobertura_temporal(...)`**:
    Orquesta la búsqueda y genera estadísticas agregadas (imágenes por año, calidad promedio). Exporta el resultado final a un archivo CSV en la carpeta `output/`.

### <a name="modulo-api-utils"></a>3.3. API Utils (`api_utils.py`)

Provee robustez ante fallos de red.

**Decorador `@retry_api_call`**:
Envuelve funciones críticas. Si una llamada a la API de GEE falla por razones transitorias (ej: `503 Service Unavailable`, `Timeout`), captura la excepción y permite decidir si reintentar o fallar silenciosamente (`raise_on_failure=False`). Esto es vital para procesos batch (como actualizar 600 colecciones) donde un solo fallo no debe detener todo el script.

---

## 4. <a name="base-datos"></a>BASE DE DATOS DE COLECCIONES

El archivo `config/colecciones_gee.json` es una base de datos documental que almacena el conocimiento del sistema sobre los activos de GEE.

**Estructura del Esquema JSON:**

```json
{
  "_metadata": {
    "version": "2.2.0",
    "last_updated": "2026-01-29T12:00:00"
  },
  "categoria_id": {
    "nombre": "Nombre Legible de la Categoría",
    "colecciones": {
      "ID_UNICO_GEE": {
        "nombre": "Título Oficial del Dataset",
        "nivel": "Nivel de Procesamiento (L1C, L2A, TOA)",
        "resolucion": "Resolución Nominal (m)",
        "temporal": "Rango de Fechas (Inicio - Fin)",
        "bandas_principales": ["Lista", "de", "bandas"],
        "last_verified": "Timestamp de última validación exitosa"
      }
    }
  }
}
```

### Resumen de Categorías Disponibles

| Categoría | Descripción | Cantidad Aprox. |
|-----------|-------------|-----------------|
| `opticas_alta_res` | Sentinel-2, Landsat (4-9), MODIS (Reflectancia) | ~100 |
| `clima` | ERA5, CHIRPS, GPM, GLDAS, WorldClim | ~300 |
| `vegetacion` | Índices derivados (NDVI, EVI, LAI, FPAR) | ~35 |
| `elevacion` | DEMs globales y locales (SRTM, ALOS, ArcticDEM) | ~3 |
| `sar` | Radar de Apertura Sintética (Sentinel-1, PALSAR) | ~7 |
| `landcover` | Mapas de cobertura (WorldCover, NLCD, Dynamic World) | ~15 |
| `agua` | Cuerpos de agua, recurrencia, salinidad, temperatura | ~30 |
| `atmosfera` | Gases traza (Sentinel-5P: NO2, CO, O3, CH4) | ~90 |
| `fuego` | Detección de puntos de calor y áreas quemadas | ~20 |
| `poblacion` | Densidad poblacional y asentamientos humanos | ~15 |

---

## 5. <a name="instalacion"></a>INSTALACIÓN Y CONFIGURACIÓN

### Requisitos Previos
1.  **Docker**: Debe estar instalado y en ejecución.
2.  **Cuenta de Google**: Debe tener acceso a Google Earth Engine (registrarse en earthengine.google.com).
3.  **Proyecto GCP**: Debe tener un Project ID de Google Cloud habilitado para usar la API de Earth Engine.

### Paso 1: Obtener el Código
Clone el repositorio en su máquina local:

```bash
git clone https://github.com/chachr81/gee_area_explorer.git
cd gee_area_explorer
```

### Paso 2: Configuración de Entorno
Copie el archivo de ejemplo y edítelo con su ID de proyecto:

```bash
cp .env.example .env
```

Edite `.env`:
```ini
GEE_PROJECT=mi-proyecto-gcp-id-12345
```

### Paso 3: Construcción del Contenedor
Construya la imagen Docker localmente (esto instalará todas las dependencias de Python y GDAL):

```bash
docker-compose build cli
```

### Paso 4: Autenticación (Crucial)
Debe autorizar al contenedor para usar sus credenciales de Google. Este paso se realiza **una sola vez**.

```bash
docker-compose run --rm cli earthengine authenticate
```

El sistema le proporcionará una URL.
1.  Abra la URL en su navegador.
2.  Autorice el acceso.
3.  Copie el código de verificación.
4.  Péguelo en la terminal.

Las credenciales se guardarán en un volumen Docker persistente (`gee-credentials`).

---

## 6. <a name="tutorial"></a>GUÍA DE USO (TUTORIAL COMPLETO)

### <a name="uso-interactivo"></a>A. Modo Interactivo (Usuario Humano)

Este modo es ideal para exploración, descubrimiento de datos y pruebas rápidas.

1.  **Prepare su Área de Interés**:
    Copie su archivo `.geojson` (Polígono o FeatureCollection) en la carpeta `data/geojson/` del proyecto.
    *   *Ejemplo*: `data/geojson/mi_finca.geojson`

2.  **Inicie la Herramienta**:
    ```bash
    docker-compose run --rm cli
    ```

3.  **Navegación por Menú**:
    *   Seleccione la opción **2. Búsqueda personalizada**.
    *   La herramienta cargará el catálogo (esto puede tomar unos segundos).
    *   **Selección de Colección**: Puede buscar por nombre (ej: "Sentinel") o navegar por categorías.
    *   **Selección de Área**: La herramienta listará automáticamente los archivos en `data/geojson`. Seleccione el número correspondiente a su archivo.
    *   **Parámetros**: Ingrese fecha de inicio, fin y porcentaje máximo de nubes (0-100).

4.  **Resultados**:
    La herramienta procesará la consulta y mostrará en pantalla un resumen. El archivo CSV detallado se guardará en `output/`.

### <a name="uso-pipeline"></a>B. Modo Pipeline (Automatización / Scripts)

Este modo está diseñado para integrar la herramienta en flujos de trabajo automatizados (Cron, Airflow, Bash scripts). No requiere interacción humana.

**Sintaxis General:**
```bash
docker-compose run --rm cli python scripts/gee_search.py [RUTA_GEOJSON]
```

**Escenario de Ejemplo:**
Usted tiene un pipeline que genera un GeoJSON de un área afectada por un incendio y necesita saber inmediatamente qué imágenes satelitales están disponibles para esa zona.

1.  El pipeline deposita `incendio_2024.geojson` en `data/geojson/`.
2.  El pipeline ejecuta:
    ```bash
    docker-compose run --rm cli python scripts/gee_search.py data/geojson/incendio_2024.geojson
    ```
3.  El script utiliza la colección por defecto (Sentinel-2 L2A Harmonized) y genera el CSV en `output/`.
4.  El pipeline lee el CSV generado para descargar las imágenes o procesar los IDs.

---

## 7. <a name="mantenimiento"></a>MANTENIMIENTO DEL SISTEMA

Con el tiempo, Google agrega nuevas colecciones y depreca otras. Para mantener su catálogo local sincronizado y saludable:

### Verificar Salud del Sistema
Ejecuta una serie de pruebas de conexión y validación de una muestra de colecciones.

```bash
docker-compose run --rm cli python scripts/test_integral.py
```

### Actualizar y Limpiar Catálogo
Este proceso recorre todo el catálogo JSON, verifica cada activo contra la API, actualiza metadatos y elimina entradas inválidas.

```bash
docker-compose --profile ops run --rm maintenance python scripts/maintain_catalog.py --revalidate --clean
```

### Generar Reporte de Estado
Muestra un resumen de cuántas colecciones hay por categoría y su estado.

```bash
docker-compose --profile ops run --rm maintenance python scripts/maintain_catalog.py --report
```

---

## 8. <a name="troubleshooting"></a>SOLUCIÓN DE PROBLEMAS

### Error: "Credential path not found" o "gcloud not found"
Esto indica que el contenedor no encuentra las credenciales en el volumen.
*   **Solución**: Ejecute nuevamente el paso de autenticación (`earthengine authenticate`). Verifique que el volumen `gee-credentials` exista (`docker volume ls`).

### Error: "Collection query aborted after accumulating over 5000 elements"
Esto ocurre cuando GEE intenta procesar demasiados metadatos de una colección masiva (como Landsat) sin filtros suficientes.
*   **Solución**: El código ha sido parcheado (v2.2.0) para usar `ee.data.getAsset` y evitar este error. Si persiste, asegúrese de estar usando la última versión del código (`git pull`).

### Los archivos GeoJSON no aparecen en el menú
*   **Solución**: Asegúrese de que los archivos estén físicamente en la carpeta `data/geojson/` de su máquina host y que tengan la extensión `.geojson` (minúsculas preferible). Docker monta esta carpeta en tiempo de ejecución.

### Permisos de Escritura en Linux
Los archivos en `output/` se crean con el usuario interno del contenedor (root).
*   **Solución**: Puede cambiar el propietario desde su host: `sudo chown -R $USER:$USER output/`.

---

**Desarrollado con Python y Google Earth Engine API.**
Licencia MIT.
