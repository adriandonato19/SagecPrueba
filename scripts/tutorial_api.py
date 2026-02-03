
"""
Script de Tutorial: Cómo consultar una API con Python
-----------------------------------------------------

Este script te enseñará lo básico para consultar una API usando la librería `requests`.
Usaremos una API pública de prueba llamada JSONPlaceholder.

Requisitos:
    Asegúrate de tener instalada la librería requests:
    pip install requests
"""

import requests
import json

def consultar_usuario_ejemplo():
    # 1. Definir la URL del endpoint (el punto de acceso de la API)
    # En este caso, buscaremos los datos del usuario con ID 1
    url = "https://jsonplaceholder.typicode.com/users/1"

    print(f"📡 Consultando API: {url} ...")

    try:
        # 2. Hacer la petición GET
        # GET se usa para PEDIR datos. (POST sería para ENVIAR datos)
        respuesta = requests.get(url)

        # 3. Verificar el Código de Estado (Status Code)
        # 200 significa "OK" (Éxito)
        # 404 significa "No Encontrado"
        # 500 significa "Error del Servidor"
        print(f"Estado de la respuesta: {respuesta.status_code}")

        if respuesta.status_code == 200:
            # 4. Convertir la respuesta a JSON (diccionario de Python)
            datos = respuesta.json()
            
            print("\n✅ Consulta Exitosa! Datos recibidos:")
            print("-" * 30)
            # Imprimimos el JSON bonito
            print(json.dumps(datos, indent=4))
            print("-" * 30)
            
            # Acceder a datos específicos
            print(f"Nombre: {datos['name']}")
            print(f"Email: {datos['email']}")
            print(f"Ciudad: {datos['address']['city']}")
            
        else:
            print(f"❌ Hubo un error. Código: {respuesta.status_code}")

    except Exception as e:
        print(f"⚠️ Error de conexión: {e}")

if __name__ == "__main__":
    consultar_usuario_ejemplo()
