
import sys
import os
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from integracion.adapters import normalizar_datos_empresa

# JSON del usuario
user_json_item = {
    "numero_aviso": "8-237-715-2007-62950",
    "nombreComercial": "DONATO SYSTEM",
    "razon_social_juridica": None,
    "razon_social_natural": "JOSE BOSCO DONATO MOCK",
    "ruc": "",
    "cedula_representante": "8-237-715",
    "representante_legal": "JOSE BOSCO DONATO MOCK ",
    "estado": "Vigente",
    "tipo": "Natural",
    "fecha_inicio_operaciones": "2001-08-25",
    "provincia": "PANAMÁ",
    "distrito": "SAN MIGUELITO",
    "corregimiento": "RUFINA ALFARO",
    "urbanizacion": "VIA DOMINGO DIAZ, BRISAS DEL GOLF, CALLE 32 NORTE, CASA N0. L-55",
    "calle": None,
    "casa": None,
    "edificio": None,
    "apartamento": None,
    "id_empresa": 154521,
    "id_sucursal": 67436,
    "anio": 2007,
    "monto_estimado": 5000,
    "updated_at": "2021-03-08 15:36:54"
}

print("Probando normalización con JSON del usuario...")
normalized = normalizar_datos_empresa(user_json_item)

print("\nRESULTADO NORMALIZADO:")
for k, v in normalized.items():
    print(f"{k}: '{v}'")

print("\nVERIFICACIÓN:")
if normalized['numero_aviso'] == "8-237-715-2007-62950":
    print("SUCCESS: numero_aviso se extrajo correctamente.")
else:
    print(f"FAIL: numero_aviso incorrecto: '{normalized['numero_aviso']}'")

if normalized['numero_licencia']:
    print(f"SUCCESS: numero_licencia encontrado: '{normalized['numero_licencia']}'")
else:
    print("INFO: numero_licencia está vacío (esperado según JSON).")
