# Contribuyendo a GEE Area Explorer

Gracias por tu interés en contribuir.

## Cómo Contribuir

### Reportar Bugs
- Usa el template de [Bug Report](.github/ISSUE_TEMPLATE/bug_report.md)
- Incluye pasos claros para reproducir el error
- Especifica tu entorno (OS, Python version, etc.)

### Sugerir Features
- Usa el template de [Feature Request](.github/ISSUE_TEMPLATE/feature_request.md)
- Explica el caso de uso y beneficio
- Considera alternativas y limitaciones

### Pull Requests

1. **Fork el repositorio**
2. **Crea una rama** para tu feature
   ```bash
   git checkout -b feature/mi-nueva-caracteristica
   ```
3. **Haz tus cambios**
   - Sigue el estilo de código existente
   - Agrega comentarios donde sea necesario
   - Actualiza la documentación si aplica

4. **Commit con mensajes claros**
   ```bash
   git commit -m "feat: agrega nueva funcionalidad X"
   ```
   
   Convención de commits:
   - `feat:` nueva característica
   - `fix:` corrección de bug
   - `docs:` cambios en documentación
   - `refactor:` refactorización de código
   - `test:` agregar o modificar tests

5. **Push y crea Pull Request**
   ```bash
   git push origin feature/mi-nueva-caracteristica
   ```

## Estándares de Código

- **Python 3.12+**
- Seguir PEP 8
- Docstrings en español
- Type hints donde sea posible

## Testing

Si agregas nueva funcionalidad, considera agregar tests:
```bash
pytest tests/
```

## Preguntas

¿Dudas? Abre un [Issue](https://github.com/chachr81/gee_area_explorer/issues) con tu pregunta.

---

**Nota:** Este es un proyecto educativo enfocado en facilitar el aprendizaje de Google Earth Engine API.
