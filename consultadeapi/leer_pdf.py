import PyPDF2

# Abrimos el PDF de referencia
pdf_path = 'aviso_operacion_Dtech_PARQUE LEFEVRE.pdf'

with open(pdf_path, 'rb') as f:
    reader = PyPDF2.PdfReader(f)
    
    print(f"Número de páginas: {len(reader.pages)}")
    print("\n" + "="*50)
    
    for i, page in enumerate(reader.pages):
        print(f"\n--- PÁGINA {i+1} ---\n")
        text = page.extract_text()
        print(text)
        
        # Guardar el texto extraído en un archivo
        with open('texto_pdf_extraido.txt', 'w', encoding='utf-8') as out:
            out.write(text)
        
        print("\n" + "="*50)
