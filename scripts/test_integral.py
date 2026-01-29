#!/usr/bin/env python3
"""
Test Integral de GEE Area Explorer
===================================
Este script realiza una verificación completa del sistema, incluyendo:
1. Autenticación
2. Enriquecimiento masivo de metadata (Revalidación)
3. Búsqueda y filtrado
4. Análisis espacial/temporal real
"""

import sys
import time
from pathlib import Path

# Agregar el directorio raíz al path
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

from src.gee_toolkit.auth_utils import initialize_gee
from src.gee_toolkit.catalog import CatalogoGEE
from src.gee_toolkit.geo_utils import cargar_geojson
from src.gee_toolkit.analysis import analizar_cobertura_temporal

def run_integral_test():
    print("\n" + "="*80)
    print("INICIANDO TEST INTEGRAL DE GEE AREA EXPLORER")
    print("="*80)

    # 1. Autenticación
    print("\n[PASO 1] Verificando Autenticación...")
    try:
        initialize_gee()
        print("[OK] Autenticación exitosa.")
    except Exception as e:
        print(f"[ERROR] Fallo en autenticación: {e}")
        return

    # 2. Carga de Catálogo
    print("\n[PASO 2] Cargando Catálogo...")
    catalogo = CatalogoGEE()
    df_inicial = catalogo.generar_inventario_completo(exportar_csv=False)
    print(f"[OK] Catálogo cargado con {len(df_inicial)} colecciones.")

    # 3. Revalidación Masiva (Enriquecimiento de Metadata)
    print("\n[PASO 3] Iniciando Revalidación Masiva (API-First)...")
    print("[INFO] Este proceso enriquecerá el JSON con resoluciones y niveles oficiales.")
    print("[INFO] Procesando colecciones (esto puede tardar unos minutos)...")
    
    total = 0
    actualizados = 0
    errores = 0
    
    start_time = time.time()
    
    # Iterar por todas las categorías y colecciones
    for cat_id, cat_info in catalogo.colecciones.items():
        if cat_id.startswith('_'): continue
        ids = list(cat_info.get('colecciones', {}).keys())
        for cid in ids:
            total += 1
            if total % 20 == 0:
                print(f"  - Procesadas {total} colecciones...")
            
            try:
                if catalogo.verificar_y_actualizar(cid):
                    actualizados += 1
                else:
                    errores += 1
            except Exception:
                errores += 1
    
    end_time = time.time()
    print(f"\n[OK] Revalidación completada en {int(end_time - start_time)} segundos.")
    print(f"     - Total procesadas: {total}")
    print(f"     - Actualizadas con éxito: {actualizados}")
    print(f"     - Errores/No accesibles: {errores}")

    # 4. Verificación de Resultados
    print("\n[PASO 4] Verificando Niveles de Procesamiento después de API-First...")
    catalogo.listar_niveles_disponibles()

    # 5. Test de Análisis Real
    print("\n[PASO 5] Ejecutando Análisis Real (Sentinel-2 en Ñuñoa)...")
    ruta_area = ROOT_DIR / 'data' / 'geojson' / 'nunoa.geojson'
    if ruta_area.exists():
        geometry, _ = cargar_geojson(ruta_area)
        try:
            analizar_cobertura_temporal(
                collection_id='COPERNICUS/S2_SR_HARMONIZED',
                geometry=geometry,
                nombre_area='Ñuñoa_Test',
                fecha_inicio='2023-01-01',
                fecha_fin='2023-03-31' # Rango corto para el test
            )
            print("[OK] Análisis completado exitosamente.")
        except Exception as e:
            print(f"[ERROR] Error en análisis: {e}")
    else:
        print("[SKIP] No se encontró el área de prueba en data/geojson/nunoa.geojson")

    print("\n" + "="*80)
    print("TEST INTEGRAL FINALIZADO")
    print("="*80)

if __name__ == "__main__":
    run_integral_test()
