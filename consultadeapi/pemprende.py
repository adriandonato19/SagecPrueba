import requests

def consultar_api(busqueda):
    # Definimos la URL con el término de búsqueda formateado
    url = f'https://api.panamaemprende.gob.pa/api/consulta/multiple/{busqueda}'
    
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
            
            empresas = data_json.get('data', {}).get('data', [])
            
            if not empresas:
                print("No se encontraron resultados.")
            else:
                print(f"Se encontraron {len(empresas)} resultados en esta página:\n")
                for empresa in empresas:
                    nombre = empresa.get('nombreComercial') or empresa.get('razon_social_juridica')
                    id_empresa = empresa.get('id_empresa')
                    link_pdf = f"https://www.panamaemprende.gob.pa/Empresa/pdf/{id_empresa}"
                    
                    print(f"Empresa: {nombre}")
                    print(f"PDF: {link_pdf}")
                    print("-" * 30)
            
        else:
            print(f"Error en la consulta. Código de estado: {llamada.status_code}")
            print("Respuesta:", llamada.text) 
            
    except Exception as e:
        print(f"Ocurrió un error: {e}")

if __name__ == "__main__":
    # Prueba con cédula real
    termino = "8-237-715"
    consultar_api(termino)