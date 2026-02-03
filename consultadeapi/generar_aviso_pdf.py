import requests
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch, cm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os

# ============== CONFIGURACIÓN ==============
HEADERS = {
    'X-User': 'cert',
    'X-Password': 'NlQpUjtTRlo+OTI8NnRQOV1ocjB+QVVDMS1CIm5nRnd5eTIhJVxtNyglPFtG'
}

API_URL = "https://api.panamaemprende.gob.pa/api/consulta/multiple/"

# Colores del documento oficial
AZUL_HEADER = colors.HexColor('#003366')  # Azul oscuro del encabezado
AZUL_TITULO = colors.HexColor('#1a3a6e')  # Azul del título
AZUL_SECCION = colors.HexColor('#2c5282')  # Azul de las secciones
GRIS_FONDO = colors.HexColor('#f0f4f8')   # Gris claro de fondo

# ============== FUNCIONES ==============

def consultar_empresa(termino_busqueda):
    """Consulta la API y retorna la lista de empresas encontradas"""
    url = f"{API_URL}{termino_busqueda}"
    response = requests.get(url, headers=HEADERS)
    
    if response.status_code == 200:
        data = response.json()
        return data.get('data', {}).get('data', [])
    else:
        print(f"Error en consulta: {response.status_code}")
        return []

