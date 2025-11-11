#!/usr/bin/env python3
"""
Script de mantenimiento del catálogo GEE.

Funciones:
- Re-validar colecciones expiradas contra API
- Agregar nuevas colecciones Level 2/3
- Limpiar colecciones inválidas
- Generar reporte de estado del catálogo

Uso:
    python scripts/maintain_catalog.py --revalidate
    python scripts/maintain_catalog.py --add MODIS/061/MOD13A1
    python scripts/maintain_catalog.py --report
    python scripts/maintain_catalog.py --clean
"""

import sys
import argparse
import logging
from pathlib import Path

# Agregar src al path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from gee_toolkit.catalog import CatalogoGEE
from gee_toolkit.config import get_project_id
import ee


def configurar_logging():
    """Configura logging para el script."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def inicializar_gee():
    """Inicializa conexión con GEE."""
    try:
        project_id = get_project_id()
        ee.Initialize(project=project_id)
        catalog = CatalogoGEE(project_id=project_id)
        print(f"[OK] Conectado a GEE (proyecto: {project_id})")
        return catalog
    except Exception as e:
        print(f"[ERROR] Error al inicializar GEE: {e}")
        sys.exit(1)


def revalidar_colecciones(catalog, dias_expiracion=30, limite=None):
    """
    Re-valida colecciones expiradas contra la API de GEE.
    
    Args:
        catalog: Instancia de CatalogoGEE
        dias_expiracion: Umbral de días para considerar expirada
        limite: Máximo de colecciones a validar (None = TODAS)
                Usar límite solo para pruebas rápidas, por defecto valida todas.
    """
    print("\n" + "="*80)
    print("RE-VALIDACIÓN DE COLECCIONES EXPIRADAS")
    print("="*80)
    
    # Buscar colecciones expiradas
    print(f"\n[1] Buscando colecciones expiradas (>{dias_expiracion} días)...")
    expiradas = catalog.verificar_colecciones_expiradas(dias_expiracion=dias_expiracion)
    
    if not expiradas:
        print("    [OK] No hay colecciones expiradas")
        return
    
    print(f"    Encontradas: {len(expiradas)} colecciones")
    
    # Aplicar límite si se especifica
    a_validar = expiradas[:limite] if limite else expiradas
    
    if limite:
        print(f"    [ADVERTENCIA] Usando límite de {limite} colecciones (para pruebas rápidas)")
        print("    [INFO] Para validar todas, ejecuta sin --limit")
    
    print(f"\n[2] Re-validando {len(a_validar)} colecciones contra API...")
    
    validas = 0
    invalidas = 0
    actualizadas = 0
    
    for i, col_id in enumerate(a_validar, 1):
        try:
            print(f"    [{i}/{len(a_validar)}] {col_id}...", end=" ")
            
            # Verificar y actualizar si cambió
            resultado = catalog.verificar_coleccion(col_id, actualizar_si_cambio=True)
            
            if resultado:
                validas += 1
                print("[OK] Válida")
            else:
                invalidas += 1
                print("[ERROR] No encontrada")
                
        except Exception as e:
            invalidas += 1
            print(f"[ERROR] Error: {e}")
    
    # Resumen
    print(f"\n[3] Resumen:")
    print(f"    • Válidas: {validas}")
    print(f"    • Inválidas: {invalidas}")
    print(f"    • Pendientes: {len(expiradas) - len(a_validar)}")
    
    if invalidas > 0:
        print(f"\n    [ADVERTENCIA] {invalidas} colecciones no pudieron validarse")
        print("    Considera ejecutar --clean para eliminarlas")


def agregar_coleccion(catalog, collection_id, categoria='auto_agregadas'):
    """
    Agrega una nueva colección al catálogo desde la API.
    
    Args:
        catalog: Instancia de CatalogoGEE
        collection_id: ID de la colección en GEE
        categoria: Categoría donde agregarla
    """
    print("\n" + "="*80)
    print("AGREGAR NUEVA COLECCIÓN")
    print("="*80)
    
    print(f"\n[1] Buscando colección en API de GEE...")
    print(f"    ID: {collection_id}")
    
    try:
        # Buscar en API sin guardar primero
        metadata = catalog.buscar_coleccion_api(collection_id)
        
        if not metadata:
            print("    [ERROR] Colección no encontrada en API")
            return False
        
        print("    [OK] Encontrada en API")
        print(f"    • Tipo: {metadata['tipo']}")
        print(f"    • Bandas: {len(metadata['bandas'])}")
        print(f"    • Bandas principales: {', '.join(metadata['bandas'][:5])}")
        
        # Agregar al catálogo
        print(f"\n[2] Agregando a categoría '{categoria}'...")
        resultado = catalog.agregar_coleccion_al_catalogo(collection_id, categoria=categoria)
        
        if resultado:
            print("    [OK] Colección agregada exitosamente")
            print(f"    • Guardada en: config/colecciones_gee.json")
            return True
        else:
            print("    [ERROR] Error al agregar colección")
            return False
            
    except Exception as e:
        print(f"    [ERROR] Error: {e}")
        return False


def generar_reporte(catalog):
    """
    Genera reporte detallado del estado del catálogo.
    
    Args:
        catalog: Instancia de CatalogoGEE
    """
    print("\n" + "="*80)
    print("REPORTE DE ESTADO DEL CATÁLOGO")
    print("="*80)
    
    # Metadata
    metadata = catalog.colecciones.get('_metadata', {})
    version = metadata.get('version', 'N/A')
    ultima_actualizacion = metadata.get('ultima_actualizacion', 'N/A')
    auto_update = metadata.get('auto_update_enabled', False)
    cache_days = metadata.get('cache_duration_days', 30)
    
    print(f"\n[1] Información General:")
    print(f"    • Versión: {version}")
    print(f"    • Última actualización: {ultima_actualizacion}")
    print(f"    • Auto-actualización: {'Habilitada' if auto_update else 'Deshabilitada'}")
    print(f"    • Duración cache: {cache_days} días")
    
    # Categorías
    categorias = [k for k in catalog.colecciones.keys() if not k.startswith('_')]
    
    print(f"\n[2] Distribución por Categoría:")
    print(f"    Total categorías: {len(categorias)}")
    
    total_colecciones = 0
    categoria_mas_grande = None
    max_colecciones = 0
    
    for cat_id in sorted(categorias):
        cat_data = catalog.colecciones[cat_id]
        nombre = cat_data.get('nombre', cat_id)
        num_cols = len(cat_data.get('colecciones', {}))
        total_colecciones += num_cols
        
        if num_cols > max_colecciones:
            max_colecciones = num_cols
            categoria_mas_grande = nombre
        
        print(f"    • {nombre}: {num_cols} colecciones")
    
    print(f"\n    TOTAL: {total_colecciones} colecciones")
    print(f"    Mayor: {categoria_mas_grande} ({max_colecciones} colecciones)")
    
    # Colecciones expiradas
    print(f"\n[3] Estado de Validación:")
    expiradas = catalog.verificar_colecciones_expiradas(dias_expiracion=cache_days)
    print(f"    • Colecciones expiradas (>{cache_days} días): {len(expiradas)}")
    print(f"    • Colecciones válidas: {total_colecciones - len(expiradas)}")
    
    if expiradas:
        print(f"\n    [ADVERTENCIA] {len(expiradas)} colecciones necesitan re-validación")
        print(f"    Ejecuta: python scripts/maintain_catalog.py --revalidate")
    
    # Colecciones auto-agregadas
    auto_agregadas = catalog.colecciones.get('auto_agregadas', {}).get('colecciones', {})
    if auto_agregadas:
        print(f"\n[4] Colecciones Auto-agregadas:")
        print(f"    Total: {len(auto_agregadas)}")
        for col_id, col_data in list(auto_agregadas.items())[:5]:
            verified = col_data.get('last_verified', 'N/A')
            print(f"    • {col_id}")
            print(f"      Verificada: {verified}")
    
    print("\n" + "="*80)


def limpiar_invalidas(catalog):
    """
    Limpia colecciones inválidas del catálogo.
    
    Args:
        catalog: Instancia de CatalogoGEE
    """
    print("\n" + "="*80)
    print("LIMPIEZA DE COLECCIONES INVÁLIDAS")
    print("="*80)
    
    print(f"\n[1] Validando todas las colecciones contra API...")
    print("    (Esto puede tardar varios minutos)")
    
    invalidas = []
    total = 0
    
    # Recorrer todas las categorías
    for cat_id, cat_data in catalog.colecciones.items():
        if cat_id.startswith('_'):
            continue
        
        colecciones = cat_data.get('colecciones', {})
        
        for col_id in colecciones.keys():
            total += 1
            print(f"    [{total}] Verificando {col_id}...", end=" ")
            
            try:
                # Verificar sin actualizar
                valida = catalog.verificar_coleccion(col_id, actualizar_si_cambio=False)
                
                if valida:
                    print("[OK]")
                else:
                    print("[ERROR] Inválida")
                    invalidas.append((cat_id, col_id))
                    
            except Exception as e:
                print(f"[ERROR] Error: {e}")
                invalidas.append((cat_id, col_id))
    
    # Resumen
    print(f"\n[2] Resultado:")
    print(f"    • Colecciones verificadas: {total}")
    print(f"    • Inválidas encontradas: {len(invalidas)}")
    
    if not invalidas:
        print("\n    [OK] No hay colecciones inválidas")
        return
    
    # Mostrar inválidas
    print(f"\n[3] Colecciones inválidas:")
    for cat_id, col_id in invalidas:
        print(f"    • {col_id} (categoría: {cat_id})")
    
    # Confirmar eliminación
    print(f"\n[4] ¿Eliminar estas {len(invalidas)} colecciones del catálogo?")
    respuesta = input("    Escribe 'si' para confirmar: ").strip().lower()
    
    if respuesta == 'si':
        eliminadas = 0
        for cat_id, col_id in invalidas:
            try:
                del catalog.colecciones[cat_id]['colecciones'][col_id]
                eliminadas += 1
                print(f"    [OK] Eliminada: {col_id}")
            except Exception as e:
                print(f"    [ERROR] Error eliminando {col_id}: {e}")
        
        # Guardar cambios
        catalog._guardar_catalogo()
        print(f"\n    [OK] {eliminadas} colecciones eliminadas del catálogo")
    else:
        print("\n    [ERROR] Operación cancelada")


def agregar_lote(catalog, archivo_lista, categoria='auto_agregadas'):
    """
    Agrega múltiples colecciones desde un archivo de texto.
    
    Args:
        catalog: Instancia de CatalogoGEE
        archivo_lista: Path al archivo con IDs (uno por línea)
        categoria: Categoría donde agregarlas
    """
    print("\n" + "="*80)
    print("AGREGAR COLECCIONES EN LOTE")
    print("="*80)
    
    archivo = Path(archivo_lista)
    
    if not archivo.exists():
        print(f"[ERROR] Archivo no encontrado: {archivo}")
        return
    
    # Leer IDs
    with archivo.open('r') as f:
        collection_ids = [line.strip() for line in f if line.strip() and not line.startswith('#')]
    
    print(f"\n[1] Archivo: {archivo.name}")
    print(f"    Colecciones a agregar: {len(collection_ids)}")
    
    # Confirmar
    print(f"\n[2] ¿Proceder con la agregación?")
    respuesta = input("    Escribe 'si' para confirmar: ").strip().lower()
    
    if respuesta != 'si':
        print("\n    [ERROR] Operación cancelada")
        return
    
    # Agregar cada colección
    print(f"\n[3] Agregando colecciones...")
    exitosas = 0
    fallidas = 0
    
    for i, col_id in enumerate(collection_ids, 1):
        print(f"\n    [{i}/{len(collection_ids)}] {col_id}")
        try:
            resultado = catalog.agregar_coleccion_al_catalogo(col_id, categoria=categoria)
            if resultado:
                exitosas += 1
                print("         [OK] Agregada")
            else:
                fallidas += 1
                print("         [ERROR] Falló")
        except Exception as e:
            fallidas += 1
            print(f"         [ERROR] Error: {e}")
    
    # Resumen
    print(f"\n[4] Resumen:")
    print(f"    • Exitosas: {exitosas}")
    print(f"    • Fallidas: {fallidas}")


def main():
    """Función principal."""
    parser = argparse.ArgumentParser(
        description='Herramienta de mantenimiento del catálogo GEE',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos de uso:
  
  # 1. PRIMER USO: Generar reporte de estado
  python scripts/maintain_catalog.py --report
  
  # 2. Re-validar TODAS las colecciones expiradas (recomendado)
  python scripts/maintain_catalog.py --revalidate
  
  # 3. Re-validar solo 10 colecciones (prueba rápida)
  python scripts/maintain_catalog.py --revalidate --limit 10
  
  # 4. Agregar una colección específica
  python scripts/maintain_catalog.py --add MODIS/061/MOD13A1
  
  # 5. Agregar múltiples colecciones desde archivo
  python scripts/maintain_catalog.py --batch colecciones.txt
  
  # 6. Limpiar colecciones inválidas (interactivo)
  python scripts/maintain_catalog.py --clean
  
NOTA: --limit es OPCIONAL, solo para pruebas rápidas.
      Por defecto valida TODAS las colecciones expiradas.
        """
    )
    
    parser.add_argument(
        '--report',
        action='store_true',
        help='Genera reporte de estado del catálogo'
    )
    
    parser.add_argument(
        '--revalidate',
        action='store_true',
        help='Re-valida colecciones expiradas contra API'
    )
    
    parser.add_argument(
        '--limit',
        type=int,
        metavar='N',
        help='Límite de colecciones a re-validar'
    )
    
    parser.add_argument(
        '--add',
        type=str,
        metavar='COLLECTION_ID',
        help='Agrega una colección específica al catálogo'
    )
    
    parser.add_argument(
        '--batch',
        type=str,
        metavar='FILE',
        help='Agrega colecciones desde archivo de texto (un ID por línea)'
    )
    
    parser.add_argument(
        '--category',
        type=str,
        default='auto_agregadas',
        help='Categoría para colecciones nuevas (default: auto_agregadas)'
    )
    
    parser.add_argument(
        '--clean',
        action='store_true',
        help='Limpia colecciones inválidas del catálogo (interactivo)'
    )
    
    parser.add_argument(
        '--days',
        type=int,
        default=30,
        metavar='N',
        help='Días para considerar colección expirada (default: 30)'
    )
    
    args = parser.parse_args()
    
    # Validar que se especificó al menos una operación
    if not any([args.report, args.revalidate, args.add, args.batch, args.clean]):
        parser.print_help()
        sys.exit(0)
    
    # Configurar logging
    configurar_logging()
    
    # Inicializar GEE
    catalog = inicializar_gee()
    
    # Ejecutar operaciones
    try:
        if args.report:
            generar_reporte(catalog)
        
        if args.revalidate:
            revalidar_colecciones(catalog, dias_expiracion=args.days, limite=args.limit)
        
        if args.add:
            agregar_coleccion(catalog, args.add, categoria=args.category)
        
        if args.batch:
            agregar_lote(catalog, args.batch, categoria=args.category)
        
        if args.clean:
            limpiar_invalidas(catalog)
        
        print("\n[OK] Operación completada")
        
    except KeyboardInterrupt:
        print("\n\n[ADVERTENCIA] Operación interrumpida por el usuario")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] Error: {e}")
        logging.exception("Error en main:")
        sys.exit(1)


if __name__ == '__main__':
    main()
