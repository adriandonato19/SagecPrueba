import os
import sys
from datetime import date
from django.utils import timezone

# Configurar entorno Django
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from tramites.models import Tramite
from identidad.models import UsuarioMICI

def crear_caso_abrego():
    print("--- CREANDO CASO DE PRUEBA: LUIS ABREGO (XTREME STORE) ---")
    
    # Usuario solicitante (cualquiera)
    usuario = UsuarioMICI.objects.first()
    if not usuario:
        print("X No hay usuarios en la BD. Crea un superuser primero.")
        return

    # Datos manuales proporcionados
    datos_empresa = {
        'razon_social': 'XTREME STORE, S.A.',
        'razon_comercial': 'PANAMÁ ATV STORE', # Ojo: template usa razon_comercial
        # El usuario puso "RAZÓN COMERCIAL: PANAMÁ ATV STORE" en el texto
        'numero_aviso': '573584-1-447039-2007-27352',
        'numero_licencia': '707200408', # Dato manual que la API no trae
        'representante_legal': 'LUIS GABRIEL ABREGO DUARTE',
        'ruc': '573584-1-447039',
        'dv': '89',
        'ruc_completo': '573584-1-447039-89', 
        'fecha_inicio_operaciones': '2004-01-01', # 1 de Enero de 2004
        'ubicacion_completa': 'Vía Ricardo J Alfaro, Calle 2da, Camino Real, Casa N0. 31-C, Frente a estética Lucy., Corregimiento de Betania, Distrito de Panamá, Provincia de Panamá',
        'estatus': 'Cancelado', # Estatus especial
        'fecha_cierre': '2016-01-20', # Cancelado el 20 de enero de 2016
        
        # Campos extra que el adaptador normalmente llena
        'provincia': 'Panamá',
        'distrito': 'Panamá',
        'corregimiento': 'Betania'
    }

    # Snapshot es una lista de 1 elemento (dict plano)
    snapshot = [datos_empresa]
    
    # Crear trámite
    tramite = Tramite.objects.create(
        tipo_documento='OFICIO', # Asumimos Oficio por el texto
        solicitante=usuario,
        empresa_snapshot=snapshot,
        origen_consulta=datos_empresa['ruc'],
        numero_referencia=f"TEST-ABREGO-{Tramite.objects.count() + 1}",
        estado=Tramite.BORRADOR,
        destinatario='Señor LUIS ABREGO',
        proposito='autenticación de un certificado de operación no operativo para trámite de traspaso vehicular',
        fecha_solicitud=date(2025, 5, 28),
        
        # Datos para que use el Layout Viejo (o Nuevo?)
        # El texto proporcionado parece ser del Layout Viejo ("En respuesta a su solicitud...")
        # Si queremos probar el Layout Viejo, NO definimos oficio_entrante (o lo dejamos vacío)
        # PERO, el usuario quiere probar con ESTOS DATOS. El texto que pegó ES el cuerpo del PDF.
        # Si el texto dice "Respetado Sr. Ábrego...", eso suena al Layout Nuevo (Saludo). 
        # Pero el párrafo "En respuesta a su solicitud..." es típico del Layout Viejo.
        # UN MOMENTO: El usuario pegó AMBOS bloques?
        # "Señor LUIS ABREGO... Respetado Sr. Ábrego... En respuesta..."
        
        # VOY A ASUMIR LAYOUT VIEJO PORQUE NO HAY NUMERO DE OFICIO EN EL TEXTO PROPORCIONADO 
        # (Salvo que "Aviso de Operaciones 573584..." sea el oficio, pero no parece).
        # Espera, "En respuesta a su solicitud... recibida... el 28 de mayo".
        
        oficio_entrante='', # Vacío para forzar Layout Viejo
    )
    
    print("="*60)
    print(f"OK CASO ABREGO CREADO")
    print(f"UUID: {tramite.uuid}")
    print(f"URL PDF: http://127.0.0.1:8000/tramites/{tramite.uuid}/pdf/")
    print("="*60)
    
    # Generar PDF inmediatamente
    from tramites.services.generador_pdf import generar_pdf_tramite
    pdf = generar_pdf_tramite(tramite)
    filename = 'test_abrego.pdf'
    with open(filename, 'wb') as f:
        f.write(pdf.read())
    print(f"PDF generado localmente: {filename} ({os.path.getsize(filename)} bytes)")

if __name__ == '__main__':
    crear_caso_abrego()
