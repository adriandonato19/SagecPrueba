
import os
import django
from django.conf import settings

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from integracion.services import buscar_empresa

try:
    print("-" * 50)
    print(f"USE_MOCK_API: {getattr(settings, 'USE_MOCK_API', 'No definido (default=True)')}")
    
    query = "8-765-4321"
    print(f"Buscando empresa con RUC: {query}")
    print("-" * 50)
    
    resultado = buscar_empresa(query, 'ruc')
    
    if resultado:
        print("RESULTADO ENCONTRADO:")
        detalle = resultado['detalle']
        print(f"Razón Social: {detalle.get('razon_social')}")
        print(f"RUC: {detalle.get('ruc')} | DV: {detalle.get('dv')}")
        print(f"Aviso Operación: '{detalle.get('numero_aviso')}'")
        print(f"Licencia: '{detalle.get('numero_licencia')}'")
        print(f"Estatus: '{detalle.get('estatus')}'")
        print("-" * 50)
        print("CLAVES DISPONIBLES EN DETALLE:")
        print(list(detalle.keys()))
    else:
        print("NO SE ENCONTRÓ NINGUNA EMPRESA.")

except Exception as e:
    import traceback
    traceback.print_exc()
