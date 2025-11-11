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

# Agregar el directorio raíz al path
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

import ee
import geopandas as gpd
import pandas as pd
from datetime import datetime
from typing import Dict, List, Tuple

from src.gee_toolkit.config import get_project_id
from src.gee_toolkit.catalog import CatalogoGEE
from src.gee_toolkit.colecciones_config import soporta_filtro_nubes, get_descripcion_filtro


def cargar_geojson(ruta_geojson: Path) -> Tuple[ee.Geometry, gpd.GeoDataFrame]:
    """Carga un archivo GeoJSON y lo convierte a geometría de Earth Engine."""
    try:
        gdf = gpd.read_file(ruta_geojson)
        
        if len(gdf) == 0:
            raise ValueError("El GeoJSON no contiene features")
        
        geom_geojson = gdf.geometry.iloc[0].__geo_interface__
        ee_geometry = ee.Geometry(geom_geojson)
        
        return ee_geometry, gdf
        
    except Exception as e:
        print(f"[ERROR] No se pudo cargar el GeoJSON: {e}")
        sys.exit(1)


def buscar_imagenes_por_espacio(
    collection_id: str,
    geometry: ee.Geometry,
    fecha_inicio: str,
    fecha_fin: str,
    max_nubes: float = 100,
    limite: int = 500
) -> List[Dict]:
    """
    Busca imágenes en una colección por espacio, tiempo y cobertura nubosa.
    
    Args:
        collection_id: ID de la colección
        geometry: Geometría del área de interés
        fecha_inicio: Fecha inicial (YYYY-MM-DD)
        fecha_fin: Fecha final (YYYY-MM-DD)
        max_nubes: Porcentaje máximo de nubes
        limite: Número máximo de imágenes a retornar
    
    Returns:
        Lista de diccionarios con información de cada imagen
    """
    coleccion = ee.ImageCollection(collection_id) \
        .filterBounds(geometry) \
        .filterDate(fecha_inicio, fecha_fin)
    
    # Verificar si la colección soporta filtro de nubes usando configuración
    soporta, propiedad = soporta_filtro_nubes(collection_id)
    
    if max_nubes < 100:
        if soporta is True:
            # Aplicar filtro según la propiedad disponible
            coleccion = coleccion.filter(ee.Filter.lt(propiedad, max_nubes))
            print(f"[INFO] Filtro de nubes aplicado: {propiedad} < {max_nubes}%")
        elif soporta is False:
            # Colección conocida sin filtro de nubes
            print(f"[INFO] Esta colección no tiene filtro de nubes (SAR/Climática/Producto derivado)")
        else:
            # Colección no catalogada - intentar detectar
            print(f"[INFO] Verificando si la colección soporta filtro de nubes...")
            try:
                count = coleccion.size().getInfo()
                if count > 0:
                    first_img = coleccion.first()
                    props = first_img.getInfo()['properties']
                    
                    if 'CLOUDY_PIXEL_PERCENTAGE' in props:
                        coleccion = coleccion.filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', max_nubes))
                        print(f"[INFO] Filtro de nubes aplicado: CLOUDY_PIXEL_PERCENTAGE < {max_nubes}%")
                    elif 'CLOUD_COVER' in props:
                        coleccion = coleccion.filter(ee.Filter.lt('CLOUD_COVER', max_nubes))
                        print(f"[INFO] Filtro de nubes aplicado: CLOUD_COVER < {max_nubes}%")
                    else:
                        print(f"[INFO] Esta colección no tiene propiedades de nubes")
            except Exception as e:
                print(f"[WARN] No se pudo verificar propiedades de nubes: {e}")
    
    coleccion = coleccion.limit(limite)
    
    # Obtener lista de imágenes
    try:
        img_list = coleccion.toList(limite)
        size = img_list.size().getInfo()
        
        if size == 0:
            return []
        
        imagenes = []
        for i in range(size):
            img = ee.Image(img_list.get(i))
            info = img.getInfo()
            
            # Extraer metadata
            props = info.get('properties', {})
            fecha_ms = props.get('system:time_start')
            fecha = None
            if fecha_ms:
                from datetime import datetime
                fecha = datetime.fromtimestamp(fecha_ms / 1000).strftime('%Y-%m-%d')
            
            # Extraer % nubes si existe
            nubes = props.get('CLOUDY_PIXEL_PERCENTAGE') or props.get('CLOUD_COVER')
            
            imagenes.append({
                'id': info['id'],
                'fecha': fecha,
                'nubes': nubes,
                'properties': props
            })
        
        return imagenes
    
    except Exception as e:
        print(f"[ERROR] al obtener imágenes: {e}")
        return []


