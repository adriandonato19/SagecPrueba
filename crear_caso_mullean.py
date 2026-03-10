import os
import django
import sys
from datetime import date
from django.utils import timezone

# Configurar entorno Django
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from tramites.models import Tramite
from identidad.models import UsuarioMICI

def crear_caso_mullean():
    print("Creando caso de prueba: MULLEAN GROUP, S.A.")
    
    # Usuario solicitante (admin o cualquiera activo)
    usuario = UsuarioMICI.objects.first()
    if not usuario:
        print("Error: No hay usuarios en el sistema.")
        return

    # Datos de los avisos (recreados de la imagen)
    avisos_mullean = [
        {
            'numero_aviso': '1674633-1-680487-2016-507979',
            'nombre_comercial': 'MULLEAN GROUP, S.A.',
            'nombre_representante': 'Gregoria Tajan',
            'razon_social': 'MULLEAN GROUP, S.A.',
            'ruc': '1674633-1-680487',
            'dv': '20',
            'ruc_completo': '1674633-1-680487 DV 20',
            'fecha_inicio_operaciones': '1 de mayo de 2016',
            'direccion': 'Dirección de prueba basada en RUC',
            'estado': 'Vigente'
        },
        {
            'numero_aviso': '1674633-1-680487-2016-507979-S1',
            'nombre_comercial': 'MULLEAN GROUP, S.A.',
            'nombre_representante': 'Gregoria Tajan',
            'razon_social': 'MULLEAN GROUP, S.A.',
            'ruc': '1674633-1-680487',
            'dv': '20',
            'ruc_completo': '1674633-1-680487 DV 20',
            'fecha_inicio_operaciones': '1 de julio de 2016',
            'direccion': 'Dirección de prueba basada en RUC',
            'estado': 'En Solicitud'
        }
    ]

    # Crear el trámite
    tramite = Tramite.objects.create(
        tipo_documento='OFICIO',
        solicitante=usuario,
        # Snapshot debe ser una lista para multi-empresa
        empresa_snapshot=[
            {
                'razon_social': 'MULLEAN GROUP, S.A.',
                'ruc': '1674633-1-680487',
                'avisos_relacionados': avisos_mullean
            }
        ],
        origen_consulta='1674633-1-680487',
        numero_referencia=f"OFICIO-TEST-{Tramite.objects.count() + 1}",
        estado=Tramite.BORRADOR,
        destinatario='Licenciada SENIA LEZCANO',
        proposito='Verificación de avisos',
        fecha_solicitud=date(2025, 5, 30),
        
        # Nuevos campos de Oficio
        oficio_entrante='No.7487/202500039050/sl',
        carpetilla='202500039050',
        fecha_oficio_entrante=date(2025, 5, 30),
        fecha_recepcion=date(2025, 6, 2),
        solicitante_externo='Licenciada SENIA LEZCANO',
        cargo_solicitante='Fiscal Adjunta de la Fiscalía Anticorrupción del Sistema Penal Acusatorio Sección de Atención Primaria',
        institucion_solicitante='MINISTERIO PÚBLICO'
    )
    
    print(f"Trámite creado exitosamente.")
    print(f"UUID: {tramite.uuid}")
    print(f"URL PDF (local): http://127.0.0.1:8000/tramites/{tramite.uuid}/pdf/")

if __name__ == '__main__':
    crear_caso_mullean()
