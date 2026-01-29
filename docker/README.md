# Guía de Despliegue Docker (GEE Area Explorer)

[🇺🇸 View in English](README.en.md)

Este documento detalla el procedimiento técnico para desplegar la herramienta como un contenedor Docker autocontenido ("Appliance"). Esta es la forma recomendada de uso, ya que garantiza un entorno estable con todas las dependencias geoespaciales (GDAL, earthengine-api) preinstaladas.

---

## 1. Requisitos Previos

Antes de iniciar, asegúrese de contar con lo siguiente:

1.  **Docker Engine & Docker Compose**: Instalados y en ejecución en su máquina host.
2.  **Cuenta de Google**: Una cuenta con acceso habilitado a [Google Earth Engine](https://signup.earthengine.google.com/).
3.  **Proyecto en Google Cloud Platform (GCP)**: Un proyecto activo donde se ejecutará la facturación (o cuota gratuita) de las consultas.

### Configuración del Proyecto GCP (Paso Crítico)

Para que la herramienta funcione, debe tener un "Project ID" válido.

1.  Vaya a la [Consola de Google Cloud](https://console.cloud.google.com/).
2.  Cree un nuevo proyecto o seleccione uno existente.
3.  **Habilitar API**: En el menú "APIs & Services" > "Library", busque **"Earth Engine API"** y actívela.
4.  **Registrar Proyecto**: Vaya al [Editor de Código de GEE](https://code.earthengine.google.com/), haga clic en su icono de usuario (arriba a la derecha) y asegúrese de que su proyecto Cloud esté registrado para uso de Earth Engine.
5.  **Obtener ID**: Copie el **Project ID** (ej: `mi-proyecto-geo-12345`).

---

## 2. Preparación del Entorno

### Estructura de Directorios

Cree una carpeta para el proyecto con la siguiente estructura:

```text
mi-despliegue/
├── docker-compose.yml      # (Provisto en el repositorio)
├── .env                    # Archivo para variables de entorno
├── data/
│   └── geojson/            # Carpeta de entrada para sus archivos .geojson
├── output/                 # Carpeta de salida para los resultados en CSV
└── logs/                   # (Opcional) Registros de ejecución
```

### Configuración de Credenciales (.env)

Cree un archivo `.env` en la raíz con el siguiente contenido:

```ini
GEE_PROJECT=su-id-de-proyecto-aqui
```

---

## 3. Construcción e Instalación

Construya la imagen Docker (solo se hace una vez):

```bash
docker-compose build cli
```

---

## 4. Autenticación (Paso Único)

Autorice al contenedor para acceder a Google Earth Engine. Este paso guarda un token persistente.

```bash
docker-compose run --rm cli earthengine authenticate
```

**Procedimiento:**
1.  Abra la URL que aparecerá en la terminal.
2.  Autorice el acceso con su cuenta de Google.
3.  Copie el código de autorización y péguelo en la terminal.

---

## 5. Ejecución de la Herramienta

### Modo Interactivo (Recomendado para Exploración)
Lanza un menú visual que le guía en el proceso.

```bash
docker-compose run --rm cli
```

### Modo de Línea de Comandos (Para Scripts)
Ideal para integrar en flujos de trabajo automatizados.

```bash
docker-compose run --rm cli python scripts/gee_search.py data/geojson/su_area.geojson
```

---

## 6. Solución de Problemas Comunes

*   **Error: "Project ID not found"**: Verifique que el archivo `.env` exista y contenga la variable `GEE_PROJECT`.
*   **Error: "Credential path not found"**: Repita el paso de autenticación.
*   **Permisos en Linux**: Si los archivos en `output/` son creados por `root`, cambie su propietario con `sudo chown -R $USER:$USER output/`.