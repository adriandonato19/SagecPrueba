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
        modo = request.POST.get('modo', '')
        ruc_full = request.POST.get('ruc', '').strip()
        
        # Inferir modo selección si hay carrito con empresas pero modo no vino explícito
        seleccion_carrito_check = request.session.get('seleccion_tramite', [])
        if not modo and seleccion_carrito_check and not ruc_full:
            modo = 'seleccion'
            log_debug("DEBUG POST: Modo inferido como 'seleccion' por carrito existente.")
        # Limpiar el RUC si trae sucursal para la búsqueda técnica
        ruc = "-".join(ruc_full.split("-")[:3]) 

        tipo_documento = request.POST.get('tipo_documento', 'CERTIFICADO')
        destinatario = request.POST.get('destinatario', '').strip()
        proposito = request.POST.get('proposito', '').strip()
        fecha_solicitud_str = request.POST.get('fecha_solicitud', '').strip()
        pregunta_adicional = request.POST.get('pregunta_adicional', '').strip()
        
        resultado = None
        
        # LOGICA MULTI-EMPRESA
        if modo == 'seleccion':
            seleccion_carrito = request.session.get('seleccion_tramite', [])
            if not seleccion_carrito:
                messages.error(request, 'No hay empresas seleccionadas.')
                return redirect('integracion:buscador')
            
            # El resultado será directamente la lista de empresas
            # Nota: Esto cambia la estructura de empresa_snapshot de dict a list
            resultado = seleccion_carrito
            log_debug(f"DEBUG POST: Creando trámite MULTIPLE con {len(resultado)} empresas.")
            
        else:
            # LOGICA PREVIA (SINGLE)
            numero_aviso_seleccionado = request.POST.get('aviso', '').strip()
            
            # PRIMERO: Intentar buscar el aviso en sesión para obtener datos completos
            if avisos_session and numero_aviso_seleccionado:
                log_debug(f"DEBUG POST: Buscando aviso {numero_aviso_seleccionado} en sesión...")
                for aviso in avisos_session:
                    if str(aviso.get('numero_aviso')) == str(numero_aviso_seleccionado):
                        # Si no teníamos RUC del POST, extraerlo del aviso o del número de aviso
                        if not ruc:
                            ruc = aviso.get('ruc', '') or aviso.get('ruc_completo', '')
                            # Fallback: extraer RUC de numero_aviso (formato: RUC-AÑO-NUMERO-SUC)
                            if not ruc and numero_aviso_seleccionado:
                                parts = numero_aviso_seleccionado.split('-')
                                if len(parts) >= 3:
                                    ruc = '-'.join(parts[:3])
                            log_debug(f"DEBUG POST: RUC extraído del aviso: {ruc}")
                        
                        # Solo incluir el aviso seleccionado (no todos los del mismo RUC)
                        resultado = {
                            'detalle': aviso,
                            'avisos': [aviso]
                        }
                        log_debug(f"DEBUG POST: ENCONTRADO en sesión! {len(resultado['avisos'])} avisos vinculados.")
                        break
            else:
                log_debug("DEBUG POST: No se buscó en sesión (falta session o aviso id)")
            
            # Validar que tenemos RUC (después de intentar extraerlo)
            if not ruc and not resultado:
                messages.error(request, 'Debe proporcionar un RUC.')
                return redirect('integracion:buscador')
           
            if not resultado:
                log_debug("DEBUG POST: No se encontró resultado final.")
                messages.error(request, 'La sesión de búsqueda ha expirado o el aviso no coincide. Por favor busque la empresa nuevamente.')
                return redirect('integracion:buscador')
        
        # Parsear fecha de solicitud (soportar múltiples formatos)
        from datetime import datetime
        formatos = ['%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y']
        
        def parsear_fecha(fecha_str):
            if not fecha_str: return None
            for fmt in formatos:
                try:
                    return datetime.strptime(fecha_str, fmt).date()
                except ValueError:
                    continue
            return None

        fecha_solicitud = parsear_fecha(fecha_solicitud_str)
        fecha_oficio_entrante = parsear_fecha(request.POST.get('fecha_oficio_entrante', ''))
        fecha_recepcion = parsear_fecha(request.POST.get('fecha_recepcion', ''))
        
        # Datos del Oficio Entrante
        oficio_entrante = request.POST.get('oficio_entrante', '').strip()
        carpetilla = request.POST.get('carpetilla', '').strip()
        solicitante_externo = request.POST.get('solicitante_externo', '').strip()
        cargo_solicitante = request.POST.get('cargo_solicitante', '').strip()
        institucion_solicitante = request.POST.get('institucion_solicitante', '').strip()

        # Preparar snapshot con avisos
        if isinstance(resultado, list):
            # Modo Selección Múltiple: El snapshot es la lista completa
            snapshot = resultado
        else:
            # Modo Único (Compatibilidad): Es un dict con 'detalle' y 'avisos'
            snapshot = resultado['detalle'].copy()
            snapshot['avisos_relacionados'] = resultado['avisos']
        
        # Recopilar preguntas adicionales (lista general, no por empresa)
        datos_qa = []
        try:
            total_preguntas = int(request.POST.get('total_preguntas', '0'))
        except (ValueError, TypeError):
            total_preguntas = 0
        
        for i in range(1, total_preguntas + 1):
            pregunta_text = request.POST.get(f'pregunta_{i}', '').strip()
            if pregunta_text:
                datos_qa.append({
                    'pregunta': pregunta_text,
                    'respuesta': ''
                })
        
        # Retrocompatibilidad: si viene pregunta_adicional (campo viejo), agregarla también
        if pregunta_adicional and not datos_qa:
            datos_qa.append({
                'pregunta': pregunta_adicional,
                'respuesta': ''
            })
        
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
            fecha_solicitud=fecha_solicitud,
            # Nuevos campos
            oficio_entrante=oficio_entrante,
            carpetilla=carpetilla,
            fecha_oficio_entrante=fecha_oficio_entrante,
            fecha_recepcion=fecha_recepcion,
            solicitante_externo=solicitante_externo,
            cargo_solicitante=cargo_solicitante,
            institucion_solicitante=institucion_solicitante,
            
            pregunta_adicional=pregunta_adicional,
            datos_qa=datos_qa
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
    modo = request.GET.get('modo', '')
    ruc = request.GET.get('crear_tramite', '')
    aviso_id = request.GET.get('aviso', '')
    
    avisos_session = request.session.get('avisos_busqueda', [])
    seleccion_carrito = request.session.get('seleccion_tramite', [])
    
    empresa_detalle = None
    lista_empresas = []
    source = "NONE"
    
    # MODO SELECCIÓN MÚLTIPLE (CARRITO)
    if modo == 'seleccion' and seleccion_carrito:
        log_debug(f"DEBUG GET: Modo Selección Múltiple. {len(seleccion_carrito)} empresas.")
        lista_empresas = seleccion_carrito
        # Usar la primera como 'principal' para rellenar campos por defecto si es necesario,
        # o dejar empresa_detalle como None y manejar la lista en el template.
        empresa_detalle = seleccion_carrito[0] 
        source = "CARRITO"
    
    # 1. Intentar buscar en sesión por ID de aviso (Prioridad Máxima - Flujo Single)
    elif aviso_id and avisos_session:
        log_debug(f"DEBUG GET: Buscando aviso_id='{aviso_id}' en sesión...")
        for av in avisos_session:
             # log_debug(f"DEBUG GET: Comparando con {av.get('numero_aviso')}")
             if str(av.get('numero_aviso')) == str(aviso_id):
                 empresa_detalle = av
                 lista_empresas = [av]
                 source = "SESSION"
                 log_debug(f"DEBUG GET: MATCH en sesión! {av.get('razon_social')}")
                 break
    
    # 2. Fallback (si existe RUC pero no aviso específico en sesión)
    elif not empresa_detalle and ruc:
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
             
             lista_empresas = [empresa_detalle]
        log_debug(f"DEBUG GET: Resultado API Source={source}")

    if empresa_detalle or lista_empresas:
        log_debug(f"DEBUG GET: Empresa Final o Lista Cargada. Source={source}")
    else:
        log_debug("DEBUG GET: Empresa Final es NONE")
    
    # Si no teníamos RUC del GET pero sí encontramos empresa, extraerlo
    if not ruc and empresa_detalle:
        ruc = empresa_detalle.get('ruc', '') or empresa_detalle.get('ruc_completo', '')

    return render(request, 'tramites/crear.html', {
        'ruc': ruc,
        'aviso': aviso_id,
        'empresa': empresa_detalle, # Para compatibilidad hacia atrás
        'lista_empresas': lista_empresas, # Nueva variable para múltiples
        'modo': modo
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
    
    # Pre-enumerar preguntas QA para evitar dependencia de forloop.counter en templates
    datos_qa_enum = []
    if tramite.datos_qa and isinstance(tramite.datos_qa, list):
        for idx, item in enumerate(tramite.datos_qa):
            datos_qa_enum.append({
                'titulo': f'Pregunta {idx + 1}',
                'indice': str(idx),
                'pregunta': item.get('pregunta', ''),
                'respuesta': item.get('respuesta', ''),
            })
    
    return render(request, 'tramites/detalle.html', {
        'tramite': tramite,
        'datos_qa_enum': datos_qa_enum,
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
        
        # Guardar respuesta a pregunta adicional si existe
        respuesta_pregunta = request.POST.get('respuesta_pregunta', '').strip()
        if respuesta_pregunta and tramite.pregunta_adicional:
            tramite.respuesta_pregunta = respuesta_pregunta
            tramite.save(update_fields=['respuesta_pregunta'])
            
        # Guardar respuestas a preguntas múltiples (Lista)
        if tramite.datos_qa and isinstance(tramite.datos_qa, list):
            updated_qa = False
            for idx, item in enumerate(tramite.datos_qa):
                respuesta_key = f"respuesta_{idx}"
                respuesta = request.POST.get(respuesta_key, '').strip()
                if respuesta:
                    item['respuesta'] = respuesta
                    updated_qa = True
            
            if updated_qa:
                tramite.save(update_fields=['datos_qa'])
        
        tramite.aprobar(request.user)
        
        # Regenerar PDF con la respuesta incluida
        try:
            pdf_bytesio = generar_pdf_tramite(tramite)
            pdf_content = pdf_bytesio.read()
            
            temp_pdf_dir = Path(__file__).parent / 'temp_pdfs'
            temp_pdf_dir.mkdir(exist_ok=True)
            
            pdf_filename = f'tramite_{tramite.uuid}.pdf'
            pdf_path = temp_pdf_dir / pdf_filename
            
            with open(pdf_path, 'wb') as f:
                f.write(pdf_content)
            
            tramite.archivo_pdf.name = f'temp_pdfs/{pdf_filename}'
            tramite.save(update_fields=['archivo_pdf'])
            log_debug(f"DEBUG: PDF regenerado con respuesta para trámite {tramite.uuid}")
        except Exception as e:
            log_debug(f"ERROR: No se pudo regenerar PDF: {e}")
        
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
    # Validar que si es un trámite que requiere firma y no está firmado, se intente generar
    # if not tramite.archivo_pdf ... (Eliminado para permitir regeneración)
    pass
    
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
        # Intentar regenerar
        try:
            pdf_bytesio = generar_pdf_tramite(tramite)
            pdf_content = pdf_bytesio.read()
            
            temp_pdf_dir = Path(__file__).parent / 'temp_pdfs'
            temp_pdf_dir.mkdir(exist_ok=True)
            
            pdf_filename = f'tramite_{tramite.uuid}.pdf'
            pdf_path = temp_pdf_dir / pdf_filename
            
            with open(pdf_path, 'wb') as f:
                f.write(pdf_content)
            
            tramite.archivo_pdf.name = f'temp_pdfs/{pdf_filename}'
            tramite.save(update_fields=['archivo_pdf'])
        except Exception as e:
            return HttpResponse(f'<div class="p-4 text-red-600">Error al generar PDF: {str(e)}</div>', status=500)
    
    return render(request, 'tramites/partials/modal_vista_previa_pdf.html', {
        'tramite': tramite
    })
