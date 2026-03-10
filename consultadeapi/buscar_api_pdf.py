import requests

# Probamos diferentes endpoints de API para el PDF
id_empresa = 154521

urls_posibles = [
    f"https://api.panamaemprende.gob.pa/api/empresa/pdf/{id_empresa}",
    f"https://api.panamaemprende.gob.pa/api/consulta/pdf/{id_empresa}",
    f"https://api.panamaemprende.gob.pa/Empresa/pdf/{id_empresa}",
    f"https://api.panamaemprende.gob.pa/api/Empresa/pdf/{id_empresa}",
]

headers = {
    'X-User': 'cert',
    'X-Password': 'NlQpUjtTRlo+OTI8NnRQOV1ocjB+QVVDMS1CIm5nRnd5eTIhJVxtNyglPFtG'
}

for url in urls_posibles:
    print(f"\nProbando: {url}")
    try:
        response = requests.get(url, headers=headers, timeout=10)
        print(f"  Status: {response.status_code}")
        print(f"  Content-Type: {response.headers.get('Content-Type')}")
        print(f"  Tamaño: {len(response.content)} bytes")
        
        if response.content[:4] == b'%PDF':
            print("  ¡ES UN PDF!")
            with open(f'pdf_{id_empresa}.pdf', 'wb') as f:
                f.write(response.content)
            print(f"  Guardado como pdf_{id_empresa}.pdf")
            break
    except Exception as e:
        print(f"  Error: {e}")
