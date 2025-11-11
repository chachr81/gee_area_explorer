#!/usr/bin/env python3
"""
Catálogo Completo de Google Earth Engine
=========================================

Script para explorar TODAS las colecciones disponibles en GEE
y generar un inventario exhaustivo para planificación de productos.

Genera:
- Tabla completa de colecciones con metadatos clave
- Clasificación por tipo de dato
- Nivel de procesamiento
- Resoluciones espaciales y temporales
- Exportación a CSV para análisis posterior

Autor: Data Scientist
Fecha: 2025-11-11
"""

import ee
import pandas as pd
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path
from .config import get_project_id as get_project_id_from_config

# Configurar logging
logger = logging.getLogger(__name__)


class CatalogoGEE:
    """
    Generador de catálogo exhaustivo de colecciones GEE.
    
    Attributes:
        project_id: ID del proyecto de Google Cloud
        colecciones: Diccionario con el catálogo completo de colecciones
    """
    
    def __init__(self, project_id: Optional[str] = None):
        """
        Inicializa el generador de catálogo.
        
        Args:
            project_id: ID del proyecto de Google Cloud (opcional)
            
        Raises:
            ee.EEException: Error de autenticación o inicialización de GEE
            FileNotFoundError: Si no se encuentra el archivo de catálogo
        """
        if not project_id:
            project_id = get_project_id_from_config()
        
        self.project_id: Optional[str] = project_id
        self.catalog_path: Optional[Path] = None  # Se define en _cargar_catalogo
        logger.info(f"Inicializando CatalogoGEE con proyecto: {self.project_id}")
        self._inicializar_gee()
        
        # Cargar catálogo desde archivo JSON externo
        self.colecciones: Dict[str, Any] = self._cargar_catalogo()
    
    def _inicializar_gee(self) -> None:
        """
        Inicializa conexión con GEE.
        
        Raises:
            ee.EEException: Error de autenticación o configuración de GEE
        """
        try:
            ee.Initialize(project=self.project_id)
            print("[OK] Conexión exitosa con Google Earth Engine")
            if self.project_id:
                print(f"[INFO] Proyecto: {self.project_id}")
        except ee.EEException as gee_error:
            error_msg = str(gee_error)
            print(f"[ERROR] Error al inicializar GEE: {error_msg}")
            
            if "authentication" in error_msg.lower():
                print("[INFO] Solución: Ejecuta 'earthengine authenticate'")
            elif "project" in error_msg.lower():
                print("[INFO] Solución: Configura la variable GEE_PROJECT o pasa project_id")
            
            raise
    
    def _cargar_catalogo(self) -> Dict[str, Any]:
        """
        Carga el catálogo de colecciones desde archivo JSON externo.
        
        Returns:
            Diccionario con el catálogo completo
            
        Raises:
            FileNotFoundError: Si no se encuentra colecciones_gee.json
            json.JSONDecodeError: Si el JSON tiene errores de sintaxis
        """
        # Buscar JSON en config/ relativo al proyecto
        self.catalog_path = Path(__file__).parent.parent.parent / 'config' / 'colecciones_gee.json'
        
        try:
            with open(self.catalog_path, 'r', encoding='utf-8') as f:
                catalogo = json.load(f)
            
            # Validar estructura de metadata
            if '_metadata' not in catalogo:
                catalogo['_metadata'] = {
                    'version': '2.0.0',
                    'last_updated': datetime.now().isoformat(),
                    'auto_update_enabled': True,
                    'cache_duration_days': 30
                }
                self._guardar_catalogo(catalogo)
            
            categorias = len([k for k in catalogo.keys() if not k.startswith('_')])
            print(f"[OK] Catálogo cargado: {categorias} categorías")
            return catalogo
        except FileNotFoundError:
            print(f"[ERROR] No se encontró el archivo: {self.catalog_path}")
            print("[INFO] Generando catálogo por defecto...")
            return self._definir_catalogo_completo()
        except json.JSONDecodeError as json_error:
            print(f"[ERROR] Error al parsear JSON: {json_error}")
            print("[INFO] Usando catálogo por defecto...")
            return self._definir_catalogo_completo()

    
    def _definir_catalogo_completo(self) -> Dict[str, Any]:
        """
        Define el catálogo completo de colecciones GEE (fallback si no hay JSON).
        
        NOTA: Este método es un fallback. El catálogo principal está en colecciones_gee.json
        
        Returns:
            Diccionario básico con algunas colecciones de ejemplo
        """
        print("[WARN] Usando catálogo simplificado (fallback)")
        return {
            'opticas_alta_res': {
                'nombre': 'Imágenes Ópticas de Alta Resolución',
                'colecciones': {
                    'COPERNICUS/S2_SR_HARMONIZED': {
                        'nombre': 'Sentinel-2 MSI L2A (Harmonized)',
                        'resolucion': '10m',
                        'temporal': '2017-presente',
                        'nivel': 'L2A (Surface Reflectance)',
                        'qa': True
                    }
                }
            }
        }
    
    def _guardar_catalogo(self, catalogo: Dict[str, Any]) -> None:
        """
        Guarda el catálogo actualizado en el archivo JSON.
        
        Args:
            catalogo: Diccionario completo del catálogo a guardar
        """
        if not self.catalog_path:
            logger.error("No se ha definido catalog_path")
            return
            
        try:
            with open(self.catalog_path, 'w', encoding='utf-8') as f:
                json.dump(catalogo, f, indent=2, ensure_ascii=False)
            logger.info(f"Catálogo guardado exitosamente en {self.catalog_path}")
        except Exception as e:
            logger.error(f"Error al guardar catálogo: {e}")
    
    def buscar_coleccion_api(self, collection_id: str) -> Optional[Dict[str, Any]]:
        """
        Busca información de una colección consultando el API de GEE.
        
        Args:
            collection_id: ID de la colección a buscar (ej: 'COPERNICUS/S2_SR_HARMONIZED')
            
        Returns:
            Diccionario con metadata de la colección o None si no existe
        """
        try:
            # Intentar obtener info de la colección
            collection = ee.ImageCollection(collection_id)
            info = collection.limit(1).first().getInfo()
            
            metadata = {
                'nombre': collection_id.split('/')[-1],
                'collection_id': collection_id,
                'tipo': info.get('type', 'ImageCollection'),
                'bandas': [band['id'] for band in info.get('bands', [])],
                'propiedades': list(info.get('properties', {}).keys()),
                'last_verified': datetime.now().isoformat(),
                'source': 'api'
            }
            
            logger.info(f"Colección {collection_id} encontrada en API")
            return metadata
            
        except ee.EEException as e:
            logger.warning(f"Colección {collection_id} no encontrada en API: {e}")
            return None
    
    def _detectar_categoria(self, collection_id: str, metadata: Dict[str, Any]) -> str:
        """
        Detecta automáticamente la categoría correcta para una colección.
        
        Args:
            collection_id: ID de la colección
            metadata: Metadata de la colección
            
        Returns:
            Clave de categoría detectada
        """
        col_id_upper = collection_id.upper()
        nombre = metadata.get('nombre', '').upper()
        
        # Reglas de clasificación por sensor/producto
        if 'S5P' in col_id_upper or 'TROPOMI' in nombre:
            return 'atmosfera'
        elif 'S3/OLCI' in col_id_upper or 'OCEANDATA' in col_id_upper or 'HYCOM' in col_id_upper or 'OISST' in col_id_upper:
            return 'agua'
        elif 'GSW' in col_id_upper or 'WATER' in nombre:
            return 'agua'
        elif 'GDDP-CMIP6' in col_id_upper or 'ERA5' in col_id_upper or 'DAYMET' in col_id_upper or 'GRIDMET' in col_id_upper or 'FLDAS' in col_id_upper:
            return 'clima'
        elif 'MOD17' in col_id_upper or 'MYD17' in col_id_upper or 'MOD16' in col_id_upper or 'MOD13' in col_id_upper or 'MYD13' in col_id_upper or 'MCD15' in col_id_upper:
            return 'vegetacion'
        elif 'MOD44B' in col_id_upper:  # Vegetation Continuous Fields
            return 'vegetacion'
        elif 'MCD43' in col_id_upper or 'MOD09' in col_id_upper or 'MYD11' in col_id_upper:
            return 'opticas_alta_res'
        elif 'LANDSAT' in col_id_upper and 'LC08' in col_id_upper:
            return 'opticas_alta_res'
        elif 'MCD12' in col_id_upper or 'WORLDCOVER' in col_id_upper or 'DYNAMICWORLD' in col_id_upper or 'CORINE' in col_id_upper or 'LANDCOVER' in col_id_upper:
            return 'landcover'
        elif 'MCD64' in col_id_upper or 'FIRMS' in col_id_upper or 'MOD14' in col_id_upper or 'FIRECCI' in col_id_upper:
            return 'fuego'
        elif 'MOD10' in col_id_upper or 'MYD10' in col_id_upper or 'SNOW' in nombre or 'ICE' in nombre:
            return 'criosphere'
        elif 'GRACE' in col_id_upper:
            return 'elevacion'
        elif 'ALOS/PALSAR' in col_id_upper or 'SAR' in nombre:
            return 'sar'
        elif 'MCD19' in col_id_upper or 'AEROSOL' in nombre:
            return 'atmosfera'
        elif 'GPW' in col_id_upper or 'POPULATION' in nombre:
            return 'poblacion'
        
        # Por defecto: ópticas si es imagen, clima si es meteorología
        if 'MODIS' in col_id_upper or 'SENTINEL' in col_id_upper or 'LANDSAT' in col_id_upper:
            return 'opticas_alta_res'
        
        return 'clima'  # Categoría por defecto
    
    def agregar_coleccion_al_catalogo(self, collection_id: str, 
                                      categoria: Optional[str] = None) -> bool:
        """
        Agrega una nueva colección al catálogo consultando el API.
        Auto-detecta la categoría si no se especifica.
        
        Args:
            collection_id: ID de la colección a agregar
            categoria: Categoría donde agregar (opcional, se auto-detecta)
            
        Returns:
            True si se agregó exitosamente, False en caso contrario
        """
        # Buscar en API
        metadata = self.buscar_coleccion_api(collection_id)
        
        if not metadata:
            logger.warning(f"No se pudo agregar {collection_id}: no existe en GEE")
            return False
        
        # Auto-detectar categoría si no se especificó
        if categoria is None:
            categoria = self._detectar_categoria(collection_id, metadata)
            logger.info(f"Categoría auto-detectada para {collection_id}: {categoria}")
        
        # Crear categoría si no existe
        if categoria not in self.colecciones:
            logger.error(f"Categoría '{categoria}' no existe en catálogo")
            return False
        
        # Agregar colección
        self.colecciones[categoria]['colecciones'][collection_id] = {
            'nombre': metadata['nombre'],
            'bandas_principales': metadata['bandas'][:6],  # Primeras 6 bandas
            'tipo': metadata['tipo'],
            'last_verified': metadata['last_verified']
        }
        
        # Guardar cambios
        self._guardar_catalogo(self.colecciones)
        logger.info(f"Colección {collection_id} agregada a categoría '{categoria}'")
        
        return True
    
    def verificar_coleccion(self, collection_id: str, 
                           actualizar_si_cambio: bool = True) -> bool:
        """
        Verifica si una colección existe en el API y actualiza metadata si cambió.
        
        Args:
            collection_id: ID de la colección a verificar
            actualizar_si_cambio: Si True, actualiza el catálogo si detecta cambios
            
        Returns:
            True si la colección existe, False en caso contrario
        """
        metadata_api = self.buscar_coleccion_api(collection_id)
        
        if not metadata_api:
            logger.warning(f"Colección {collection_id} ya no existe en GEE")
            return False
        
        # Buscar en catálogo local
        for categoria_id, categoria_info in self.colecciones.items():
            if categoria_id.startswith('_'):
                continue
                
            if collection_id in categoria_info['colecciones']:
                col_local = categoria_info['colecciones'][collection_id]
                
                # Comparar bandas
                bandas_api = set(metadata_api['bandas'])
                bandas_local = set(col_local.get('bandas_principales', []))
                
                if bandas_api != bandas_local and actualizar_si_cambio:
                    logger.info(f"Actualizando bandas de {collection_id}")
                    col_local['bandas_principales'] = metadata_api['bandas'][:6]
                    col_local['last_verified'] = metadata_api['last_verified']
                    self._guardar_catalogo(self.colecciones)
                
                return True
        
        logger.info(f"Colección {collection_id} no está en catálogo local")
        return False
    
    def verificar_colecciones_expiradas(self, dias_expiracion: int = 30) -> List[str]:
        """
        Encuentra colecciones que no se han verificado en X días.
        
        Args:
            dias_expiracion: Número de días después de los cuales una colección se considera expirada
            
        Returns:
            Lista de collection_ids que necesitan re-validación
        """
        from datetime import timedelta
        
        ahora = datetime.now()
        expiradas = []
        
        for categoria_id, categoria_info in self.colecciones.items():
            if categoria_id.startswith('_'):
                continue
            
            for col_id, col_info in categoria_info['colecciones'].items():
                last_verified_str = col_info.get('last_verified')
                
                if not last_verified_str:
                    # Sin verificación previa → marcar como expirada
                    expiradas.append(col_id)
                    continue
                
                try:
                    last_verified = datetime.fromisoformat(last_verified_str)
                    dias_desde_verificacion = (ahora - last_verified).days
                    
                    if dias_desde_verificacion > dias_expiracion:
                        expiradas.append(col_id)
                        logger.info(f"{col_id} expirada ({dias_desde_verificacion} días)")
                        
                except ValueError:
                    expiradas.append(col_id)
        
        logger.info(f"Encontradas {len(expiradas)} colecciones expiradas")
        return expiradas
    
    def _procesar_coleccion(self, categoria_id: str, categoria_nombre: str, 
                           col_id: str, col_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Procesa una colección individual y extrae sus metadatos.
        
        Args:
            categoria_id: ID de la categoría
            categoria_nombre: Nombre de la categoría
            col_id: ID de la colección
            col_info: Información de la colección
            
        Returns:
            Diccionario con registro procesado
        """
        return {
            'categoria': categoria_nombre,
            'collection_id': col_id,
            'nombre': col_info.get('nombre', ''),
            'resolucion_espacial': col_info.get('resolucion', ''),
            'resolucion_temporal': col_info.get('frecuencia', col_info.get('temporal', '')),
            'periodo_temporal': col_info.get('temporal', ''),
            'nivel_procesamiento': col_info.get('nivel', ''),
            'qa_disponible': col_info.get('qa', False),
            'bandas_principales': ', '.join(col_info.get('bandas_principales', [])),
            'variables': ', '.join(col_info.get('variables', [])),
            'aplicaciones': ', '.join(col_info.get('aplicaciones', [])),
            'notas': col_info.get('nota', col_info.get('cobertura', ''))
        }

    def buscar_por_nivel_procesamiento(self, nivel: str) -> pd.DataFrame:
        """
        Busca colecciones por nivel de procesamiento.
        
        Args:
            nivel: Nivel a buscar (L1C, L2A, L2, TOA, etc.)
            
        Returns:
            DataFrame con colecciones que coinciden
        """
        df = self.generar_inventario_completo(exportar_csv=False)
        
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
    
    def listar_niveles_disponibles(self) -> pd.DataFrame:
        """
        Lista todos los niveles de procesamiento disponibles en el catálogo.
        
        Returns:
            DataFrame con niveles únicos y conteo de colecciones
        """
        df = self.generar_inventario_completo(exportar_csv=False)
        
        # Filtrar niveles no vacíos
        niveles = df[df['nivel_procesamiento'] != '']['nivel_procesamiento'].value_counts()
        
        print("\n" + "="*80)
        print("NIVELES DE PROCESAMIENTO DISPONIBLES")
        print("="*80)
        
        for nivel, count in niveles.items():
            print(f"  {nivel:40s} → {count:2d} colecciones")
        
        print(f"\n[OK] Total: {len(niveles)} niveles diferentes")
        
        return niveles.to_frame(name='n_colecciones').reset_index()


    
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
            # Saltar metadata
            if categoria_id.startswith('_'):
                continue
                
            categoria_nombre = categoria_info['nombre']
            n_colecciones = len(categoria_info['colecciones'])
            
            print(f"\n{categoria_nombre}")
            print(f"  Colecciones: {n_colecciones}")
            
            for col_id, col_info in categoria_info['colecciones'].items():
                registro = self._procesar_coleccion(
                    categoria_id, categoria_nombre, col_id, col_info
                )
                registros.append(registro)
        
        df = pd.DataFrame(registros)
        
        print(f"\n[OK] Inventario generado: {len(df)} colecciones")
        print(f"[OK] Categorías: {df['categoria'].nunique()}")
        
        if exportar_csv:
            self._exportar_csv(df)
        
        return df
    
    def _exportar_csv(self, df: pd.DataFrame) -> Path:
        """
        Exporta DataFrame a CSV con timestamp.
        
        Args:
            df: DataFrame a exportar
            
        Returns:
            Path del archivo exportado
        """
        
        output_dir = Path(__file__).parent.parent.parent / 'output'
        output_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        csv_path = output_dir / f'catalogo_gee_{timestamp}.csv'
        
        df.to_csv(csv_path, index=False, encoding='utf-8')
        print(f"[OK] Exportado a: {csv_path}")
        
        return csv_path
    
    def analizar_por_categoria(self, df: pd.DataFrame) -> None:
        """
        Analiza el catálogo por categoría.
        
        Args:
            df: DataFrame con inventario completo
        """
        print("\n" + "="*80)
        print("ANÁLISIS POR CATEGORÍA")
        print("="*80)
        
        resumen = df.groupby('categoria').agg({
            'collection_id': 'count',
            'resolucion_espacial': lambda x: ', '.join(x.unique()[:3])
        }).rename(columns={
            'collection_id': 'n_colecciones',
            'resolucion_espacial': 'resoluciones_ejemplo'
        })
        
        print("\n" + resumen.to_string())
    
    def filtrar_por_criterios(self, df: pd.DataFrame, 
                             resolucion_max: Optional[str] = None,
                             incluir_qa: Optional[bool] = None,
                             categoria: Optional[str] = None) -> pd.DataFrame:
        """
        Filtra colecciones por criterios específicos.
        
        Args:
            df: DataFrame con inventario
            resolucion_max: Resolución máxima (ej: '100m') - no implementado aún
            incluir_qa: True para solo colecciones con QA
            categoria: Filtrar por categoría específica
            
        Returns:
            DataFrame filtrado
        """
        df_filtrado = df.copy()
        
        if categoria:
            df_filtrado = df_filtrado[df_filtrado['categoria_id'] == categoria]
        
        if incluir_qa is not None:
            df_filtrado = df_filtrado[df_filtrado['qa_disponible'] == incluir_qa]
        
        # TODO: Implementar filtro por resolución (requiere parsear strings como "30m", "1km")
        
        return df_filtrado
    
    def _calcular_estadisticas_resolucion_temporal(self, df: pd.DataFrame) -> Dict[str, int]:
        """
        Calcula estadísticas sobre resoluciones temporales.
        
        Args:
            df: DataFrame con inventario
            
        Returns:
            Diccionario con conteos de diferentes tipos de resolución temporal
        """
        patrones = {
            'tiempo_real': r'real|minutos|horas',
            'diario': r'Diaria|Daily',
            'estatico': r'Estático'
        }
        
        estadisticas = {}
        for nombre, patron in patrones.items():
            estadisticas[nombre] = df['resolucion_temporal'].str.contains(
                patron, case=False, na=False
            ).sum()
        
        return estadisticas
    
    def generar_resumen_ejecutivo(self, df: pd.DataFrame) -> None:
        """
        Genera un resumen ejecutivo del catálogo.
        
        Args:
            df: DataFrame con inventario completo
        """
        print("\n" + "="*80)
        print("RESUMEN EJECUTIVO DEL CATÁLOGO GEE")
        print("="*80)
        
        # Estadísticas generales
        print(f"\nESTADÍSTICAS GENERALES:")
        print(f"  - Total de colecciones catalogadas: {len(df)}")
        print(f"  - Categorías: {df['categoria'].nunique()}")
        print(f"  - Colecciones con QA: {df['qa_disponible'].sum()}")
        print(f"  - Colecciones sin QA: {(~df['qa_disponible']).sum()}")
        
        # Resoluciones espaciales
        print(f"\nRESOLUCIONES ESPACIALES:")
        resoluciones_unicas = df['resolucion_espacial'].unique()
        print(f"  - Diferentes resoluciones: {len(resoluciones_unicas)}")
        
        resoluciones_metricas = [r for r in resoluciones_unicas if 'm' in str(r)]
        if resoluciones_metricas:
            try:
                res_min = min(resoluciones_metricas, 
                            key=lambda x: float(str(x).replace('m', '').split('(')[0].strip()))
                print(f"  - Mejor resolución: {res_min}")
            except (ValueError, AttributeError):
                print("  - Rango: Desde alta resolución hasta productos regionales")
        
        # Resoluciones temporales
        stats_temp = self._calcular_estadisticas_resolucion_temporal(df)
        print(f"\nRESOLUCIONES TEMPORALES:")
        print(f"  - Datos en tiempo casi real: {stats_temp['tiempo_real']}")
        print(f"  - Datos diarios: {stats_temp['diario']}")
        print(f"  - Datos estáticos: {stats_temp['estatico']}")
        
        # Top 5 categorías
        print(f"\nTOP 5 CATEGORÍAS POR NÚMERO DE COLECCIONES:")
        top_categorias = df['categoria'].value_counts().head(5)
        for i, (cat, count) in enumerate(top_categorias.items(), 1):
            print(f"  {i}. {cat}: {count} colecciones")


def main() -> None:
    """
    Función principal del script.
    """
    print("\n" + "="*80)
    print("CATÁLOGO COMPLETO DE GOOGLE EARTH ENGINE")
    print("Exploración Exhaustiva para Planificación de Productos")
    print("="*80)
    
    try:
        # Inicializar catálogo
        catalogo = CatalogoGEE()
        
        # Generar inventario completo
        df_inventario = catalogo.generar_inventario_completo(exportar_csv=True)
        
        # Análisis por categoría
        catalogo.analizar_por_categoria(df_inventario)
        
        # Resumen ejecutivo
        catalogo.generar_resumen_ejecutivo(df_inventario)
        
        # Mostrar algunas colecciones destacadas
        _mostrar_colecciones_destacadas(df_inventario)
        
        print("\n" + "="*80)
        print("[OK] ANÁLISIS COMPLETADO")
        print("="*80)
        print("\nPróximos pasos:")
        print("1. Revisa el CSV exportado en la carpeta 'output/'")
        print("2. Identifica las colecciones relevantes para tus productos")
        print("3. Usa exploracion_google_earth_engine.py para análisis detallado")
        print("4. Define tus productos basándote en las capacidades disponibles")
        
    except ee.EEException as gee_error:
        print(f"\n[ERROR] Error de GEE: {gee_error}")
        print("[INFO] Verifica tu autenticación y proyecto configurado")
        return
    except Exception as error:
        print(f"\n[ERROR] Error inesperado: {error}")
        raise


def _mostrar_colecciones_destacadas(df: pd.DataFrame, max_categorias: int = 5) -> None:
    """
    Muestra colecciones destacadas por categoría.
    
    Args:
        df: DataFrame con inventario
        max_categorias: Número máximo de categorías a mostrar
    """
    print("\n" + "="*80)
    print("COLECCIONES DESTACADAS POR CATEGORÍA")
    print("="*80)
    
    categorias_mostrar = df['categoria'].unique()[:max_categorias]
    
    for categoria in categorias_mostrar:
        print(f"\n{categoria}")
        cols_categoria = df[df['categoria'] == categoria].head(3)
        
        for _, col in cols_categoria.iterrows():
            print(f"  - {col['nombre']}")
            print(f"    ID: {col['collection_id']}")
            print(f"    Resolución: {col['resolucion_espacial']} | "
                  f"Temporal: {col['resolucion_temporal']}")


if __name__ == "__main__":
    main()
