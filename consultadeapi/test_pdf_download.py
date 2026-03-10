import requests

# Probamos descargar uno de los PDFs
url_pdf = "https://www.panamaemprende.gob.pa/Empresa/pdf/154521"

# Headers de autenticación (los mismos de la API)
headers = {
    'X-User': 'cert',
    'X-Password': 'NlQpUjtTRlo+OTI8NnRQOV1ocjB+QVVDMS1CIm5nRnd5eTIhJVxtNyglPFtG'
}

print(f"Intentando descargar: {url_pdf}")

# Probamos CON los headers de autenticación
response = requests.get(url_pdf, headers=headers)
print(f"Status code: {response.status_code}")
print(f"Content-Type: {response.headers.get('Content-Type')}")
print(f"Tamaño respuesta: {len(response.content)} bytes")

# Si es PDF, los primeros bytes serán "%PDF"
primeros_bytes = response.content[:20]
print(f"\nPrimeros bytes: {primeros_bytes}")

if primeros_bytes.startswith(b'%PDF'):
    with open('aviso_operacion.pdf', 'wb') as f:
        f.write(response.content)
    print("\n¡PDF descargado exitosamente como 'aviso_operacion.pdf'!")
else:
    print("\nNo es un PDF. Guardando respuesta para análisis...")
    with open('respuesta_pdf.html', 'wb') as f:
        f.write(response.content)
