import fitz  # PyMuPDF
import os

# Crear carpeta para las imágenes extraídas
output_folder = "imagenes_extraidas"
if not os.path.exists(output_folder):
    os.makedirs(output_folder)

# Abrir el PDF
pdf_path = "aviso_operacion_Dtech_PARQUE LEFEVRE.pdf"
doc = fitz.open(pdf_path)

print(f"Analizando: {pdf_path}")
print(f"Páginas: {len(doc)}")

# Información del documento
print("\n--- Metadatos ---")
print(doc.metadata)

# Extraer imágenes
print("\n--- Extrayendo imágenes ---")
image_count = 0

for page_num in range(len(doc)):
    page = doc[page_num]
    image_list = page.get_images()
    
    print(f"Página {page_num + 1}: {len(image_list)} imágenes encontradas")
    
    for img_index, img in enumerate(image_list):
        xref = img[0]
        base_image = doc.extract_image(xref)
        image_bytes = base_image["image"]
        image_ext = base_image["ext"]
        
        image_filename = f"{output_folder}/imagen_{page_num+1}_{img_index+1}.{image_ext}"
        
        with open(image_filename, "wb") as img_file:
            img_file.write(image_bytes)
        
        print(f"  Guardada: {image_filename}")
        image_count += 1

# También guardar la página como imagen para referencia
page = doc[0]
pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x zoom para mejor calidad
pix.save(f"{output_folder}/pagina_completa.png")
print(f"\nPágina completa guardada como: {output_folder}/pagina_completa.png")

print(f"\nTotal de imágenes extraídas: {image_count}")

# Obtener dimensiones de la página
page = doc[0]
print(f"\nDimensiones de página: {page.rect.width} x {page.rect.height} puntos")

doc.close()
