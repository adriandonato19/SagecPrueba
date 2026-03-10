import requests
import urllib.parse
import json

def consultar_api(busqueda):
    # Encode the search term to handle spaces and special characters
    busqueda_encoded = urllib.parse.quote(busqueda)
    
    # Definimos la URL con el término de búsqueda formateado
    url = f'https://api.panamaemprende.gob.pa/api/consulta/multiple/{busqueda_encoded}'
    
    # Definimos los headers para la autenticación
    headers = {
        'X-User': 'cert',
        'X-Password': 'NlQpUjtTRlo+OTI8NnRQOV1ocjB+QVVDMS1CIm5nRnd5eTIhJVxtNyglPFtG'
    }

    try:
        print(f"Consultando {url}...")
        # Pasamos los headers en la petición
        llamada = requests.get(url, headers=headers)
        
        if llamada.status_code == 200:
            data_json = llamada.json()
            print("\nConsulta exitosa")
            
            # Guardar el raw json por si acaso
            with open('resultado_roger.json', 'w', encoding='utf-8') as f:
                json.dump(data_json, f, indent=4, ensure_ascii=False)
            
            empresas = data_json.get('data', {}).get('data', [])
            
            if not empresas:
                print("No se encontraron resultados.")
            else:
                print(f"Se encontraron {len(empresas)} resultados:\n")
                for empresa in empresas:
                    nombre = empresa.get('nombreComercial') or empresa.get('razon_social_juridica')
                    id_empresa = empresa.get('id_empresa')
                    ruc = empresa.get('ruc')
                    
                    print(f"Empresa: {nombre}")
                    print(f"RUC: {ruc}")
                    print(f"ID: {id_empresa}")
                    print(f"PDF: https://www.panamaemprende.gob.pa/Empresa/pdf/{id_empresa}")
                    print("-" * 30)
                return True # Indicate success
            
        else:
            print(f"Error en la consulta. Código de estado: {llamada.status_code}")
            print("Respuesta:", llamada.text) 
            
    except Exception as e:
        print(f"Ocurrió un error: {e}")
    
    return False

if __name__ == "__main__":
    # "PEREZ" funcionó como prueba de control, confirmando que la búsqueda por nombre funciona.
    # Sin embargo, "Roger madriñan" no arroja resultados en ninguna de estas variantes.
    variaciones = [
        "Gabriel Carrizo",
        "GABRIEL CARRIZO",
        "Gabriel Jose Carrizo",
        "GABRIEL JOSE CARRIZO",
        "Jose Gabriel Carrizo",
        "JOSE GABRIEL CARRIZO",
        "Jose Carrizo",
        "JOSE CARRIZO",
        "CARRIZO"
    ]
    
    for termino in variaciones:
        print(f"\n---> Probando con: '{termino}'")
        if consultar_api(termino):
            print(f"¡ÉXITO con '{termino}'!")
            break

