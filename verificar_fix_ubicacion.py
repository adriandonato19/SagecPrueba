import os
import sys
import django

sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.conf import settings
from integracion.services import buscar_empresa

def verificar():
    print("--- VERIFICANDO FIX DE UBICACIÓN ---")
    settings.USE_MOCK_API = False
    
    query = 'XTREME STORE'
    print(f"Buscando '{query}' en servicio (Real API)...")
    
    resultado = buscar_empresa(query, 'todos')
    
    if resultado:
        detalle = resultado['detalle']
        print("\n[Detalle Principal Normalized]")
        print(f"Razón Social: {detalle.get('razon_social')}")
        print(f"Ubicación Completa: '{detalle.get('ubicacion_completa')}'")
        
        avisos = resultado['avisos']
        print(f"\n[Avisos: {len(avisos)}]")
        for i, av in enumerate(avisos[:3]):
            print(f"  [{i+1}] Aviso: {av.get('numero_aviso')}")
            print(f"      Ubicación: '{av.get('ubicacion_completa')}'")
            
            # Imprimir componentes individuales si sale vacía
            if av.get('ubicacion_completa') == 'No especificada':
                print(f"      -> Debug: Prov={av.get('provincia')}, Dist={av.get('distrito')}, Calle={av.get('calle')}")
    else:
        print("No se encontraron resultados.")

if __name__ == '__main__':
    verificar()
