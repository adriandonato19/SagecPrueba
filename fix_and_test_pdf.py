
import os
import django
import sys
import json
from datetime import date
from io import BytesIO

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from tramites.models import Tramite
from tramites.services.generador_pdf import generar_pdf_tramite

try:
    print("Iniciando inyección de datos de prueba...")
    t = Tramite.objects.last()
    if not t:
        print("No hay trámites.")
        sys.exit(1)

    print(f"Trámite actual: {t.uuid}")
    
    # Datos de prueba ROBUSTOS
    datos_prueba = {
        'ruc': '8-765-4321',
        'dv': '99',
        'ruc_completo': '8-765-4321-99',
        'razon_social': 'Juan Alberto Álvarez Martínez', 
        'razon_comercial': 'J.A. PANAMA & CIA',
        'numero_aviso': '2026-AVISO-001',
        'numero_licencia': 'LIC-2026-999',
        'representante_legal': 'María Eugenia',
        'fecha_inicio_operaciones': '1994-06-20',
        # ... y todo lo demás para que no falte nada
        'capital_invertido': '500.00',
        'estatus': 'Vigente',
        'sucursal': '000',
        # Ubicación completa
        'provincia': 'Panamá',
        'distrito': 'Panamá',
        'corregimiento': 'Bella Vista',
        'calle': '50',
        'edificio': 'Torre Global',
        'ubicacion_completa': 'Panamá, Panamá, Bella Vista, Calle 50, Torre Global'
    }
    
    # Preservar datos existentes si quiero
    if not t.empresa_snapshot:
        t.empresa_snapshot = {}
    
    t.empresa_snapshot.update(datos_prueba)
    t.save()
    print("Datos ACTUALIZADOS en empresa_snapshot y guardados en BD.")
    
    # Generar PDF
    print("Regenerando PDF...")
    pdf_buffer = generar_pdf_tramite(t)
    
    # Verificar tipo de retorno
    if isinstance(pdf_buffer, BytesIO):
        with open('prueba_oficio_fixed.pdf', 'wb') as f:
            f.write(pdf_buffer.getvalue())
        print(f"PDF generado y guardado en 'prueba_oficio_fixed.pdf' ({len(pdf_buffer.getvalue())} bytes)")
    else:
        print(f"ERROR: Tipo inesperado {type(pdf_buffer)}")
    
except Exception as e:
    import traceback
    traceback.print_exc()
