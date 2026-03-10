import requests
import pdfkit
import os
import base64
from pathlib import Path

# ============== CONFIGURACIÓN ==============
HEADERS = {
    'X-User': 'cert',
    'X-Password': 'NlQpUjtTRlo+OTI8NnRQOV1ocjB+QVVDMS1CIm5nRnd5eTIhJVxtNyglPFtG'
}

API_URL = "https://api.panamaemprende.gob.pa/api/consulta/multiple/"

# Configuración de wkhtmltopdf (ajustar ruta si es necesario)
WKHTMLTOPDF_PATH = r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe'

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

def cargar_plantilla():
    """Carga la plantilla HTML Tailwind"""
    with open('plantilla_tailwind.html', 'r', encoding='utf-8') as f:
        return f.read()

def get_logo_base64():
    """Convierte el logo a base64 para incrustarlo en el HTML"""
    logo_path = Path('logo_gobierno.png')
    if logo_path.exists():
        with open(logo_path, 'rb') as f:
            return base64.b64encode(f.read()).decode('utf-8')
    return None

def generar_pdf_tailwind(empresa, output_folder="pdfs_tailwind"):
    """Genera un PDF usando pdfkit con la plantilla Tailwind exacta"""
    
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
    provincia = empresa.get('provincia', 'N/A')
    distrito = empresa.get('distrito', 'N/A')
    corregimiento = empresa.get('corregimiento') or 'N/A'
    urbanizacion = empresa.get('urbanizacion') or 'N/A'
    calle = empresa.get('calle') or '--'
    casa = empresa.get('casa') or '--'
    edificio = empresa.get('edificio') or ''
    apartamento = empresa.get('apartamento') or ''
    monto = empresa.get('monto_estimado', 0)
    fecha_inicio = empresa.get('fecha_inicio_operaciones', 'N/A')
    telefono = empresa.get('telefono') or 'N/A'
    
    # Construir dirección completa
    direccion_parts = []
    if urbanizacion and urbanizacion != 'N/A':
        direccion_parts.append(f"Urbanización {urbanizacion}")
    if edificio:
        direccion_parts.append(f"edificio: {edificio}")
    if apartamento:
        direccion_parts.append(f"departamento: {apartamento}")
    if telefono != 'N/A':
        direccion_parts.append(f"Teléfonos {telefono}")
    direccion_completa = ", ".join(direccion_parts) if direccion_parts else "N/A"
    
    # Cargar y rellenar plantilla
    html_content = cargar_plantilla()
    
    # Convertir logo a base64 para incrustar
    logo_b64 = get_logo_base64()
    if logo_b64:
        html_content = html_content.replace(
            'src="logo_gobierno.png"',
            f'src="data:image/png;base64,{logo_b64}"'
        )
    
    # Reemplazar placeholders
    replacements = {
        '{{NUMERO_AVISO}}': numero_aviso,
        '{{NOMBRE_COMERCIAL}}': nombre_comercial,
        '{{RAZON_SOCIAL}}': razon_social,
        '{{RUC}}': ruc if ruc else cedula_rep,
        '{{CEDULA}}': cedula_rep,
        '{{REPRESENTANTE}}': representante,
        '{{PROVINCIA}}': provincia,
        '{{DISTRITO}}': distrito,
        '{{CORREGIMIENTO}}': corregimiento,
        '{{URBANIZACION}}': urbanizacion,
        '{{CALLE}}': calle,
        '{{CASA}}': casa,
        '{{EDIFICIO}}': edificio,
        '{{APARTAMENTO}}': apartamento,
        '{{CAPITAL}}': f"{monto:,.2f}",
        '{{FECHA_INICIO}}': fecha_inicio,
        '{{DIRECCION_COMPLETA}}': direccion_completa,
        '{{ACTIVIDADES}}': '(Actividades comerciales registradas según el sistema Panamá Emprende)'
    }
    
    for placeholder, value in replacements.items():
        html_content = html_content.replace(placeholder, str(value))
    
    # Nombre del archivo
    nombre_limpio = nombre_comercial.replace(' ', '_').replace('/', '_').replace(',', '').replace('.', '')[:25]
    nombre_archivo = f"{nombre_limpio}_{numero_aviso.split('-')[0]}.pdf"
    ruta_pdf = os.path.join(output_folder, nombre_archivo)
    
    # Configuración de pdfkit
    options = {
        'page-size': 'Letter',
        'margin-top': '10mm',
        'margin-right': '10mm',
        'margin-bottom': '10mm',
        'margin-left': '10mm',
        'encoding': 'UTF-8',
        'enable-local-file-access': None,
        'javascript-delay': 2000,  # Esperar a que Tailwind se cargue
        'no-stop-slow-scripts': None
    }
    
    try:
        # Intentar usar wkhtmltopdf si está instalado
        config = pdfkit.configuration(wkhtmltopdf=WKHTMLTOPDF_PATH)
        pdfkit.from_string(html_content, ruta_pdf, options=options, configuration=config)
        print(f"PDF generado: {ruta_pdf}")
    except OSError as e:
        print(f"Error: wkhtmltopdf no encontrado. Por favor instálalo desde: https://wkhtmltopdf.org/downloads.html")
        print(f"Ruta esperada: {WKHTMLTOPDF_PATH}")
        # Guardar HTML para referencia
        html_path = ruta_pdf.replace('.pdf', '.html')
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(f"HTML guardado: {html_path}")
        return None
    
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
        
        print("\nGenerando PDFs con plantilla Tailwind...")
        for empresa in empresas:
            generar_pdf_tailwind(empresa)
        
        print("\n¡Proceso completado!")
