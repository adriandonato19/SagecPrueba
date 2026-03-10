# 🏛️ SAGEC - Sistema Automatizado de Generación de Certificados

**Ministerio de Comercio e Industrias (MICI)**

SAGEC es una plataforma web desarrollada en **Django** diseñada para gestionar, generar, aprobar y firmar digitalmente oficios y certificaciones de empresas registradas en Panamá.

---

## 🚀 Inicio Rápido

### Requisitos Previo
- Python 3.10+
- Entorno virtual (recomendado)

### Ejecución
```bash
# 1. Activar entorno virtual
.\venv\Scripts\activate

# 2. Correr servidor
python manage.py runserver
```
Acceder en: `http://127.0.0.1:8000/`

---

## 🧠 Arquitectura del Proyecto

El proyecto sigue una arquitectura modular ("Scream Architecture") donde las carpetas principales describen **qué hace el sistema**, no qué framework usa.

### Módulos Principales (Carpetas Raíz)

#### 1. `integracion/` (El Cerebro de Datos)
Conecta con el mundo exterior (API Panamá Emprende).
- **`services.py`**: Contiene la lógica de conexión.
    - **Estrategia Triple-Fallback**: Si buscas una empresa, el sistema intenta:
        1. Búsqueda Exacta.
        2. Wildcards (`ADRIAN%DONATO`).
        3. Smart Search (palabra por palabra).
- **`adapters.py`**: Traduce el JSON "feo" de la API externa a un diccionario Python limpio y estandarizado que usa nuestro sistema.

#### 2. `tramites/` (El Corazón del Negocio)
Maneja to todo el ciclo de vida de los documentos.
- **`models.py`**: Define el `Tramite`. Tiene una **Máquina de Estados**:
    `BORRADOR` -> `PENDIENTE` -> `APROBADO` -> `FIRMADO`.
- **`services/generador_pdf.py`**: Usa **WeasyPrint** para dibujar los PDFs finales usando plantillas HTML (`tramites/templates/tramites/pdf/`).

#### 3. `identidad/` (Seguridad)
Maneja usuarios y permisos.
- Roles: `FISCAL` (Solicitante), `TRABAJADOR` (Procesador), `DIRECTOR` (Firmante).

#### 4. `auditoria/` (La Caja Negra)
Registra CADA acción importante (quién buscó qué, quién aprobó qué) en una tabla inmutable para seguridad forense.

---

## 🔍 Flujos Clave

### 1. Búsqueda de Empresa (La Lógica Inteligente)
Cuando un usuario busca en `/consultar/`:
1. El sistema llama a `integracion.services.buscar_empresa`.
2. Intenta conectar con la API Oficial.
3. Si encuentra datos, los "normaliza" (adapta) y los muestra.
4. Si el usuario decide "Crear Trámite", guarda temporalmente esos datos en la sesión para no tener que volver a consultar.

### 2. Generación de PDF
Cuando se aprueba un trámite:
1. `generador_pdf.py` toma los datos de la empresa.
2. Carga la plantilla `oficio_oficial.html`.
3. Si hay sucursales, carga `anexo_aviso.html` y lo adjunta al final.
4. Genera un solo PDF consolidado listas para firmar.

---

## 🛠️ Tecnologías Clave
- **Django**: Framework web backend.
- **HTMX**: Para interactividad en el frontend sin escribir mucho Javascript.
- **Tailwind CSS**: Para el diseño visual (clases como `bg-blue-500`).
- **WeasyPrint**: Motor de generación de PDFs.
- **Requests**: Para hablar con la API de Panamá Emprende.

---

## 📂 ¿Dónde tocar código?

- **¿Cambiar el diseño del PDF?** -> `tramites/templates/tramites/pdf/`
- **¿Cambiar la lógica de búsqueda?** -> `integracion/services.py`
- **¿Agregar campos al usuario?** -> `identidad/models.py`
- **¿Cambiar configuración (API Keys)?** -> `config/settings/base.py`
