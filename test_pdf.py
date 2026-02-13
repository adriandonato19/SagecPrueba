
import sys
import os
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Sagec.settings')
django.setup()

from tramites.models import Tramite
from tramites.services.generador_pdf import generar_pdf_tramite
import traceback

try:
    print("Iniciando prueba de PDF...")
    t = Tramite.objects.last()
    if not t:
        print("No hay trámites para probar.")
        sys.exit(1)
        
    print(f"Probando trámite: {t.uuid}")
    pdf = generar_pdf_tramite(t)
    print("PDF GENERADO EXITOSAMENTE")
except Exception as e:
    print("ERROR AL GENERAR PDF:")
    print(traceback.format_exc())
