"""
Servicio de integración con API externa (mock por ahora).

$Reusable$
"""
import requests
from django.conf import settings
from typing import Optional, Dict
from .mock_data import buscar_por_ruc
from .adapters import normalizar_datos_empresa, construir_ubicacion_completa, normalizar_lista_avisos


import urllib.parse
import datetime

def log_debug(msg):
    try:
        with open('search_debug.log', 'a', encoding='utf-8') as f:
            ts = datetime.datetime.now().isoformat()
            f.write(f"[{ts}] {msg}\n")
    except:
        pass

def buscar_empresa_api_externa(query: str, tipo_busqueda: str) -> Optional[Dict]:
    """
    Realiza la petición HTTP a la API externa de Panamá Emprende.
    Si la búsqueda exacta falla, intenta buscar por palabras clave (apellidos)
    y filtra los resultados localmente.
    """
    if not settings.API_PANAMA_EMPRENDE_USER:
        return None

    def consultar_api_raw(termino):
        """Helper para hacer la consulta raw a la API"""
        try:
            termino_upper = termino.upper()
            termino_encoded = urllib.parse.quote(termino_upper)
            base_url = settings.API_PANAMA_EMPRENDE_URL.rstrip('/')
            url = f"{base_url}/{termino_encoded}"
            
            headers = {
                'X-User': settings.API_PANAMA_EMPRENDE_USER,
                'X-Password': settings.API_PANAMA_EMPRENDE_PASSWORD
            }

            print(f"Consultando API Externa: {url}")
            response = requests.get(url, headers=headers, timeout=(10, 30))
            
            if response.status_code != 200:
                print(f"Error API: {response.status_code}")
                return []
                
            data = response.json()
            return data.get('data', {}).get('data', [])
        except Exception as e:
            print(f"Excepción en consulta API: {str(e)}")
            return []

    # 1. Intentar búsqueda exacta primero
    empresas = consultar_api_raw(query)
    
    # 2. Intentar búsqueda con Wildcards (reemplazar espacios por %)
    # Esto permite encontrar "ADRIAN DONATO" como "ADRIAN%DONATO" (matching "ADRIAN JOSE DONATO")
    if not empresas and ' ' in query.strip():
        query_wildcard = query.strip().replace(' ', '%')
        print(f"Búsqueda exacta falló. Intentando con wildcard: '{query_wildcard}'")
        log_debug(f"DEBUG - Wildcard Search: '{query_wildcard}'")
        empresas = consultar_api_raw(query_wildcard)

    # 3. Estrategia de búsqueda inteligente (Smart Search) si falla todo lo anterior
    if not empresas and ' ' in query.strip():
        palabras = [p for p in query.strip().upper().split() if len(p) > 2] # Ignorar palabras cortas
        
        if palabras:
            # Estrategia Iterativa: Probar con cada palabra clave disponible (ej: Apellido, luego Nombre)
            # Esto ayuda cuando una palabra devuelve muchos resultados y trunca la lista de la API
            
            empresas_encontradas_total = []
            
            # Invertimos para probar apellidos primero (usualmente más únicos que nombres)
            for palabra_clave in reversed(palabras):
                print(f"Búsqueda exacta falló. Intentando Smart Search con: '{palabra_clave}'")
                log_debug(f"DEBUG - Smart Search Key: '{palabra_clave}'")
                
                candidatos = consultar_api_raw(palabra_clave)
                log_debug(f"DEBUG - Candidatos encontrados para '{palabra_clave}': {len(candidatos)}")
                
                query_parts = query.upper().split()
                
                match_count_local = 0
                for emp in candidatos:
                    texto_completo = (
                        str(emp.get('nombreComercial', '')) + " " +
                        str(emp.get('razon_comercial', '')) + " " + 
                        str(emp.get('razon_social', '')) + " " +
                        str(emp.get('representante_legal', '')) + " " +
                        str(emp.get('cedula_representante', ''))
                    ).upper()
                    
                    # Calcular puntaje de coincidencia
                    matches = [part in texto_completo for part in query_parts]
                    score = sum(matches)
                    total_parts = len(query_parts)
                    
                    # Lógica de Aceptación:
                    # 1. Match Perfecto (todas las palabras)
                    # 2. Match Parcial Alto (más de 1 palabra y falló solo 1 o match > 60%)
                    #    Ej: "FOAM CLEAN SERVICE" (3) -> "FOAM CLEAN" (2) -> 2/3 = 66% -> OK
                    
                    es_perfecto = (score == total_parts)
                    es_parcial_valido = (total_parts > 1 and score >= total_parts - 1)
                    
                    should_add = False
                    if es_perfecto:
                        should_add = True
                    elif es_parcial_valido:
                        # Solo aceptar parciales si NO tenemos perfectos previos (Opcional, pero aquí acumulamos todo y luego ordenamos)
                        should_add = True
                    
                    if should_add:
                        # Evitar duplicados
                        id_empresa = emp.get('aviso_operacion') or emp.get('numero_aviso')
                        # Check duplicado en lista total
                        duplicado = any((e['data'].get('aviso_operacion') or e['data'].get('numero_aviso')) == id_empresa for e in empresas_encontradas_total)
                        
                        if not duplicado:
                            empresas_encontradas_total.append({
                                'data': emp,
                                'score': score,
                                'perfect': es_perfecto
                            })
                            match_count_local += 1
                
                if match_count_local > 0:
                    log_debug(f"DEBUG - ¡Encontrados {match_count_local} candidatos (Score >= {len(query_parts)-1}) con '{palabra_clave}'!")

            # Post-procesamiento: Ordenar y limpiar
            # Prioridad: Perfectos primero, luego por score descendente
            if empresas_encontradas_total:
                empresas_encontradas_total.sort(key=lambda x: (x['perfect'], x['score']), reverse=True)
                empresas = [item['data'] for item in empresas_encontradas_total]
                log_debug(f"Filtrado inteligente FINAL: {len(empresas)} coincidencia(s) totales (Mejor Score: {empresas_encontradas_total[0]['score']}/{len(query_parts)})")
            else:
                empresas = []

    if not empresas:
        return None
        
    return {
        'detalle': empresas[0],
        'avisos': empresas
    }


def buscar_empresa(query: str, tipo_busqueda: str = 'todos') -> Optional[Dict]:
    """
    Busca una empresa por RUC, cédula, razón social, nombre o número de aviso.
    
    Args:
        query: Término a buscar
        tipo_busqueda: 'ruc', 'cedula', 'razon_social', 'nombre', 'aviso' o 'todos'
    
    Returns:
        Diccionario con 'detalle' y 'avisos' o None si no se encuentra
    
    $Reusable$
    """
    # Verificar flag de configuración
    usar_mock = getattr(settings, 'USE_MOCK_API', True)
    
    if usar_mock:
        resultado = buscar_por_ruc(query, tipo_busqueda)
    else:
        resultado = buscar_empresa_api_externa(query, tipo_busqueda)
        # ELIMINADO FALLBACK A MOCK POR SOLICITUD DEL USUARIO
        # if not resultado:
        #     print("API Real sin resultados, buscando en Mock Data...")
        #     resultado = buscar_por_ruc(query, tipo_busqueda)
    
    if resultado:
        # Normalizar datos usando adapters
        detalle_normalizado = normalizar_datos_empresa(resultado['detalle'])
        detalle_normalizado['ubicacion_completa'] = construir_ubicacion_completa(detalle_normalizado)
        
        avisos_normalizados = normalizar_lista_avisos(resultado['avisos'])
        
        return {
            'detalle': detalle_normalizado,
            'avisos': avisos_normalizados,
        }
    
    return None

