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
from integracion.services import buscar_empresa

def crear_caso_real_api():
    print("--- INICIANDO PRUEBA CON DATOS REALES DE API ---")
    
    # 1. Buscar en la API
    ruc_busqueda = '1674633-1-680487'
    print(f"Consultando API para RUC: {ruc_busqueda}...")
    
    try:
        # Usamos buscar_empresa que ya devuelve la estructura normalizada
        resultado = buscar_empresa(ruc_busqueda, 'ruc')
        
        if not resultado:
            print("X ERROR: La API no devolvió resultados para este RUC.")
            return

        print(f"OK DATOS RECIBIDOS DE API: {len(resultado.get('avisos', []))} avisos encontrados.")
        print(f"   Razon Social: {resultado['detalle']['razon_social']}")
        
        # 2. Preparar snapshot en el formato CORRECTO (igual que el carrito)
        # El carrito almacena cada empresa como un dict plano con:
        #   razon_social, numero_aviso, avisos_relacionados, etc. al NIVEL SUPERIOR
        # NO como {'detalle': {...}, 'avisos': [...]}
        
        detalle = resultado['detalle']
        avisos = resultado['avisos']
        
        # Construir snapshot con la misma estructura que usa el carrito
        empresa_snapshot_item = detalle.copy()
        empresa_snapshot_item['avisos_relacionados'] = avisos
        
        # Para Oficio con una empresa: snapshot es una LISTA con un solo item
        snapshot = [empresa_snapshot_item]
        
        # Usuario solicitante
        usuario = UsuarioMICI.objects.first()
        
        # 3. Crear el tramite con los datos REALES + Metadatos del Oficio
        tramite = Tramite.objects.create(
            tipo_documento='OFICIO',
            solicitante=usuario,
            empresa_snapshot=snapshot,
            origen_consulta=ruc_busqueda,
            numero_referencia=f"API-REAL-{Tramite.objects.count() + 1}",
            estado=Tramite.BORRADOR,
            destinatario='Licenciada SENIA LEZCANO',
            proposito='Verificacion de avisos (Datos Reales API)',
            fecha_solicitud=date(2025, 5, 30),
            
            # Datos del Oficio (Simulados, porque esto lo mete el usuario)
            oficio_entrante='No.7487/202500039050/sl',
            carpetilla='202500039050',
            fecha_oficio_entrante=date(2025, 5, 30),
            fecha_recepcion=date(2025, 6, 2),
            solicitante_externo='Licenciada SENIA LEZCANO',
            cargo_solicitante='Fiscal Adjunta de la Fiscalia Anticorrupcion del Sistema Penal Acusatorio Seccion de Atencion Primaria',
            institucion_solicitante='MINISTERIO PUBLICO'
        )
        
        print("="*60)
        print(f"OK TRAMITE CREADO CON DATOS REALES DE API")
        print(f"UUID: {tramite.uuid}")
        print(f"URL PDF: http://127.0.0.1:8000/tramites/{tramite.uuid}/pdf/")
        print("="*60)
        
    except Exception as e:
        print(f"X ERROR CRÍTICO AL CONSULTAR API: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    crear_caso_real_api()
