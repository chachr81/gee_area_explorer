#!/usr/bin/env python3
"""
GEE Area Explorer - Búsqueda de Imágenes Satelitales por Área Geográfica
==========================================================================

Herramienta de línea de comandos para buscar y analizar disponibilidad de
imágenes satelitales en Google Earth Engine por área geográfica, rango de
fechas y cobertura de nubes.

Características:
    - Búsqueda por área (entrada GeoJSON)
    - Filtrado por fechas y porcentaje de nubes
    - Análisis de cobertura temporal
    - Exportación a CSV
    - Exploración interactiva del catálogo

Uso:
    python scripts/gee_search.py                        # Menú interactivo
    python scripts/gee_search.py <ruta_geojson>         # Análisis directo
    
Ejemplos:
    python scripts/gee_search.py data/geojson/area.geojson
"""

import sys
from pathlib import Path
from datetime import datetime

# Agregar el directorio raíz al path
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

from src.gee_toolkit.config import get_project_id
from src.gee_toolkit.auth_utils import initialize_gee
from src.gee_toolkit.catalog import CatalogoGEE
from src.gee_toolkit.colecciones_config import get_descripcion_filtro
from src.gee_toolkit.geo_utils import cargar_geojson
from src.gee_toolkit.analysis import analizar_cobertura_temporal


def menu_interactivo():
    """Muestra el menú interactivo para búsqueda espacial."""
    print("\n" + "="*70)
    print("BÚSQUEDA DE IMÁGENES EN GEE")
    print("="*70)
    print("""
Opciones:
1. Análisis rápido: Cobertura de Sentinel-2 en área de ejemplo
2. Búsqueda personalizada: seleccionar colección, área, fechas y nubes
3. Listar niveles de procesamiento disponibles
4. Buscar colecciones por nivel de procesamiento
5. Salir
""")
    
    opcion = input("Selecciona opción (1-5): ").strip()
    return opcion


