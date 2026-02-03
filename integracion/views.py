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
