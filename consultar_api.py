import os
import sys
import json
import pprint

# Configurar entorno Django
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from django.conf import settings

import os
import sys
import json
import pprint
import requests
import urllib.parse
from datetime import datetime

# Configurar entorno Django
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from django.conf import settings

def consultar_pagina(termino, page=1):
    try:
        termino_upper = termino.upper()
        termino_encoded = urllib.parse.quote(termino_upper)
        base_url = settings.API_PANAMA_EMPRENDE_URL.rstrip('/')
        url = f"{base_url}/{termino_encoded}"
        
        # Agregar parametro de pagina si la API lo soporta (Query String standard)
        if page > 1:
            url += f"?page={page}"
            
        headers = {
            'X-User': settings.API_PANAMA_EMPRENDE_USER,
            'X-Password': settings.API_PANAMA_EMPRENDE_PASSWORD
        }

        print(f"   [GET] {url} ...")
        response = requests.get(url, headers=headers, timeout=(10, 30))
        
        if response.status_code != 200:
            print(f"   ❌ Error API: {response.status_code}")
            return None
            
        return response.json()
    except Exception as e:
        print(f"   ❌ Excepción: {e}")
        return None

def main():
    print("="*60)
    print("   CONSULTADOR API PANAMÁ EMPRENDE (CON PAGINACIÓN)")
    print("="*60)
    
    while True:
        print("\n" + "-"*60)
        query = input("Ingresa búsqueda (o 'salir'): ").strip()
        
        if query.lower() in ['salir', 'exit', 'quit']:
            break
            
        if not query:
            continue
            
        if query.lower() in ['salir', 'exit', 'quit']:
            break
            
        if not query:
            continue
            
        # Parsear filtros extra del query string estilo "termino | status:vigente | prov:panama"
        # O preguntar interactivamente? Mejor interactivamente.
        
        filtros = {}
        print("\n¿Deseas aplicar filtros específicos? (Dejar vacío para omitir)")
        f_status = input("  - Estatus (ej: Vigente, Cancelado): ").strip()
        if f_status: filtros['estado'] = f_status
        
        f_prov = input("  - Provincia (ej: Panamá, Colón): ").strip()
        if f_prov: filtros['provincia'] = f_prov
        
        f_lic = input("  - Solo con Licencia? (s/n): ").strip().lower()
        if f_lic == 's': filtros['con_licencia'] = True
        
        if filtros:
            print(f"🔎 Filtros Activos: {filtros}")
            
        page = 1
        total_items = 0
        matches_found = 0
        all_results = []
        
        while True:
            data_full = consultar_pagina(query, page)
            
            if not data_full:
                break
                
            # Estructura esperada Laravel
            meta_data = data_full.get('data', {})
            resultados = meta_data.get('data', [])
            
            pagination = {
                'current_page': meta_data.get('current_page'),
                'last_page': meta_data.get('last_page'),
                'total': meta_data.get('total'),
                'per_page': meta_data.get('per_page')
            }
            
            if isinstance(meta_data, list):
                resultados = meta_data
                pagination = {'current_page': 1, 'last_page': 1, 'total': len(resultados)}

            if not resultados:
                if page == 1: print(f"\n❌ No hay resultados en la API para '{query}'.")
                break
                
            # Provisar resultados y aplicar filtros
            rr_filtrados = []
            for emp in resultados:
                cumple_todos = True
                
                # Filtro Estatus
                if 'estado' in filtros:
                    if filtros['estado'].lower() not in (emp.get('estado') or '').lower():
                        cumple_todos = False
                
                # Filtro Provincia
                if 'provincia' in filtros:
                    ubicacion = f"{emp.get('provincia')} {emp.get('distrito')} {emp.get('corregimiento')}".lower()
                    if filtros['provincia'].lower() not in ubicacion:
                        cumple_todos = False
                        
                # Filtro Licencia
                licencia_val = None
                for k,v in emp.items():
                    if 'licen' in k.lower() and v:
                        licencia_val = v
                        
                if 'con_licencia' in filtros:
                    if not licencia_val:
                         cumple_todos = False
                
                if cumple_todos:
                    emp['_licencia'] = licencia_val or "❌ No Lic."
                    rr_filtrados.append(emp)
                    all_results.append(emp)
            
            # Mostrar Solo Filtrados
            if rr_filtrados:
                print(f"\n✅ PÁGINA {page} - Encontrados {len(rr_filtrados)} coincidencia(s) con filtros:")
                start_idx = len(all_results) - len(rr_filtrados) + 1
                for i, emp in enumerate(rr_filtrados):
                    idx_global = start_idx + i
                    print(f"  [{idx_global}] {emp.get('ruc')} | {emp.get('razon_social')} | {emp.get('estado')} | {emp['_licencia']}")
            else:
                pass

            total_items += len(resultados)
            
            # Control de Paginación
            last_page = pagination.get('last_page', 1)
            current = pagination.get('current_page', 1)
            
            if current >= last_page or len(resultados) == 0:
                print(f"\n🏁 Fin de búsqueda. Total revisado: {total_items} items.")
                
                # Loop de inspección final
                while True:
                    cmd = input("\n[v <N>: Ver Detalle | Enter: Nueva Búsqueda]: ").strip().lower()
                    if not cmd: break
                    
                    if cmd.startswith('v '):
                        try:
                            idx = int(cmd.split()[1]) - 1
                            if 0 <= idx < len(all_results):
                                print("\n" + "="*40)
                                print(f"DETALLE RESULTADO #{idx+1}")
                                print("="*40)
                                # Pretty print raw dict
                                print(json.dumps(all_results[idx], indent=2, ensure_ascii=False))
                            else:
                                print("❌ Índice inválido.") 
                        except:
                            print("❌ Comando inválido (ej: v 1)")
                break
            
            # Auto-avance si hay filtros activos y no hemos encontrado nada aun (o pocos)
            if not rr_filtrados:
                 msg = f"Pagina {page} sin coincidencias de filtro."
            else:
                 msg = ""
                 
            opcion = input(f"\n{msg} ¿Página {current + 1} de {last_page}? (Enter: Sí, v <N>: Ver Detalle, n: No, a: Auto-Todas): ").lower()
            
            if opcion.startswith('v '):
                try:
                    idx = int(opcion.split()[1]) - 1
                    if 0 <= idx < len(all_results):
                        print("\n" + "="*40)
                        print(f"DETALLE RESULTADO #{idx+1}")
                        print("="*40)
                        print(json.dumps(all_results[idx], indent=2, ensure_ascii=False))
                        input("\nPresiona Enter para continuar paginando...")
                    else:
                         print("❌ Índice inválido.")
                except:
                     pass
                # No avanzamos pagina si inspeccionamos
                continue
                
            if opcion == 'n':
                break
            elif opcion == 'a':
                page += 1
                continue
            else:
                page += 1

if __name__ == '__main__':
    main()
