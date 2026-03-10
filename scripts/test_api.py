"""
Script de prueba rápida para verificar conexión a API Panamá Emprende.
Ejecutar con: python scripts/test_api.py
"""
import os
import sys

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

# Ahora podemos importar nuestros servicios
from integracion.services import buscar_empresa_api_externa, buscar_empresa
from django.conf import settings

print("=" * 60)
print("TEST DE CONEXIÓN A API PANAMÁ EMPRENDE")
print("=" * 60)

print(f"\nConfiguración actual:")
print(f"  URL: {settings.API_PANAMA_EMPRENDE_URL}")
print(f"  User: {settings.API_PANAMA_EMPRENDE_USER}")
print(f"  Password: {settings.API_PANAMA_EMPRENDE_PASSWORD[:10]}...")
print(f"  USE_MOCK_API: {settings.USE_MOCK_API}")

# Términos de prueba para verificar "Smart Search"
terminos_prueba = [
    "ADRIAN%DONATO",     # Prueba de wildcard
    "ADRIAN JOSE DONATO",
]

print("\n" + "-" * 60)
print("Probando búsquedas directas a la API...")
print("-" * 60)

for termino in terminos_prueba:
    with open('test_results.txt', 'a', encoding='utf-8') as f:
        f.write(f"\n>>> Buscando: '{termino}'\n")
        
        # Probar función directa de API externa
        resultado = buscar_empresa_api_externa(termino, 'todos')
        
        if resultado:
            empresas = resultado.get('avisos', [])
            f.write(f"    [OK] Se encontraron {len(empresas)} resultado(s)\n")
            if empresas:
                primera = empresas[0]
                nombre = primera.get('nombreComercial') or primera.get('razon_comercial', 'N/A')
                f.write(f"    Primera empresa: {nombre}\n")
        else:
            f.write(f"    [X] Sin resultados o error de conexion\n")

print("Resultados guardados en test_results.txt")
