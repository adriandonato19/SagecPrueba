"""
Adaptadores para normalizar datos de la API externa (Actualizado para el nuevo JSON y campo sucursal).

$Reusable$
"""
from typing import Dict, List, Optional


def normalizar_datos_empresa(datos_api: Dict) -> Dict:
    """
    Normaliza los datos de la API de Panamá Emprende a formato interno.
    Soporta formato Mock antiguo y API Real nueva.
    """
    # Manejar el RUC que ya puede venir con guiones o separado del DV
    ruc_raw = str(datos_api.get('ruc', ''))
    dv = str(datos_api.get('dv', ''))
    
    if dv and dv not in ruc_raw:
        ruc_completo = f"{ruc_raw}-{dv}"
    else:
        ruc_completo = ruc_raw

    # Campos compatibles con ambas versiones (Mock y Real)
    razon_social = (datos_api.get('razon_social') or 
                    datos_api.get('razon_social_juridica') or 
                    datos_api.get('razon_social_natural') or '')
                    
    razon_comercial = datos_api.get('razon_comercial') or datos_api.get('nombreComercial', '')
    
    numero_aviso = datos_api.get('aviso_operacion') or datos_api.get('numero_aviso', '')
    
    estatus = datos_api.get('estado_sucursal') or datos_api.get('estado', '')
    
    capital = datos_api.get('capital_invertido') or datos_api.get('monto_estimado', 0.00)

    return {
        'ruc': ruc_raw,
        'dv': dv,
        'ruc_completo': ruc_completo,
        'razon_social': razon_social,
        'razon_comercial': razon_comercial,
        'numero_aviso': numero_aviso,
        'numero_licencia': datos_api.get('numero_licencia', ''),
        'representante_legal': datos_api.get('representante_legal', ''),
        'cedula_representante': datos_api.get('cedula_representante', ''), # Nuevo
        'fecha_inicio_operaciones': datos_api.get('fecha_inicio_operaciones', ''),
        'provincia': datos_api.get('provincia', ''),
        'distrito': datos_api.get('distrito', ''),
        'corregimiento': datos_api.get('corregimiento', ''),
        'urbanizacion': datos_api.get('urbanizacion', ''),
        'calle': datos_api.get('calle', ''),
        'casa': datos_api.get('casa', ''),
        'edificio': datos_api.get('edificio', ''),
        'apartamento': datos_api.get('apartamento', ''),
        'actividad_comercial': datos_api.get('actividad_comercial', ''),
        'actividades_comerciales_ciiu': datos_api.get('ciiu', ''),
        'capital_invertido': f"{float(capital):.2f}",
        'estatus': estatus,
        'sucursal': datos_api.get('sucursal', '000'),
        'tipo_apireal': True if 'nombreComercial' in datos_api else False # Flag interno
    }


def construir_ubicacion_completa(datos: Dict) -> str:
    """
    Construye la dirección completa concatenando campos de ubicación.
    """
    partes = []
    
    if datos.get('provincia'):
        partes.append(datos['provincia'])
    if datos.get('distrito'):
        partes.append(datos['distrito'])
    if datos.get('corregimiento'):
        partes.append(datos['corregimiento'])
    if datos.get('urbanizacion'):
        partes.append(f"Urb. {datos['urbanizacion']}")
    if datos.get('calle'):
        partes.append(f"Calle {datos['calle']}")
    if datos.get('casa'):
        partes.append(f"Casa {datos['casa']}")
    if datos.get('edificio'):
        partes.append(f"Edif. {datos['edificio']}")
    if datos.get('apartamento'):
        partes.append(f"Apto. {datos['apartamento']}")
    
    return ', '.join(filter(None, partes)) if partes else 'No especificada'


def normalizar_lista_avisos(avisos_api: List[Dict]) -> List[Dict]:
    """
    Normaliza una lista de avisos de operación.
    """
    normalized = []
    for aviso in avisos_api:
        # Reutilizamos la lógica principal para cada item
        item = normalizar_datos_empresa(aviso)
        # Campos extra específicos para lista
        item['fecha_inicio'] = item['fecha_inicio_operaciones']
        normalized.append(item)
    return normalized
