from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse, Http404
from .services import buscar_empresa
from .mock_data import MOCK_EMPRESAS_API
from .adapters import normalizar_datos_empresa, construir_ubicacion_completa
from auditoria.services import registrar_evento, obtener_ip_cliente
from auditoria.models import BitacoraEvento


@login_required
def buscador_view(request):
    """Vista principal del buscador de empresas."""
    return render(request, 'integracion/buscador.html')


@login_required
@require_http_methods(["GET", "POST"])
def api_search_view(request):
    """
    Endpoint HTMX para búsqueda de empresas.
    Devuelve fragmento HTML con tabla de avisos.
    """
    query = request.GET.get('q', '').strip() or request.POST.get('q', '').strip()
    tipo_busqueda = request.GET.get('tipo', 'todos').strip() or request.POST.get('tipo', 'todos').strip()
    
    if not query:
        return render(request, 'integracion/resultados_vacios.html')
    
    resultado = buscar_empresa(query, tipo_busqueda)
    
    # Registrar evento de consulta
    ip_cliente = obtener_ip_cliente(request)
    registrar_evento(
        tipo_evento=BitacoraEvento.CONSULTA_API,
        actor=request.user,
        ip_origen=ip_cliente,
        descripcion=f'Consulta de empresa por {tipo_busqueda}: {query}',
        metadata={'query': query, 'tipo_busqueda': tipo_busqueda, 'encontrado': resultado is not None}
    )
    
    if not resultado:
        return render(request, 'integracion/resultados_no_encontrados.html', {
            'query': query
        })
    
    # Guardar los avisos en la sesión para poderlos recuperar al crear trámite
    # Esto evita tener que hacer otra búsqueda que podría dar resultados diferentes
    request.session['avisos_busqueda'] = resultado['avisos']
    request.session['detalle_busqueda'] = resultado['detalle']
    
    return render(request, 'integracion/resultados_empresa.html', {
        'empresa': resultado['detalle'],
        'avisos': resultado['avisos'],
        'query': query,
    })


@login_required
def detalle_empresa_hx(request, aviso):
    """
    Devuelve el contenido del modal para una empresa específica por aviso.
    Busca primero en la sesión del usuario.
    """
    # Buscar en sesión (ya están normalizados)
    avisos_session = request.session.get('avisos_busqueda', [])
    empresa = next((e for e in avisos_session if str(e.get('numero_aviso')) == str(aviso)), None)
    
    if not empresa:
        raise Http404("Empresa no encontrada")
        
    # Nota: Los datos en sesión ya vienen normalizados por el adaptador en la búsqueda
    
    return render(request, 'integracion/partials/modal_detalle.html', {
        'empresa': empresa
    })

@login_required
@require_http_methods(["POST"])
def agregar_al_carrito_hx(request, aviso):
    """Agrega una empresa (aviso) a la selección actual."""
    avisos_busqueda = request.session.get('avisos_busqueda', [])
    seleccion = request.session.get('seleccion_tramite', [])
    
    # Buscar el objeto completo en la búsqueda reciente
    candidato = next((e for e in avisos_busqueda if str(e.get('numero_aviso')) == str(aviso)), None)
    
    if candidato:
        # Evitar duplicados
        exists = any(str(s.get('numero_aviso')) == str(aviso) for s in seleccion)
        if not exists:
            # Encontrar avisos relacionados en la búsqueda actual (mismo RUC)
            # Esto es CRÍTICO porque al buscar otra empresa, avisos_busqueda cambiará.
            ruc_obj = candidato.get('ruc')
            avisos_relacionados = [a for a in avisos_busqueda if a.get('ruc') == ruc_obj]
            
            # Adjuntar al candidato
            candidato_copy = candidato.copy() # Copia superficial para no alterar session actual si fuera ref
            candidato_copy['avisos_relacionados'] = avisos_relacionados
            
            seleccion.append(candidato_copy)
            request.session['seleccion_tramite'] = seleccion
            request.session.modified = True
            
    return render(request, 'integracion/partials/carrito_status.html', {
        'seleccion': seleccion
    })

@login_required
@require_http_methods(["POST"])
def remover_del_carrito_hx(request, aviso):
    """Elimina una empresa de la selección."""
    seleccion = request.session.get('seleccion_tramite', [])
    seleccion = [s for s in seleccion if str(s.get('numero_aviso')) != str(aviso)]
    
    request.session['seleccion_tramite'] = seleccion
    request.session.modified = True
    
    return render(request, 'integracion/partials/carrito_status.html', {
        'seleccion': seleccion
    })

@login_required
def status_carrito_hx(request):
    """Renderiza el estado actual del carrito (ej. al recargar página)."""
    seleccion = request.session.get('seleccion_tramite', [])
    return render(request, 'integracion/partials/carrito_status.html', {
        'seleccion': seleccion
    })