def generar_pdf_oficial(empresa, output_folder="pdfs_oficiales"):
    """Genera un PDF con diseño idéntico al oficial de Panamá Emprende"""
    
    # Crear carpeta de salida si no existe
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    
    # Extraer datos
    numero_aviso = empresa.get('numero_aviso', 'N/A')
    nombre_comercial = empresa.get('nombreComercial', 'N/A')
    razon_social = empresa.get('razon_social_juridica') or empresa.get('razon_social_natural') or 'N/A'
    ruc = empresa.get('ruc', '')
    cedula_rep = empresa.get('cedula_representante', 'N/A')
    representante = empresa.get('representante_legal', 'N/A')
    estado = empresa.get('estado', 'N/A')
    tipo = empresa.get('tipo', 'N/A')
    fecha_inicio = empresa.get('fecha_inicio_operaciones', 'N/A')
    provincia = empresa.get('provincia', 'N/A')
    distrito = empresa.get('distrito', 'N/A')
    corregimiento = empresa.get('corregimiento') or ''
    urbanizacion = empresa.get('urbanizacion') or ''
    calle = empresa.get('calle') or ''
    casa = empresa.get('casa') or ''
    edificio = empresa.get('edificio') or ''
    apartamento = empresa.get('apartamento') or ''
    monto = empresa.get('monto_estimado', 0)
    
    # Nombre del archivo
    nombre_limpio = nombre_comercial.replace(' ', '_').replace('/', '_').replace(',', '')[:25]
    nombre_archivo = f"{nombre_limpio}_{numero_aviso.split('-')[0]}.pdf"
    ruta_pdf = os.path.join(output_folder, nombre_archivo)
    
    # Crear documento
    doc = SimpleDocTemplate(ruta_pdf, pagesize=letter,
                            rightMargin=0.5*inch, leftMargin=0.5*inch,
                            topMargin=0.3*inch, bottomMargin=0.3*inch)
    
    # Estilos
    styles = getSampleStyleSheet()
    
    # Estilos personalizados
    header_style = ParagraphStyle(
        'Header',
        parent=styles['Normal'],
        fontSize=10,
        alignment=TA_CENTER,
        textColor=colors.white,
        fontName='Helvetica-Bold',
        leading=12
    )
    
    title_style = ParagraphStyle(
        'Title',
        parent=styles['Normal'],
        fontSize=18,
        alignment=TA_CENTER,
        textColor=AZUL_TITULO,
        fontName='Helvetica-Bold',
        spaceAfter=10
    )
    
    section_header_style = ParagraphStyle(
        'SectionHeader',
        parent=styles['Normal'],
        fontSize=10,
        alignment=TA_CENTER,
        textColor=colors.white,
        fontName='Helvetica-Bold',
        leading=14
    )
    
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=9,
        alignment=TA_JUSTIFY,
        leading=12,
        spaceBefore=2,
        spaceAfter=2
    )
    
    bold_style = ParagraphStyle(
        'Bold',
        parent=styles['Normal'],
        fontSize=9,
        fontName='Helvetica-Bold',
        leading=12
    )
    
    small_style = ParagraphStyle(
        'Small',
        parent=styles['Normal'],
        fontSize=8,
        alignment=TA_JUSTIFY,
        leading=10
    )
    
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=8,
        alignment=TA_CENTER,
        leading=10
    )
    
    # Contenido
    story = []
    
    # ============ ENCABEZADO AZUL ============
    header_data = [[
        Paragraph("""
        <b>GOBIERNO NACIONAL</b><br/>
        <font size="8">★ CON PASO FIRME ★</font><br/><br/>
        <b>MINISTERIO DE<br/>COMERCIO E INDUSTRIAS</b><br/>
        <font size="7">Panamá Emprende</font>
        """, header_style)
    ]]
    
    header_table = Table(header_data, colWidths=[7.5*inch])
    header_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), AZUL_HEADER),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 0.15*inch))
    
    # ============ TÍTULO ============
    story.append(Paragraph("<u><b>AVISO DE OPERACIÓN</b></u>", title_style))
    story.append(Spacer(1, 0.1*inch))
    
    # Subtítulo
    sub_data = [[
        Paragraph("REPÚBLICA DE PANAMÁ<br/>MINISTERIO DE COMERCIO E INDUSTRIAS<br/>DIRECCIÓN GENERAL DE COMERCIO INTERIOR", 
                 ParagraphStyle('Sub', fontSize=8, alignment=TA_CENTER, leading=10))
    ]]
    sub_table = Table(sub_data, colWidths=[7.5*inch])
    sub_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), GRIS_FONDO),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.grey),
    ]))
    story.append(sub_table)
    story.append(Spacer(1, 0.1*inch))
    
    # ============ AVISO Y EXPEDIDO ============
    aviso_expedido = [
        [
            Paragraph("<b>Aviso de Operación N°</b>", section_header_style),
            Paragraph("<b>Expedido a favor de</b>", section_header_style)
        ],
        [
            Paragraph(f"{numero_aviso}<br/>{representante}<br/><br/><b>Capital Invertido</b><br/>B/.{monto:,.2f}", normal_style),
            Paragraph(f"{representante}<br/><br/>{cedula_rep} DV0", normal_style)
        ]
    ]
    
    aviso_table = Table(aviso_expedido, colWidths=[3.75*inch, 3.75*inch])
    aviso_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), AZUL_SECCION),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.grey),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(aviso_table)
    story.append(Spacer(1, 0.1*inch))
    
    # ============ NOMBRE COMERCIAL ============
    nombre_data = [
        [Paragraph(f"<b>{nombre_comercial}</b>", 
                  ParagraphStyle('NombreComercial', fontSize=14, alignment=TA_CENTER, fontName='Helvetica-Bold'))]
    ]
    nombre_table = Table(nombre_data, colWidths=[7.5*inch])
    nombre_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), GRIS_FONDO),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.grey),
    ]))
    story.append(nombre_table)
    story.append(Spacer(1, 0.1*inch))
    
    # ============ DECLARACIÓN ============
    # Construir dirección
    direccion_parts = []
    if urbanizacion:
        direccion_parts.append(f"Urbanización {urbanizacion}")
    if edificio:
        direccion_parts.append(f"edificio: {edificio}")
    if apartamento:
        direccion_parts.append(f"departamento: {apartamento}")
    
    direccion_str = ", ".join(direccion_parts) if direccion_parts else "N/A"
    
    declaracion = f"""Yo, <b>{representante}</b>, con cédula de identidad personal <b>{cedula_rep}</b>, nacionalidad Panameño, con domicilio en Provincia de 
<b>{provincia}</b> Distrito de <b>{distrito}</b>, Corregimiento <b>{corregimiento or 'N/A'}</b>, {direccion_str}."""
    
    story.append(Paragraph(declaracion, normal_style))
    story.append(Spacer(1, 0.05*inch))
    
    # Declaro lo siguiente
    story.append(Paragraph("<b>Declaro lo siguiente:</b>", bold_style))
    
    ubicacion_negocio = f"""El establecimiento denominado <b>{nombre_comercial}</b>, está ubicado en la Provincia de <b>{provincia}</b>, Distrito de <b>{distrito}</b>, Corregimiento de <b>{corregimiento or 'N/A'}</b>, Calle <b>{calle or '--'}</b>, casa: <b>{casa or '--'}</b>, Urbanización <b>{urbanizacion or '--'}</b>, Inicio de operaciones: <b>{fecha_inicio}</b>"""
    
    story.append(Paragraph(ubicacion_negocio, normal_style))
    story.append(Spacer(1, 0.05*inch))
    
    # Actividades (placeholder ya que la API no proporciona este dato)
    story.append(Paragraph("<b>Se dedicará a las actividades de:</b>", bold_style))
    story.append(Paragraph("<i>(Información de actividades comerciales según registro)</i>", small_style))
    story.append(Spacer(1, 0.1*inch))
    
    # ============ FIRMAS ============
    firma_data = [
        [
            Paragraph(f"{representante}<br/>C.I.P. {cedula_rep}<br/><b>Firma del Declarante (Tramitador)</b>", footer_style),
            Paragraph(f"{representante}<br/>C.I.P. {cedula_rep}<br/><b>Firma del Dueño del Negocio</b>", footer_style)
        ]
    ]
    
    firma_table = Table(firma_data, colWidths=[3.75*inch, 3.75*inch])
    firma_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 20),
        ('LINEABOVE', (0, 0), (0, 0), 0.5, colors.black),
        ('LINEABOVE', (1, 0), (1, 0), 0.5, colors.black),
    ]))
    story.append(Spacer(1, 0.3*inch))
    story.append(firma_table)
    
    # ============ CLÁUSULA DE RESPONSABILIDAD ============
    story.append(Spacer(1, 0.15*inch))
    
    clausula_header = [[Paragraph("<b>Cláusula de Responsabilidad:</b>", section_header_style)]]
    clausula_table = Table(clausula_header, colWidths=[7.5*inch])
    clausula_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), AZUL_SECCION),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    story.append(clausula_table)
    
    clausula_texto = """En caso de que este Aviso de Operación haya sido procesado por una persona distinta al Representante Legal o administrador del establecimiento comercial, dicha persona será solidariamente responsable de la información suministrada. Declaro bajo la gravedad del juramento que toda la información por mi afirmada al sistema PanamáEmprende en el presente proceso de Aviso de Operación, son ciertos."""
    
    story.append(Paragraph(clausula_texto, small_style))
    story.append(Spacer(1, 0.1*inch))
    
    # Nota final
    nota_final = """<b>Fundamento Legal:</b> Ley 5 de 2007 y Ley 2 de 2011.<br/>
PanamáEmprende ha avisado de la apertura del negocio a la caja del seguro social al municipio respectivo."""
    story.append(Paragraph(nota_final, small_style))
    
    # Generar PDF
    doc.build(story)
    
    print(f"PDF generado: {ruta_pdf}")
    return ruta_pdf


# ============== PROGRAMA PRINCIPAL ==============

if __name__ == "__main__":
    # Buscar por cédula
    termino = "8-237-715"
    
    print(f"Buscando: {termino}")
    empresas = consultar_empresa(termino)
    
    if not empresas:
        print("No se encontraron empresas.")
    else:
        print(f"Se encontraron {len(empresas)} empresas.\n")
        
        for i, empresa in enumerate(empresas):
            print(f"{i+1}. {empresa.get('nombreComercial')} - {empresa.get('estado')}")
        
        print("\nGenerando PDFs con diseño oficial...")
        for empresa in empresas:
            generar_pdf_oficial(empresa)
        
        print("\n¡Listo! Los PDFs están en la carpeta 'pdfs_generados'")
