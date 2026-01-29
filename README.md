# GEE Area Explorer Toolkit

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Earth Engine API](https://img.shields.io/badge/Earth%20Engine-API-green.svg)](https://earthengine.google.com/)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://www.docker.com/)
[![Updated with Gemini CLI](https://img.shields.io/badge/Updated%20with-Gemini%20CLI-blueviolet.svg)](#)

[View in English](README.en.md)

GEE Area Explorer es una herramienta diseñada para validar la disponibilidad de imágenes satelitales en Google Earth Engine (GEE) según criterios espaciales y temporales. Está construida para integrarse como un paso de pre-validación en pipelines de datos, evitando cómputos innecesarios sobre colecciones masivas.

---

## INDICE DE CONTENIDOS

1.  [Visión General del Sistema](#vision-general)
2.  [Arquitectura de Software](#arquitectura)
3.  [Descripción Detallada de Módulos](#modulos)
    *   [Interfaz de Búsqueda (Orquestador)](#modulo-search)
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

Al interactuar con Google Earth Engine mediante programación, surgen desafíos comunes como la gestión de la disponibilidad de datos y la optimización de consultas para evitar errores de timeout. Intentar acceder a una colección deprecada, privada o realizar un filtrado espacial sobre millones de imágenes puede detener un flujo de trabajo automatizado.

GEE Area Explorer aborda estos problemas mediante:

1.  **Validación API-First**: Utiliza la API REST de GEE (`ee.data`) para verificar la existencia y metadatos de las colecciones sin instanciar objetos pesados en el servidor de cómputo.
2.  **Inventario Local**: Mantiene un registro JSON persistente de las colecciones validadas, actuando como una caché para acelerar las consultas.
3.  **Búsqueda Optimizada**: Implementa estrategias de filtrado (ej. `limit`) previas a la materialización de resultados para prevenir el desbordamiento de memoria en el cliente.
4.  **Despliegue Contenerizado**: Se distribuye como un contenedor Docker, encapsulando el entorno de ejecución y sus dependencias (Python, GDAL) para garantizar la portabilidad y consistencia.

---

## 2. <a name="arquitectura"></a>ARQUITECTURA DE SOFTWARE

El sistema está construido en Python 3.12 bajo una arquitectura modular. La interacción se realiza exclusivamente a través de la línea de comandos (CLI), permitiendo su ejecución en servidores o entornos automatizados.

### Árbol de Directorios y Archivos

```text
gee_area_explorer/
├── config/
│   └── colecciones_gee.json       # [PERSISTENCIA] Base de datos JSON con metadatos de colecciones.
├── src/
│   └── gee_toolkit/               # [NÚCLEO] Paquete Python principal.
│       ├── __init__.py            # Inicializador del paquete.
│       ├── api_utils.py           # [UTILIDAD] Decoradores para manejo de excepciones GEE.
│       ├── auth_utils.py          # [SEGURIDAD] Gestión de credenciales y sesiones.
│       ├── analysis.py            # [LÓGICA] Algoritmos de intersección espacial y filtrado.
│       ├── catalog.py             # [LÓGICA] Gestión del ciclo de vida del catálogo.
│       ├── config.py              # [CONFIG] Carga de variables de entorno.
│       └── geo_utils.py           # [UTILIDAD] Lectura y transformación de GeoJSON.
├── scripts/
│   ├── gee_search.py              # [CLI] Punto de entrada para búsquedas interactivas.
│   ├── maintain_catalog.py        # [CLI] Herramienta de mantenimiento del catálogo.
│   ├── generate_docs.py           # [DOCS] Generador de documentación Markdown.
│   └── test_integral.py           # [TEST] Script de validación de integración.
├── docker/
│   ├── Dockerfile                 # Definición de la imagen del sistema.
│   └── docker-entrypoint.sh       # Script de arranque del contenedor.
├── data/
│   └── geojson/                   # [INPUT] Directorio para archivos de área de interés.
├── output/                        # [OUTPUT] Directorio para reportes generados.
└── requirements.txt               # Dependencias de Python.
```

---

## 3. <a name="modulos"></a>DESCRIPCIÓN DETALLADA DE MÓDULOS

A continuación se detalla la responsabilidad y funcionamiento de los módulos críticos en `src/gee_toolkit`.

### <a name="modulo-search"></a>3.1. Interfaz de Búsqueda (`gee_search.py`)

Este script es el punto de entrada principal. Actúa como el orquestador que conecta al usuario con el motor del toolkit.

**Responsabilidades y Flujos:**

1.  **Gestión de Entrada**: Soporta modo interactivo (menús) y modo directo (vía argumentos).
2.  **Menú Principal (Opciones)**:
    *   **Opción 1: Análisis Rápido**: Ejecuta una búsqueda pre-configurada de Sentinel-2 sobre el área de ejemplo (Ñuñoa) para validar que el sistema responde correctamente.
    *   **Opción 2: Búsqueda Personalizada**: El flujo más robusto. Permite:
        *   *Selección de Colección*: Mediante sub-menú (filtrado por nombre, navegación por categorías, búsqueda por nivel de procesamiento o ingreso directo de ID).
        *   *Selección de Área*: Escaneo automático de `data/geojson/` permitiendo elegir el archivo por número.
        *   *Parámetros*: Definición de fechas (con sugerencias automáticas basadas en la colección) y límite de nubes.
    *   **Opción 3: Auditoría de Niveles**: Muestra un resumen técnico de todos los niveles de procesamiento (L1C, L2A, TOA, etc.) presentes en el catálogo actual.
    *   **Opción 4: Exportación por Nivel**: Permite filtrar colecciones por un nivel específico y exportar ese listado a un archivo CSV en `output/`.
3.  **Coordinación de Búsqueda**: Utiliza la clase `CatalogoGEE` para filtrar datos y llama a `analizar_cobertura_temporal` para ejecutar la lógica espacial.
4.  **Formateo de Resultados**: Presenta un resumen legible en consola antes de escribir el reporte CSV final.

### <a name="modulo-catalog"></a>3.2. Catalog (`catalog.py`)

La clase `CatalogoGEE` gestiona el ciclo de vida del catálogo de metadatos (`colecciones_gee.json`).

**Funciones Clave:**

*   **`buscar_coleccion_api(collection_id)`**:
    Verifica el estado de un activo en GEE antes de su uso. Su estrategia consiste en:
    1.  Consultar `ee.data.getAsset(id)` para una validación ligera, retornando `None` si el activo no existe o es inaccesible (404/403).
    2.  Analizar las propiedades del activo para descartarlo si está marcado como `deprecated`.
    3.  Omitir la inspección profunda de imágenes para colecciones masivas (ej. Landsat), previniendo timeouts.

*   **`limpiar_invalidas()`**:
    Itera sobre el catálogo local y elimina las entradas correspondientes a activos que ya no son accesibles en GEE.

*   **`descubrir_colecciones(providers)`**:
    Funciona como un crawler que explora carpetas públicas de GEE (ej. `projects/earthengine-public/assets/COPERNICUS`) para identificar nuevas `ImageCollection`.

### <a name="modulo-analysis"></a>3.3. Analysis (`analysis.py`)

Este módulo ejecuta las consultas espaciales y temporales contra GEE.

**Funciones Clave:**

*   **`buscar_imagenes_por_espacio(id, geometry, dates, ...)`**:
    Ejecuta la consulta principal aplicando filtros en un orden optimizado:
    1.  Aplica `filterBounds(geometry)` para delegar el filtrado espacial al backend de GEE.
    2.  Aplica `filterDate(start, end)` para acotar temporalmente la búsqueda.
    3.  Aplica `limit(limit)` antes de materializar la lista de resultados para prevenir errores de memoria.

*   **`analizar_cobertura_temporal(...)`**:
    Orquesta el proceso de búsqueda, genera estadísticas agregadas (ej. imágenes por año) y exporta los resultados a un archivo CSV.

### <a name="modulo-api-utils"></a>3.4. API Utils (`api_utils.py`)

Provee decoradores para aumentar la resiliencia de la aplicación.

**`@retry_api_call`**:
Envuelve las llamadas a la API de GEE. En caso de errores transitorios (`503 Service Unavailable`, `Timeout`), puede reintentar la operación o fallar de forma controlada (`raise_on_failure=False`), lo cual es útil para procesos batch.

---

## 4. BASE DE DATOS DE COLECCIONES

El archivo `config/colecciones_gee.json` funciona como una base de datos documental que almacena los metadatos de los activos GEE.

**Estructura del Esquema JSON:**
```json
{
  "_metadata": { "version": "2.2.0", "last_updated": "..." },
  "categoria_id": {
    "nombre": "Nombre de la Categoría",
    "colecciones": {
      "ID_GEE": {
        "nombre": "Título del Dataset",
        "nivel": "Nivel de Procesamiento",
        "resolucion": "Resolución Nominal",
        "temporal": "Rango de Fechas",
        "bandas_principales": [],
        "last_verified": "Timestamp"
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
| `poblacion` | Population density and human settlements | ~15 |

> Para la lista completa y detallada de todas las colecciones, consulte el **[Catálogo de Colecciones Completo](docs/CATALOGO_COLECCIONES.md)**.

---

## 5. <a name="setup"></a>Installation and Setup

### Requisitos Previos
1.  Docker y Docker Compose.
2.  Una cuenta de Google con acceso a Google Earth Engine.
3.  Un Project ID de Google Cloud Platform (GCP) habilitado para la API de GEE.

### Paso 1: Obtener el Código
Clone el repositorio en su máquina local:
```bash
git clone https://github.com/chachr81/gee_area_explorer.git
cd gee_area_explorer
```

### Paso 2: Configuración de Entorno
Copie el archivo de ejemplo y defina su ID de proyecto:
```bash
cp .env.example .env
```
Edite `.env`:
```ini
GEE_PROJECT=su-id-de-proyecto-gcp
```

### Paso 3: Construcción del Contenedor
Este comando construye la imagen Docker localmente, instalando todas las dependencias.
```bash
docker-compose build cli
```

### Paso 4: Autenticación (Una sola vez)
Autorice al contenedor para usar sus credenciales de GEE. Este paso se realiza una única vez.
```bash
docker-compose run --rm cli earthengine authenticate
```
Siga las instrucciones en la terminal: abra la URL, autorice el acceso y pegue el código de verificación. Las credenciales se guardarán en un volumen Docker (`gee-credentials`).

---

## 6. <a name="tutorial"></a>GUÍA DE USO (TUTORIAL COMPLETO)

### <a name="uso-interactivo"></a>A. Modo Interactivo

Modo diseñado para exploración y pruebas rápidas.

1.  **Prepare su Área de Interés**:
    Copie su archivo GeoJSON en la carpeta `data/geojson/`.
2.  **Inicie la Herramienta**:
    ```bash
    docker-compose run --rm cli
    ```
3.  **Navegación por Menú**:
    El menú le guiará para seleccionar una colección, un archivo de área y los parámetros de la búsqueda.
4.  **Resultados**:
    La herramienta procesará la consulta y guardará un archivo CSV en el directorio `output/`.

### <a name="uso-pipeline"></a>B. Modo Pipeline (Automatización)

Diseñado para integrar la herramienta en flujos de trabajo automatizados.

**Sintaxis General:**
```bash
docker-compose run --rm cli python scripts/gee_search.py [RUTA_GEOJSON]
```
Este comando ejecutará el análisis sobre el GeoJSON especificado usando parámetros por defecto.

---

## 7. <a name="mantenimiento"></a>MANTENIMIENTO DEL SISTEMA

### Verificar Salud del Sistema
Ejecuta una serie de pruebas de conexión y validación de colecciones.
```bash
docker-compose run --rm cli python scripts/test_integral.py
```

### Actualizar y Limpiar Catálogo
Verifica cada activo del catálogo contra la API de GEE y elimina las entradas inválidas.
```bash
docker-compose --profile ops run --rm maintenance python scripts/maintain_catalog.py --revalidate --clean
```

---

## 8. <a name="troubleshooting"></a>SOLUCIÓN DE PROBLEMAS

*   **"Credential path not found"**: Indica un fallo de autenticación. Ejecute de nuevo el paso 4 de la instalación.
*   **"Collection query aborted after accumulating over 5000 elements"**: La arquitectura actual está diseñada para prevenir este error. Si ocurre, asegúrese de tener la última versión del código.
*   **Permisos de Escritura en Linux**: Los archivos generados en `output/` pertenecen al usuario `root` del contenedor. Cambie su propiedad con `sudo chown -R $USER:$USER output/`.

---

**Nota sobre la contribución**: Este proyecto fue refactorizado y documentado con la asistencia de Gemini CLI (modelo Gemini 3 Pro).
Licencia MIT.