
import requests
import urllib.parse
import json
import urllib3

# Desactivar advertencias de SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

API_URL_BASE = 'https://api.panamaemprende.gob.pa/api/consulta/multiple'
API_USER = 'cert'
API_PASS = 'NlQpUjtTRlo+OTI8NnRQOV1ocjB+QVVDMS1CIm5nRnd5eTIhJVxtNyglPFtG'

termino = "ADRIAN JOSE DONATO"
termino_encoded = urllib.parse.quote(termino)
url = f"{API_URL_BASE}/{termino_encoded}"

print(f"Consultando DIRECTO: {url}")

headers = {
    'X-User': API_USER,
    'X-Password': API_PASS
}

try:
    response = requests.get(url, headers=headers, verify=False, timeout=20)
    print(f"Status Code: {response.status_code}")
    
    try:
        data = response.json()
        print("Respuesta JSON guardada en 'debug_api_response.json'")
        with open('debug_api_response.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        # Ver si hay data
        items = data.get('data', {}).get('data', [])
        print(f"\nItems encontrados: {len(items)}")
        if items:
            first = items[0]
            print("Claves del primer item:")
            print(list(first.keys()))
            print("\nValores relevantes:")
            print(f"RUC: {first.get('ruc')}")
            print(f"Aviso Operación (raw): {first.get('aviso_operacion')} (tipo: {type(first.get('aviso_operacion'))})")
            print(f"Número Aviso (raw): {first.get('numero_aviso')}")
            print(f"Licencia (raw): {first.get('numero_licencia')}")
    except:
        print("No es JSON válido o error al parsear.")
        print(response.text[:500])

except Exception as e:
    print(f"Error de conexión: {e}")
