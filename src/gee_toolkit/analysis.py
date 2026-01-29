"""
Módulo de análisis y búsqueda de imágenes en Earth Engine.
"""

import ee
import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from .colecciones_config import soporta_filtro_nubes
from .api_utils import retry_api_call

@retry_api_call()
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
    Optimizado para evitar operaciones costosas (size(), geometry() global).
    """
    coleccion = ee.ImageCollection(collection_id)
    
    # [OPTIMIZACIÓN] Eliminada la validación `coleccion.geometry().intersects()`.
    # Calcular la geometría de una colección entera es muy costoso y causa freezes.
    # Confiamos en filterBounds; si no hay intersección, devolverá vacío rápido.

    coleccion = coleccion \
        .filterBounds(geometry) \
        .filterDate(fecha_inicio, fecha_fin)
    
    # Verificar filtros de nubes de manera eficiente
    soporta, propiedad = soporta_filtro_nubes(collection_id)
    
    if max_nubes < 100:
        if soporta is True:
            coleccion = coleccion.filter(ee.Filter.lt(propiedad, max_nubes))
            print(f"[INFO] Filtro de nubes aplicado: {propiedad} < {max_nubes}%")
        elif soporta is False:
            print(f"[INFO] Sin filtro de nubes (tipo de colección no óptico)")
        else:
            # Detección dinámica optimizada: NO contar toda la colección
            print(f"[INFO] Verificando propiedades de nubes...")
            try:
                # Solo traemos 1 imagen para inspeccionar metadata
                sample = coleccion.limit(1).first()
                # getInfo() aquí es rápido porque es solo 1 elemento
                info = sample.getInfo()
                
                if info:
                    props = info.get('properties', {})
                    if 'CLOUDY_PIXEL_PERCENTAGE' in props:
                        coleccion = coleccion.filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', max_nubes))
                        print(f"[INFO] Filtro detectado y aplicado: CLOUDY_PIXEL_PERCENTAGE")
                    elif 'CLOUD_COVER' in props:
                        coleccion = coleccion.filter(ee.Filter.lt('CLOUD_COVER', max_nubes))
                        print(f"[INFO] Filtro detectado y aplicado: CLOUD_COVER")
            except Exception:
                # Si falla (ej: colección vacía), simplemente no aplicamos filtro extra
                pass
    
    # Aplicar límite estricto ANTES de cualquier operación de lista
    coleccion = coleccion.limit(limite)
    
    try:
        # toList() ahora opera sobre un máximo de 'limite' elementos
        img_list = coleccion.toList(limite)
        
        # Obtenemos el tamaño de la lista ya recortada (rápido)
        size = img_list.size().getInfo()
        
        if size == 0:
            return []
        
        imagenes = []
        # Traer toda la info de una vez es más eficiente que iterar getInfo()
        # getInfo() sobre la lista completa
        lista_info = img_list.getInfo()
        
        for info in lista_info:
            props = info.get('properties', {})
            fecha_ms = props.get('system:time_start')
            fecha = None
            if fecha_ms:
                fecha = datetime.fromtimestamp(fecha_ms / 1000).strftime('%Y-%m-%d')
            
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
    max_nubes: float = 100,
    output_dir: Optional[Path] = None
):
    """
    Analiza la cobertura temporal de una colección en un área e imprime reporte.
    
    Args:
        collection_id: ID de la colección
        geometry: Geometría del área
        nombre_area: Nombre del área para display
        fecha_inicio: Fecha inicio (YYYY-MM-DD)
        fecha_fin: Fecha fin (YYYY-MM-DD)
        max_nubes: % máximo de nubes
        output_dir: Directorio para guardar el CSV (opcional, default 'output')
    """
    print("\n" + "="*70)
    print(f"ANÁLISIS DE COBERTURA TEMPORAL: {nombre_area.upper()}")
    print("="*70)
    
    # Calcular área (protegido contra errores geométricos)
    try:
        # Usamos bestEffort=True y maxError para evitar fallos en geometrías complejas
        area_m2 = geometry.area(maxError=1000).getInfo()
        area_ha = area_m2 / 10000
        print(f"\n[INFO] Área aprox: {area_ha:.2f} ha ({area_m2/1000000:.2f} km²)")
    except Exception:
        print(f"\n[INFO] Área: (Cálculo omitido por complejidad geométrica)")

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
            if output_dir is None:
                output_dir = Path('output')
            
            output_dir.mkdir(exist_ok=True, parents=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            csv_path = output_dir / f'busqueda_espacial_{nombre_area}_{timestamp}.csv'
            
            df.to_csv(csv_path, index=False)
            print(f"\n[OK] Resultados exportados a: {csv_path}")
        
    except Exception as e:
        print(f"[ERROR] Error en análisis: {e}")
