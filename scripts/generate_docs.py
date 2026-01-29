#!/usr/bin/env python3
"""
Generador de Documentación del Catálogo GEE
===========================================
Lee config/colecciones_gee.json y genera un archivo Markdown formateado.
"""

import json
from pathlib import Path
from datetime import datetime

def generate_markdown():
    root_dir = Path(__file__).parent.parent
    json_path = root_dir / 'config' / 'colecciones_gee.json'
    doc_path = root_dir / 'docs' / 'CATALOGO_COLECCIONES.md'
    
    # Crear directorio docs si no existe
    doc_path.parent.mkdir(exist_ok=True)
    
    if not json_path.exists():
        print(f"[ERROR] No se encontró {json_path}")
        return

    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    md_lines = []
    
    # Encabezado
    md_lines.append("# Catálogo de Colecciones GEE Area Explorer")
    md_lines.append(f"**Generado automáticamente:** {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    md_lines.append(f"**Versión del Catálogo:** {data.get('_metadata', {}).get('version', 'N/A')}")
    md_lines.append("\nEste documento detalla todas las colecciones disponibles en el sistema, organizadas por categoría temática.\n")
    
    # Índice
    md_lines.append("## Índice de Categorías")
    categorias = [k for k in data.keys() if not k.startswith('_')]
    for cat in categorias:
        nombre_cat = data[cat].get('nombre', cat.title())
        md_lines.append(f"- [{nombre_cat}](#{cat.lower()})")
    md_lines.append("\n---")
    
    # Contenido
    for cat_key in categorias:
        cat_data = data[cat_key]
        nombre_cat = cat_data.get('nombre', cat_key.title())
        colecciones = cat_data.get('colecciones', {})
        
        md_lines.append(f"\n## <a id='{cat_key.lower()}'></a>{nombre_cat}")
        if 'nota' in cat_data:
            md_lines.append(f"> *Nota: {cat_data['nota']}*\n")
            
        md_lines.append(f"**Total colecciones:** {len(colecciones)}\n")
        
        if not colecciones:
            md_lines.append("*No hay colecciones en esta categoría.* ")
            continue
            
        # Tabla
        md_lines.append("| ID Colección | Nombre / Descripción | Nivel | Resolución | Periodo |")
        md_lines.append("|---|---|---|---|---|")
        
        for cid, info in sorted(colecciones.items()):
            nombre = info.get('nombre', '')
            nivel = info.get('nivel', 'N/A')
            res = info.get('resolucion', 'N/A')
            
            # Formatear periodo
            periodo = info.get('temporal', 'N/A')
            if info.get('date_start'):
                periodo = f"{info['date_start']} a {info.get('date_end', 'Presente')}"
            
            # Limpiar nombre si es redundante
            if not nombre or nombre == cid:
                nombre = "*(Sin descripción)*"
            
            # Escapar pipes en descripciones
            nombre = nombre.replace('|', '-')
            
            md_lines.append(f"| `{cid}` | {nombre} | {nivel} | {res} | {periodo} |")
            
    # Escribir archivo
    with open(doc_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(md_lines))
    
    print(f"[OK] Documentación generada en: {doc_path}")

if __name__ == '__main__':
    generate_markdown()
