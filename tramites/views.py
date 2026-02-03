from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.views.decorators.http import require_http_methods
from django.http import HttpResponse, Http404
from django.utils import timezone
from django.conf import settings
from pathlib import Path
import os
from .models import Tramite
from .services.generador_pdf import generar_pdf_tramite, calcular_hash_pdf
from identidad.decorators import require_rol
from identidad.models import UsuarioMICI
from integracion.services import buscar_empresa, log_debug
from auditoria.services import registrar_evento, obtener_ip_cliente
from auditoria.models import BitacoraEvento


@login_required
@require_rol(UsuarioMICI.TRABAJADOR, UsuarioMICI.DIRECTOR)
def bandeja_admin_view(request):
    """
    Bandeja de administración con tabs por estado.
    Filtros y paginación server-side con HTMX.
    """
    estado_filtro = request.GET.get('estado', '')
    busqueda = request.GET.get('q', '').strip()
    page = request.GET.get('page', 1)
    
    # Base queryset: todos los trámites
    queryset = Tramite.objects.all()
    
    # Filtro por estado
    if estado_filtro and estado_filtro != 'TODOS':
        queryset = queryset.filter(estado=estado_filtro)
    
    # Búsqueda
    if busqueda:
        queryset = queryset.filter(
            Q(numero_referencia__icontains=busqueda) |
            Q(origen_consulta__icontains=busqueda) |
            Q(solicitante__username__icontains=busqueda) |
            Q(solicitante__first_name__icontains=busqueda) |
            Q(solicitante__last_name__icontains=busqueda)
        )
    
    # Contadores por estado
    contadores = {
        'TODOS': Tramite.objects.count(),
        Tramite.BORRADOR: Tramite.objects.filter(estado=Tramite.BORRADOR).count(),
        Tramite.PENDIENTE: Tramite.objects.filter(estado=Tramite.PENDIENTE).count(),
        Tramite.APROBADO: Tramite.objects.filter(estado=Tramite.APROBADO).count(),
        Tramite.FIRMADO: Tramite.objects.filter(estado=Tramite.FIRMADO).count(),
        Tramite.RECHAZADO: Tramite.objects.filter(estado=Tramite.RECHAZADO).count(),
    }
    
    # Paginación
    paginator = Paginator(queryset, 10)
    tramites = paginator.get_page(page)
    
    # Tabs para la UI
    tabs = [
        {'label': 'Todos', 'url': '?estado=', 'count': contadores['TODOS'], 'active': not estado_filtro or estado_filtro == 'TODOS'},
        {'label': 'Pendientes', 'url': f'?estado={Tramite.PENDIENTE}', 'count': contadores[Tramite.PENDIENTE], 'active': estado_filtro == Tramite.PENDIENTE},
        {'label': 'Aprobados', 'url': f'?estado={Tramite.APROBADO}', 'count': contadores[Tramite.APROBADO], 'active': estado_filtro == Tramite.APROBADO},
        {'label': 'Firmados', 'url': f'?estado={Tramite.FIRMADO}', 'count': contadores[Tramite.FIRMADO], 'active': estado_filtro == Tramite.FIRMADO},
        {'label': 'Rechazados', 'url': f'?estado={Tramite.RECHAZADO}', 'count': contadores[Tramite.RECHAZADO], 'active': estado_filtro == Tramite.RECHAZADO},
    ]
    
    context = {
        'tramites': tramites,
        'tabs': tabs,
        'estado_filtro': estado_filtro,
        'busqueda': busqueda,
        'contadores': contadores,
    }
    
    # Si es petición HTMX, devolver solo la tabla
    if request.headers.get('HX-Request'):
        return render(request, 'tramites/partials/tabla_tramites.html', context)
    
    return render(request, 'tramites/bandeja_admin.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def crear_tramite_view(request):
    """Crear un nuevo trámite desde la búsqueda de empresa."""
    
    # === LOGGING DIAGNÓSTICO ===
    log_debug("="*60)
    log_debug(f"DEBUG: crear_tramite_view METHOD={request.method}")
    log_debug(f"DEBUG: GET params: {request.GET}")
    
    # Recuperar datos de sesión para diagnóstico
    avisos_session = request.session.get('avisos_busqueda', [])
    log_debug(f"DEBUG: Sesión contiene {len(avisos_session)} avisos.")
    if avisos_session:
        primer_aviso = avisos_session[0]
        log_debug(f"DEBUG: Primer aviso en sesión: {primer_aviso.get('razon_social')} RUC: {primer_aviso.get('ruc')}")
    else:
        log_debug("DEBUG: SESIÓN VACÍA o NO EXISTE 'avisos_busqueda'")
    log_debug("="*60)
    # ==========================

    if request.method == 'POST':
        ruc_full = request.POST.get('ruc', '').strip()
        # Limpiar el RUC si trae sucursal para la búsqueda técnica
        ruc = "-".join(ruc_full.split("-")[:3]) 

        tipo_documento = request.POST.get('tipo_documento', 'CERTIFICADO')
        destinatario = request.POST.get('destinatario', '').strip()
        proposito = request.POST.get('proposito', '').strip()
        fecha_solicitud_str = request.POST.get('fecha_solicitud', '').strip()
        
        if not ruc:
            messages.error(request, 'Debe proporcionar un RUC.')
            return redirect('integracion:buscador')
        
        # Validar campos requeridos para certificados
        if tipo_documento == 'CERTIFICADO':
            if not destinatario:
                messages.error(request, 'El destinatario es obligatorio para certificados.')
                return redirect('tramites:crear')
            if not proposito:
                messages.error(request, 'El propósito es obligatorio para certificados.')
                return redirect('tramites:crear')
        
        # PRIMERO: Intentar usar los datos de la sesión
        numero_aviso_seleccionado = request.POST.get('aviso', '').strip() or request.GET.get('aviso', '').strip()
        
        resultado = None
        
        if avisos_session and numero_aviso_seleccionado:
            log_debug(f"DEBUG POST: Buscando aviso {numero_aviso_seleccionado} en sesión...")
            # Buscar el aviso específico en los datos de la sesión
            for aviso in avisos_session:
                if str(aviso.get('numero_aviso')) == str(numero_aviso_seleccionado):
                    # Encontrar todos los avisos que pertenezcan al mismo RUC (para incluir sucursales)
                    ruc_obj = aviso.get('ruc')
                    avisos_relacionados = [a for a in avisos_session if a.get('ruc') == ruc_obj]
                    
                    resultado = {
                        'detalle': aviso,
                        'avisos': avisos_relacionados if avisos_relacionados else [aviso]
                    }
                    log_debug(f"DEBUG POST: ENCONTRADO en sesión! {len(resultado['avisos'])} avisos vinculados.")
                    break
        else:
            log_debug("DEBUG POST: No se buscó en sesión (falta session o aviso id)")
       
        # Si no encontramos en sesión, NO hacer búsqueda normal (fallback) para evitar datos erróneos
        if not resultado:
            log_debug("DEBUG POST: No encontrado en sesión. Fallback DESHABILITADO para prevenir Jaime Lee Chen.")
            # log_debug(f"DEBUG POST: Fallback API por RUC: {ruc}")
            # resultado = buscar_empresa(ruc)
            # ...
            messages.error(request, 'La sesión de búsqueda ha expirado o el aviso no coincide. Por favor busque la empresa nuevamente.')
            return redirect('integracion:buscador')
        
        if not resultado:
            log_debug("DEBUG POST: No se encontró resultado final.")
            messages.error(request, 'No se encontró información para el RUC proporcionado.')
            return redirect('integracion:buscador')
        
        # Parsear fecha de solicitud
        fecha_solicitud = None
        if fecha_solicitud_str:
            try:
                from datetime import datetime
                fecha_solicitud = datetime.strptime(fecha_solicitud_str, '%Y-%m-%d').date()
            except ValueError:
                pass
        
        # Preparar snapshot con avisos
        snapshot = resultado['detalle'].copy()
        snapshot['avisos_relacionados'] = resultado['avisos']
        
        # Crear trámite
        tramite = Tramite.objects.create(
            tipo_documento=tipo_documento,
            solicitante=request.user,
            empresa_snapshot=snapshot,
            origen_consulta=ruc,
            numero_referencia=f"{tipo_documento[:3]}-{timezone.now().strftime('%Y%m%d')}-{Tramite.objects.count() + 1}",
            estado=Tramite.BORRADOR,
            destinatario=destinatario,
            proposito=proposito,
            fecha_solicitud=fecha_solicitud
        )
        
        # Generar PDF inmediatamente al crear el trámite
        try:
            pdf_bytesio = generar_pdf_tramite(tramite)
            pdf_content = pdf_bytesio.read()
            
            # Crear carpeta temporal si no existe
            temp_pdf_dir = Path(__file__).parent / 'temp_pdfs'
            temp_pdf_dir.mkdir(exist_ok=True)
            
            # Guardar PDF en carpeta temporal
            pdf_filename = f'tramite_{tramite.uuid}.pdf'
            pdf_path = temp_pdf_dir / pdf_filename
            
            with open(pdf_path, 'wb') as f:
                f.write(pdf_content)
            
            # Guardar ruta en el modelo
            tramite.archivo_pdf.name = f'temp_pdfs/{pdf_filename}'
            tramite.save()
            
        except Exception as e:
            # Si falla la generación del PDF, continuar pero registrar el error
            print(f"ERROR PDF: {e}")
            messages.warning(request, f'Trámite creado pero hubo un problema al generar el PDF: {str(e)}')
        
        # Registrar evento de creación (el signal también lo registrará, pero aquí tenemos más contexto)
        ip_cliente = obtener_ip_cliente(request)
        registrar_evento(
            tipo_evento=BitacoraEvento.CREACION_TRAMITE,
            actor=request.user,
            ip_origen=ip_cliente,
            recurso=tramite,
            descripcion=f'Creación de {tramite.get_tipo_documento_display()} - RUC: {ruc}',
            metadata={'tipo_documento': tipo_documento, 'ruc': ruc}
        )
        
        messages.success(request, f'Trámite creado correctamente.')
        return redirect('tramites:detalle', id=tramite.uuid)
    
    # GET: mostrar formulario de creación
    # -----------------------------------
    ruc = request.GET.get('crear_tramite', '')
    aviso_id = request.GET.get('aviso', '')
    
    empresa_detalle = None
    source = "NONE"
    
    # 1. Intentar buscar en sesión por ID de aviso (Prioridad Máxima)
    if aviso_id and avisos_session:
        log_debug(f"DEBUG GET: Buscando aviso_id='{aviso_id}' en sesión...")
        for av in avisos_session:
             # log_debug(f"DEBUG GET: Comparando con {av.get('numero_aviso')}")
             if str(av.get('numero_aviso')) == str(aviso_id):
                 empresa_detalle = av
                 source = "SESSION"
                 log_debug(f"DEBUG GET: MATCH en sesión! {av.get('razon_social')}")
                 break
    
    # 2. Fallback: buscar por RUC en API si no estaba en sesión
    if not empresa_detalle and ruc:
        log_debug(f"DEBUG GET: Fallback API busqueda por RUC '{ruc}'...")
        res = buscar_empresa(ruc)
        if res:
             if aviso_id:
                 # Intentar encontrar el aviso específico
                 empresa_detalle = next((a for a in res['avisos'] if str(a.get('numero_aviso')) == str(aviso_id)), res['detalle'])
                 source = "API_RUC_FILTER"
             else:
                 empresa_detalle = res['detalle']
                 source = "API_RUC_DEFAULT"
        log_debug(f"DEBUG GET: Resultado API Source={source}")

    if empresa_detalle:
        log_debug(f"DEBUG GET: Empresa Final: {empresa_detalle.get('razon_social')} (Aviso: {empresa_detalle.get('numero_aviso')})")
    else:
        log_debug("DEBUG GET: Empresa Final es NONE")

    return render(request, 'tramites/crear.html', {
        'ruc': ruc,
        'aviso': aviso_id,
        'empresa': empresa_detalle,
    })


@login_required
def mis_certificados_view(request):
    """Lista de certificados del usuario actual."""
    certificados = Tramite.objects.filter(
        solicitante=request.user,
        tipo_documento='CERTIFICADO'
    ).order_by('-fecha_creacion')
    
    return render(request, 'tramites/mis_certificados.html', {
        'certificados': certificados
    })


@login_required
def mis_oficios_view(request):
    """Lista de oficios del usuario actual."""
    oficios = Tramite.objects.filter(
        solicitante=request.user,
        tipo_documento__in=['OFICIO', 'CERTIFICADO']
    ).order_by('-fecha_creacion')
    
    return render(request, 'tramites/mis_oficios.html', {
        'oficios': oficios
    })


@login_required
@require_http_methods(["GET", "POST"])
def detalle_view(request, id):
    """Vista de detalle de un trámite."""
    tramite = get_object_or_404(Tramite, uuid=id)
    
    # Verificar permisos: solo el solicitante, revisor o firmante pueden ver
    puede_ver = (
        tramite.solicitante == request.user or
        tramite.revisor == request.user or
        tramite.firmante == request.user or
        request.user.puede_aprobar
    )
    
    if not puede_ver:
        messages.error(request, 'No tiene permisos para ver este trámite.')
        raise Http404
    
    # Manejar POST (enviar trámite)
    if request.method == 'POST' and request.POST.get('accion') == 'enviar':
        if tramite.estado == Tramite.BORRADOR and tramite.solicitante == request.user:
            try:
                estado_anterior = tramite.estado
                tramite.enviar()
                
                # Registrar cambio de estado
                ip_cliente = obtener_ip_cliente(request)
                registrar_evento(
                    tipo_evento=BitacoraEvento.CAMBIO_ESTADO,
                    actor=request.user,
                    ip_origen=ip_cliente,
                    recurso=tramite,
                    descripcion=f'Cambio de estado: {estado_anterior} -> {tramite.estado}',
                    metadata={'estado_anterior': estado_anterior, 'estado_nuevo': tramite.estado}
                )
                
                messages.success(request, 'Trámite enviado para revisión correctamente.')
            except Exception as e:
                messages.error(request, str(e))
        else:
            messages.error(request, 'No puede enviar este trámite.')
        return redirect('tramites:detalle', id=tramite.uuid)
    
    return render(request, 'tramites/detalle.html', {
        'tramite': tramite
    })


@login_required
@require_rol(UsuarioMICI.TRABAJADOR, UsuarioMICI.DIRECTOR)
@require_http_methods(["POST"])
def aprobar_view(request, id):
    """Aprobar un trámite pendiente."""
    tramite = get_object_or_404(Tramite, uuid=id)
    
    if tramite.estado != Tramite.PENDIENTE:
        messages.error(request, f'El trámite no está en estado pendiente.')
        return redirect('tramites:detalle', id=tramite.uuid)
    
    try:
        estado_anterior = tramite.estado
        tramite.aprobar(request.user)
        
        # Registrar evento de aprobación
        ip_cliente = obtener_ip_cliente(request)
        registrar_evento(
            tipo_evento=BitacoraEvento.APROBACION,
            actor=request.user,
            ip_origen=ip_cliente,
            recurso=tramite,
            descripcion=f'Aprobación de trámite - Estado anterior: {estado_anterior}',
            metadata={'estado_anterior': estado_anterior, 'revisor': request.user.username}
        )
        
        messages.success(request, 'Trámite aprobado correctamente.')
    except Exception as e:
        messages.error(request, str(e))
    
    return redirect('tramites:detalle', id=tramite.uuid)


@login_required
@require_rol(UsuarioMICI.DIRECTOR)
@require_http_methods(["GET", "POST"])
def firmar_view(request, id):
    """Firmar un trámite aprobado: descargar PDF, firmar externamente y subirlo."""
    tramite = get_object_or_404(Tramite, uuid=id)
    
    if tramite.estado != Tramite.APROBADO:
        messages.error(request, f'El trámite debe estar aprobado para poder firmarlo.')
        return redirect('tramites:detalle', id=tramite.uuid)
    
    if request.method == 'POST':
        # Validar que se haya subido un archivo
        if 'archivo_pdf_firmado' not in request.FILES:
            messages.error(request, 'Debe subir el PDF firmado.')
            return render(request, 'tramites/firmar.html', {'tramite': tramite})
        
        archivo_subido = request.FILES['archivo_pdf_firmado']
        
        # Validar que sea PDF
        if not archivo_subido.name.lower().endswith('.pdf'):
            messages.error(request, 'El archivo debe ser un PDF (.pdf).')
            return render(request, 'tramites/firmar.html', {'tramite': tramite})
        
        # Validar tamaño (máximo 10MB)
        if archivo_subido.size > 10 * 1024 * 1024:
            messages.error(request, 'El archivo PDF no puede exceder 10MB.')
            return render(request, 'tramites/firmar.html', {'tramite': tramite})
        
        try:
            estado_anterior = tramite.estado
            
            # Leer contenido del PDF subido
            pdf_content = archivo_subido.read()
            
            # Calcular hash SHA-256 del PDF firmado
            hash_documento = calcular_hash_pdf(pdf_content)
            
            # Guardar PDF firmado en carpeta temporal
            temp_pdf_dir = Path(__file__).parent / 'temp_pdfs' / 'firmados'
            temp_pdf_dir.mkdir(parents=True, exist_ok=True)
            
            pdf_filename = f'tramite_{tramite.uuid}_firmado.pdf'
            pdf_path = temp_pdf_dir / pdf_filename
            
            with open(pdf_path, 'wb') as f:
                f.write(pdf_content)
            
            # Resetear el archivo para guardarlo en el modelo
            archivo_subido.seek(0)
            
            # Guardar en el modelo usando el FileField
            tramite.archivo_pdf_firmado.save(pdf_filename, archivo_subido, save=False)
            
            # Marcar como firmado con el hash (el archivo ya está guardado)
            tramite.marcar_firmado(request.user, hash_documento=hash_documento)
            
            # Registrar evento de firma
            ip_cliente = obtener_ip_cliente(request)
            registrar_evento(
                tipo_evento=BitacoraEvento.FIRMA,
                actor=request.user,
                ip_origen=ip_cliente,
                recurso=tramite,
                descripcion=f'Firma de documento - Estado anterior: {estado_anterior}',
                metadata={'estado_anterior': estado_anterior, 'hash': hash_documento, 'archivo': pdf_filename}
            )
            
            messages.success(request, 'PDF firmado subido correctamente. El trámite ha sido marcado como firmado.')
            return redirect('tramites:detalle', id=tramite.uuid)
        except Exception as e:
            messages.error(request, f'Error al procesar el PDF firmado: {str(e)}')
    
    return render(request, 'tramites/firmar.html', {
        'tramite': tramite
    })


@login_required
def descargar_view(request, id):
    """Descargar el PDF de un trámite firmado."""
    tramite = get_object_or_404(Tramite, uuid=id)
    
    # Verificar permisos
    puede_ver = (
        tramite.solicitante == request.user or
        tramite.revisor == request.user or
        tramite.firmante == request.user or
        request.user.puede_aprobar
    )
    
    if not puede_ver:
        messages.error(request, 'No tiene permisos para descargar este documento.')
        raise Http404
    
    # Permitir descarga si el PDF existe (se genera al crear el trámite)
    if not tramite.archivo_pdf or not tramite.archivo_pdf.name:
        messages.error(request, 'El PDF aún no está disponible.')
        return redirect('tramites:detalle', id=tramite.uuid)
    
    # Determinar qué PDF servir: firmado si existe, sino el original
    try:
        pdf_content = None
        pdf_filename = f'tramite_{tramite.uuid}.pdf'
        
        # Prioridad 1: PDF firmado si existe y el trámite está firmado
        if tramite.estado == Tramite.FIRMADO and tramite.archivo_pdf_firmado and tramite.archivo_pdf_firmado.name:
            pdf_path = Path(__file__).parent / 'temp_pdfs' / 'firmados' / f'tramite_{tramite.uuid}_firmado.pdf'
            if pdf_path.exists():
                with open(pdf_path, 'rb') as f:
                    pdf_content = f.read()
                pdf_filename = f'tramite_{tramite.uuid}_firmado.pdf'
        
        # Prioridad 2: PDF original si existe
        if not pdf_content and tramite.archivo_pdf and tramite.archivo_pdf.name:
            pdf_path = Path(__file__).parent / tramite.archivo_pdf.name
            if pdf_path.exists():
                with open(pdf_path, 'rb') as f:
                    pdf_content = f.read()
        
        # Prioridad 3: Generar PDF si no existe ninguno
        if not pdf_content:
            pdf_bytesio = generar_pdf_tramite(tramite)
            pdf_content = pdf_bytesio.read()
            
            # Guardar PDF generado en carpeta temporal
            temp_pdf_dir = Path(__file__).parent / 'temp_pdfs'
            temp_pdf_dir.mkdir(exist_ok=True)
            pdf_path = temp_pdf_dir / pdf_filename
            
            with open(pdf_path, 'wb') as f:
                f.write(pdf_content)
            
            # Actualizar modelo si no tenía archivo
            if not tramite.archivo_pdf or not tramite.archivo_pdf.name:
                tramite.archivo_pdf.name = f'temp_pdfs/{pdf_filename}'
                tramite.save()
        
        # Registrar evento de descarga
        ip_cliente = obtener_ip_cliente(request)
        registrar_evento(
            tipo_evento=BitacoraEvento.DESCARGA,
            actor=request.user,
            ip_origen=ip_cliente,
            recurso=tramite,
            descripcion=f'Descarga de PDF del trámite {tramite.numero_referencia or tramite.uuid}',
            metadata={'hash': tramite.hash_seguridad or 'N/A', 'tipo': 'firmado' if tramite.estado == Tramite.FIRMADO and tramite.archivo_pdf_firmado else 'original'}
        )
        
        # Determinar si es inline (vista previa) o attachment (descarga)
        inline = request.GET.get('inline', '0') == '1'
        content_disposition = 'inline' if inline else 'attachment'
        
        # Servir el PDF
        response = HttpResponse(pdf_content, content_type='application/pdf')
        response['Content-Disposition'] = f'{content_disposition}; filename="{pdf_filename}"'
        return response
    except Exception as e:
        messages.error(request, f'Error al generar el PDF: {str(e)}')
        return redirect('tramites:detalle', id=tramite.uuid)


@login_required
def vista_previa_pdf_hx(request, id):
    """Vista previa del PDF en un modal (HTMX)."""
    tramite = get_object_or_404(Tramite, uuid=id)
    
    # Verificar permisos
    puede_ver = (
        tramite.solicitante == request.user or
        tramite.revisor == request.user or
        tramite.firmante == request.user or
        request.user.puede_aprobar
    )
    
    if not puede_ver:
        return HttpResponse('<div class="p-4 text-red-600">No tiene permisos para ver este documento.</div>', status=403)
    
    # Verificar que exista algún PDF (original o firmado)
    tiene_pdf = (
        (tramite.archivo_pdf and tramite.archivo_pdf.name) or 
        (tramite.archivo_pdf_firmado and tramite.archivo_pdf_firmado.name)
    )
    
    if not tiene_pdf:
        return HttpResponse('<div class="p-4 text-yellow-600">El PDF aún no está disponible. Por favor, intente más tarde.</div>', status=400)
    
    return render(request, 'tramites/partials/modal_vista_previa_pdf.html', {
        'tramite': tramite
    })
