import requests
from xhtml2pdf import pisa
import os

# ============== CONFIGURACIÓN ==============
HEADERS = {
    'X-User': 'cert',
    'X-Password': 'NlQpUjtTRlo+OTI8NnRQOV1ocjB+QVVDMS1CIm5nRnd5eTIhJVxtNyglPFtG'
}

API_URL = "https://api.panamaemprende.gob.pa/api/consulta/multiple/"

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
    """Carga la plantilla HTML"""
    with open('plantilla_aviso.html', 'r', encoding='utf-8') as f:
        return f.read()

def generar_pdf_final(empresa, output_folder="pdfs_nuevos"):
    """Genera un PDF usando xhtml2pdf con la plantilla exacta"""
    
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
    
    # Construir dirección completa
    direccion_parts = []
    if urbanizacion and urbanizacion != 'N/A':
        direccion_parts.append(f"Urbanización {urbanizacion}")
    if edificio:
        direccion_parts.append(f"edificio: {edificio}")
    if apartamento:
        direccion_parts.append(f"departamento: {apartamento}")
    direccion_completa = ", ".join(direccion_parts) if direccion_parts else "N/A"
    
    # Cargar y rellenar plantilla
    html_content = cargar_plantilla()
    
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
    
    # Generar PDF con xhtml2pdf
    with open(ruta_pdf, "wb") as pdf_file:
        pisa_status = pisa.CreatePDF(html_content, dest=pdf_file)
    
    if pisa_status.err:
        print(f"Error al generar PDF: {nombre_comercial}")
    else:
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
        
        print("\nGenerando PDFs con diseño exacto...")
        for empresa in empresas:
            generar_pdf_final(empresa)
        
        print("\n¡Listo! Los PDFs están en la carpeta 'pdfs_finales'")
