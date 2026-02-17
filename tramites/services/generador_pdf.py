"""
Servicio para generar PDFs de trámites usando WeasyPrint.

$Reusable$
"""
from django.template.loader import render_to_string
from django.conf import settings
from django.urls import reverse
from weasyprint import HTML
from io import BytesIO
import hashlib
import qrcode
import base64
from datetime import datetime


def formatear_fecha_espanol(fecha):
    """
    Formatea una fecha al formato español completo.
    Ej: "3 de junio de 2025"
    
    $Reusable$
    """
    if not fecha:
        return ""
    
    meses = {
        1: "enero", 2: "febrero", 3: "marzo", 4: "abril",
        5: "mayo", 6: "junio", 7: "julio", 8: "agosto",
        9: "septiembre", 10: "octubre", 11: "noviembre", 12: "diciembre"
    }
    
    if isinstance(fecha, str):
        try:
            fecha = datetime.strptime(fecha, "%Y-%m-%d")
        except:
            return fecha
    
    return f"{fecha.day} de {meses[fecha.month]} de {fecha.year}"


def generar_qr_code(url_validacion):
    """
    Genera un código QR como imagen base64.
    
    Args:
        url_validacion: URL completa para validar el documento
    
    Returns:
        String con data URI de la imagen QR (base64)
    
    $Reusable$
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=2,
    )
    qr.add_data(url_validacion)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Convertir a base64
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    img_str = base64.b64encode(buffer.getvalue()).decode()
    
    return f"data:image/png;base64,{img_str}"


def generar_pdf_tramite(tramite):
    """
    Genera el PDF de un trámite usando WeasyPrint.
    Para certificados usa la plantilla oficial, para oficios usa la plantilla estándar.
    
    Args:
        tramite: Instancia de Tramite
    
    Returns:
        BytesIO con el contenido del PDF
    
    $Reusable$
    """
    # Obtener datos de empresa del snapshot (Soporte Dict o List)
    raw_snapshot = tramite.empresa_snapshot
    lista_empresas = []
    
    if isinstance(raw_snapshot, list):
        lista_empresas = raw_snapshot
    elif isinstance(raw_snapshot, dict):
        lista_empresas = [raw_snapshot]
    else:
        lista_empresas = []
        
    # Enriquecer datos (ubicacion)
    for emp in lista_empresas:
        if 'ubicacion_completa' not in emp:
            from integracion.adapters import construir_ubicacion_completa
            emp['ubicacion_completa'] = construir_ubicacion_completa(emp)
            
    # Empresa principal (para datos singulares)
    empresa_principal = lista_empresas[0] if lista_empresas else {}
    
    # Limpiar y deduplicar avisos dentro de cada empresa en lista_empresas
    # Esto es necesario para que el loop en el template por empresa no muestre duplicados
    lista_empresas_clean = []
    for emp in lista_empresas:
        # Copiar para no modificar el original si fuera mutable (aunque viene de JSON)
        emp_clean = emp.copy()
        raw_avisos = emp.get('avisos_relacionados', [])
        clean_avisos = []
        seen_navs = set()
        for a in raw_avisos:
            nav = a.get('numero_aviso', '')
            if nav and nav not in seen_navs:
                seen_navs.add(nav)
                clean_avisos.append(a)
            elif not nav:
                clean_avisos.append(a)
        emp_clean['avisos_relacionados'] = clean_avisos
        lista_empresas_clean.append(emp_clean)
    
    # Reemplazar la lista original con la limpia para el contexto
    lista_empresas = lista_empresas_clean

    # Recolectar todos los avisos de todas las empresas (sin duplicados)
    todos_avisos_raw = []
    for emp in lista_empresas:
        todos_avisos_raw.extend(emp.get('avisos_relacionados', []))
    
    # Deduplicar por numero_aviso
    seen_avisos = set()
    todos_avisos = []
    for aviso in todos_avisos_raw:
        nav = aviso.get('numero_aviso', '')
        if nav and nav not in seen_avisos:
            seen_avisos.add(nav)
            todos_avisos.append(aviso)
        elif not nav:
            todos_avisos.append(aviso)

    # Determinar qué plantilla usar
    # Unificamos para usar siempre la plantilla oficial (solicitud usuario)
    template_name = 'tramites/pdf/oficio_oficial.html'
    
    # Generar código QR para todos los documentos oficiales
    # URL de validación (en producción sería una URL pública)
    url_validacion = f"{settings.BASE_DIR}/validar/{tramite.uuid}"
    qr_code_data = generar_qr_code(url_validacion)
    
    # Formatear fechas en español
    fecha_emision_formateada = formatear_fecha_espanol(datetime.now())
    fecha_firma_formateada = formatear_fecha_espanol(tramite.fecha_firma) if tramite.fecha_firma else fecha_emision_formateada
    fecha_solicitud_formateada = formatear_fecha_espanol(tramite.fecha_solicitud) if tramite.fecha_solicitud else formatear_fecha_espanol(tramite.fecha_creacion)
    
    # Formatear fecha de inicio de operaciones de la empresa principal
    fecha_inicio_ops = empresa_principal.get('fecha_inicio_operaciones')
    fecha_inicio_ops_formateada = formatear_fecha_espanol(fecha_inicio_ops) if fecha_inicio_ops else ""
    
    # Rutas a imágenes oficiales
    # WeasyPrint compatible con rutas Windows file URI
    base_img_path = settings.BASE_DIR / 'static' / 'img'
    logo_path = (base_img_path / 'logo_oficial.png').as_uri()
    footer_path = (base_img_path / 'footer_certificado.png').as_uri()
    
    # Pre-computar valores que el auto-formatter rompe en el template
    anio_creacion = tramite.fecha_creacion.strftime('%Y') if tramite.fecha_creacion else ''
    ref_num = tramite.numero_referencia or 'XXX'
    referencia_completa = f"MICI-DGCI-AL-N-N°-[{ref_num}]-{anio_creacion}"
    
    # Extraer nombre para saludo
    destinatario = tramite.destinatario or 'Destinatario'
    # Simular el filtro extraer_nombre_destinatario: tomar la parte después de "Señor" u otra cortesía
    nombre_saludo = destinatario
    for prefijo in ['Señor ', 'Señora ', 'Sr. ', 'Sra. ', 'Licenciado ', 'Licenciada ']:
        if destinatario.upper().startswith(prefijo.upper()):
            nombre_saludo = destinatario[len(prefijo):]
            break
    nombre_saludo = nombre_saludo[:30]
    
    # Formatear fechas adicionales
    fecha_oficio_entrante_formateada = formatear_fecha_espanol(tramite.fecha_oficio_entrante) if tramite.fecha_oficio_entrante else ""
    fecha_recepcion_formateada = formatear_fecha_espanol(tramite.fecha_recepcion) if tramite.fecha_recepcion else ""
    
    context = {
        'tramite': tramite,
        'empresa': empresa_principal, # Compatibilidad
        'lista_empresas': lista_empresas, # Multi
        'avisos': todos_avisos,
        'qr_code_data': qr_code_data,
        'fecha_emision_formateada': fecha_emision_formateada,
        'fecha_firma_formateada': fecha_firma_formateada,
        'fecha_solicitud_formateada': fecha_solicitud_formateada,
        'fecha_inicio_ops_formateada': fecha_inicio_ops_formateada,
        # Nuevas fechas formatadas
        'fecha_oficio_entrante_formateada': fecha_oficio_entrante_formateada,
        'fecha_recepcion_formateada': fecha_recepcion_formateada,
        
        'logo_path': logo_path,
        'footer_path': footer_path,
        'pregunta_adicional': tramite.pregunta_adicional,
        'respuesta_pregunta': tramite.respuesta_pregunta,
        'datos_qa': tramite.datos_qa,
        'referencia_completa': referencia_completa,
        'saludo_nombre': nombre_saludo,
    }
    
    # Renderizar plantilla HTML
    html_content = render_to_string(template_name, context)
    
    # Convertir HTML a PDF
    # Usar base_url para que WeasyPrint pueda cargar imágenes locales
    pdf_file = BytesIO()
    HTML(
        string=html_content,
        base_url=str(settings.BASE_DIR)
    ).write_pdf(pdf_file)
    pdf_file.seek(0)
    
    return pdf_file


def calcular_hash_pdf(pdf_bytes):
    """
    Calcula el hash SHA-256 de un PDF.
    
    Args:
        pdf_bytes: Bytes del archivo PDF
    
    Returns:
        String hexadecimal del hash SHA-256
    
    $Reusable$
    """
    return hashlib.sha256(pdf_bytes).hexdigest()
