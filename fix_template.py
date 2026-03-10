"""Script para corregir los tags multilinea en el template PDF."""
import os

path = r'c:\Users\Adrian Donato\Documents\SAGEC MICI\Sagec\tramites\templates\tramites\pdf\oficio_oficial.html'

with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

print("Contenido antes:")
print("Referencia encontrada:", "tramite.fecha_creacion|date" in content)
print("Saludo encontrado:", "extraer_nombre_destinatario" in content)

# Reemplazar la referencia (tag dividido en 2 lineas)
old_ref = '''MICI-DGCI-AL-N-N°-[{{ tramite.numero_referencia|default:"XXX" }}]-{{
                    tramite.fecha_creacion|date:"Y" }}'''
new_ref = '''MICI-DGCI-AL-N-N°-[{{ tramite.numero_referencia|default:"XXX" }}]-{{ tramite.fecha_creacion|date:"Y" }}'''

if old_ref in content:
    content = content.replace(old_ref, new_ref)
    print("✓ Referencia corregida")
else:
    print("⚠ Referencia ya corregida o patrón no encontrado")

# Reemplazar el saludo (tag dividido en 3 lineas)
old_saludo = '''<p>Respetado Sr. {% if tramite.destinatario %}{{
                    tramite.destinatario|extraer_nombre_destinatario|slice:":30" }}{% else %}Destinatario{% endif %}:
                </p>'''
new_saludo = '''<p>Respetado Sr. {% if tramite.destinatario %}{{ tramite.destinatario|extraer_nombre_destinatario|slice:":30" }}{% else %}Destinatario{% endif %}:</p>'''

if old_saludo in content:
    content = content.replace(old_saludo, new_saludo)
    print("✓ Saludo corregido")
else:
    print("⚠ Saludo ya corregido o patrón no encontrado")

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

print("\n¡Archivo guardado!")
