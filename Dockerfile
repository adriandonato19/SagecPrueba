FROM python:3.12-slim

# Dependencias del sistema para WeasyPrint (PDF) y otras librerías
RUN apt-get update && apt-get install -y --no-install-recommends \
    # WeasyPrint
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    libffi-dev \
    shared-mime-info \
    # Fuentes
    fonts-liberation \
    fonts-dejavu-core \
    # Herramientas
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Instalar dependencias Python primero (para aprovechar caché de Docker)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

# Copiar el proyecto
COPY . .

# Crear carpetas necesarias
RUN mkdir -p staticfiles media/pdfs tramites/temp_pdfs

# Script de entrada
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/docker-entrypoint.sh"]
