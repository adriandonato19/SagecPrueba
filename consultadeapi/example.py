import requests

def consultar_api():
    url = 'https://jsonplaceholder.typicode.com/todos/1'
    try:
        # Realizamos la petición GET
        print(f"Consultando {url}...")
        response = requests.get(url)
        
        # Verificamos el código de estado HTTP (200 = OK)
        if response.status_code == 200:
            data = response.json() # Parseamos el JSON recibido
            print("\n¡Consulta exitosa!")
            print("Datos recibidos:")
            print(data)
        else:
            print(f"Error en la consulta. Código de estado: {response.status_code}")
            
    except Exception as e:
        print(f"Ocurrió un error: {e}")

if __name__ == "__main__":
    consultar_api()
