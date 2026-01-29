# Contribuyendo a GEE Area Explorer

¡Gracias por tu interés en mejorar este proyecto!

## Flujo de Trabajo para Colaboradores

Este proyecto sigue un modelo de desarrollo basado en **Trunk Based Development** con ramas de características efímeras.

### 1. Reportar Problemas
*   Antes de abrir un issue, busca si ya existe.
*   Usa las plantillas de GitHub para **Bug Reports** o **Feature Requests**.
*   Proporciona logs completos y, si es posible, el archivo GeoJSON que causó el error.

### 2. Desarrollo Local
Para trabajar en el código, recomendamos usar el entorno Docker para garantizar la paridad con producción.

```bash
# Construir imagen local
docker-compose build cli

# Ejecutar tests de integración
docker-compose run --rm cli python scripts/test_integral.py
```

### 3. Enviar Cambios (Pull Requests)
1.  Haz un Fork del repositorio.
2.  Crea una rama descriptiva (`feat/nueva-busqueda`, `fix/error-memoria`).
3.  **Ejecuta el test integral** antes de enviar. Si el test falla, el PR no será aceptado.
4.  Asegúrate de no subir credenciales (`.env`) ni archivos temporales.

## Estándares de Código

*   **Python 3.12+**.
*   **Type Hints**: Usar tipado estático en firmas de funciones.
*   **Docstrings**: Google Style o NumPy Style.
*   **Idioma**: El código y los comentarios deben estar en inglés técnico o español neutro (preferiblemente español para este fork).

## Versionado

Este proyecto usa [Semantic Versioning 2.0.0](https://semver.org/).

*   **MAJOR** (1.0.0): Cambios incompatibles en la API o CLI.
*   **MINOR** (1.1.0): Nuevas funcionalidades retro-compatibles.
*   **PATCH** (1.0.1): Corrección de bugs.

La versión oficial se gestiona a través de etiquetas (tags) en el repositorio y en la imagen Docker (`vX.Y.Z`).

---
**Nota:** Este proyecto es una herramienta de ingeniería profesional. Por favor, mantén el tono técnico en las discusiones.