
import os
import sys

# Add project root to path so we can import django settings
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

# Configure Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

try:
    import django
    django.setup()
except ImportError:
    raise ImportError("Couldn't import Django. Are you sure it's installed?")

from django.core.management import call_command
from identidad.models import UsuarioMICI

def create_database():
    print("--- Starting Database Creation ---")
    
    # 1. Apply Migrations (Recreating tables if DB was deleted)
    print("\n1. Running migrations to create tables...")
    call_command('migrate')
    
    # 2. Create Test Users
    print("\n2. Creating test users for each role...")
    
    users_to_create = [
        {
            'username': 'fiscal',
            'email': 'fiscal@exterminio.gob.pa',
            'password': 'password123',
            'rol': UsuarioMICI.FISCAL,
            'first_name': 'Lic.',
            'last_name': 'Fiscal',
            'cedula': '8-100-100',
            'institucion': 'Ministerio Público'
        },
        {
            'username': 'trabajador',
            'email': 'mici@mici.gob.pa',
            'password': 'password123',
            'rol': UsuarioMICI.TRABAJADOR,
            'first_name': 'Funcionario',
            'last_name': 'Operativo',
            'cedula': '8-200-200',
            'institucion': 'MICI'
        },
        {
            'username': 'director',
            'email': 'director@mici.gob.pa',
            'password': 'password123',
            'rol': UsuarioMICI.DIRECTOR,
            'first_name': 'Sr.',
            'last_name': 'Director',
            'cedula': '8-300-300',
            'institucion': 'Despacho Superior'
        }
    ]

    for user_data in users_to_create:
        if not UsuarioMICI.objects.filter(username=user_data['username']).exists():
            UsuarioMICI.objects.create_user(
                username=user_data['username'],
                email=user_data['email'],
                password=user_data['password'],
                rol=user_data['rol'],
                first_name=user_data['first_name'],
                last_name=user_data['last_name'],
                cedula=user_data['cedula'],
                institucion=user_data['institucion']
            )
            print(f"  [OK] Created {user_data['rol']}: {user_data['username']} / {user_data['password']}")
        else:
            print(f"  [SKIP] User {user_data['username']} already exists")

    # 3. Create Superuser
    if not UsuarioMICI.objects.filter(username='admin').exists():
        UsuarioMICI.objects.create_superuser(
            username='admin',
            email='admin@sagec.local',
            password='admin',
            cedula='0-000-000'
        )
        print("  [OK] Created Superuser: admin / admin")
    
    print("\n--- Database Setup Complete ---")

if __name__ == "__main__":
    create_database()
