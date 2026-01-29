# Guía de Despliegue Docker (GEE Area Explorer)

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
4.  **Registrar Proyecto**: Vaya al [Editor de Código de GEE](https://code.earthengine.google.com/), haga clic en su icono de usuario (arriba a la derecha) y asegúrese de que su proyecto Cloud esté registrado para uso de Earth Engine (puede elegir "Unpaid usage" para investigación/educación).
5.  **Obtener ID**: Copie el **Project ID** (ej: `mi-proyecto-geo-12345`). *Nota: No es el nombre del proyecto, es el ID.*

---

## 2. Preparación del Entorno

La herramienta requiere una estructura de directorios específica en su máquina host para mapear datos y configuraciones al contenedor.

### Estructura de Directorios

Cree una carpeta para el proyecto y asegúrese de que tenga la siguiente estructura:

```text
mi-despliegue/
├── docker-compose.yml      # (Provisto en el repositorio)
├── .env                    # Archivo de secretos
├── data/
│   └── geojson/            # CARPETA DE ENTRADA: Coloque aquí sus archivos .geojson
├── output/                 # CARPETA DE SALIDA: Aquí aparecerán los CSV generados
└── logs/                   # (Opcional) Registros de ejecución
```

### Configuración de Credenciales (.env)

Cree un archivo llamado `.env` en la raíz de su directorio de despliegue. Este archivo inyectará el ID del proyecto al contenedor.

**Contenido de `.env`:**

```ini
# ID de su proyecto Google Cloud (Obtenido en el paso 1)
GEE_PROJECT=su-id-de-proyecto-aqui
```

---

## 3. Construcción e Instalación

Una vez configurado el entorno, construya la imagen Docker. Este paso descargará una imagen base ligera de Python y compilará las librerías geoespaciales.

```bash
docker-compose build cli
```

---

## 4. Autenticación (Paso Único)

La herramienta necesita un token de acceso para comunicarse con Google Earth Engine. Este token se genera mediante un flujo OAuth2 y se guardará en un volumen Docker persistente (`gee-credentials`), por lo que **solo necesita hacerlo una vez**.

Ejecute el siguiente comando:

```bash
docker-compose run --rm cli earthengine authenticate
```

**Procedimiento:**
1.  El terminal mostrará una URL larga (ej: `https://accounts.google.com/o/oauth2/auth...`).
2.  Abra esa URL en su navegador web.
3.  Seleccione la cuenta de Google asociada a su proyecto GEE.
4.  Autorice el acceso a la aplicación "Earth Engine CLI".
5.  Google le proporcionará un **Código de Autorización**. Cópielo.
6.  Vuelva a su terminal, pegue el código y presione `Enter`.

Si tiene éxito, verá el mensaje: `Successfully saved authorization token`.

---

## 5. Ejecución de la Herramienta

Existen dos modos de operación dependiendo de su caso de uso.

### Modo A: Interactivo (Recomendado para Exploración)

Lanza un menú visual en la terminal que le guía paso a paso.

```bash
docker-compose run --rm cli
```

1.  **Seleccione una opción** (ej: "2. Búsqueda personalizada").
2.  La herramienta escaneará automáticamente la carpeta `./data/geojson` de su host y le mostrará una lista numerada de archivos disponibles.
3.  Seleccione el número de su archivo.
4.  Configure fechas y filtros de nubosidad.
5.  El resultado se guardará en `./output/`.

### Modo B: Línea de Comandos (Para Pipelines/Scripts)

Puede invocar scripts específicos directamente sin interacción humana. Ideal para tareas programadas (Cron) o orquestadores (Airflow).

**Sintaxis:**
`docker-compose run --rm cli python scripts/[SCRIPT] [ARGUMENTOS]`

#### Ejemplo: Analizar un área específica
```bash
docker-compose run --rm cli python scripts/gee_search.py data/geojson/zona_incendio.geojson
```

#### Ejemplo: Validar integridad del catálogo
```bash
docker-compose run --rm cli python scripts/test_integral.py
```

---

## 6. Mantenimiento y Administración

### Actualización del Catálogo
El sistema incluye una base de datos local (`config/colecciones_gee.json`) con metadatos de +600 colecciones. Para mantenerla actualizada o eliminar activos obsoletos:

```bash
# Revalidar todas las colecciones y limpiar deprecadas
docker-compose --profile ops run --rm maintenance python scripts/maintain_catalog.py --revalidate --clean
```

---

## 7. Solución de Problemas Comunes

### Error: "Project ID not found"
*   **Causa**: El archivo `.env` no existe o la variable `GEE_PROJECT` está vacía.
*   **Solución**: Verifique que el archivo `.env` esté en la misma carpeta que `docker-compose.yml` y tenga el formato correcto.

### Error: "Credential path not found"
*   **Causa**: El contenedor no encuentra el token de autenticación.
*   **Solución**: El volumen `gee-credentials` podría estar vacío o corrupto. Repita el paso **4. Autenticación**.

### Archivos de salida bloqueados (Linux)
*   **Causa**: Los archivos en `output/` se crean con usuario `root` (UID 0) porque así corre el proceso dentro del contenedor.
*   **Solución**: Ejecute `sudo chown -R $USER:$USER output/` en su host para recuperar la propiedad de los archivos.