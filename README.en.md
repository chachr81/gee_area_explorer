# GEE Area Explorer Toolkit

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Earth Engine API](https://img.shields.io/badge/Earth%20Engine-API-green.svg)](https://earthengine.google.com/)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://www.docker.com/)
[![Updated with Gemini CLI](https://img.shields.io/badge/Updated%20with-Gemini%20CLI-blueviolet.svg)](#)

[Ver en Español](README.md)

GEE Area Explorer is a software tool designed to validate the availability of satellite imagery in Google Earth Engine (GEE) based on spatial and temporal criteria. It is built to be integrated as a pre-validation step in data pipelines, preventing unnecessary computations on massive collections.

---

## TABLE OF CONTENTS

1.  [System Overview](#overview)
2.  [Software Architecture](#architecture)
3.  [Detailed Module Description](#modules)
    *   [Catalog (Metadata Management)](#module-catalog)
    *   [Analysis (Search Engine)](#module-analysis)
    *   [API Utils (Resilience)](#module-api-utils)
    *   [Search Interface](#module-search)
4.  [Collection Database](#database)
5.  [Installation and Setup](#setup)
6.  [Complete User Guide](#usage)
    *   [Interactive Mode](#interactive-mode)
    *   [Pipeline Mode (CLI)](#pipeline-mode)
7.  [System Maintenance](#maintenance)
8.  [Troubleshooting](#troubleshooting)

---

## 1. <a name="overview"></a>System Overview

When interacting with Google Earth Engine programmatically, common challenges arise, such as managing data availability and optimizing queries to avoid timeout errors. Attempting to access a deprecated or private collection, or performing a spatial filter on millions of images, can halt an entire automated workflow.

GEE Area Explorer addresses these issues by:

1.  **API-First Validation**: It uses GEE's REST API (`ee.data`) to check the existence and metadata of collections without instantiating heavy server-side objects.
2.  **Local Inventory**: It maintains a persistent JSON record of validated collections, acting as a cache to speed up lookups.
3.  **Optimized Search**: It implements filtering strategies (e.g., `limit`) before materializing results to prevent client-side memory overflows.
4.  **Containerized Deployment**: It is distributed as a Docker container, encapsulating the execution environment and its dependencies (Python, GDAL) to ensure portability and consistency.

---

## 2. <a name="architecture"></a>Software Architecture

The system is built in Python 3.12 following a modular architecture. All interaction is done through the command line (CLI), enabling its execution on servers or in automated environments.

### Directory and File Tree

```text
gee_area_explorer/
├── config/
│   └── colecciones_gee.json       # [PERSISTENCE] JSON database with collection metadata.
├── src/
│   └── gee_toolkit/               # [CORE] Main Python package.
│       ├── __init__.py            # Package initializer.
│       ├── api_utils.py           # [UTILITY] Decorators for GEE exception handling.
│       ├── auth_utils.py          # [SECURITY] Credential and session management.
│       ├── analysis.py            # [LOGIC] Spatial intersection and filtering algorithms.
│       ├── catalog.py             # [LOGIC] Catalog lifecycle management.
│       ├── config.py              # [CONFIG] Environment variable loading.
│       └── geo_utils.py           # [UTILITY] GeoJSON reading and transformation.
├── scripts/
│   ├── gee_search.py              # [CLI] Entry point for interactive searches.
│   ├── maintain_catalog.py        # [CLI] Catalog maintenance tool.
│   ├── generate_docs.py           # [DOCS] Markdown documentation generator.
│   └── test_integral.py           # [TEST] Integration validation script.
├── docker/
│   ├── Dockerfile                 # System image definition.
│   └── docker-entrypoint.sh       # Container startup script.
├── data/
│   └── geojson/                   # [INPUT] Directory for area of interest files.
├── output/                        # [OUTPUT] Directory for generated reports.
└── requirements.txt               # Python dependencies.
```

---

## 3. <a name="modules"></a>Detailed Module Description

The following details the responsibility and functionality of the critical modules in `src/gee_toolkit`.

### <a name="module-search"></a>3.1. Search Interface (`gee_search.py`)

This script is the main entry point. It acts as the orchestrator connecting the user with the toolkit's core engine.

**Responsibilities and Flows:**

1.  **Input Handling**: Supports both interactive mode (menus) and direct mode (via arguments).
2.  **Main Menu (Options)**:
    *   **Option 1: Quick Analysis**: Runs a pre-configured Sentinel-2 search on the sample area (Ñuñoa) to validate system response.
    *   **Option 2: Custom Search**: The most robust flow. It allows:
        *   *Collection Selection*: Via sub-menu (filtering by name, browsing by categories, searching by processing level, or direct ID entry).
        *   *Area Selection*: Automatic scanning of `data/geojson/`, allowing selection by number.
        *   *Parameters*: Definition of dates (with automatic suggestions based on the collection) and cloud cover limit.
    *   **Option 3: Level Audit**: Displays a technical summary of all processing levels (L1C, L2A, TOA, etc.) present in the current catalog.
    *   **Option 4: Export by Level**: Allows filtering collections by a specific level and exporting the list to a CSV file in `output/`.
3.  **Search Coordination**: Uses the `CatalogoGEE` class to filter data and calls `analizar_cobertura_temporal` to execute spatial logic.
4.  **Result Formatting**: Displays a human-readable summary in the console before writing the final CSV report.


### <a name="module-catalog"></a>3.2. Catalog (`catalog.py`)

The `CatalogoGEE` class manages the lifecycle of the metadata catalog (`colecciones_gee.json`).

**Key Functions:**

*   **`buscar_coleccion_api(collection_id)`**:
    Checks the status of a GEE asset before use. Its strategy involves:
    1.  Querying `ee.data.getAsset(id)` for lightweight validation, returning `None` if the asset does not exist or is inaccessible (404/403).
    2.  Parsing asset properties to discard it if marked as `deprecated`.
    3.  Skipping deep image inspection for massive collections (e.g., Landsat) to prevent timeouts.

*   **`limpiar_invalidas()`**:
    Iterates over the local catalog and removes entries corresponding to assets that are no longer accessible in GEE.

*   **`descubrir_colecciones(providers)`**:
    Acts as a crawler, exploring public GEE folders (e.g., `projects/earthengine-public/assets/COPERNICUS`) to identify new `ImageCollection`s.

### <a name="module-analysis"></a>3.3. Analysis (`analysis.py`)

This module executes spatial and temporal queries against GEE.

**Key Functions:**

*   **`buscar_imagenes_por_espacio(id, geometry, dates, ...)`**:
    Executes the main query by applying filters in an optimized order:
    1.  Applies `filterBounds(geometry)` to delegate spatial filtering to the GEE backend.
    2.  Applies `filterDate(start, end)` to narrow the search temporally.
    3.  Applies `limit(limit)` before materializing the list of results to prevent memory errors.

*   **`analizar_cobertura_temporal(...)`**:
    Orchestrates the search process, generates aggregated statistics (e.g., images per year), and exports the results to a CSV file.

### <a name="module-api-utils"></a>3.4. API Utils (`api_utils.py`)

Provides decorators to increase application resilience.

**`@retry_api_call` Decorator**:
Wraps GEE API calls. In case of transient errors (`503 Service Unavailable`, `Timeout`), it can retry the operation or fail gracefully (`raise_on_failure=False`), which is useful for batch processes.

---

## 4. Collection Database

The `config/colecciones_gee.json` file serves as a document database storing metadata for GEE assets.

**JSON Schema Structure:**
```json
{
  "_metadata": { "version": "2.2.0", "last_updated": "..." },
  "category_id": {
    "name": "Category Name",
    "collections": {
      "GEE_ID": {
        "name": "Dataset Title",
        "level": "Processing Level",
        "resolution": "Nominal Resolution",
        "temporal": "Date Range",
        "main_bands": [],
        "last_verified": "Timestamp"
      }
    }
  }
}
```

### Summary of Available Categories

| Category | Description | Approx. Count |
|-----------|-------------|-----------------|
| `opticas_alta_res` | Sentinel-2, Landsat (4-9), MODIS (Reflectance) | ~100 |
| `clima` | ERA5, CHIRPS, GPM, GLDAS, WorldClim | ~300 |
| `vegetacion` | Derived indices (NDVI, EVI, LAI, FPAR) | ~35 |
| `elevacion` | Global and local DEMs (SRTM, ALOS, ArcticDEM) | ~3 |
| `sar` | Synthetic Aperture Radar (Sentinel-1, PALSAR) | ~7 |
| `landcover` | Land cover maps (WorldCover, NLCD, Dynamic World) | ~15 |
| `agua` | Water bodies, recurrence, salinity, temperature | ~30 |
| `atmosfera` | Trace gases (Sentinel-5P: NO2, CO, O3, CH4) | ~90 |
| `fuego` | Fire hotspots and burned areas detection | ~20 |
| `poblacion` | Population density and human settlements | ~15 |

> For the complete and detailed list of all collections, see the **[Full Collection Catalog](docs/CATALOGO_COLECCIONES.md)**.

---

## 5. <a name="setup"></a>Installation and Setup

### Prerequisites
1.  Docker and Docker Compose.
2.  A Google account with access to Google Earth Engine.
3.  A Google Cloud Platform (GCP) Project ID enabled for the GEE API.

### Step 1: Get the Code
Clone the repository to your local machine:
```bash
git clone https://github.com/chachr81/gee_area_explorer.git
cd gee_area_explorer
```

### Step 2: Environment Setup
Copy the example file and define your project ID:
```bash
cp .env.example .env
```
Edit `.env`:
```ini
GEE_PROJECT=your-gcp-project-id
```

### Step 3: Build the Container
This command builds the Docker image locally, installing all dependencies.
```bash
docker-compose build cli
```

### Step 4: Authentication (One-time step)
Authorize the container to use your GEE credentials. This is a one-time operation.
```bash
docker-compose run --rm cli earthengine authenticate
```
Follow the instructions in the terminal: open the URL, authorize access, and paste the verification code. The credentials will be saved in a Docker volume (`gee-credentials`).

---

## 6. <a name="usage"></a>Complete User Guide

### <a name="interactive-mode"></a>A. Interactive Mode

This mode is designed for exploration and quick tests.

1.  **Prepare your Area of Interest**:
    Copy your GeoJSON file into the `data/geojson/` folder.
2.  **Start the Tool**:
    ```bash
    docker-compose run --rm cli
    ```
3.  **Menu Navigation**:
    The menu will guide you to select a collection, an area file, and the search parameters.
4.  **Results**:
    The tool will process the query and save a CSV file in the `output/` directory.

### <a name="pipeline-mode"></a>B. Pipeline Mode (Automation)

Designed to integrate the tool into automated workflows.

**General Syntax:**
```bash
docker-compose run --rm cli python scripts/gee_search.py [PATH_TO_GEOJSON]
```
This command will run the analysis on the specified GeoJSON using default parameters.

---

## 7. <a name="maintenance"></a>System Maintenance

### Check System Health
Runs a series of connection and collection validation tests.
```bash
docker-compose run --rm cli python scripts/test_integral.py
```

### Update and Clean Catalog
Verifies each asset in the catalog against the GEE API and removes invalid entries.
```bash
docker-compose --profile ops run --rm maintenance python scripts/maintain_catalog.py --revalidate --clean
```

---

## 8. <a name="troubleshooting"></a>Troubleshooting

*   **"Credential path not found"**: Indicates an authentication failure. Rerun the authentication step.
*   **"Collection query aborted after accumulating over 5000 elements"**: The current architecture is designed to prevent this error. If it occurs, ensure you have the latest version of the code.
*   **Write permissions on Linux**: Files generated in `output/` belong to the container's `root` user. Change their ownership with `sudo chown -R $USER:$USER output/`.

---

**A Note on Contribution**: This project was refactored and documented with the assistance of Gemini CLI (Gemini 3 Pro model).
MIT License.