def analizar_cobertura_temporal(
    collection_id: str,
    geometry: ee.Geometry,
    nombre_area: str,
    fecha_inicio: str = '2020-01-01',
    fecha_fin: str = '2024-12-31',
    max_nubes: float = 100
):
    """
    Analiza la cobertura temporal de una colección en un área.
    
    Args:
        collection_id: ID de la colección
        geometry: Geometría del área
        nombre_area: Nombre del área para display
        fecha_inicio: Fecha inicio (YYYY-MM-DD)
        fecha_fin: Fecha fin (YYYY-MM-DD)
        max_nubes: % máximo de nubes
    """
    print("\n" + "="*70)
    print(f"ANÁLISIS DE COBERTURA TEMPORAL: {nombre_area.upper()}")
    print("="*70)
    
    # Calcular área
    area_m2 = geometry.area().getInfo()
    area_ha = area_m2 / 10000
    print(f"\n[INFO] Área: {area_ha:.2f} ha ({area_m2/1000000:.2f} km²)")
    print(f"[INFO] Colección: {collection_id}")
    print(f"[INFO] Período: {fecha_inicio} a {fecha_fin}")
    print(f"[INFO] Filtro nubes: ≤{max_nubes}%")
    
    # Buscar imágenes
    print("\n[INFO] Analizando cobertura temporal...")
    
    try:
        imagenes = buscar_imagenes_por_espacio(
            collection_id=collection_id,
            geometry=geometry,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            max_nubes=max_nubes,
            limite=500
        )
        
        if not imagenes:
            print("[WARN] No se encontraron imágenes")
            return
        
        print(f"[OK] Imágenes encontradas: {len(imagenes)}")
        
        # Análisis por año
        df = pd.DataFrame(imagenes)
        if 'fecha' in df.columns and df['fecha'].notna().any():
            df['año'] = pd.to_datetime(df['fecha']).dt.year
            por_año = df.groupby('año').size()
            
            print("\n" + "-"*70)
            print("DISTRIBUCIÓN TEMPORAL:")
            print("-"*70)
            for año, count in por_año.items():
                print(f"  {año}: {count:3d} imágenes")
            
            # Análisis de nubes si está disponible
            if 'nubes' in df.columns and df['nubes'].notna().any():
                print("\n" + "-"*70)
                print("CALIDAD (% NUBES):")
                print("-"*70)
                print(f"  Promedio: {df['nubes'].mean():.1f}%")
                print(f"  Mínimo:   {df['nubes'].min():.1f}%")
                print(f"  Máximo:   {df['nubes'].max():.1f}%")
                
                # Mejores imágenes
                mejores = df.nsmallest(5, 'nubes')[['fecha', 'nubes']]
                print("\n" + "-"*70)
                print("TOP 5 MEJORES IMÁGENES (menos nubes):")
                print("-"*70)
                for idx, row in mejores.iterrows():
                    print(f"  {row['fecha']} - {row['nubes']:.2f}% nubes")
            
            # Exportar CSV
            output_dir = Path('output')
            output_dir.mkdir(exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            csv_path = output_dir / f'busqueda_espacial_{nombre_area}_{timestamp}.csv'
            
            df.to_csv(csv_path, index=False)
            print(f"\n[OK] Resultados exportados a: {csv_path}")
        
    except Exception as e:
        print(f"[ERROR] Error en análisis: {e}")


def menu_interactivo():
    """Display interactive menu for spatial search."""
    print("\n" + "="*70)
    print("GEE IMAGE SEARCH")
    print("="*70)
    print("""
Options:
1. Quick analysis: Sentinel-2 coverage in sample area
2. Custom search: select collection, area, dates, and cloud filter
3. List available processing levels
4. Search collections by processing level
5. Exit
""")
    
    opcion = input("Selecciona opción (1-5): ").strip()
    return opcion


def main():
    """Función principal."""
    # Inicializar GEE
    try:
        project_id = get_project_id()
        ee.Initialize(project=project_id)
        print("[OK] Conexión exitosa a Earth Engine")
        print(f"[OK] Proyecto: {project_id}\n")
    except Exception as e:
        print(f"[ERROR] No se pudo conectar a GEE: {e}")
        sys.exit(1)
    
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
            analizar_cobertura_temporal(
                collection_id='COPERNICUS/S2_SR_HARMONIZED',
                geometry=geometry,
                nombre_area='Ñuñoa'
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
            print("\nOpciones:")
            print("  1. Ver lista completa de colecciones")
            print("  2. Buscar por categoría")
            print("  3. Buscar por nivel de procesamiento")
            print("  4. Ingresar ID directamente (si ya lo conoces)")
            
            busqueda_opcion = input("\nSelecciona opción (1-4): ").strip()
            
            collection_id = None
            col_info = None
            
            if busqueda_opcion == '1':
                # Mostrar lista paginada
                print("\n" + "="*70)
                print("LISTA DE COLECCIONES DISPONIBLES")
                print("="*70)
                
                # Crear lista enumerada para referencia
                cols_list = []
                for i, (idx, row) in enumerate(colecciones_validas.iterrows(), 1):
                    cols_list.append((i, idx, row))
                    
                    nombre = row['nombre'] if row['nombre'] else row['collection_id']
                    resolucion = row['resolucion_espacial'] if row['resolucion_espacial'] else 'No especificado'
                    periodo = row['periodo_temporal'] if row['periodo_temporal'] else 'No especificado'
                    nivel = row['nivel_procesamiento'] if row['nivel_procesamiento'] else 'No especificado'
                    
                    print(f"\n{i}. {nombre}")
                    print(f"   ID: {row['collection_id']}")
                    print(f"   Categoría: {row['categoria']}")
                    print(f"   Resolución: {resolucion}")
                    print(f"   Período: {periodo}")
                    print(f"   Nivel: {nivel}")
                    
                    if i % 5 == 0 and i < len(colecciones_validas):
                        continuar = input("\nMostrar más? (s/n): ").strip().lower()
                        if continuar != 's':
                            break
                
                num_seleccion = input("\nNúmero de colección a usar (o Enter para cancelar): ").strip()
                if num_seleccion.isdigit():
                    num_sel = int(num_seleccion)
                    # Buscar en la lista enumerada
                    for display_num, real_idx, row in cols_list:
                        if display_num == num_sel:
                            col_info = row
                            collection_id = col_info['collection_id']
                            break
            
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
                    for i in range(len(cols_cat)):
                        row = cols_cat.iloc[i]
                        nombre = row['nombre'] if row['nombre'] else row['collection_id']
                        periodo = row['periodo_temporal'] if row['periodo_temporal'] else 'No especificado'
                        resolucion = row['resolucion_espacial'] if row['resolucion_espacial'] else 'No especificado'
                        
                        print(f"\n  {i+1}. {nombre}")
                        print(f"     ID: {row['collection_id']}")
                        print(f"     Resolución: {resolucion}")
                        print(f"     Período: {periodo}")
                    
                    num_sel = input("\nNúmero de colección: ").strip()
                    if num_sel.isdigit():
                        idx_sel = int(num_sel) - 1
                        if 0 <= idx_sel < len(cols_cat):
                            col_info = cols_cat.iloc[idx_sel]
                            collection_id = col_info['collection_id']
            
            elif busqueda_opcion == '3':
                # Buscar por nivel
                niveles_df = catalogo.listar_niveles_disponibles()
                nivel = input("\nNivel de procesamiento (ej: L2A, TOA, L1C): ").strip()
                
                resultados = catalogo.buscar_por_nivel_procesamiento(nivel).reset_index(drop=True)
                if len(resultados) > 0:
                    print(f"\n[OK] {len(resultados)} colecciones con nivel '{nivel}':")
                    for i, row in resultados.iterrows():
                        nombre = row['nombre'] if row['nombre'] else row['collection_id']
                        periodo = row['periodo_temporal'] if row['periodo_temporal'] else 'No especificado'
                        
                        print(f"\n  {i+1}. {nombre}")
                        print(f"     ID: {row['collection_id']}")
                        print(f"     Categoría: {row['categoria']}")
                        print(f"     Período: {periodo}")
                    
                    num_sel = input("\nNúmero de colección: ").strip()
                    if num_sel.isdigit():
                        idx_sel = int(num_sel) - 1
                        if 0 <= idx_sel < len(resultados):
                            col_info = resultados.iloc[idx_sel]
                            collection_id = col_info['collection_id']
            
            elif busqueda_opcion == '4':
                # Ingresar ID directamente
                collection_id = input("\nID colección (ej: COPERNICUS/S2_SR_HARMONIZED): ").strip()
                if not collection_id:
                    print("[ERROR] Debe ingresar un ID de colección")
                    continue
                
                # Buscar info en catálogo
                matches = colecciones_validas[colecciones_validas['collection_id'] == collection_id]
                if len(matches) > 0:
                    col_info = matches.iloc[0]
            
            else:
                print("[ERROR] Opción inválida")
                continue
            
            if not collection_id:
                print("[ERROR] No se seleccionó ninguna colección")
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
            
            # 2. Seleccionar área GeoJSON
            geojson_path = input("\nRuta GeoJSON (ej: data/geojson/nunoa.geojson): ").strip()
            
            if not geojson_path:
                print("[ERROR] Debe ingresar una ruta de GeoJSON")
                continue
            
            if not Path(geojson_path).exists():
                print(f"[ERROR] No existe: {geojson_path}")
                continue
            
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
                geometry, _ = cargar_geojson(Path(geojson_path))
                nombre_area = Path(geojson_path).stem
                
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
