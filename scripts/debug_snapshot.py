import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from tramites.models import Tramite
import json

t = Tramite.objects.order_by('-fecha_creacion').first()
print(f"UUID: {t.uuid}")
print(f"Tipo de snapshot: {type(t.empresa_snapshot)}")
print(f"es_multi_empresa: {t.es_multi_empresa}")

if t.es_multi_empresa:
    print(f"Cantidad de empresas: {len(t.empresa_snapshot)}")
    for i, emp in enumerate(t.empresa_snapshot):
        print(f"\n--- Empresa {i+1} ---")
        print(f"  ruc: '{emp.get('ruc', 'NO EXISTE')}'")
        print(f"  ruc_completo: '{emp.get('ruc_completo', 'NO EXISTE')}'")
        print(f"  cedula_representante: '{emp.get('cedula_representante', 'NO EXISTE')}'")
        print(f"  razon_social: '{emp.get('razon_social', 'NO EXISTE')}'")
else:
    emp = t.empresa_snapshot
    print(f"\n--- Empresa Única ---")
    print(f"  ruc: '{emp.get('ruc', 'NO EXISTE')}'")
    print(f"  ruc_completo: '{emp.get('ruc_completo', 'NO EXISTE')}'")
    print(f"  cedula_representante: '{emp.get('cedula_representante', 'NO EXISTE')}'")
    print(f"  razon_social: '{emp.get('razon_social', 'NO EXISTE')}'")
