#!/usr/bin/env python3
"""
Catálogo Completo de Google Earth Engine
=========================================

Módulo central para la gestión, descubrimiento y mantenimiento de colecciones GEE.
"""

import ee
import pandas as pd
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from copy import deepcopy
from .config import get_project_id as get_project_id_from_config
from .api_utils import retry_api_call, safe_ee_execute

# Configurar logging
logger = logging.getLogger(__name__)


class CatalogoGEE:
    """
    Gestor de catálogo de colecciones GEE con capacidades de descubrimiento y mantenimiento.
    """
    
    def __init__(self, project_id: Optional[str] = None):
        if not project_id:
            project_id = get_project_id_from_config()
        
        self.project_id: Optional[str] = project_id
        self.catalog_path: Path = Path(__file__).parent.parent.parent / 'config' / 'colecciones_gee.json'
        
        # Cargar catálogo
        self.colecciones: Dict[str, Any] = self._cargar_catalogo()
    
    def _cargar_catalogo(self) -> Dict[str, Any]:
        try:
            if not self.catalog_path.exists():
                return self._definir_catalogo_defecto()
                
            with open(self.catalog_path, 'r', encoding='utf-8') as f:
                catalogo = json.load(f)
            
            # Validar metadata
            if '_metadata' not in catalogo:
                catalogo['_metadata'] = {
                    'version': '2.2.0',
                    'last_updated': datetime.now().isoformat(),
                    'auto_update_enabled': True,
                    'cache_duration_days': 30
                }
                self._guardar_catalogo(catalogo)
            
            return catalogo
        except Exception as e:
            logger.error(f"Error cargando catálogo: {e}")
            return self._definir_catalogo_defecto()

    def _guardar_catalogo(self, catalogo: Optional[Dict[str, Any]] = None) -> None:
        if catalogo is None:
            catalogo = self.colecciones
            
        try:
            self.catalog_path.parent.mkdir(exist_ok=True)
            with open(self.catalog_path, 'w', encoding='utf-8') as f:
                json.dump(catalogo, f, indent=2, ensure_ascii=False)
            logger.info(f"Catálogo guardado en {self.catalog_path}")
        except Exception as e:
            logger.error(f"Error guardando catálogo: {e}")

    def _definir_catalogo_defecto(self) -> Dict[str, Any]:
        return {
            '_metadata': {'version': '1.0.0', 'last_updated': datetime.now().isoformat()},
            'opticas_alta_res': {
                'nombre': 'Imágenes Ópticas de Resolución Media',
                'colecciones': {}
            }
        }

    def _detectar_nivel_procesamiento(self, collection_id: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Infiere el nivel de procesamiento a partir de metadata oficial o del ID.
        """
        cid = collection_id.upper()
        props = {}
        if metadata and 'properties' in metadata:
            props = {k.upper(): str(v).upper() for k, v in metadata['properties'].items()}
        
        # 1. Intentar extraer de propiedades oficiales de GEE
        nivel_oficial = props.get('SYSTEM:PROCESSING_LEVEL') or props.get('PROCESSING_LEVEL') or props.get('DATA_TYPE')
        if nivel_oficial:
            # Normalización básica
            if 'L1C' in nivel_oficial: return 'L1C'
            if 'L2A' in nivel_oficial: return 'L2A'
            if 'SURFACE REFLECTANCE' in nivel_oficial: return 'L2 (SR)'
            return nivel_oficial.title()

        # 2. Heurística por ID (Fallback)
        # Sentinel
        if 'S2_SR' in cid or 'L2A' in cid: return 'L2A'
        if 'S2_HARMONIZED' in cid and 'SR' not in cid: return 'L1C'
        if 'COPERNICUS/S2' in cid and 'SR' not in cid: return 'L1C'
        if 'S1_GRD' in cid: return 'L1_GRD'
        if 'S5P' in cid: return 'L2 (Atmosférico)'
        
        # Landsat
        if 'C02/T1_L2' in cid or 'C02/T2_L2' in cid: return 'L2'
        if 'C02/T1_TOA' in cid or 'C02/T2_TOA' in cid: return 'TOA'
        if 'C02/T1_RT' in cid: return 'RAW'
        if 'C02/T1' in cid or 'C02/T2' in cid: return 'L1 (DN)'
        
        # MODIS
        if any(x in cid for x in ['MOD09', 'MYD09', 'MCD09']):
            if 'GA' in cid: return 'L2G'
            return 'L3' if 'A1' in cid else 'L2'
            
        return 'No especificado'

    def _detectar_categoria(self, collection_id: str, metadata: Dict[str, Any]) -> str:
        cid = collection_id.upper()
        nombre = metadata.get('nombre', '').upper()
        desc = str(metadata.get('descripcion', '')).upper()
        texto = f"{cid} {nombre} {desc}"

        if any(x in cid for x in ['S5P', 'TROPOMI']) or any(x in texto for x in ['NO2', 'CO', 'O3', 'SO2', 'CH4', 'ATMOSPHERE']):
            return 'atmosfera'
        if any(x in cid for x in ['HYCOM', 'GSW', 'OCEANDATA']) or any(x in texto for x in ['WATER', 'OCEAN', 'SST', 'HYDRO']):
            return 'agua'
        if any(x in cid for x in ['GEDI', 'HANSEN', 'GLAD']) or any(x in texto for x in ['FOREST', 'BIOMASS', 'CANOPY', 'TREE']):
            return 'lidar_biomasa'
        if any(x in cid for x in ['FAO', 'WAPOR']) or any(x in texto for x in ['CROP', 'AGRICULTURE', 'YIELD']):
            return 'agricultura'
        if any(x in cid for x in ['ISDASOIL', 'OPENLANDMAP']) or 'SOIL' in texto:
            return 'suelos'
        if any(x in cid for x in ['FIRMS', 'FIRE', 'MCD64']) or 'BURNED' in texto:
            return 'fuego'
        if 'SNOW' in texto or 'ICE' in texto or 'CRYOSPHERE' in texto:
            return 'criosphere'
        if any(x in cid for x in ['WORLDCOVER', 'CORINE', 'NLCD', 'DYNAMICWORLD']):
            return 'landcover'
        if any(x in cid for x in ['DEM', 'SRTM', 'ELEVATION']):
            return 'elevacion'
        if 'SAR' in texto or 'SENTINEL-1' in cid:
            return 'sar'
        if any(x in cid for x in ['ERA5', 'CHIRPS', 'GPM', 'CLIMATE']):
            return 'clima'
        if any(x in cid for x in ['MOD13', 'NDVI', 'EVI']):
            return 'vegetacion'
        if any(x in cid for x in ['WORLDPOP', 'GPW', 'URBAN']):
            return 'poblacion'
        
        return 'clima'

    @retry_api_call(raise_on_failure=False)
    def buscar_coleccion_api(self, collection_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene metadata enriquecida de la API de Earth Engine.
        Usa ee.data.getAsset para metadata ligera y evita computaciones pesadas.
        """
        try:
            # 1. Obtener metadata ligera vía REST API (Asset ID)
            # Esto evita 'accumulating over 5000 elements' al no instanciar ImageCollection pesado
            try:
                asset_info = ee.data.getAsset(collection_id)
            except ee.EEException:
                # Si falla getAsset (ej: no existe), retornamos None
                return None
                
            if not asset_info or asset_info.get('type') != 'IMAGE_COLLECTION':
                return None
            
            props = asset_info.get('properties', {})
            title = props.get('title', asset_info.get('id', '').split('/')[-1])
            
            # FILTRO DE CALIDAD: Detectar Assets Deprecados
            is_deprecated = props.get('deprecated', False)
            if str(is_deprecated).lower() == 'true' or '[DEPRECATED]' in str(title).upper():
                logger.warning(f"Asset deprecado ignorado: {collection_id}")
                return None
            
            # 2. Intentar obtener bandas y resolución de una imagen RECIENTE
            # CONTINGENCIA: Saltamos inspección de imágenes para colecciones masivas conocidas
            # que causan timeouts incluso con filtros (Landsat, Sentinel).
            # Confiamos solo en la metadata del asset para estas.
            es_masiva = any(x in collection_id for x in ['LANDSAT/', 'COPERNICUS/', 'MODIS/'])
            
            first_img = None
            res = "No especificado"
            bandas = []
            
            if not es_masiva:
                try:
                    col = ee.ImageCollection(collection_id)
                    # Estrategia: Buscar en Enero 2024 (30 días)
                    filtered = col.filterDate('2024-01-01', '2024-01-31').limit(1)
                    
                    if filtered.size().getInfo() > 0:
                        first_img_info = filtered.first().getInfo()
                        if first_img_info and 'bands' in first_img_info:
                            bandas = [b['id'] for b in first_img_info['bands']]
                except Exception:
                    pass
            else:
                # Para colecciones masivas, intentamos extraer bandas de metadata si existe en properties
                pass

            # Extraer periodo temporal de propiedades (ya vienen en asset_info)
            periodo = "Consultar en GEE"
            time_start = asset_info.get('startTime') # Formato: "2013-03-18T15:59:36Z"
            time_end = asset_info.get('endTime')
            
            if time_start:
                try:
                    d1 = time_start[:7] # YYYY-MM
                    d2 = time_end[:7] if time_end else "Presente"
                    periodo = f"{d1} a {d2}"
                except: pass
            elif 'date_range' in props:
                periodo = str(props['date_range'])

            return {
                'nombre': title,
                'collection_id': collection_id,
                'properties': props,
                'bandas': bandas,
                'resolucion': res,
                'periodo': periodo,
                'last_verified': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error procesando {collection_id}: {e}")
            return None

    def agregar_coleccion_al_catalogo(self, collection_id: str, categoria: Optional[str] = None) -> bool:
        metadata = self.buscar_coleccion_api(collection_id)
        if not metadata: 
            print(f"  [ERROR] No se pudo acceder al asset: {collection_id}")
            return False
        
        if not categoria:
            categoria = self._detectar_categoria(collection_id, metadata)
        
        if categoria not in self.colecciones:
            self.colecciones[categoria] = {'nombre': categoria.replace('_', ' ').title(), 'colecciones': {}}
            
        self.colecciones[categoria]['colecciones'][collection_id] = {
            'nombre': metadata['nombre'],
            'bandas_principales': metadata['bandas'][:6],
            'resolucion': metadata['resolucion'],
            'temporal': metadata['periodo'],
            'last_verified': metadata['last_verified'],
            'nivel': self._detectar_nivel_procesamiento(collection_id, metadata)
        }
        self._guardar_catalogo()
        return True

    def verificar_y_actualizar(self, collection_id: str) -> bool:
        """
        Consulta la API de GEE y actualiza toda la metadata del asset en el catálogo.
        """
        metadata = self.buscar_coleccion_api(collection_id)
        if not metadata: return False
        
        for cat in self.colecciones.values():
            if isinstance(cat, dict) and collection_id in cat.get('colecciones', {}):
                cat['colecciones'][collection_id].update({
                    'nombre': metadata['nombre'],
                    'bandas_principales': metadata['bandas'][:6],
                    'resolucion': metadata['resolucion'],
                    'temporal': metadata['periodo'],
                    'last_verified': metadata['last_verified'],
                    'nivel': self._detectar_nivel_procesamiento(collection_id, metadata)
                })
                self._guardar_catalogo()
                return True
        return False

    def revalidar_expiradas(self, dias: int = 30, limite: Optional[int] = None):
        print(f"\n[INFO] Revalidando colecciones con más de {dias} días de antigüedad...")
        expiradas = self._obtener_ids_expirados(dias)
        if not expiradas:
            print("  [OK] Todas las colecciones están al día.")
            return

        a_validar = expiradas[:limite] if limite else expiradas
        validas, invalidas = 0, 0

        for col_id in a_validar:
            print(f"  Verificando {col_id}...", end=" ")
            if self.verificar_y_actualizar(col_id):
                validas += 1
                print("[OK]")
            else:
                invalidas += 1
                print("[FALLÓ]")
        
        print(f"\n[RESUMEN] Válidas: {validas}, Fallidas: {invalidas}")

    def _obtener_ids_expirados(self, dias: int) -> List[str]:
        umbral = datetime.now() - timedelta(days=dias)
        expirados = []
        for cat in self.colecciones.values():
            if not isinstance(cat, dict) or 'colecciones' not in cat: continue
            for cid, data in cat['colecciones'].items():
                last = data.get('last_verified')
                if not last or datetime.fromisoformat(last) < umbral:
                    expirados.append(cid)
        return expirados

    def verificar_y_actualizar(self, collection_id: str) -> bool:
        """
        Consulta la API de GEE y actualiza toda la metadata del asset en el catálogo.
        """
        metadata = self.buscar_coleccion_api(collection_id)
        if not metadata: return False
        
        for cat in self.colecciones.values():
            if isinstance(cat, dict) and collection_id in cat.get('colecciones', {}):
                cat['colecciones'][collection_id].update({
                    'nombre': metadata['nombre'],
                    'bandas_principales': metadata['bandas'][:6],
                    'resolucion': metadata['resolucion'],
                    'temporal': metadata['periodo'],
                    'last_verified': metadata['last_verified'],
                    'nivel': self._detectar_nivel_procesamiento(collection_id, metadata)
                })
                self._guardar_catalogo()
                return True
        return False

    def limpiar_invalidas(self, silencioso: bool = False):
        """
        Escanea el catálogo y elimina colecciones que ya no son accesibles en GEE o están deprecadas.
        """
        print("\n[INFO] Iniciando limpieza de colecciones inaccesibles o deprecadas...")
        invalidas = []
        for cid, cat in self._iter_colecciones():
            try:
                # Usar getAsset es mucho más rápido y seguro que instanciar colecciones
                info = ee.data.getAsset(cid)
                
                # Check adicional: Deprecación
                props = info.get('properties', {})
                is_deprecated = props.get('deprecated', False)
                title = props.get('title', '').upper()
                
                if str(is_deprecated).lower() == 'true' or '[DEPRECATED]' in title:
                    print(f"  [DEPRECADO] {cid}")
                    invalidas.append((cat, cid))
                    
            except Exception as e:
                msg = str(e).lower()
                if 'not found' in msg or 'permission' in msg or 'access' in msg or 'forbidden' in msg:
                    print(f"  [INACCESIBLE] {cid}")
                    invalidas.append((cat, cid))
        
        if not invalidas:
            print("  [OK] No se encontraron colecciones inválidas.")
            return

        print(f"  [!] Se encontraron {len(invalidas)} colecciones inaccesibles, prohibidas o deprecadas.")
        
        if not silencioso:
            for cat, cid in invalidas:
                print(f"    - {cid}")
            
            confirm = input("\n¿Eliminar estas colecciones permanentemente? (si/no): ").strip().lower()
            if confirm != 'si':
                print("  [INFO] Operación cancelada.")
                return

        # Proceder con la eliminación
        for cat, cid in invalidas:
            del self.colecciones[cat]['colecciones'][cid]
        
        self._guardar_catalogo()
        print(f"  [OK] Catálogo limpio. Se eliminaron {len(invalidas)} colecciones.")

    def recategorizar(self):
        print("\n[INFO] Re-evaluando categorías segón la nueva lógica...")
        movimientos = 0
        original = deepcopy(self.colecciones)
        
        for cat_id, cat_info in original.items():
            if cat_id.startswith('_'): continue
            for cid, data in cat_info.get('colecciones', {}).items():
                nueva_cat = self._detectar_categoria(cid, data)
                if nueva_cat != cat_id:
                    print(f"  [MOVE] {cid}: {cat_id} -> {nueva_cat}")
                    if nueva_cat not in self.colecciones:
                        self.colecciones[nueva_cat] = {'nombre': nueva_cat.replace('_', ' ').title(), 'colecciones': {}}
                    self.colecciones[nueva_cat]['colecciones'][cid] = data
                    del self.colecciones[cat_id]['colecciones'][cid]
                    movimientos += 1
        
        if movimientos > 0:
            self._guardar_catalogo()
            print(f"\n[OK] Se movieron {movimientos} colecciones.")
        else:
            print("  [OK] Todas las categorías son correctas.")

    def agregar_lote(self, file_path: str):
        path = Path(file_path)
        if not path.exists():
            print(f"[ERROR] No existe el archivo {file_path}")
            return
            
        with open(path, 'r') as f:
            ids = [line.strip() for line in f if line.strip() and not line.startswith('#')]
        
        print(f"[INFO] Procesando lote de {len(ids)} colecciones...")
        exitos = 0
        for cid in ids:
            if self.agregar_coleccion_al_catalogo(cid):
                exitos += 1
                print(f"  [OK] Agregada: {cid}")
            else:
                print(f"  [ERROR] No encontrada: {cid}")
        print(f"\n[RESUMEN] Agregadas con éxito: {exitos}/{len(ids)}")

    def descubrir_colecciones(self, providers: Optional[List[str]] = None):
        if not providers:
            providers = [
                "COPERNICUS", "LANDSAT", "MODIS", "NASA", "ECMWF", "USGS", "JAXA", "ESA", "NOAA", "JRC",
                "LARSE", "FAO", "WRI", "GOOGLE", "GRIDMET", "WWF", "UMD", "Tsinghua", "COPERNICUS/Landcover"
            ]
        
        base_path = "projects/earthengine-public/assets"
        total_nuevas = 0
        ids_existentes = {cid for cid, _ in self._iter_colecciones()}

        def _crawl(folder: str):
            nonlocal total_nuevas
            try:
                res = ee.data.listAssets({'parent': folder})
                if not res: return
                for asset in res.get('assets', []):
                    aid, atype = asset.get('id'), asset.get('type')
                    if not aid or not atype: continue
                    legacy_id = aid.replace(f"{base_path}/", "")
                    
                    if atype == 'IMAGE_COLLECTION' and legacy_id not in ids_existentes:
                        print(f"[NUEVO] {legacy_id}")
                        if self.agregar_coleccion_al_catalogo(legacy_id):
                            ids_existentes.add(legacy_id)
                            total_nuevas += 1
                    elif atype == 'FOLDER':
                        _crawl(aid)
            except Exception:
                pass

        for p in providers:
            print(f"Explorando {p}...")
            _crawl(f"{base_path}/{p}")
        print(f"\n[FIN] Descubiertas {total_nuevas} nuevas colecciones.")

    def _iter_colecciones(self):
        for cat_id, cat_info in self.colecciones.items():
            if cat_id.startswith('_'): continue
            for cid in cat_info.get('colecciones', {}).keys():
                yield cid, cat_id

    def generar_reporte(self):
        print("\n" + "="*50)
        print("REPORTE DE ESTADO DEL CATÁLOGO")
        print("="*50)
        total = 0
        for cat_id, cat_info in sorted(self.colecciones.items()):
            if cat_id.startswith('_'): continue
            count = len(cat_info.get('colecciones', {}))
            total += count
            print(f" • {cat_info['nombre']}: {count} colecciones")
        print(f"\nTOTAL: {total} colecciones")
        print("="*50)

    def generar_inventario_completo(self, exportar_csv: bool = True) -> pd.DataFrame:
        """
        Genera un DataFrame con todas las colecciones del catálogo. 
        
        Args:
            exportar_csv: Si True, exporta a CSV
            
        Returns:
            DataFrame con el inventario completo
        """
        print("\n" + "="*80)
        print("GENERANDO INVENTARIO COMPLETO DE COLECCIONES GEE")
        print("="*80)
        
        registros = []
        
        for categoria_id, categoria_info in self.colecciones.items():
            if categoria_id.startswith('_'): continue
                
            categoria_nombre = categoria_info['nombre']
            n_colecciones = len(categoria_info.get('colecciones', {}))
            
            # print(f"\n{categoria_nombre}: {n_colecciones} colecciones") # Optional logging
            
            for col_id, col_info in categoria_info.get('colecciones', {}).items():
                # Procesar colección para el DataFrame
                registro = {
                    'categoria': categoria_nombre,
                    'categoria_id': categoria_id,
                    'collection_id': col_id,
                    'nombre': col_info.get('nombre', ''),
                    'resolucion_espacial': col_info.get('resolucion', ''),
                    'resolucion_temporal': col_info.get('frecuencia', col_info.get('temporal', '')),
                    'periodo_temporal': col_info.get('temporal', ''),
                    'nivel_procesamiento': col_info.get('nivel', ''), # Asegurar que este campo exista o se infiera
                    'qa_disponible': col_info.get('qa', False),
                    'bandas_principales': ', '.join(col_info.get('bandas_principales', [])),
                    'last_verified': col_info.get('last_verified', '')
                }
                
                # Intentar inferir nivel si no existe en el JSON
                if not registro['nivel_procesamiento']:
                    registro['nivel_procesamiento'] = self._detectar_nivel_procesamiento(col_id)
                
                registros.append(registro)
        
        df = pd.DataFrame(registros)
        
        if exportar_csv and not df.empty:
            self._exportar_csv(df)
        
        return df

    def listar_niveles_disponibles(self) -> pd.DataFrame:
        """
        Lista todos los niveles de procesamiento disponibles en el catálogo con detalles.
        
        Returns:
            DataFrame con niveles ónicos, conteo y ejemplos.
        """
        df = self.generar_inventario_completo(exportar_csv=False)
        
        if df.empty:
            print("[WARN] El catálogo está vacío.")
            return pd.DataFrame()

        # Normalizar niveles vacíos
        df['nivel_procesamiento'] = df['nivel_procesamiento'].fillna('No especificado')
        df.loc[df['nivel_procesamiento'] == '', 'nivel_procesamiento'] = 'No especificado'

        # Agrupar y contar
        niveles = df.groupby('nivel_procesamiento').agg(
            n_colecciones=('collection_id', 'count'),
            ejemplos=('collection_id', lambda x: list(x)[:3])  # Tomar 3 ejemplos
        ).sort_values('n_colecciones', ascending=False)
        
        print("\n" + "="*90)
        print(f"{ 'NIVEL DE PROCESAMIENTO':<40} | {'CANTIDAD':<8} | {'SOPORTE NUBES (Estimado)':<20}")
        print("-" * 90)
        
        for nivel, row in niveles.iterrows():
            count = row['n_colecciones']
            
            # Estimación de soporte de nubes basado en convenciones
            soporte_nubes = "Probable" if any(x in str(nivel).upper() for x in ['SR', 'TOA', 'L2', 'L1C']) else "No/Variable"
            if 'RAW' in str(nivel).upper(): soporte_nubes = "No"
            
            print(f"{str(nivel):<40} | {count:<8} | {soporte_nubes:<20}")
            # Mostrar ejemplos indentados
            print(f"   Ejemplos: {', '.join(row['ejemplos'])}")
            print("-" * 90)
        
        print(f"\n[OK] Total: {len(niveles)} niveles diferentes en {len(df)} colecciones")
        
        return niveles.reset_index()

    def buscar_por_nivel_procesamiento(self, nivel: str) -> pd.DataFrame:
        """
        Busca colecciones por nivel de procesamiento.
        
        Args:
            nivel: Nivel a buscar (L1C, L2A, L2, TOA, etc.)
            
        Returns:
            DataFrame con colecciones que coinciden
        """
        df = self.generar_inventario_completo(exportar_csv=False)
        
        if df.empty:
            return pd.DataFrame()

        # Búsqueda flexible (case-insensitive)
        mask = df['nivel_procesamiento'].str.contains(nivel, case=False, na=False)
        resultados = df[mask].copy()
        
        print(f"\n[OK] Encontradas {len(resultados)} colecciones con nivel '{nivel}'")
        
        if len(resultados) > 0:
            print("\nColecciones encontradas:")
            for idx, row in resultados.iterrows():
                print(f"  • {row['collection_id']}")
                print(f"    Nivel: {row['nivel_procesamiento']}")
                print(f"    Categoría: {row['categoria']}")
        
        return resultados