def main():
    """Función principal."""
    # Inicializar GEE usando utilidades robustas
    initialize_gee()
    
    # Si se pasó un archivo GeoJSON como argumento, analizar directamente
    if len(sys.argv) > 1:
        ruta_geojson = Path(sys.argv[1])
        if not ruta_geojson.exists():
            print(f"[ERROR] No existe el archivo: {ruta_geojson}")
            sys.exit(1)
        
        geometry, gdf = cargar_geojson(ruta_geojson)
        nombre_area = ruta_geojson.stem.replace('_', ' ').title()
        
        analizar_cobertura_temporal(
            collection_id='COPERNICUS/S2_SR_HARMONIZED',
            geometry=geometry,
            nombre_area=nombre_area
        )
        return
    
    # Menú interactivo
    while True:
        opcion = menu_interactivo()
        
        if opcion == '1':
            # Ejemplo rápido con Ñuñoa
            ruta = Path('data/geojson/nunoa.geojson')
            if not ruta.exists():
                print(f"[ERROR] No existe: {ruta}")
                continue
            
            geometry, _ = cargar_geojson(ruta)
            
            # Usar un rango más corto para la demo rápida (último año completo)
            fecha_inicio_demo = '2023-01-01'
            fecha_fin_demo = '2023-12-31'
            
            print(f"\n[INFO] Ejecutando demo rápida ({fecha_inicio_demo} al {fecha_fin_demo})...")
            
            analizar_cobertura_temporal(
                collection_id='COPERNICUS/S2_SR_HARMONIZED',
                geometry=geometry,
                nombre_area='Ñuñoa',
                fecha_inicio=fecha_inicio_demo,
                fecha_fin=fecha_fin_demo
            )
            
            input("\nPresiona Enter para continuar...")
        
        elif opcion == '2':
            # Búsqueda custom
            print("\n" + "="*70)
            print("BÚSQUEDA PERSONALIZADA POR ESPACIO")
            print("="*70)
            
            # 1. Mostrar catálogo y seleccionar colección
            print("\n[INFO] Cargando catálogo de colecciones...")
            catalogo = CatalogoGEE(project_id=get_project_id())
            df_catalogo = catalogo.generar_inventario_completo(exportar_csv=False)
            
            # Filtrar solo colecciones con ImageCollection (no DEM estáticos)
            colecciones_validas = df_catalogo[
                ~df_catalogo['categoria'].str.contains('Elevación|Población', case=False, na=False)
            ].copy()
            
            print(f"\n[OK] {len(colecciones_validas)} colecciones disponibles para búsqueda temporal")
            print("\nOpciones de búsqueda:")
            print("  1. Filtrar por nombre o ID (ej: 'sentinel', 'landsat')")
            print("  2. Buscar por categoría")
            print("  3. Buscar por nivel de procesamiento")
            print("  4. Ver lista completa (paginada)")
            print("  5. Ingresar ID directamente (si ya lo conoces)")
            
            busqueda_opcion = input("\nSelecciona opción (1-5): ").strip()
            
            collection_id = None
            col_info = None
            
            if busqueda_opcion == '1':
                # Filtrar por texto
                filtro = input("\nTexto a buscar (nombre o ID): ").strip().lower()
                if not filtro:
                    print("[INFO] Búsqueda cancelada")
                    continue
                
                resultados = colecciones_validas[
                    colecciones_validas['collection_id'].str.contains(filtro, case=False, na=False) |
                    colecciones_validas['nombre'].str.contains(filtro, case=False, na=False)
                ].reset_index(drop=True)
                
                if len(resultados) == 0:
                    print(f"[INFO] No se encontraron colecciones con '{filtro}'")
                    continue
                
                print(f"\n[OK] {len(resultados)} resultados encontrados:")
                num_seleccion = None
                for i, row in resultados.iterrows():
                    nombre = row['nombre'] if row['nombre'] else row['collection_id']
                    print(f"  {i+1}. {nombre} ({row['collection_id']})")
                    
                    if (i + 1) % 20 == 0 and (i + 1) < len(resultados):
                        ans = input(f"\n[Página {(i+1)//20}] Ingresa número para elegir o Enter para ver más: ").strip()
                        if ans.isdigit():
                            num_seleccion = ans
                            break
                        elif ans.lower() == 's': break

                if not num_seleccion:
                    num_seleccion = input("\nNúmero de colección (o Enter para cancelar): ").strip()
                
                if num_seleccion.isdigit():
                    idx_sel = int(num_seleccion) - 1
                    if 0 <= idx_sel < len(resultados):
                        col_info = resultados.iloc[idx_sel]
                        collection_id = col_info['collection_id']
            
            elif busqueda_opcion == '2':
                # Buscar por categoría
                categorias = colecciones_validas['categoria'].unique()
                print("\n" + "="*70)
                print("CATEGORÍAS DISPONIBLES")
                print("="*70)
                for i, cat in enumerate(categorias, 1):
                    count = len(colecciones_validas[colecciones_validas['categoria'] == cat])
                    print(f"  {i}. {cat} ({count} colecciones)")
                
                cat_num = input("\nSelecciona categoría (número): ").strip()
                if cat_num.isdigit() and 1 <= int(cat_num) <= len(categorias):
                    cat_seleccionada = categorias[int(cat_num) - 1]
                    cols_cat = colecciones_validas[colecciones_validas['categoria'] == cat_seleccionada].reset_index(drop=True)
                    
                    print(f"\n[OK] Colecciones en '{cat_seleccionada}':")
                    num_seleccion = None
                    for i in range(len(cols_cat)):
                        row = cols_cat.iloc[i]
                        nombre = row['nombre'] if row['nombre'] else row['collection_id']
                        print(f"  {i+1}. {nombre} ({row['collection_id']})")
                        
                        if (i + 1) % 20 == 0 and (i + 1) < len(cols_cat):
                            ans = input(f"\n[Página {(i+1)//20}] Ingresa número para elegir o Enter para ver más: ").strip()
                            if ans.isdigit():
                                num_seleccion = ans
                                break
                            elif ans.lower() == 's': break
                    
                    if not num_seleccion:
                        num_seleccion = input("\nNúmero de colección (o Enter para cancelar): ").strip()
                    
                    if num_seleccion.isdigit():
                        idx_sel = int(num_seleccion) - 1
                        if 0 <= idx_sel < len(cols_cat):
                            col_info = cols_cat.iloc[idx_sel]
                            collection_id = col_info['collection_id']
            
            elif busqueda_opcion == '3':
                # Buscar por nivel
                niveles_df = catalogo.listar_niveles_disponibles()
                nivel = input("\nNivel de procesamiento (ej: L2A, TOA, L1C): ").strip().upper()
                
                resultados = catalogo.buscar_por_nivel_procesamiento(nivel).reset_index(drop=True)
                if len(resultados) > 0:
                    print(f"\n[OK] {len(resultados)} colecciones con nivel '{nivel}':")
                    num_seleccion = None
                    for i, row in resultados.iterrows():
                        nombre = row['nombre'] if row['nombre'] else row['collection_id']
                        print(f"  {i+1}. {nombre} ({row['collection_id']})")
                        
                        if (i + 1) % 20 == 0 and (i + 1) < len(resultados):
                            ans = input(f"\n[Página {(i+1)//20}] Ingresa número para elegir o Enter para ver más: ").strip()
                            if ans.isdigit():
                                num_seleccion = ans
                                break
                            elif ans.lower() == 's': break
                    
                    if not num_seleccion:
                        num_seleccion = input("\nNúmero de colección (o Enter para cancelar): ").strip()
                    
                    if num_seleccion.isdigit():
                        idx_sel = int(num_seleccion) - 1
                        if 0 <= idx_sel < len(resultados):
                            col_info = resultados.iloc[idx_sel]
                            collection_id = col_info['collection_id']
                else:
                    print(f"[INFO] No se encontraron colecciones con nivel '{nivel}'")
                    continue
            
            elif busqueda_opcion == '4':
                # Mostrar lista paginada
                print("\n" + "="*70)
                print("LISTA COMPLETA DE COLECCIONES")
                print("="*70)
                
                cols_list = []
                num_seleccion = None
                for i, (idx, row) in enumerate(colecciones_validas.iterrows(), 1):
                    cols_list.append((i, idx, row))
                    nombre = row['nombre'] if row['nombre'] else row['collection_id']
                    print(f"{i}. {nombre} ({row['collection_id']})")
                    
                    if i % 20 == 0 and i < len(colecciones_validas):
                        ans = input(f"\n[Página {i//20}] Ingresa número para elegir o Enter para ver 20 más: ").strip()
                        if ans.isdigit():
                            num_seleccion = ans
                            break
                        elif ans.lower() == 'n': break # Salir de la lista
                
                if not num_seleccion:
                    num_seleccion = input("\nNúmero de colección (o Enter para cancelar): ").strip()
                
                if num_seleccion.isdigit():
                    num_sel = int(num_seleccion)
                    # Buscar en la lista acumulada hasta el momento
                    for display_num, real_idx, row in cols_list:
                        if display_num == num_sel:
                            col_info = row
                            collection_id = col_info['collection_id']
                            break
            
            elif busqueda_opcion == '5':
                # Ingresar ID directamente
                collection_id = input("\nID colección (ej: COPERNICUS/S2_SR_HARMONIZED): ").strip()
                if not collection_id:
                    print("[INFO] Selección cancelada")
                    continue
                
                matches = colecciones_validas[colecciones_validas['collection_id'] == collection_id]
                if len(matches) > 0:
                    col_info = matches.iloc[0]
            
            else:
                print("[ERROR] Opción inválida")
                continue
            
            if not collection_id:
                print("[INFO] No se seleccionó ninguna colección. Volviendo al menú principal...")
                continue
            
            # Extraer fechas default desde metadata si está disponible
            fecha_inicio_default = '2020-01-01'
            fecha_fin_default = datetime.now().strftime('%Y-%m-%d')
            
            if col_info is not None and 'periodo_temporal' in col_info:
                periodo = str(col_info['periodo_temporal'])
                # Parsear "2017-presente" o "2000-2020"
                if 'presente' in periodo.lower():
                    parts = periodo.split('-')
                    if len(parts) >= 2 and parts[0].isdigit():
                        fecha_inicio_default = f"{parts[0]}-01-01"
                elif '-' in periodo:
                    parts = periodo.split('-')
                    if len(parts) == 2:
                        if parts[0].isdigit() and len(parts[0]) == 4:
                            fecha_inicio_default = f"{parts[0]}-01-01"
                        if parts[1].isdigit() and len(parts[1]) == 4:
                            fecha_fin_default = f"{parts[1]}-12-31"
            
            print(f"\n[OK] Colección seleccionada: {collection_id}")
            if col_info is not None:
                print(f"[INFO] Período disponible: {col_info.get('periodo_temporal', 'No especificado')}")
                print(f"[INFO] Resolución: {col_info.get('resolucion_espacial', 'No especificado')}")
                print(f"[INFO] Nivel: {col_info.get('nivel_procesamiento', 'No especificado')}")
            
            # Mostrar info sobre filtro de nubes
            descripcion_filtro = get_descripcion_filtro(collection_id)
            print(f"[INFO] {descripcion_filtro}")
            
            # 2. Seleccionar área GeoJSON (Auto-discovery)
            geojson_dir = Path('data/geojson')
            geojson_files = sorted(list(geojson_dir.glob('*.geojson')))
            
            if not geojson_files:
                print(f"\n[ERROR] No se encontraron archivos .geojson en {geojson_dir}")
                print("       Por favor, coloca tus archivos de área en la carpeta 'data/geojson/'")
                input("Presiona Enter para volver...")
                continue

            print("\n" + "-"*50)
            print("SELECCIÓN DE ÁREA DE ESTUDIO")
            print("-"*50)
            print(f"Archivos encontrados en {geojson_dir}:")
            
            for i, f in enumerate(geojson_files, 1):
                print(f"  {i}. {f.name}")
            
            sel_geo = input("\nSelecciona número de archivo: ").strip()
            if not sel_geo.isdigit() or int(sel_geo) < 1 or int(sel_geo) > len(geojson_files):
                print("[ERROR] Selección inválida.")
                continue
                
            ruta_geojson = geojson_files[int(sel_geo)-1]
            print(f"[OK] Archivo seleccionado: {ruta_geojson}")
            
            # 3. Fechas con defaults inteligentes
            fecha_inicio = input(f"Fecha inicio [default: {fecha_inicio_default}]: ").strip()
            if not fecha_inicio:
                fecha_inicio = fecha_inicio_default
            
            fecha_fin = input(f"Fecha fin [default: {fecha_fin_default}]: ").strip()
            if not fecha_fin:
                fecha_fin = fecha_fin_default
            
            # 4. Filtro de nubes
            max_nubes = input("% nubes máximo [default: 100]: ").strip()
            if not max_nubes:
                max_nubes = 100
            else:
                try:
                    max_nubes = float(max_nubes)
                except ValueError:
                    print("[WARN] Valor inválido, usando 100%")
                    max_nubes = 100
            
            try:
                geometry, _ = cargar_geojson(ruta_geojson)
                nombre_area = ruta_geojson.stem
                
                analizar_cobertura_temporal(
                    collection_id=collection_id,
                    geometry=geometry,
                    nombre_area=nombre_area,
                    fecha_inicio=fecha_inicio,
                    fecha_fin=fecha_fin,
                    max_nubes=max_nubes
                )
            except Exception as e:
                print(f"[ERROR] No se pudo cargar el GeoJSON: {e}")
            
            input("\nPresiona Enter para continuar...")
        
        elif opcion == '3':
            # Listar niveles
            catalogo = CatalogoGEE(project_id=get_project_id())
            catalogo.listar_niveles_disponibles()
            
            input("\nPresiona Enter para continuar...")
        
        elif opcion == '4':
            # Buscar por nivel
            nivel = input("\nNivel de procesamiento (ej: L2A, TOA, L1C): ").strip()
            
            catalogo = CatalogoGEE(project_id=get_project_id())
            resultados = catalogo.buscar_por_nivel_procesamiento(nivel)
            
            if len(resultados) > 0:
                # Exportar CSV
                output_dir = Path('output')
                output_dir.mkdir(exist_ok=True)
                
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                csv_path = output_dir / f'colecciones_nivel_{nivel}_{timestamp}.csv'
                
                resultados.to_csv(csv_path, index=False)
                print(f"\n[OK] Exportado a: {csv_path}")
            
            input("\nPresiona Enter para continuar...")
        
        elif opcion == '5':
            print("\n¡Hasta luego!")
            break
        
        else:
            print("\n[ERROR] Opción inválida")


if __name__ == '__main__':
    main()