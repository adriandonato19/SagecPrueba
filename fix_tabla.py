"""Script para corregir los tags multilinea en tabla_tramites.html"""
import os

path = r'c:\Users\Adrian Donato\Documents\SAGEC MICI\Sagec\tramites\templates\tramites\partials\tabla_tramites.html'

with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

print("Contenido actual (muestra):")
print(content[1500:1900])

# Buscar el patron multilinea del solicitante
old_pattern = '<div class="text-sm text-gray-900">{{\n                            tramite.solicitante.get_full_name|default:tramite.solicitante.username }}</div>'
new_pattern = '<div class="text-sm text-gray-900">{{ tramite.solicitante.get_full_name|default:tramite.solicitante.username }}</div>'

if old_pattern in content:
    content = content.replace(old_pattern, new_pattern)
    print("\n✓ Solicitante corregido (patron normal)")
else:
    # Intentar con CRLF
    old_crlf = '<div class="text-sm text-gray-900">{{\r\n                            tramite.solicitante.get_full_name|default:tramite.solicitante.username }}</div>'
    if old_crlf in content:
        content = content.replace(old_crlf, new_pattern)
        print("\n✓ Solicitante corregido (patron CRLF)")
    else:
        print("\n⚠ Patron no encontrado - puede que ya esté corregido")

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

print("\n¡Archivo guardado!")
