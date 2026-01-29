#!/usr/bin/env python3
"""
GEE Catalog Maintenance Tool
============================
Herramienta modular para la gestión del catálogo de Google Earth Engine.
"""

import sys
import argparse
import logging
from pathlib import Path

# Agregar src al path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from gee_toolkit.catalog import CatalogoGEE
from gee_toolkit.auth_utils import initialize_gee

def main():
    parser = argparse.ArgumentParser(description='Herramienta de mantenimiento del catálogo GEE')
    
    parser.add_argument('--report', action='store_true', help='Genera reporte de estado')
    parser.add_argument('--revalidate', action='store_true', help='Re-valida colecciones expiradas')
    parser.add_argument('--discover', action='store_true', help='Busca nuevas colecciones públicas')
    parser.add_argument('--recategorize', action='store_true', help='Actualiza categorías')
    parser.add_argument('--clean', action='store_true', help='Limpia colecciones inaccesibles')
    parser.add_argument('--add', type=str, metavar='ID', help='Agrega una colección específica')
    parser.add_argument('--batch', type=str, metavar='FILE', help='Agrega colecciones desde un archivo')
    parser.add_argument('--days', type=int, default=30, help='Días para considerar expiración (default: 30)')
    parser.add_argument('--limit', type=int, help='Límite de colecciones a procesar')

    args = parser.parse_args()

    # Validar si se especificó alguna acción concreta
    acciones = [args.report, args.revalidate, args.discover, args.recategorize, 
                args.clean, args.add, args.batch]
    
    if not any(acciones):
        parser.print_help()
        return

    # Inicialización de producción
    initialize_gee()
    catalog = CatalogoGEE()

    try:
        if args.report:
            catalog.generar_reporte()
        
        if args.revalidate:
            catalog.revalidar_expiradas(dias=args.days, limite=args.limit)
        
        if args.discover:
            catalog.descubrir_colecciones()
            
        if args.recategorize:
            catalog.recategorizar()
            
        if args.clean:
            catalog.limpiar_invalidas()

        if args.add:
            if catalog.agregar_coleccion_al_catalogo(args.add):
                print(f"[OK] Colección {args.add} agregada.")
            else:
                print(f"[ERROR] No se pudo agregar {args.add}.")

        if args.batch:
            catalog.agregar_lote(args.batch)

    except KeyboardInterrupt:
        print("\n[!] Operación cancelada por el usuario.")
    except Exception as e:
        print(f"\n[ERROR] Ocurrió un fallo inesperado: {e}")
        logging.exception("Error en maintain_catalog:")

if __name__ == '__main__':
    main()