import os
import sys
import json
import pprint

# Configurar entorno Django
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from tramites.models import Tramite

def diagnosticar_ultimo_tramite():
    print("--- DIAGNÓSTICO DE ESTRUCTURA DE DATOS ---")
    
    # Obtener el último trámite creado
    try:
        tramite = Tramite.objects.last()
        if not tramite:
            print("No hay trámites en la base de datos.")
            return
            
        print(f"Trámite UUID: {tramite.uuid}")
        print(f"Tipo: {tramite.tipo_documento}")
        print(f"Oficio Entrante: {tramite.oficio_entrante}")
        
        snapshot = tramite.empresa_snapshot
        
        print("\n--- TIPO DE DATOS EN SNAPSHOT ---")
        print(f"Tipo: {type(snapshot)}")
        
        if isinstance(snapshot, list):
            print(f"Cantidad de elementos: {len(snapshot)}")
            if len(snapshot) > 0:
                print("\n--- ESTRUCTURA DEL PRIMER ELEMENTO (Campos disponibles para el Template) ---")
                primer_elemento = snapshot[0]
                # Imprimir llaves disponibles
                print("Llaves disponibles:")
                for k in sorted(primer_elemento.keys()):
                    val_preview = str(primer_elemento[k])
                    if len(val_preview) > 50: val_preview = val_preview[:47] + "..."
                    print(f"  - {k}: {val_preview}")
                    
                # Verificar específicamente campos problematicos
                print("\n--- VERIFICACIÓN DE CAMPOS CLAVE ---")
                print(f"empresa.razon_social: {primer_elemento.get('razon_social', 'NO EXISTE')}")
                print(f"empresa.razonsocial: {primer_elemento.get('razonsocial', 'NO EXISTE (Correcto, no debería existir)')}")
                
                # Verificar anidamiento incorrecto
                if 'detalle' in primer_elemento:
                    print("\n[!] ADVERTENCIA: Se detectó llave 'detalle'. Esto indica estructura ANIDADA (Incorrecta).")
                    print("    El template espera las llaves 'razon_social', etc. en el nivel superior, no dentro de 'detalle'.")
        
        elif isinstance(snapshot, dict):
            print("\n--- SNAPSHOT ES UN DICCIONARIO (Modo Simple Antiguo) ---")
            print("Llaves y Valores:")
            for k in sorted(snapshot.keys()):
                val = snapshot[k]
                print(f"  - {k}: {val!r}")
            
            if 'detalle' in snapshot:
                 print("\n[!] Estructura Anidada detectada en Modo Simple.")
        
        else:
            print("Formato desconocido.")

    except Exception as e:
        print(f"Error al leer trámite: {e}")

    print("\n--- DIAGNÓSTICO DE API RAW (Buscando License Key) ---")
    try:
        from django.conf import settings
        # FORZAR USO DE API REAL
        settings.USE_MOCK_API = False
        print(">> FORZANDO settings.USE_MOCK_API = False")
        
        from integracion.services import buscar_empresa_api_externa
        
        from integracion.services import buscar_empresa_api_externa
        
        # BUSCAR POR NOMBRE REAL: XTREME STORE
        termino_busqueda = 'XTREME STORE'
        tipo = 'todos'
        
        print(f"Consultando API Externa por NOMBRE: '{termino_busqueda}'...")
        
        # La función devuelve una LISTA de resultados si es búsqueda por nombre (internamente)
        # Pero buscar_empresa_api_externa devuelve una lista de diccionarios raw
        from integracion.services import buscar_empresa_api_externa
        
        # Nota: buscar_empresa_api_externa devuelve una lista de resultados raw
        # No un dict con 'detalle'.
        # Voy a usar la función interna consultar_api_raw si pudiera, pero no es exportada.
        # Usaré buscar_empresa_api_externa que devuelve un dict con 'detalle' y 'avisos' ???
        # NO, revisé el código en integracion/services.py:
        # devuelve Optional[Dict] con keys 'detalle' (dict) y 'avisos' (list)
        
        raw_data = buscar_empresa_api_externa(termino_busqueda, tipo)
        
        if raw_data:
            detalle = raw_data.get('detalle', {})
            print(f"\n[Raw API Response - Detalle para '{termino_busqueda}']")
            print(f"Razón Social: {detalle.get('razon_social')}")
            print(f"RUC: {detalle.get('ruc')}")
            
            print("\n[Buscando License Key en este resultado]")
            found_licencia = False
            for k, v in detalle.items():
                if 'licen' in k.lower():
                    print(f"  -> MATCH: {k}: {v!r}")
                    found_licencia = True
            
            if not found_licencia:
                print("  [!] No se encontraron llaves con 'licen'.")
                
            # Buscar estatus
            print(f"Estatus: {detalle.get('estado')}")
            
            # Ver si hay avisos
            avisos = raw_data.get('avisos', [])
            print(f"\nAvisos encontrados: {len(avisos)}")
            for i, av in enumerate(avisos):
                print(f"  [{i+1}] Aviso: {av.get('numero_aviso')} - Estado: {av.get('estado')}")
                # Buscar licencia en los avisos tambien
                for k, v in av.items():
                    if 'licen' in k.lower():
                        print(f"      -> Licencia en Aviso: {k}: {v!r}")

        else:
            print("  [!] API Externa devolvió None para 'XTREME STORE'.")
    except Exception as e:
         print(f"Error al consultar API Raw: {e}")

if __name__ == '__main__':
    diagnosticar_ultimo_tramite()
