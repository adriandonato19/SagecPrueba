import os
import sys
import django

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from tramites.models import Tramite

count = Tramite.objects.filter(tipo_documento='CERTIFICADO').count()
print(f"Quedan {count} certificados.")
