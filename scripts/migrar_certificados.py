import os
import sys
import django

# Agregar el directorio raíz al path para encontrar 'config'
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configurar el entorno de Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from tramites.models import Tramite

def migrar_certificados_a_oficios():
    certificados = Tramite.objects.filter(tipo_documento='CERTIFICADO')
    count = certificados.count()
    
    print(f"Encontrados {count} trámites con tipo 'CERTIFICADO'.")
    
    if count > 0:
        # Actualizar todos a OFICIO
        certificados.update(tipo_documento='OFICIO')
        print(f"✅ Se han migrado {count} trámites a tipo 'OFICIO'.")
    else:
        print("No hay trámites para migrar.")

if __name__ == '__main__':
    migrar_certificados_a_oficios()
